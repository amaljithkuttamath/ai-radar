"""Hugging Face Daily Papers collector — curated + upvote-ranked traction signal.
Captures signals.hf_upvotes. Stdlib only.

NOTE: verify the endpoint shape against live output (see README roadmap); the parser below
reads the /api/daily_papers response and reports malformed source responses.

Run: python -m collectors.hf_papers
"""

from __future__ import annotations
import os
import sys
import re
import math
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, write_items, parse_window, CONFIG
from radar.collection import SourceBatch
from radar.http import fetch_json  # noqa: E402

WINDOW = os.environ.get("WINDOW", "48h")


def fetch_day(date_str: str) -> list[dict]:
    url = f"https://huggingface.co/api/daily_papers?date={date_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "ai-radar/0.1"})
    data = fetch_json(req)
    if not isinstance(data, list):
        raise ValueError("HF papers response must be a list")
    return data


def _gh_url(repo) -> str:
    """Normalize the HF githubRepo field (sometimes an 'owner/name' slug, sometimes a full URL)."""
    if not repo:
        return ""
    repo = str(repo).strip()
    if repo.startswith("http"):
        return repo
    return f"https://github.com/{repo.lstrip('/')}"


def to_item(entry: dict) -> dict | None:
    paper = entry.get("paper", entry)
    arxiv_id = paper.get("id") or paper.get("arxivId")
    if not arxiv_id:
        return None
    arxiv_id = re.sub(r"v\d+$", "", str(arxiv_id))
    # numComments lives on the top-level daily entry; repo/project/keywords on the paper.
    comments = entry.get("numComments", paper.get("numComments", 0)) or 0
    return make_item(
        id=f"arxiv:{arxiv_id}",
        category="research",
        title=paper.get("title", ""),
        url=f"https://arxiv.org/abs/{arxiv_id}",
        source="HF Daily Papers",
        authors=[a.get("name") for a in paper.get("authors", []) if a.get("name")],
        published=paper.get("publishedAt"),
        raw_summary=paper.get("summary", ""),
        # Secondary artifacts the feed already hands us, captured so the artifact heuristic and
        # the gh-stars enricher can fire without a second fetch.
        links={"github": _gh_url(paper.get("githubRepo")), "project": paper.get("projectPage") or ""},
        keywords=paper.get("ai_keywords") or [],
        # Preserve discussion activity alongside each refreshed observation.
        signals={"hf_upvotes": paper.get("upvotes", entry.get("upvotes", 0)) or 0, "hf_comments": comments},
    )


def _in_window(it: dict, cutoff: datetime) -> bool:
    """Drop items provably older than the cutoff; keep ones with a missing/unparseable
    published date (degrade gracefully, per this module's philosophy)."""
    pub = it.get("published")
    if not pub:
        return True
    try:
        pub_dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
    except ValueError:
        return True
    if pub_dt.tzinfo is None:
        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
    return pub_dt >= cutoff


def main() -> dict:
    import yaml

    cfg = yaml.safe_load((CONFIG / "sources.yaml").read_text())
    batch = SourceBatch("hf_papers")
    if not cfg.get("research", {}).get("hf_daily_papers", True):
        return batch.finish(0)
    cutoff = datetime.now(timezone.utc) - parse_window(WINDOW)
    days = math.ceil(parse_window(WINDOW).total_seconds() / 86400) + 1
    items = {}

    def fetch_items(date):
        for entry in fetch_day(date):
            item = to_item(entry)
            if item and _in_window(item, cutoff):
                yield item

    for day in range(days):
        date = (datetime.now(timezone.utc) - timedelta(days=day)).strftime("%Y-%m-%d")
        for item in batch.fetch(date, fetch_items, date):
            items.setdefault(item["id"], item)
    written = write_items("research", list(items.values()))
    print(f"[hf_papers] {written} observations written")
    return batch.finish(written)


if __name__ == "__main__":
    main()
