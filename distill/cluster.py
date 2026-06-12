"""Topic clustering for the daily candidate set.

Groups main-list candidates into emergent themes using:
  1. Semantic clustering (when distill.embed is available and embeddings succeed) —
     agglomerative/threshold clustering over cosine distances.
  2. Lexical fallback — shared focus-term / keyword overlap (stdlib only).

Both paths degrade to a flat (no-op) grouping when clustering yields nothing useful
(< 2 clusters, or all items in one cluster). The caller (synthesize) detects this and
keeps the existing flat list unchanged.

Public API:
  cluster_items(items: list[dict]) -> list[dict]
    Each dict: {"label": str, "theme_summary": str, "item_ids": list[str]}
    Returns an empty list when clustering is unhelpful.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Cosine threshold: items are in the same cluster if cosine(a, b) >= THRESHOLD.
# 0.45 is conservatively high — only clearly related items are grouped.
_COSINE_THRESHOLD = 0.45
_MIN_CLUSTERS = 2  # fewer than this => degrade to flat list
_MAX_CLUSTERS = 8  # cap on reported themes (merge tiny leftovers)
_MIN_CLUSTER_SIZE = 2  # singleton clusters are not useful


# ---------------------------------------------------------------------------
# Semantic clustering (embedding-based, optional)
# ---------------------------------------------------------------------------

def _semantic_clusters(items: list[dict]) -> list[dict] | None:
    """Try to cluster using embeddings. Returns None on any failure."""
    try:
        from distill.embed import embed, cosine  # lazy import — may not be available

        texts = []
        for it in items:
            blob = " ".join(filter(None, [
                it.get("title", ""),
                (it.get("raw_summary") or "")[:200],
            ]))
            texts.append(blob)

        vecs = embed(texts)
        # Need all embeddings to proceed
        if any(v is None for v in vecs):
            return None

        n = len(items)
        # Build similarity matrix
        sim: list[list[float]] = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i, n):
                s = cosine(vecs[i], vecs[j])  # type: ignore[arg-type]
                sim[i][j] = sim[j][i] = s

        # Greedy agglomerative clustering: assign each item to the first existing
        # cluster whose centroid (mean of members) is close enough.
        cluster_members: list[list[int]] = []
        assignment: list[int] = [-1] * n

        for i in range(n):
            best_c = -1
            best_s = _COSINE_THRESHOLD - 1e-9  # must exceed threshold to join
            for c_idx, members in enumerate(cluster_members):
                avg_sim = sum(sim[i][m] for m in members) / len(members)
                if avg_sim > best_s:
                    best_s = avg_sim
                    best_c = c_idx
            if best_c >= 0:
                cluster_members[best_c].append(i)
                assignment[i] = best_c
            else:
                assignment[i] = len(cluster_members)
                cluster_members.append([i])

        return _build_cluster_output(items, cluster_members)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Lexical clustering (stdlib fallback)
# ---------------------------------------------------------------------------

def _lexical_clusters(items: list[dict]) -> list[dict] | None:
    """Group items by shared focus-term / keyword overlap. Stdlib only."""
    try:
        from distill.focus import active_terms, _term_hit, _blob

        terms = active_terms()

        def _item_term_set(it: dict) -> frozenset[str]:
            blob = _blob(it)
            return frozenset(t for t in terms if _term_hit(t, blob))

        # Fall back to title-word overlap if no terms configured
        def _item_kw_set(it: dict) -> frozenset[str]:
            stop = {"a", "an", "the", "of", "and", "for", "in", "on", "with",
                    "to", "via", "from", "is", "are", "by"}
            words = set(it.get("title", "").lower().split())
            return frozenset(w for w in words if len(w) > 3 and w not in stop)

        term_sets = [_item_term_set(it) or _item_kw_set(it) for it in items]
        n = len(items)

        cluster_members: list[list[int]] = []
        assignment: list[int] = [-1] * n

        for i in range(n):
            best_c = -1
            best_overlap = 0
            for c_idx, members in enumerate(cluster_members):
                # Jaccard-like: shared terms / union for the cluster representative
                rep_terms = frozenset().union(*(term_sets[m] for m in members))
                shared = len(term_sets[i] & rep_terms)
                if shared > best_overlap:
                    best_overlap = shared
                    best_c = c_idx
            if best_c >= 0 and best_overlap >= 1:
                cluster_members[best_c].append(i)
                assignment[i] = best_c
            else:
                assignment[i] = len(cluster_members)
                cluster_members.append([i])

        return _build_cluster_output(items, cluster_members)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Shared output builder
# ---------------------------------------------------------------------------

def _build_cluster_output(items: list[dict], cluster_members: list[list[int]]) -> list[dict] | None:
    """Convert raw membership lists into the public cluster format.
    Returns None when clustering is unhelpful (< 2 non-singleton clusters)."""
    # Filter out singletons and oversized clusters
    useful = [m for m in cluster_members if len(m) >= _MIN_CLUSTER_SIZE]
    # Collect singletons as an "Other" bucket if there are any leftover
    singletons = [m[0] for m in cluster_members if len(m) < _MIN_CLUSTER_SIZE]

    if len(useful) < _MIN_CLUSTERS:
        return None  # Not useful — caller degrades to flat list

    # Cap the number of reported clusters
    useful = sorted(useful, key=len, reverse=True)[:_MAX_CLUSTERS]

    out: list[dict] = []
    for members in useful:
        cluster_items = [items[i] for i in members]
        # Label: most common focus term across members, or top title word
        label = _cluster_label(cluster_items)
        item_ids = [it["id"] for it in cluster_items]
        out.append({
            "label": label,
            "item_ids": item_ids,
            "size": len(item_ids),
        })

    # Append a catch-all "Other" group for singletons if non-empty
    if singletons:
        other_ids = [items[i]["id"] for i in singletons]
        out.append({
            "label": "Other",
            "item_ids": other_ids,
            "size": len(other_ids),
        })

    return out if len(out) >= _MIN_CLUSTERS else None


def _cluster_label(cluster_items: list[dict]) -> str:
    """Derive a short label for a cluster from shared terms or title words."""
    try:
        from distill.focus import active_terms, _term_hit, _blob
        terms = active_terms()
        if terms:
            counts: dict[str, int] = {}
            for it in cluster_items:
                blob = _blob(it)
                for t in terms:
                    if _term_hit(t, blob):
                        counts[t] = counts.get(t, 0) + 1
            if counts:
                top = max(counts, key=lambda k: counts[k])
                return top.title()
    except Exception:
        pass

    # Fallback: longest common title word (heuristic)
    stop = {"a", "an", "the", "of", "and", "for", "in", "on", "with", "to", "via",
            "from", "is", "are", "by", "new", "large", "model", "language"}
    word_counts: dict[str, int] = {}
    for it in cluster_items:
        for w in it.get("title", "").lower().split():
            if len(w) > 4 and w not in stop:
                word_counts[w] = word_counts.get(w, 0) + 1
    if word_counts:
        top = max(word_counts, key=lambda k: word_counts[k])
        return top.title()
    return "General"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def cluster_items(items: list[dict]) -> list[dict]:
    """Cluster items into emergent themes. Returns a list of cluster dicts or [] when
    clustering is unhelpful (all items in one group, or < 2 non-singleton clusters).

    Tries semantic (embedding-based) clustering first; falls back to lexical if
    embeddings are unavailable or fail. Returns [] if both fail or yield nothing useful.
    """
    if len(items) < _MIN_CLUSTER_SIZE * _MIN_CLUSTERS:
        return []  # Too few items to cluster meaningfully

    result = _semantic_clusters(items)
    if result is not None:
        return result

    result = _lexical_clusters(items)
    if result is not None:
        return result

    return []
