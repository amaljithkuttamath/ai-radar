"""A 200 is not a digest — validating what the model actually returned.

On 2026-08-14, 2026-08-25 and 2026-09-18 the newsletter that shipped was the model's own
planning notes: ~13KB opening "Let me analyze this task carefully", truncated mid-sentence,
no title, no sections. Three times in six weeks, published to `reports/` and to the board,
and nobody noticed until a deterministic structure check went looking months later.

Nothing in the pipeline was broken in the usual sense. The request succeeded. The shrink
ladder and the permanent-HTTP degradation both worked exactly as designed. The gap was
that every one of those defences asks whether the *request* succeeded, and none asked
whether the *answer* did.

Root cause: `max_tokens` was 4000, sized for a model that answers directly, while the
pipeline had moved to whatever free model the catalogue offers — increasingly a reasoning
model that spends thousands of tokens thinking first. The budget ran out before the digest
began, and `finish_reason: length` was discarded.

Run: uv run --group dev pytest tests/test_synthesize_output.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Deliberately does NOT set RADAR_MODEL_BACKEND. `distill.synthesize` reads it at import
# time, so setting it here would leak process-wide into every other test module — which it
# did, making the separation fence see a template backend ("nothing to be separate from")
# and silently pass a test that exists to prove it refuses. `usable_digest` is pure and
# needs no backend.

import llm  # noqa: E402
from distill import synthesize  # noqa: E402
from grader import deterministic  # noqa: E402

GOOD = """\
# AI Radar — 2026-09-20

**Top-line:** Something happened.

## What changed

