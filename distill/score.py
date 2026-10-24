"""Heuristic traction score (0–5) from observable signals. Stdlib only.
Scores use five observable signals and are never modified by synthesis.

Reads data/raw within WINDOW, writes scored copies to data/scored/.
Run: python -m distill.score
"""

from __future__ import annotations
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import iter_raw, ROOT, _safe_name
from radar.storage import atomic_json  # noqa: E402
from distill.focus import focus_match, active_terms  # noqa: E402

WINDOW = os.environ.get("WINDOW", "48h")
SCORED = ROOT / "data" / "scored"

FRONTIER = (
    "anthropic",
    "openai",
    "deepmind",
    "google",
    "meta",
    "fair",
    "microsoft",
    "deepseek",
    "qwen",
    "alibaba",
    "mistral",
    "ai2",
    "allen",
    "cohere",
    "xai",
    "nvidia",
    "amd",
)
ARTIFACT_HINTS = ("github.com", "huggingface.co", "/code", "dataset", "weights", "/api")
SOTA_HINTS = ("state-of-the-art", "state of the art", "sota", "outperform", "beats", "new best", "benchmark")


def heuristic_score(it: dict) -> tuple[int, list[str]]:
    s, why = 0, []
    blob = " ".join(
        [
            it.get("title", ""),
            it.get("raw_summary", ""),
            it.get("source", ""),
            " ".join(it.get("authors") or []),
        ]
    ).lower()

    attribution = " ".join([it.get("source", ""), " ".join(it.get("authors") or [])]).lower()
    if any(re.search(rf"\b{re.escape(name)}\b", attribution) for name in FRONTIER):
        s += 1
        why.append("frontier/strong-group authorship")
    if any(h in blob for h in SOTA_HINTS):
        s += 1
        why.append("concrete result claimed")
    links = it.get("links", {}) or {}
    has_repo = bool(links.get("github") or links.get("project"))
    if has_repo or any(h in blob for h in ARTIFACT_HINTS) or "github" in (it.get("url", "")):
        s += 1
        why.append("usable artifact" + (" (repo linked)" if links.get("github") else ""))
    sig = it.get("signals", {}) or {}
    if (
        (sig.get("hf_upvotes", 0) or 0) >= 15
        or (sig.get("hf_likes", 0) or 0) >= 50
        or (sig.get("gh_stars", 0) or 0) >= 50
        or (sig.get("hn_points", 0) or 0) >= 30
    ):
        s += 1
        why.append("observed community traction")
    # Strong traction tier: high-signal items shouldn't be buried by lower-signal ones
    if (
        (sig.get("hf_upvotes", 0) or 0) >= 40
        or (sig.get("hf_likes", 0) or 0) >= 120
        or (sig.get("gh_stars", 0) or 0) >= 80
        or (sig.get("hn_points", 0) or 0) >= 150
    ):
        s += 1
        why.append("strong observed community traction")
    # Five observed criteria, bounded to the documented 0–5 scale.
    return min(s, 5), why


# focus_match now lives in distill/focus.py (profile-driven, alias-aware). FOCUS is still a
# re-rank boost, NOT a score component — kept separate on purpose.


def score_items(items: list[dict]) -> int:
    SCORED.mkdir(parents=True, exist_ok=True)
    # Clear prior runs: only in-window items should exist in data/scored/. Without this,
    # stale scored files accumulate (named by id, never pruned) and leak into every digest.
    for old in SCORED.glob("*.json"):
        old.unlink()
    n = 0
    for original in items:
        it = dict(original)
        score, why = heuristic_score(it)
        it["score"] = score
        it["score_reasons"] = why
        it["focus_match"] = focus_match(it)
        it.pop("_path", None)
        out = SCORED / f"{_safe_name(it['id'])}.json"
        atomic_json(out, it)
        n += 1
    print(f"[score] scored {n} items (window={WINDOW}, focus_terms={len(active_terms())})")
    return n


def main() -> None:
    score_items(list(iter_raw(WINDOW)))


if __name__ == "__main__":
    main()
