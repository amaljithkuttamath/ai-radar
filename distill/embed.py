"""GitHub Models embeddings client for semantic FOCUS matching.

Stdlib-only (urllib + json + hashlib). Reads GITHUB_TOKEN from the environment.
Endpoint: https://models.github.ai/inference/embeddings
Model: text-embedding-3-small (or the GH Models equivalent).

Cache: embeddings are stored under data/embed_cache/ keyed by a hex digest of the
input text so the same topic-term strings are never re-embedded across runs.

Public API:
  embed(texts: list[str]) -> list[list[float]]  # batch, cached
  cosine(a, b) -> float
  embed_match(item, terms) -> bool  # True if item blob is close enough to the mean term vec

All external calls are wrapped in try/except so a token error, HTTP error, or any other
failure falls through gracefully — the caller receives a float('nan') sentinel or False,
never an exception propagated upward.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import ROOT  # noqa: E402

_CACHE_DIR = ROOT / "data" / "embed_cache"
_ENDPOINT = "https://models.github.ai/inference/embeddings"
_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
EMBED_THRESHOLD = float(os.environ.get("EMBED_THRESHOLD", "0.30"))


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _load_cached(key: str) -> list[float] | None:
    try:
        p = _CACHE_DIR / f"{key}.json"
        if p.exists():
            return json.loads(p.read_text())
    except Exception:
        pass
    return None


def _save_cached(key: str, vec: list[float]) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / f"{key}.json").write_text(json.dumps(vec))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# GitHub Models embeddings call
# ---------------------------------------------------------------------------

def _call_embeddings(texts: list[str]) -> list[list[float]]:
    """Call the GitHub Models embeddings endpoint. Returns one vector per input text.
    Raises on HTTP/network error — callers are responsible for handling."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set — cannot call embeddings endpoint")
    body = json.dumps({"model": _MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        _ENDPOINT, data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    # OpenAI-compatible response: {"data": [{"embedding": [...], "index": N}, ...]}
    items = sorted(data["data"], key=lambda x: x["index"])
    return [it["embedding"] for it in items]


# ---------------------------------------------------------------------------
# Batch embedding with caching
# ---------------------------------------------------------------------------

def embed(texts: list[str]) -> list[list[float] | None]:
    """Return one embedding vector per input text.

    Uses the on-disk cache; only fetches uncached texts from the endpoint.
    Returns None in any slot where embedding failed (caller should handle).
    Never raises.
    """
    if not texts:
        return []

    keys = [_cache_key(t) for t in texts]
    result: list[list[float] | None] = [None] * len(texts)

    # Load cached
    uncached_idxs: list[int] = []
    for i, (k, _) in enumerate(zip(keys, texts)):
        vec = _load_cached(k)
        if vec is not None:
            result[i] = vec
        else:
            uncached_idxs.append(i)

    if not uncached_idxs:
        return result

    # Fetch uncached in one batch
    try:
        batch_texts = [texts[i] for i in uncached_idxs]
        vecs = _call_embeddings(batch_texts)
        for slot, idx in enumerate(uncached_idxs):
            if slot < len(vecs):
                result[idx] = vecs[slot]
                _save_cached(keys[idx], vecs[slot])
    except Exception as exc:
        print(f"[embed] embedding API error: {exc}", file=sys.stderr)
        # Leave those slots as None

    return result


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [−1, 1]. Returns 0.0 on zero-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _mean_vec(vecs: list[list[float]]) -> list[float] | None:
    """Element-wise mean of a list of same-length vectors. Returns None if empty."""
    valid = [v for v in vecs if v is not None]
    if not valid:
        return None
    dim = len(valid[0])
    out = [0.0] * dim
    for v in valid:
        for j, x in enumerate(v):
            out[j] += x
    n = len(valid)
    return [x / n for x in out]


# ---------------------------------------------------------------------------
# Public semantic match
# ---------------------------------------------------------------------------

def embed_match(item: dict, terms: tuple[str, ...], threshold: float | None = None) -> bool:
    """True if the item blob embedding is within `threshold` cosine similarity of the
    mean topic-term embedding. Falls back to False (not lexical) on any error, so the
    caller (focus.py) handles the lexical fallback itself.

    threshold defaults to EMBED_THRESHOLD env (default 0.30).
    """
    if threshold is None:
        threshold = EMBED_THRESHOLD
    try:
        if not terms:
            return False
        from distill.focus import _blob  # local import to avoid circular at module level
        blob_text = _blob(item)
        all_texts = [blob_text] + list(terms)
        vecs = embed(all_texts)
        blob_vec = vecs[0]
        term_vecs = vecs[1:]
        if blob_vec is None:
            return False
        valid_term_vecs = [v for v in term_vecs if v is not None]
        mean = _mean_vec(valid_term_vecs)
        if mean is None:
            return False
        return cosine(blob_vec, mean) >= threshold
    except Exception as exc:
        print(f"[embed] embed_match error: {exc}", file=sys.stderr)
        return False
