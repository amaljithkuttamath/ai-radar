"""Personalized FOCUS matching. FOCUS is a re-rank boost ("is this relevant to me"), kept
strictly separate from the 0–5 traction score ("is this big"). This module decides relevance.

Two layers, both honoring the project's "collection/scoring is stdlib-only" rule:

1. FOCUS env string (e.g. FOCUS="agents,evals") — if set, it OVERRIDES the profile, so CI and
   one-off lenses behave exactly as before. Plain substring match, unchanged behavior.

2. config/profile.yaml — a persistent interest profile (topics + aliases). When FOCUS is unset,
   each item is matched against the expanded topic vocabulary. This is a real upgrade over the
   old `keyword in blob`: aliases mean "interpretability" also catches "mechanistic interp" /
   "SAE" without you listing every variant in an env var.

Matching is lexical (word-boundary aware) and needs no model, so score.py stays stdlib-only.

Optional semantic layer (off by default, opt-in): set FOCUS_BACKEND=embed to match on embedding
similarity instead of keywords. That path requires an embedder and is intentionally NOT imported
unless requested, so the default install stays dependency-free. Implement embed_match() against
whatever backend you prefer (local sentence-transformers, an API, etc.).
"""
from __future__ import annotations
import os, re, functools
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "config" / "profile.yaml"


def _env_focus() -> list[str]:
    return [t.strip().lower() for t in os.environ.get("FOCUS", "").split(",") if t.strip()]


@functools.lru_cache(maxsize=1)
def _profile_terms() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (boost_terms, mute_terms) expanded from the profile. Cached: read once per run."""
    if not PROFILE.exists():
        return ((), ())
    try:
        import yaml
        cfg = yaml.safe_load(PROFILE.read_text()) or {}
    except Exception:
        return ((), ())
    boost: list[str] = []
    for t in cfg.get("topics", []) or []:
        if isinstance(t, str):
            boost.append(t.lower())
            continue
        name = (t.get("name") or "").lower()
        if name:
            boost.append(name)
        boost.extend(a.lower() for a in (t.get("aliases") or []) if a)
    mute = [m.lower() for m in (cfg.get("mute") or [])]
    # Dedup, keep order.
    return (tuple(dict.fromkeys(boost)), tuple(dict.fromkeys(mute)))


def _blob(item: dict) -> str:
    return " ".join([item.get("title", ""), item.get("raw_summary", ""),
                     item.get("source", "")]).lower()


def _term_hit(term: str, blob: str) -> bool:
    """Word-boundary match for short single-token terms (avoid 'rag' matching 'storage');
    plain substring for multi-word phrases (where boundaries are already implied)."""
    if " " in term or "-" in term:
        return term in blob
    return re.search(rf"\b{re.escape(term)}\b", blob) is not None


def active_terms() -> list[str]:
    """The effective focus vocabulary for this run (for logging / digest transparency)."""
    env = _env_focus()
    if env:
        return env
    return list(_profile_terms()[0])


def focus_match(item: dict) -> bool:
    """True if the item is in a FOCUS area. Honors FOCUS env override, then profile.
    Muted terms suppress a match even if a boost term also hit (explicit opt-out wins)."""
    blob = _blob(item)
    env = _env_focus()
    if env:
        return any(_term_hit(t, blob) for t in env)

    boost, mute = _profile_terms()
    if mute and any(_term_hit(m, blob) for m in mute):
        return False
    if os.environ.get("FOCUS_BACKEND", "").lower() == "embed":
        return embed_match(item, boost)
    return any(_term_hit(t, blob) for t in boost)


def embed_match(item: dict, terms: tuple[str, ...]) -> bool:  # pragma: no cover - opt-in
    """Optional semantic matcher. Not used unless FOCUS_BACKEND=embed. Implement against your
    embedder of choice; left as a graceful no-op fallback (returns lexical result) by default so
    enabling the flag without an embedder doesn't crash a run."""
    try:
        # e.g. from sentence_transformers import SentenceTransformer; cosine over `terms`.
        raise ImportError("no embedder configured")
    except Exception:
        blob = _blob(item)
        return any(_term_hit(t, blob) for t in terms)
