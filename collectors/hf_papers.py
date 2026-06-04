"""Hugging Face Daily Papers collector — curated + upvote-ranked traction signal.
Captures signals.hf_upvotes. Stdlib only.

NOTE: verify the endpoint shape against live output (see README roadmap); the parser below
reads the documented /api/daily_papers response and degrades gracefully if fields differ.

Run: python -m collectors.hf_papers
"""
from __future__ import annotations
import os, sys, json, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, write_items, parse_window  # noqa: E402

WINDOW = os.environ.get("WINDOW", "48h")


def fetch_day(date_str: str) -> list[dict]:
    url = f"https://huggingface.co/api/daily_papers?date={date_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "ai-radar/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def to_item(entry: dict) -> dict | None:
    paper = entry.get("paper", entry)
    arxiv_id = paper.get("id") or paper.get("arxivId")
    if not arxiv_id:
        return None
    return make_item(
        id=f"arxiv:{arxiv_id}",
        category="research",
        title=paper.get("title", ""),
        url=f"https://arxiv.org/abs/{arxiv_id}",
        source="HF Daily Papers",
        authors=[a.get("name") for a in paper.get("authors", []) if a.get("name")],
        published=paper.get("publishedAt"),
        raw_summary=paper.get("summary", ""),
        signals={"hf_upvotes": paper.get("upvotes", entry.get("upvotes", 0))},
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


def main() -> None:
    cutoff = datetime.now(timezone.utc) - parse_window(WINDOW)
    days = max(1, parse_window(WINDOW).days or 1) + 1
    items = []
    for d in range(days):
        date_str = (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%Y-%m-%d")
        try:
            for entry in fetch_day(date_str):
                it = to_item(entry)
                if it and _in_window(it, cutoff):
                    items.append(it)
        except Exception as ex:
            print(f"[hf] fetch failed for {date_str}: {ex}", file=sys.stderr)
    n = write_items("research", items)
    print(f"[hf] {len(items)} fetched, {n} new written (window={WINDOW})")


if __name__ == "__main__":
    main()
