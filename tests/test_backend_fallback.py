"""Backend selection and degradation after the GitHub Models retirement.

These cover the code paths the 2026-07-31 outage ran through. GitHub Models was retired
on 2026-07-30; `models.github.ai/inference` began returning `410 Gone`, and because the
only HTTP error `main()` handled was 413, the exception escaped and killed the run. Ten
days of green collectors and no digest followed.

The retirement is not what these tests guard. Providers die; that is not preventable. What
is preventable is a dead provider taking the whole product with it, so the assertions here
are about *degradation*: a permanent failure must still publish a digest, that digest must
admit what it is, and a transient failure must still be loud rather than silently downgraded.

Run: uv run --group dev pytest tests/ -q
"""

from __future__ import annotations

import io
import json
import os
import urllib.error

import pytest

from distill import synthesize, track


def _http(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://api.example/v1/messages", code, "Gone", {}, io.BytesIO(b""))


def _prompt_with(candidates: list[dict], *, extra_blocks: bool = False) -> str:
    """A user prompt shaped like build_prompt's output: prose, optional other top-level
    JSON blocks, then the candidate array last."""
    parts = ["Some instructions.\n"]
    if extra_blocks:
        parts.append("\nMOVERS since the previous run:\n")
        parts.append(json.dumps([{"id": "mover:1", "title": "A mover"}], indent=2))
        parts.append("\n\nSTORY ARCS:\n")
        parts.append(json.dumps([{"id": "arc:1", "runs": 3}], indent=2))
        parts.append("\n\n")
    parts.append("\n" + json.dumps(candidates, indent=2))
    return "".join(parts)


_CAND = [{
    "title": "A Paper", "category": "research", "url": "https://arxiv.org/abs/1",
    "source": "arXiv", "score": 4, "hf_upvotes": 12, "summary": "A summary.",
    "reasons": ["strong traction"],
}]


# --- candidate extraction --------------------------------------------------

def test_extract_candidates_with_only_the_candidate_array():
    assert synthesize.extract_candidates(_prompt_with(_CAND)) == _CAND


def test_extract_candidates_skips_earlier_json_blocks():
    """The regression that made the template backend useless. With MOVERS and arcs also
    present, a greedy `\\[.*\\]` span runs from the first block to the last and decodes as
    nothing. Every test fixture had a quiet window (empty delta, one array), so it passed
    in CI and failed on real data."""
    got = synthesize.extract_candidates(_prompt_with(_CAND, extra_blocks=True))
    assert got == _CAND


def test_extract_candidates_survives_brackets_inside_titles():
    """Titles routinely carry brackets ('[2607.12345] Thing'). A bracket-counting scanner
    would mis-balance on them; decoding is what makes this safe."""
    cand = [{**_CAND[0], "title": "[2607.12345] Brackets ] and [ inside"}]
    assert synthesize.extract_candidates(_prompt_with(cand, extra_blocks=True)) == cand


def test_extract_candidates_returns_none_when_absent():
    assert synthesize.extract_candidates("no json here at all") is None


def test_template_digest_reports_extraction_failure_loudly():
    """The floor of the fallback chain. If it silently emitted an empty digest, a broken
    extractor would look like a quiet news day forever."""
    out = synthesize.call_template("sys", "no json here")
    assert "Template Error" in out
    assert "extract_candidates" in out


def test_template_digest_renders_real_items():
    out = synthesize.call_template("sys", _prompt_with(_CAND, extra_blocks=True))
    assert "A Paper" in out
    assert "12 HF upvotes" in out
    assert "Template Error" not in out


# --- backend resolution ----------------------------------------------------

def test_auto_prefers_anthropic_when_a_key_exists():
    assert synthesize.resolve_backend("auto", {"ANTHROPIC_API_KEY": "sk-x"})[0] == "anthropic"


def test_auto_falls_back_to_template_without_a_key():
    backend, note = synthesize.resolve_backend("auto", {})
    assert backend == "template"
    assert "ANTHROPIC_API_KEY" in note


def test_retired_github_backend_redirects_rather_than_failing():
    """Hard-failing on `github` would break every existing config at once — distill.yml,
    the README, anyone's shell — which is the outage again by a different route."""
    backend, note = synthesize.resolve_backend("github", {})
    assert backend == "template"
    assert "retired" in note

    backend, note = synthesize.resolve_backend("github", {"ANTHROPIC_API_KEY": "sk-x"})
    assert backend == "anthropic"
    assert "retired" in note


def test_explicit_backends_pass_through_untouched():
    for name in ("anthropic", "ollama", "template", "dryrun"):
        assert synthesize.resolve_backend(name, {}) == (name, None)


# --- degradation on backend failure ---------------------------------------

@pytest.fixture
def anthropic_backend(monkeypatch):
    monkeypatch.setattr(synthesize, "BACKEND", "anthropic")


@pytest.mark.parametrize("code", sorted(synthesize.PERMANENT_HTTP))
def test_permanent_http_errors_degrade_instead_of_raising(code, anthropic_backend, monkeypatch):
    """This is the whole fix. Any of these used to escape main() and end the run."""
    def boom(system, user):
        raise _http(code)

    monkeypatch.setattr(synthesize, "call_anthropic", boom)
    out = synthesize.synthesize_with_fallback([], "sys", _prompt_with(_CAND), 1)

    assert "Degraded run" in out
    assert str(code) in out
    assert "A Paper" in out          # the template digest still rendered underneath


def test_degraded_digest_names_itself_as_unsynthesized(anthropic_backend, monkeypatch):
    """`X2 instrument_honesty`: a reader must be able to tell an assembled list from a
    written brief. Shipping the former under the latter's name is the failure the rubric
    exists to catch, and it would be invisible to everything except a human reading it."""
    monkeypatch.setattr(synthesize, "call_anthropic", lambda s, u: (_ for _ in ()).throw(_http(410)))
    out = synthesize.synthesize_with_fallback([], "sys", _prompt_with(_CAND), 1)

    assert "no model synthesis" in out.lower()
    assert out.lstrip().startswith(">")        # renders as a blockquote notice, first thing


def test_unreachable_backend_degrades(anthropic_backend, monkeypatch):
    """DNS failure and a retired host are indistinguishable at this layer, and neither is
    worth losing the digest over."""
    def boom(system, user):
        raise urllib.error.URLError("nodename nor servname provided")

    monkeypatch.setattr(synthesize, "call_anthropic", boom)
    out = synthesize.synthesize_with_fallback([], "sys", _prompt_with(_CAND), 1)
    assert "Degraded run" in out


def test_transient_server_errors_still_raise(anthropic_backend, monkeypatch):
    """A 500 or 429 is the provider having a bad minute. Degrading on those would quietly
    swap a retry for a worse digest and hide a problem worth seeing."""
    monkeypatch.setattr(synthesize, "call_anthropic", lambda s, u: (_ for _ in ()).throw(_http(500)))
    with pytest.raises(urllib.error.HTTPError):
        synthesize.synthesize_with_fallback([], "sys", _prompt_with(_CAND), 1)


def test_success_returns_the_model_output_untouched(anthropic_backend, monkeypatch):
    monkeypatch.setattr(synthesize, "call_anthropic", lambda s, u: "# A real synthesized digest")
    out = synthesize.synthesize_with_fallback([], "sys", _prompt_with(_CAND), 1)
    assert out == "# A real synthesized digest"
    assert "Degraded" not in out


def test_413_exhausts_the_shrink_ladder_then_degrades(anthropic_backend, monkeypatch):
    """413 keeps its retry ladder — the payload really can be too big — but running out of
    shrinks now degrades rather than re-raising the last error."""
    calls = []

    def always_too_large(system, user):
        calls.append(user)
        raise _http(413)

    monkeypatch.setattr(synthesize, "call_anthropic", always_too_large)
    monkeypatch.setattr(synthesize, "build_prompt",
                        lambda items, **kw: ("sys", _prompt_with(_CAND), 1))
    out = synthesize.synthesize_with_fallback([], "sys", _prompt_with(_CAND), 1)

    assert len(calls) == 5           # every rung tried before giving up
    assert "Degraded run" in out
    assert "413" in out


# --- local runs must not destroy committed state ---------------------------

def test_no_state_env_stops_the_ledger_write(tmp_path, monkeypatch):
    """README tells you to run scripts/distill.sh locally, and re-observation drops an item
    after three unreachable fetches — so one run behind a proxy silently deletes most of the
    committed ledger. Verified against a real run: 13 items dropped, 297 lines gone."""
    ledger_file = tmp_path / "tracked.json"
    monkeypatch.setattr(track, "LEDGER", ledger_file)
    monkeypatch.setenv("RADAR_NO_STATE", "1")

    track.save_ledger({"item:1": {"streak": 2}})
    assert not ledger_file.exists()


def test_ledger_writes_normally_without_the_env(tmp_path, monkeypatch):
    ledger_file = tmp_path / "tracked.json"
    monkeypatch.setattr(track, "LEDGER", ledger_file)
    monkeypatch.delenv("RADAR_NO_STATE", raising=False)

    track.save_ledger({"item:1": {"streak": 2}})
    assert json.loads(ledger_file.read_text()) == {"item:1": {"streak": 2}}


def test_explicit_path_always_writes(tmp_path, monkeypatch):
    """Test fixtures pass an explicit path and must keep working — that path is already
    pointed somewhere disposable, so the guard would only get in the way."""
    monkeypatch.setenv("RADAR_NO_STATE", "1")
    target = tmp_path / "explicit.json"

    track.save_ledger({"item:1": {}}, path=target)
    assert target.exists()
