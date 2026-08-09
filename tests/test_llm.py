"""The shared provider layer.

The property under test is the one that made unification safe: **separation is a
property of the model, not the account**. Both stages can run through one key and one
endpoint as long as the models they name come from different families — so these tests
check family detection and role selection carefully, and check that a provider which
cannot offer two families says so rather than quietly serving one.

Run: uv run --group dev pytest tests/ -q
"""

from __future__ import annotations

import urllib.error

import pytest

import llm


# --- family detection ------------------------------------------------------

@pytest.mark.parametrize("model,expected", [
    # bare ids
    ("claude-opus-5", "anthropic"),
    ("gpt-4.1", "openai"),
    ("gemini-2.5-pro", "google"),
    ("llama-3.3-70b-versatile", "meta"),
    ("qwen3:4b", "alibaba"),
    ("sonar-pro", "perplexity"),
    ("deepseek-v3", "deepseek"),
    # gateway `vendor/model` form — the shape one common provider actually serves
    ("anthropic/claude-sonnet-5", "anthropic"),
    ("meta-llama/llama-3.3-70b-instruct", "meta"),
    ("google/gemini-2.5-pro", "google"),
    ("x-ai/grok-3", "xai"),
    ("mistralai/mistral-large", "mistral"),
])
def test_family_detection(model, expected):
    assert llm.family(model) == expected


def test_unknown_model_has_no_family():
    """None is a refusal signal, not a default. `assert_separated` turns it into a
    hard failure — a fence that opens on the unfamiliar is not a fence."""
    assert llm.family("brand-new-model-9000") is None
    assert llm.family("") is None


def test_vendor_prefix_wins_over_substring():
    """`anthropic/claude-…` must resolve by its prefix, not by scanning for a hint that
    happens to appear later in the slug."""
    assert llm.family("anthropic/some-unreleased-thing") == "anthropic"


# --- role selection --------------------------------------------------------

def test_one_provider_yields_two_families(monkeypatch):
    """The property that makes a single account viable: a gateway's default pair spans
    two families, so a bare key+URL is a separated configuration with no model choice
    made by the operator."""
    monkeypatch.setenv("RADAR_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.delenv("RADAR_SYNTHESIS_MODEL", raising=False)
    monkeypatch.delenv("RADAR_GRADER_MODEL", raising=False)

    synth = llm.family(llm.model_for(llm.SYNTHESIS))
    grader = llm.family(llm.model_for(llm.GRADER))
    assert synth and grader
    assert synth != grader


def test_every_profile_default_is_a_recognised_family():
    """A default the fence cannot classify would refuse at runtime — catch it here."""
    for marker, roles in llm._PROFILES.items():
        for role, model in roles.items():
            if model:
                assert llm.family(model) is not None, f"{marker}:{role} -> {model!r}"


def test_single_family_providers_leave_the_grader_unset():
    """Perplexity serves only `sonar`; Groq and Google AI Studio are effectively one
    family each. Rather than pretend, the profile leaves the grader role empty so the
    caller raises a message naming the real fix instead of grading with a sibling."""
    for marker in ("api.perplexity.ai", "api.groq.com", "generativelanguage.googleapis.com"):
        assert llm._PROFILES[marker][llm.GRADER] == ""


def test_explicit_override_beats_the_profile(monkeypatch):
    monkeypatch.setenv("RADAR_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("RADAR_GRADER_MODEL", "x-ai/grok-3")
    assert llm.model_for(llm.GRADER) == "x-ai/grok-3"


def test_unknown_provider_has_no_defaults(monkeypatch):
    monkeypatch.setenv("RADAR_LLM_BASE_URL", "https://llm.internal.example/v1")
    monkeypatch.delenv("RADAR_SYNTHESIS_MODEL", raising=False)
    assert llm.model_for(llm.SYNTHESIS) == ""


def test_shared_key_falls_back_to_the_legacy_variable(monkeypatch):
    """Configurations written before the providers were unified keep working."""
    monkeypatch.delenv("RADAR_LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-legacy")
    assert llm.api_key() == "sk-legacy"


# --- the call --------------------------------------------------------------

def test_chat_refuses_without_a_model(monkeypatch):
    """The empty-model case is a real state (single-family provider, grader role), and
    the message has to name the fix rather than fail obscurely deep in urllib."""
    monkeypatch.setenv("RADAR_LLM_BASE_URL", "https://api.perplexity.ai")
    monkeypatch.setenv("RADAR_LLM_API_KEY", "k")
    with pytest.raises(llm.LLMError, match="--catalog"):
        llm.chat("sys", "user", "")


def test_chat_refuses_without_configuration(monkeypatch):
    monkeypatch.delenv("RADAR_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("RADAR_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(llm.LLMError, match="RADAR_LLM_BASE_URL"):
        llm.chat("sys", "user", "meta-llama/llama-3.3-70b-instruct")


def test_http_errors_propagate_unwrapped(monkeypatch):
    """`distill.synthesize` classifies permanent (410/401/404) vs transient (5xx) by
    status code. Wrapping HTTPError in LLMError would erase that distinction and make a
    dead provider look like a retryable blip — the exact failure the 2026-07 outage was."""
    monkeypatch.setenv("RADAR_LLM_BASE_URL", "https://x.test/v1")
    monkeypatch.setenv("RADAR_LLM_API_KEY", "k")

    def boom(*a, **kw):
        raise urllib.error.HTTPError("https://x.test/v1", 410, "Gone", {}, None)

    monkeypatch.setattr(llm.urllib.request, "urlopen", boom)
    with pytest.raises(urllib.error.HTTPError) as caught:
        llm.chat("sys", "user", "meta-llama/llama-3.3-70b-instruct")
    assert caught.value.code == 410


def test_unreachable_provider_raises_llm_error(monkeypatch):
    monkeypatch.setenv("RADAR_LLM_BASE_URL", "https://x.test/v1")
    monkeypatch.setenv("RADAR_LLM_API_KEY", "k")

    def boom(*a, **kw):
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(llm.urllib.request, "urlopen", boom)
    with pytest.raises(llm.LLMError, match="unreachable"):
        llm.chat("sys", "user", "meta-llama/llama-3.3-70b-instruct")


def test_describe_never_leaks_the_key(monkeypatch):
    monkeypatch.setenv("RADAR_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("RADAR_LLM_API_KEY", "sk-or-supersecret")
    out = llm.describe()
    assert "supersecret" not in out
    assert "openrouter.ai" in out
