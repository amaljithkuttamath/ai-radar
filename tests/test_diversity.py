"""Diversity filters — what stops one lab's release sweep from becoming the whole digest."""
from __future__ import annotations

from distill.diversity import dedup_near_titles, cap_per_source, diversify, _tokens
from tests.conftest import make_item


def _variant(name, stars, source="HF Trending Models"):
    return make_item(id=f"hfmodel:{name}", title=name, source=source, score=3,
                     signals={"gh_stars": stars})


def test_a_release_sweep_collapses_to_its_strongest_variant():
    items = [_variant("Ornith-1.0-9B", 20), _variant("Ornith-1.0-35B", 900),
             _variant("Ornith-1.0-9B-GGUF", 5)]
    kept = dedup_near_titles(items)
    assert len(kept) == 1
    assert kept[0]["title"] == "Ornith-1.0-35B", "the highest-ranked variant survives"


def test_an_item_without_an_id_is_dropped_alone():
    """A collapsed variant must take only itself out of the list. Keying the drop set on
    `id` meant an id-less collision registered as "" and evicted every other id-less item —
    including unrelated ones the filter never looked at."""
    items = [_variant("Ornith-1.0-9B", 20), _variant("Ornith-1.0-35B", 900),
             make_item(title="Cartographer VLM", source="Lab Blog", score=3)]
    for it in items:
        it.pop("id")
    kept = dedup_near_titles(items)
    assert [i["title"] for i in kept] == ["Ornith-1.0-35B", "Cartographer VLM"]


def test_unrelated_titles_are_left_alone():
    items = [_variant("Ornith-1.0-9B", 20), _variant("Cartographer VLM", 30)]
    assert len(dedup_near_titles(items)) == 2


def test_dedup_preserves_input_order():
    """Survivors must come back in the caller's order — synthesize sorts afterwards and a
    reshuffle here would silently reorder the digest."""
    items = [_variant("Alpha model", 1), _variant("Beta model", 2), _variant("Gamma model", 3)]
    kept = dedup_near_titles(items)
    assert [i["title"] for i in kept] == ["Alpha model", "Beta model", "Gamma model"]


def test_version_and_size_tokens_do_not_distinguish_variants():
    assert _tokens("Ornith-1.0-9B") == _tokens("Ornith-1.0-35B-GGUF")


def test_per_source_cap_keeps_the_first_n():
    items = [_variant(f"Model {n}", n, source="arXiv cs.LG") for n in range(5)]
    kept = cap_per_source(items, cap=2)
    assert len(kept) == 2
    assert [i["title"] for i in kept] == ["Model 0", "Model 1"]


def test_cap_is_per_source_not_global():
    items = [_variant("A", 1, "src-a"), _variant("B", 2, "src-a"),
             _variant("C", 3, "src-b"), _variant("D", 4, "src-b")]
    assert len(cap_per_source(items, cap=1)) == 2


def test_both_filters_disable_cleanly():
    items = [_variant("Ornith-1.0-9B", 1), _variant("Ornith-1.0-35B", 2)]
    assert dedup_near_titles(items, threshold=1.0) == items
    assert cap_per_source(items, cap=0) == items


def test_diversify_applies_both():
    items = ([_variant(f"Ornith-1.0-{n}B", n) for n in (9, 35, 70)]
             + [_variant(f"Distinct thing {n}", n, source="arXiv cs.LG") for n in range(4)])
    kept = diversify(items)
    assert len(kept) < len(items)
    assert sum(1 for i in kept if i["source"] == "arXiv cs.LG") <= 2
