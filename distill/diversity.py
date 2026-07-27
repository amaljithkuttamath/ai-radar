"""Candidate-set diversity filters. Keeps the digest from being dominated by one lab's
release sweep (three consecutive `Ornith-1.0-9B / -35B / -9B-GGUF` rows) or by
near-duplicate paper titles.

Two filters applied in order to the ranked candidate list, both **stable** (preserve rank
order among survivors) and **rank-key aware** (higher-ranked variant wins any tie):

  1. near-dup title collapse — shingle-based Jaccard over normalized title tokens; keep
     the top-ranked exemplar, drop the rest. Catches `Foo-1.0-9B / Foo-1.0-35B /
     Foo-1.0-9B-GGUF` and paper variants like `X: A New Method` / `X (Extended)`.
  2. per-source cap — at most N items from the same `source` string (e.g. one
     `arXiv cs.LG` collector produced 12 candidates today; keep the top MAX_PER_SOURCE).

Both filters degrade cleanly: MAX_PER_SOURCE=0 or JACCARD_THRESHOLD=1.0 disables the
corresponding pass. Stdlib only.
"""
from __future__ import annotations
import os, re
from distill.rank import rank_key


# Tuning knobs. Defaults are conservative — better to leave a near-dup than drop a real
# item — and can be relaxed by env for one-off runs.
MAX_PER_SOURCE = int(os.environ.get("MAX_PER_SOURCE", "2"))
JACCARD_THRESHOLD = float(os.environ.get("DIVERSITY_JACCARD", "0.6"))

_STOP = frozenset({
    "a", "an", "the", "of", "and", "for", "in", "on", "with", "to", "via", "from",
    "is", "are", "by", "new", "using", "based", "toward", "towards", "model", "models",
    "language", "large", "gguf", "fp8", "int4", "int8", "awq", "hf", "quant",
})
# Version/size tokens that shouldn't distinguish variants: `9b`, `35b`, `v2`, `2.5x`, etc.
_VARIANT_RE = re.compile(r"^(v?\d+(\.\d+)?[a-z]{0,3}|\d+[km]?b|\d+x)$")


def _tokens(title: str) -> frozenset[str]:
    """Normalized token set for shingle-based comparison. Strips punctuation, drops
    stopwords and version/size tokens so variant families collapse to the same set."""
    words = re.findall(r"[a-z0-9.]+", (title or "").lower())
    keep: list[str] = []
    for w in words:
        w = w.strip(".")
        if not w or w in _STOP or len(w) <= 2:
            continue
        if _VARIANT_RE.match(w):
            continue
        keep.append(w)
    return frozenset(keep)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


def dedup_near_titles(items: list[dict], threshold: float = JACCARD_THRESHOLD) -> list[dict]:
    """Keep the highest-ranked exemplar of any near-duplicate title cluster. Stable:
    survivors keep their original relative order. threshold >= 1.0 disables the pass."""
    if threshold >= 1.0 or len(items) < 2:
        return items
    # Rank-sorted view (by POSITION, so the survivors are identified by where they sit in the
    # input rather than by id — an item with no id is still exactly one item, and keying the
    # drop set on `it.get("id", "")` used to put "" in it and take every id-less item with it).
    ranked = sorted(range(len(items)), key=lambda i: rank_key(items[i]), reverse=True)
    kept_tokens: list[frozenset[str]] = []
    dropped: set[int] = set()
    for i in ranked:
        tok = _tokens(items[i].get("title", ""))
        if tok and any(_jaccard(tok, prev) >= threshold for prev in kept_tokens):
            dropped.add(i)
        else:
            kept_tokens.append(tok)
    # Return in the ORIGINAL order so downstream sorting is unaffected.
    return [it for i, it in enumerate(items) if i not in dropped]


def cap_per_source(items: list[dict], cap: int = MAX_PER_SOURCE) -> list[dict]:
    """At most `cap` items per `source` string. Stable: preserves the input order, so
    when the input is already rank-sorted, the highest-ranked N per source survive.
    cap <= 0 disables."""
    if cap <= 0:
        return items
    seen: dict[str, int] = {}
    out: list[dict] = []
    for it in items:
        src = it.get("source", "") or ""
        n = seen.get(src, 0)
        if n >= cap:
            continue
        seen[src] = n + 1
        out.append(it)
    return out


def diversify(items: list[dict]) -> list[dict]:
    """Apply both filters in order. Input is expected to be rank-sorted (higher first)."""
    items = dedup_near_titles(items)
    items = cap_per_source(items)
    return items