- [A thing](https://example.com/a)

## Main list

### 1. First item · 4/5
Body.
"""


def _digests() -> list[Path]:
    return sorted((ROOT / "reports").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-digest.md"))


# The four digests that actually shipped broken. Named, because a test that says "some
# digests are bad" cannot tell you when a fix stops working.
BROKEN = {
    "2026-08-14-digest.md",     # reasoning transcript, truncated mid-sentence
    "2026-08-25-digest.md",     # reasoning transcript, truncated mid-sentence
    "2026-09-18-digest.md",     # reasoning transcript, truncated mid-sentence
    "2026-09-14-digest.md",     # title and one paragraph, nothing else
}


# --- refusing what actually shipped -----------------------------------------

@pytest.mark.parametrize("name", sorted(BROKEN))
def test_the_digests_that_shipped_broken_are_refused(name):
    raw = (ROOT / "reports" / name).read_text()
    with pytest.raises(synthesize.NotADigest):
        synthesize.usable_digest(raw)


def test_every_healthy_digest_is_still_accepted():
    """The boundary matters in both directions. A validator that refuses good digests
    trades three bad days for eighty-five, which is a worse bug than the one it fixes."""
    refused = []
    for path in _digests():
        if path.name in BROKEN:
            continue
        try:
            synthesize.usable_digest(path.read_text())
        except synthesize.NotADigest as why:
            refused.append(f"{path.name}: {why}")
    assert refused == []


def test_the_validator_and_the_grader_agree_on_which_digests_are_broken():
    """Two checks written independently — one guarding what gets published, one grading
    what was — must not disagree about what a digest is. They duplicate this knowledge
    because `grader/` may not import `distill/` (ADR-0007), so the pairing is asserted
    rather than assumed, exactly as the duplicated DEGRADED_MARKER is."""
    by_validator = set()
    by_grader = set()
    for path in _digests():
        text = path.read_text()
        try:
            synthesize.usable_digest(text)
        except synthesize.NotADigest:
            by_validator.add(path.name)
        result = deterministic.evaluate(text, age_h=1.0, broken=[], link_count=5,
                                        tracked={})
        if "structure" in result["failed"]:
            by_grader.add(path.name)
    assert by_validator == by_grader == BROKEN


# --- recovering what can be recovered ---------------------------------------

def test_a_reasoning_block_is_stripped():
    """Reasoning models tag their working. The digest after it is perfectly good, and
    losing the day over a preamble would be its own bug."""
    assert synthesize.usable_digest(
        "<think>I should start by reviewing the candidates...</think>\n\n" + GOOD
    ).startswith("# AI Radar")


@pytest.mark.parametrize("tag", ["think", "thinking", "reasoning", "scratchpad"])
def test_every_reasoning_tag_spelling_is_stripped(tag):
    raw = f"<{tag}>working</{tag}>\n\n{GOOD}"
    assert synthesize.usable_digest(raw).startswith("# AI Radar")


def test_prose_before_the_title_is_dropped():
    """The three that shipped had no digest at all, but models routinely narrate first and
    then answer. That case is recoverable and must be recovered."""
    raw = ("Let me analyze this task carefully. I need to produce a digest.\n"
           "Key parameters: WINDOW=48h.\n\n" + GOOD)
    out = synthesize.usable_digest(raw)
    assert out.startswith("# AI Radar")
    assert "Let me analyze" not in out


def test_an_unclosed_reasoning_block_discards_everything_after_it():
    """An opener with no closer means the response was cut off mid-thought. What follows
    is working, not output."""
    with pytest.raises(synthesize.NotADigest):
        synthesize.usable_digest("<think>still thinking about the ranking")


def test_a_clean_digest_passes_through_unchanged():
    assert synthesize.usable_digest(GOOD) == GOOD.strip()


def test_bold_section_labels_are_accepted():
    """2026-06-04 and 2026-06-11 are legitimate quiet-window digests that label sections in
    bold. Refusing those would trade three bad digests for two good ones."""
    quiet = "# AI Radar — 2026-06-04\n\nQuiet window.\n\n**Main list**\n\nNothing today.\n"
    assert synthesize.usable_digest(quiet).startswith("# AI Radar")


# --- refusing the shapes that are not recoverable ---------------------------

def test_a_transcript_with_no_title_is_refused():
    raw = ("Let me analyze this task carefully. I need to produce a digest report.\n"
           "Key parameters:\n- TODAY = 2026-09-18\n" * 30)
    with pytest.raises(synthesize.NotADigest, match="reasoning transcript"):
        synthesize.usable_digest(raw)


def test_a_title_with_no_sections_is_refused():
    with pytest.raises(synthesize.NotADigest, match="cut off"):
        synthesize.usable_digest("# AI Radar — 2026-09-14\n\n**Top-line.** One para.\n")


def test_an_empty_response_is_refused():
    with pytest.raises(synthesize.NotADigest):
        synthesize.usable_digest("   \n\n  ")


def test_the_check_is_shape_based_not_phrase_based():
    """Matching "Let me analyze" would catch the three known transcripts and nothing else.
    A digest that happens to quote the phrase is still a digest."""
    quoting = GOOD + "\n## Insights\n\n- One model began its answer 'Let me analyze'.\n"
    assert synthesize.usable_digest(quoting).startswith("# AI Radar")


# --- truncation is surfaced, not swallowed ----------------------------------

def test_finish_reason_length_raises_truncated(monkeypatch):
    """`finish_reason: length` is the provider stating plainly that it stopped early. It
    used to be discarded, which is how a cut-off response passed for an answer."""
    import json as _json

    class _Resp:
        def read(self):
            return _json.dumps({"choices": [{"finish_reason": "length",
                                             "message": {"content": "half a thoug"}}]}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setenv("RADAR_LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("RADAR_LLM_API_KEY", "k")
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda *a, **kw: _Resp())

    with pytest.raises(llm.Truncated) as caught:
        llm.chat("s", "u", "some/model")
    assert caught.value.partial == "half a thoug"


def test_truncated_is_an_llm_error_so_existing_handlers_still_work():
    assert issubclass(llm.Truncated, llm.LLMError)


def test_a_complete_response_does_not_raise(monkeypatch):
    import json as _json

    class _Resp:
        def read(self):
            return _json.dumps({"choices": [{"finish_reason": "stop",
                                             "message": {"content": GOOD}}]}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setenv("RADAR_LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("RADAR_LLM_API_KEY", "k")
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda *a, **kw: _Resp())
    assert llm.chat("s", "u", "some/model") == GOOD


def test_the_token_ceiling_is_the_same_on_both_call_paths():
    """The native Anthropic caller does not go through `llm.chat`, so a digest budget that
    depends on which caller you took would produce this bug again on a provider switch."""
    src = (ROOT / "distill" / "synthesize.py").read_text()
    assert '"max_tokens": llm.MAX_TOKENS' in src
    assert llm.MAX_TOKENS >= 8000, "too small for a reasoning model to think and answer"
