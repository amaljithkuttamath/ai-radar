"""Heuristic traction score (0–5) from observable signals. Stdlib only.
This is the cheap, deterministic part of scoring. The model layer in synthesize.py refines
the 'novelty / challenges-assumptions' criterion, which needs judgment.

Reads data/raw within WINDOW, writes scored copies to data/scored/.
Run: python -m distill.score
"""
from __future__ import annotations
import os, sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import iter_raw, ROOT  # noqa: E402
from distill.focus import focus_match, active_terms  # noqa: E402

WINDOW = os.environ.get("WINDOW", "48h")
SCORED = ROOT / "data" / "scored"

FRONTIER = ("anthropic", "openai", "deepmind", "google", "meta", "fair", "microsoft",
            "deepseek", "qwen", "alibaba", "mistral", "ai2", "allen", "cohere", "xai",
            "nvidia", "amd")
ARTIFACT_HINTS = ("github.com", "huggingface.co", "/code", "dataset", "weights", "/api")
SOTA_HINTS = ("state-of-the-art", "state of the art", "sota", "outperform", "beats",
              "new best", "benchmark")


def heuristic_score(it: dict) -> tuple[int, list[str]]:
    s, why = 0, []
    blob = " ".join([it.get("title", ""), it.get("raw_summary", ""),
                     it.get("source", ""), " ".join(it.get("authors") or [])]).lower()

    if any(f in blob for f in FRONTIER):
        s += 1; why.append("frontier/strong-group authorship")
    if any(h in blob for h in SOTA_HINTS):
        s += 1; why.append("concrete result claimed")
    if any(h in blob for h in ARTIFACT_HINTS) or "github" in (it.get("url", "")):
        s += 1; why.append("usable artifact")
    sig = it.get("signals", {}) or {}
    if ((sig.get("hf_upvotes", 0) or 0) >= 15
            or (sig.get("hf_likes", 0) or 0) >= 50
            or (sig.get("gh_stars", 0) or 0) >= 50
            or (sig.get("hn_points", 0) or 0) >= 30):
        s += 1; why.append("trending (Tier-2 signal)")
    # 'novelty / challenges assumption' (+1) is left to the model pass — see synthesize.py.
    # Traction is 0–5: heuristic covers up to 4; the model can add the novelty point.
    return min(s, 5), why


# focus_match now lives in distill/focus.py (profile-driven, alias-aware). FOCUS is still a
# re-rank boost, NOT a score component — kept separate on purpose.


def main() -> None:
    SCORED.mkdir(parents=True, exist_ok=True)
    # Clear prior runs: only in-window items should exist in data/scored/. Without this,
    # stale scored files accumulate (named by id, never pruned) and leak into every digest.
    for old in SCORED.glob("*.json"):
        old.unlink()
    n = 0
    for it in iter_raw(WINDOW):
        score, why = heuristic_score(it)
        it["score"] = score
        it["score_reasons"] = why
        it["focus_match"] = focus_match(it)
        it.pop("_path", None)
        out = SCORED / f"{it['id'].replace(':', '_').replace('/', '_')}.json"
        out.write_text(json.dumps(it, indent=2))
        n += 1
    print(f"[score] scored {n} items (window={WINDOW}, focus={active_terms() or 'none'})")


if __name__ == "__main__":
    main()
