"""Tests for runtime model resolution — the grader picking its own model.

Why this exists. Every `_PROFILES` entry ships `GRADER: ""`, because no provider can
promise a second model family will still be free and un-throttled tomorrow. The
consequence was that the grader had no model unless a human pinned one by hand, and for 69
days nobody did — which is the outage, stated as a configuration fact rather than a story.

The test at the bottom is the one that matters: it stands up a real OpenAI-compatible
server on localhost and drives the whole path — catalogue read, free filter, family
exclusion, separation fence, model call, judged eval — with nothing stubbed but the
provider. Every unit test above it is a way of asking how that path fails.

Run: uv run --group dev pytest tests/test_auto_model.py -q
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import llm  # noqa: E402
# Bound before conftest's autouse fixture replaces the module attribute.
from llm import auto_model as real_auto_model  # noqa: E402


def _model(mid, *, free=True, ctx=8000):
    pricing = {"prompt": "0", "completion": "0"} if free else \
              {"prompt": "0.000002", "completion": "0.000004"}
    return {"id": mid, "context_length": ctx, "pricing": pricing}


CATALOGUE = [
    _model("nvidia/nemotron-3-ultra:free", ctx=128000),
    _model("deepseek/deepseek-v3:free", ctx=64000),
    _model("anthropic/claude-sonnet-5", free=False, ctx=200000),
    _model("some-vendor/unknown-model-9000:free", ctx=999000),
]

ENV = {"RADAR_LLM_BASE_URL": "https://openrouter.ai/api/v1",
       "RADAR_LLM_API_KEY": "sk-test"}


@pytest.fixture(autouse=True)
def _clear_cache():
    llm._AUTO_CACHE.clear()
    yield
    llm._AUTO_CACHE.clear()


@pytest.fixture
def served(monkeypatch):
    """Serve CATALOGUE from `llm.catalog` without a network."""
    monkeypatch.setattr(llm, "catalog", lambda env=None, timeout=30: list(CATALOGUE))


# --- choosing ---------------------------------------------------------------

def test_the_grader_resolves_a_model_when_none_is_pinned(served):
    """The whole point: a provider that promises no grader default stops meaning no
    grader."""
    assert real_auto_model(llm.GRADER, ENV) == "nvidia/nemotron-3-ultra:free"


def test_resolution_avoids_the_pinned_synthesis_family(served):
    """A resolved grader must not collide with the digest's actual author. Panickssery et
    al. (2024) measured what a same-family judge does to its own family's output."""
    env = {**ENV, "RADAR_SYNTHESIS_MODEL": "nvidia/nemotron-3-ultra:free"}
    got = real_auto_model(llm.GRADER, env)
    assert got == "deepseek/deepseek-v3:free"
    assert llm.family(got) != llm.family(env["RADAR_SYNTHESIS_MODEL"])


def test_metered_models_are_never_chosen_by_default(served):
    """OpenRouter's free variants carry `:free` while the bare id is metered, so picking a
    plausible-looking id is a 402 that degrades to a template digest and reads exactly like
    the pipeline still being broken."""
    env = {**ENV, "RADAR_SYNTHESIS_MODEL": "nvidia/nemotron-3-ultra:free"}
    for _ in range(2):
        assert "claude" not in real_auto_model(llm.GRADER, env)


def test_metered_models_can_be_opted_into(served):
    """Ranked by context length, the metered Claude wins once allowed."""
    env = {**ENV, "RADAR_ALLOW_METERED": "1",
           "RADAR_SYNTHESIS_MODEL": "nvidia/nemotron-3-ultra:free"}
    assert real_auto_model(llm.GRADER, env) == "anthropic/claude-sonnet-5"


def test_an_unrecognised_family_is_skipped_not_chosen(served):
    """It has the largest context window in the catalogue, so only the family check keeps
    it out. The fence would refuse it anyway (ADR-0007), and choosing it here would produce
    a confusing refusal about a model nobody selected."""
    assert "unknown-model-9000" not in real_auto_model(llm.GRADER, ENV)


def test_resolution_is_deterministic(served):
    assert real_auto_model(llm.GRADER, ENV) == real_auto_model(llm.GRADER, ENV)


# --- refusing ---------------------------------------------------------------

def test_no_second_family_resolves_to_empty(monkeypatch):
    """Empty is the honest answer, and since ADR-0009 it degrades to a tier-0 eval rather
    than halting. That composition is what makes attempting this responsible at all."""
    monkeypatch.setattr(llm, "catalog",
                        lambda env=None, timeout=30: [_model("nvidia/a:free")])
    env = {**ENV, "RADAR_SYNTHESIS_MODEL": "nvidia/nemotron-3-ultra:free"}
    assert real_auto_model(llm.GRADER, env) == ""


