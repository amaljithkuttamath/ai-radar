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

def _catalogue(*entries):
    """(id, context_length, free) -> catalogue rows in the provider's shape."""
    return [{"id": i, "context_length": ctx,
             "pricing": {"prompt": "0", "completion": "0"} if free
             else {"prompt": "0.0000009", "completion": "0.000002"}}
            for i, ctx, free in entries]


def test_resolve_pair_picks_two_different_families(monkeypatch):
    """The property that makes a single account viable — now derived from the live
    catalogue rather than a hardcoded pair, because free variants carry provider-specific
    suffixes that cannot be guessed correctly ahead of time."""
    monkeypatch.setattr(llm, "catalog", lambda: _catalogue(
        ("meta-llama/llama-3.3-70b-instruct:free", 131072, True),
        ("meta-llama/llama-3.1-8b-instruct:free", 131072, True),
        ("deepseek/deepseek-v3:free", 64000, True),
    ))
    pair = llm.resolve_pair()
    assert set(pair) == set(llm.ROLES)
    assert llm.family(pair[llm.SYNTHESIS]) != llm.family(pair[llm.GRADER])


def test_resolve_pair_excludes_paid_models_by_default(monkeypatch):
    """A "free tier" setup that quietly picks a metered model is worse than one that
    fails: the bill is the first thing that tells you."""
    monkeypatch.setattr(llm, "catalog", lambda: _catalogue(
        ("google/gemini-2.5-pro", 1000000, False),
        ("meta-llama/llama-3.3-70b-instruct:free", 131072, True),
        ("deepseek/deepseek-v3:free", 64000, True),
    ))
    assert "google/gemini-2.5-pro" not in llm.resolve_pair().values()
    assert "google/gemini-2.5-pro" in llm.resolve_pair(free_only=False).values()


def test_resolve_pair_is_deterministic(monkeypatch):
    """A pinned config must stay reproducible: the same catalogue always yields the
    same pair, so re-running --resolve doesn't silently move you to another model."""
    rows = _catalogue(("a/qwen-3:free", 64000, True), ("b/llama-3:free", 64000, True))
    monkeypatch.setattr(llm, "catalog", lambda: rows)
    assert llm.resolve_pair() == llm.resolve_pair()


def test_resolve_pair_reports_a_single_family_catalogue(monkeypatch):
    """Returns fewer roles than exist rather than filling the grader with a sibling of
    the synthesis model — the CLI turns that into an error naming the real fix."""
    monkeypatch.setattr(llm, "catalog", lambda: _catalogue(
        ("meta-llama/llama-3.3-70b:free", 131072, True),
        ("meta-llama/llama-3.1-8b:free", 131072, True),
    ))
    assert len(llm.resolve_pair()) < len(llm.ROLES)


@pytest.mark.parametrize("model,expected", [
    ({"pricing": {"prompt": "0", "completion": "0"}}, True),
    ({"pricing": {"prompt": "0.0000009", "completion": "0"}}, False),
    ({"pricing": {}}, False),
    ({}, False),
    ({"pricing": {"prompt": "free", "completion": "free"}}, False),
])
def test_is_free(model, expected):
    """Absent or unparsable pricing reads as NOT free. Assuming free because a field is
    missing is how a free-tier configuration quietly starts billing."""
    assert llm.is_free(model) is expected


def test_every_profile_default_is_a_recognised_family():
    """A default the fence cannot classify would refuse at runtime — catch it here."""
    for marker, roles in llm._PROFILES.items():
        for role, model in roles.items():
            if model:
                assert llm.family(model) is not None, f"{marker}:{role} -> {model!r}"


def test_openrouter_ships_no_guessed_ids():
    """Its free variants carry a `:free` suffix while the bare id is metered, so any
    hardcoded default is a 402 that degrades to template and reads like the pipeline
    is still broken. `--resolve` reads the live catalogue instead."""
    assert llm._PROFILES["openrouter.ai"] == {llm.SYNTHESIS: "", llm.GRADER: ""}


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
