"""Scoring, ranking and FOCUS matching — the deterministic core that decides what a reader
ever gets shown. All stdlib-only paths, so these run anywhere."""
from __future__ import annotations

import pytest

from distill.score import heuristic_score
from distill.rank import rank_key, magnitude
from distill import focus
from tests.conftest import make_item


# ---------------------------------------------------------------------------
# heuristic_score
# ---------------------------------------------------------------------------

def test_score_leaves_the_novelty_point_to_the_model():
    """The heuristic covers 0–4; +1 for novelty is the model's to give (see digest.md)."""
    loud = make_item(
        title="DeepMind: state-of-the-art results, outperforms prior work",
        raw_summary="code at github.com/acme/widget",
        signals={"hf_upvotes": 200, "gh_stars": 5000, "hn_points": 900},
    )
    score, _ = heuristic_score(loud)
    assert score == 4


def test_score_floor_is_zero_for_an_unremarkable_item(no_profile):
    score, why = heuristic_score(make_item(
        title="Some notes on a thing", url="https://example.com/x",
        raw_summary="", source="Example Blog", signals={}))
    assert score == 0 and why == []


@pytest.mark.parametrize("signals,expected_tiers", [
    ({"gh_stars": 10}, 0),      # below the trending floor
    ({"gh_stars": 50}, 1),      # trending
    ({"gh_stars": 80}, 2),      # trending + strong traction
])
def test_traction_tiers(signals, expected_tiers):
    item = make_item(title="acme/widget", url="https://example.com/x",
                     raw_summary="", source="s", signals=signals)
    _, why = heuristic_score(item)
    assert sum("Tier-2" in w for w in why) == expected_tiers


def test_a_linked_repo_is_reported_as_such():
    _, why = heuristic_score(make_item(links={"github": "https://github.com/acme/widget"}))
    assert "usable artifact (repo linked)" in why


# ---------------------------------------------------------------------------
# rank_key / magnitude
# ---------------------------------------------------------------------------

def test_rank_tiebreak_never_crosses_a_score_boundary():
    """The tiebreak orders within a tier; it must never promote a 3 above a 4, or routing
    (main / watch / drop) would silently depend on star counts."""
    huge = make_item(score=3, signals={"gh_stars": 10 ** 6, "hf_upvotes": 10 ** 6,
                                       "hn_points": 10 ** 6, "hf_likes": 10 ** 6})
    bare = make_item(score=4, signals={})
    assert rank_key(huge) < rank_key(bare)
    assert 3 <= rank_key(huge) < 4


def test_rank_key_is_the_score_with_no_signals():
    assert rank_key(make_item(score=2, signals={})) == 2


def test_magnitude_is_unsaturated_and_monotonic():
    """delta/track diff magnitude rather than rank_key precisely because this one keeps
    growing — a saturating number makes traction growth undetectable."""
    small = magnitude(make_item(signals={"gh_stars": 100}))
    big = magnitude(make_item(signals={"gh_stars": 10000}))
    assert big > small > 0
    assert big > 1.0, "not squashed into [0,1)"


# ---------------------------------------------------------------------------
# FOCUS
# ---------------------------------------------------------------------------

def test_focus_env_overrides_the_profile(monkeypatch):
    monkeypatch.setenv("FOCUS", "agents,evals")
    assert focus.active_terms() == ["agents", "evals"]
    assert focus.focus_match(make_item(title="An agents benchmark", raw_summary=""))
    assert not focus.focus_match(make_item(title="Protein folding", raw_summary=""))


def test_short_terms_match_on_word_boundaries(monkeypatch):
    """'rag' must not fire on 'storage' — the bug that word-boundary matching exists for."""
    monkeypatch.setenv("FOCUS", "rag")
    assert not focus.focus_match(make_item(title="Object storage at scale", raw_summary=""))
    assert focus.focus_match(make_item(title="RAG over long documents", raw_summary=""))


def test_multiword_terms_match_as_phrases(monkeypatch):
    monkeypatch.setenv("FOCUS", "long context")
    assert focus.focus_match(make_item(title="Long context attention", raw_summary=""))


