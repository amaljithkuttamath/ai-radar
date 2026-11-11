"""Hacker News front-page collector, filtered to AI stories. Stdlib only.

Hacker News is where practitioners decide what is worth their time, and its points are the
`hn_points` signal score.py already understands but nothing collected until now. Uses the
public Algolia HN Search API (front_page tag); only stories with an outbound URL and an
AI-related title are kept, so the radar does not fill with general tech news.

Run: python -m collectors.hackernews
"""

from __future__ import annotations

import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, valid_url, write_items
from radar.collection import SourceBatch
from radar.http import fetch_json  # noqa: E402

API = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=60"
MIN_POINTS = int(os.environ.get("HN_MIN_POINTS", "30"))

# Whole-word, case-insensitive. Kept short and specific: "model" or "agent" alone would let
# in fashion models and travel agents.
AI_TERMS = re.compile(
    r"\b(AI|A\.I\.|LLMs?|GPT-?\w*|Claude|Gemini|Llama|Mistral|Qwen|DeepSeek|OpenAI|Anthropic|"
    r"DeepMind|machine learning|deep learning|neural|transformer|diffusion|inference|"
    r"fine-?tun\w*|RAG|embedding\w*|agentic|AI agents?|chatbot\w*|language models?|"
    r"reasoning model\w*|NVIDIA|GPU\w*|TPU\w*|Hugging ?Face)\b",
    re.IGNORECASE,
)


def fetch() -> list[dict]:
    req = urllib.request.Request(API, headers={"User-Agent": "ai-radar/0.2"})
    data = fetch_json(req)
    hits = data.get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
        raise ValueError("HN response must contain a hits list")
    return hits


def to_item(hit: dict) -> dict | None:
    title = (hit.get("title") or "").strip()
    url = hit.get("url") or ""
    points = hit.get("points") or 0
    if not title or not valid_url(url) or points < MIN_POINTS or not AI_TERMS.search(title):
        return None
    story = hit.get("objectID")
    discussion = f"https://news.ycombinator.com/item?id={story}" if story else None
    return make_item(
        id=f"hn:{story or url}",
        category="releases",
        title=title,
        url=url,
        source="Hacker News",
        published=hit.get("created_at"),
        raw_summary=f"Hacker News front page: {points} points, {hit.get('num_comments') or 0} comments.",
        signals={"hn_points": points},
        links={"discussion": discussion} if discussion else None,
    )


def main() -> dict:
    batch = SourceBatch("hackernews")

    def fetch_items():
        for hit in fetch():
            item = to_item(hit)
            if item:
                yield item

    items = batch.fetch("front_page", fetch_items)
    written = write_items("releases", items)
    print(f"[hackernews] {written} observations written")
    return batch.finish(written)


if __name__ == "__main__":
    main()
