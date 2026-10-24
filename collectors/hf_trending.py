"""Hugging Face trending models & datasets collector. The HF papers collector already covers
research; this captures the *artifact* side — models and datasets that are trending right now,
which is the earliest practical signal that a release is landing with practitioners.

Uses the public huggingface.co/api/{models,datasets} endpoints sorted by trendingScore.
Carries signals.hf_likes and signals.hf_downloads so score.py's trending heuristic can fire.
Stdlib only.

Trending is a "right now" signal with no reliable per-item timestamp, so unlike the dated
collectors this one does not filter by publication date. Each run refreshes current
observations; movers state distinguishes returning artifacts from newly observed ones.

Run: python -m collectors.hf_trending
"""

from __future__ import annotations
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, write_items
from radar.collection import SourceBatch
from radar.http import fetch_json  # noqa: E402

API = "https://huggingface.co/api"
LIMIT = int(os.environ.get("HF_TRENDING_LIMIT", "20"))
MIN_LIKES = int(os.environ.get("HF_TRENDING_MIN_LIKES", "10"))  # noise floor


def fetch(kind: str) -> list[dict]:
    """kind in {'models', 'datasets'}."""
    q = urllib.parse.urlencode(
        {
            "sort": "trendingScore",
            "direction": -1,
            "limit": LIMIT,
            "full": "false",
        }
    )
    req = urllib.request.Request(f"{API}/{kind}?{q}", headers={"User-Agent": "ai-radar/0.1"})
    data = fetch_json(req)
    if not isinstance(data, list):
        raise ValueError("HF trending response must be a list")
    return data


def to_item(entry: dict, kind: str) -> dict | None:
    hf_id = entry.get("id") or entry.get("modelId")
    if not hf_id:
        return None
    likes = entry.get("likes") or 0
    if likes < MIN_LIKES:
        return None
    noun = "Model" if kind == "models" else "Dataset"
    return make_item(
        id=f"hf{kind[:-1]}:{hf_id}",  # hfmodel: / hfdataset:
        category="releases",
        title=f"{hf_id} (HF {noun})",
        url=f"https://huggingface.co/{'datasets/' if kind == 'datasets' else ''}{hf_id}",
        source=f"HF Trending {noun}s",
        authors=[hf_id.split("/")[0]] if "/" in hf_id else [],
        published=entry.get("lastModified") or entry.get("createdAt"),
        raw_summary=(entry.get("pipeline_tag") or "")
        + ((" · tags: " + ", ".join((entry.get("tags") or [])[:6])) if entry.get("tags") else ""),
        signals={
            "hf_likes": likes,
            "hf_downloads": entry.get("downloads") or 0,
            "hf_trending": entry.get("trendingScore") or 0,
        },
    )


def main() -> dict:
    batch = SourceBatch("hf_trending")
    items = []

    def fetch_items(kind):
        for entry in fetch(kind):
            item = to_item(entry, kind)
            if item:
                yield item

    for kind in ("models", "datasets"):
        items.extend(batch.fetch(kind, fetch_items, kind))
    written = write_items("releases", items)
    print(f"[hf_trending] {written} observations written")
    return batch.finish(written)


if __name__ == "__main__":
    main()