def test_mute_beats_boost(monkeypatch, tmp_path):
    """An explicit opt-out wins even when a boost term also hit."""
    monkeypatch.delenv("FOCUS", raising=False)
    p = tmp_path / "profile.yaml"
    p.write_text("topics:\n  - name: agents\nmute: [robotics]\n")
    monkeypatch.setattr(focus, "PROFILE", p)
    focus._profile_terms.cache_clear()
    try:
        assert focus.focus_match(make_item(title="Agents that plan", raw_summary=""))
        assert not focus.focus_match(make_item(title="Agents for robotics", raw_summary=""))
    finally:
        focus._profile_terms.cache_clear()


def test_focus_degrades_to_no_match_without_a_profile(no_profile):
    assert focus.active_terms() == []
    assert not focus.focus_match(make_item(title="anything at all", raw_summary=""))


# ---------------------------------------------------------------------------
# FOCUS_BACKEND=embed — the opt-in semantic path
# ---------------------------------------------------------------------------

def _embed_profile(monkeypatch, tmp_path):
    """A profile with one topic, FOCUS_BACKEND=embed, and no FOCUS override."""
    monkeypatch.delenv("FOCUS", raising=False)
    monkeypatch.setenv("FOCUS_BACKEND", "embed")
    p = tmp_path / "profile.yaml"
    p.write_text("topics:\n  - name: interpretability\n")
    monkeypatch.setattr(focus, "PROFILE", p)
    focus._profile_terms.cache_clear()


def test_an_unreachable_embedder_falls_back_to_lexical(monkeypatch, tmp_path):
    """The semantic layer answering 'couldn't tell' (no token, HTTP error) must cost
    precision, not the FOCUS signal — this used to silently match nothing for a whole run."""
    _embed_profile(monkeypatch, tmp_path)
    from distill import embed as embed_mod
    monkeypatch.setattr(embed_mod, "embed_match", lambda item, terms, threshold=None: None)
    try:
        assert focus.focus_match(make_item(title="Interpretability of SAEs", raw_summary=""))
        assert not focus.focus_match(make_item(title="Protein folding", raw_summary=""))
    finally:
        focus._profile_terms.cache_clear()


def test_a_semantic_no_is_not_second_guessed_by_the_keyword_matcher(monkeypatch, tmp_path):
    """A real False from the embedder is a verdict. Falling back on it too would let every
    item the semantic layer rejected back in through the lexical door."""
    _embed_profile(monkeypatch, tmp_path)
    from distill import embed as embed_mod
    monkeypatch.setattr(embed_mod, "embed_match", lambda item, terms, threshold=None: False)
    try:
        assert not focus.focus_match(make_item(title="Interpretability of SAEs",
                                               raw_summary=""))
    finally:
        focus._profile_terms.cache_clear()


def test_the_semantic_backend_can_match_what_no_keyword_would(monkeypatch, tmp_path):
    _embed_profile(monkeypatch, tmp_path)
    from distill import embed as embed_mod
    monkeypatch.setattr(embed_mod, "embed_match", lambda item, terms, threshold=None: True)
    try:
        assert focus.focus_match(make_item(title="Reading circuits off a transformer",
                                           raw_summary=""))
    finally:
        focus._profile_terms.cache_clear()


def test_embed_match_reports_couldnt_evaluate_rather_than_no(monkeypatch):
    """distill.embed's half of the contract: a failed embedding is None, not False."""
    from distill import embed as embed_mod
    monkeypatch.setattr(embed_mod, "embed", lambda texts: [None] * len(texts))
    assert embed_mod.embed_match(make_item(title="x"), ("interpretability",)) is None

    monkeypatch.setattr(embed_mod, "embed",
                        lambda texts: [[1.0, 0.0]] + [None] * (len(texts) - 1))
    assert embed_mod.embed_match(make_item(title="x"), ("interpretability",)) is None

    monkeypatch.setattr(embed_mod, "embed", lambda texts: [[1.0, 0.0], [0.0, 1.0]])
    assert embed_mod.embed_match(make_item(title="x"), ("interpretability",)) is False