def test_an_unreachable_catalogue_is_not_fatal(monkeypatch):
    def boom(env=None, timeout=30):
        raise llm.LLMError("could not read catalogue")
    monkeypatch.setattr(llm, "catalog", boom)
    assert real_auto_model(llm.GRADER, ENV) == ""


def test_resolution_is_skipped_without_a_configured_provider(served):
    assert real_auto_model(llm.GRADER, {}) == ""


def test_resolution_can_be_switched_off(served):
    assert real_auto_model(llm.GRADER, {**ENV, "RADAR_AUTO_MODEL": "0"}) == ""


# --- it never overrides a choice someone made -------------------------------

def test_a_pinned_model_is_never_replaced(served):
    env = {**ENV, "RADAR_GRADER_MODEL": "openai/gpt-4.1"}
    assert llm.model_for(llm.GRADER, env) == "openai/gpt-4.1"


def test_a_profile_default_is_never_replaced(served):
    """Groq ships a synthesis default; auto-resolution must not move it."""
    env = {"RADAR_LLM_BASE_URL": "https://api.groq.com/openai/v1",
           "RADAR_LLM_API_KEY": "k"}
    assert llm.model_for(llm.SYNTHESIS, env) == "llama-3.3-70b-versatile"


def test_pinned_model_never_consults_the_catalogue(monkeypatch):
    """`auto_model` asks for the other role's family, and if it asked `model_for` it could
    trigger the other role's resolution, which would ask back. `pinned_model` is the
    recursion-free answer and must stay that way."""
    def boom(env=None, timeout=30):
        raise AssertionError("pinned_model must never read the catalogue")
    monkeypatch.setattr(llm, "catalog", boom)
    assert llm.pinned_model(llm.GRADER, ENV) == ""


# --- end to end, against a real server --------------------------------------

class _Provider(BaseHTTPRequestHandler):
    """A minimal OpenAI-compatible provider: `/models` and `/chat/completions`."""

    verdict = json.dumps({
        **{d: {"score": 4, "why": "cites the LynnReal-Omni item explicitly"}
           for d in ("A1", "A2", "A3", "A4", "A5", "X1", "X2", "X4", "X5")},
        "missed_stories": [],
    })

    def _send(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.endswith("/models"):
            return self._send({"data": CATALOGUE})
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self._send({"choices": [{"message": {"content": self.verdict}}]})

    def log_message(self, *a):        # keep pytest output readable
        pass


@pytest.fixture
def provider():
    server = HTTPServer(("127.0.0.1", 0), _Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def test_an_unconfigured_grader_grades_anyway(provider, monkeypatch):
    """The end-to-end claim, with nothing stubbed but the provider itself.

    `RADAR_GRADER_MODEL` is unset — the exact configuration that produced no eval for 69
    days. The grader reads the catalogue, skips the metered and unrecognised entries,
    picks a family different from the pinned synthesis model, passes the separation fence,
    calls the model, and returns a parsed verdict.
    """
    from grader import judge

    monkeypatch.setenv("RADAR_LLM_BASE_URL", provider)
    monkeypatch.setenv("RADAR_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("RADAR_SYNTHESIS_MODEL", "nvidia/nemotron-3-ultra:free")
    monkeypatch.delenv("RADAR_GRADER_MODEL", raising=False)
    monkeypatch.setattr(llm, "auto_model", real_auto_model)
    llm._AUTO_CACHE.clear()

    verdict, model = judge.judge("# AI Radar — 2026-09-19\n\nbody", "rubric", 12.0, [])

    assert model == "deepseek/deepseek-v3:free"          # not nvidia: the fence's whole job
    assert llm.family(model) != llm.family("nvidia/nemotron-3-ultra:free")
    assert verdict["A1"]["score"] == 4
    assert set(judge.JUDGED_DIMS) <= set(verdict)


def test_the_fence_still_refuses_a_colliding_resolution(provider, monkeypatch):
    """Auto-resolution never replaces the fence. Forced to a colliding model, the run still
    refuses — resolution only stops handing the fence an empty string."""
    from grader import judge
    from grader.separation import SeparationViolation

    monkeypatch.setenv("RADAR_LLM_BASE_URL", provider)
    monkeypatch.setenv("RADAR_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("RADAR_SYNTHESIS_MODEL", "nvidia/nemotron-3-ultra:free")
    monkeypatch.setenv("RADAR_GRADER_MODEL", "nvidia/nemotron-3-ultra:free")

    with pytest.raises(SeparationViolation, match="nvidia"):
        judge.judge("# AI Radar — 2026-09-19\n\nbody", "rubric", 12.0, [])
