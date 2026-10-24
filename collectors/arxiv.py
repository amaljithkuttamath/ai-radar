"""arXiv collector. Pulls recent papers in configured categories within the window.
Uses the public arXiv API (Atom). Stdlib only.

Run: python -m collectors.arxiv
"""

from __future__ import annotations
import os
import sys
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, write_items, parse_window, CONFIG
from radar.collection import SourceBatch
from radar.http import fetch_bytes  # noqa: E402

API = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
WINDOW = os.environ.get("WINDOW", "48h")
MAX = int(os.environ.get("ARXIV_MAX", "120"))


def fetch(category: str, max_results: int) -> bytes:
    q = urllib.parse.urlencode(
        {
            "search_query": f"cat:{category}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        }
    )
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "ai-radar/0.1"})
    return fetch_bytes(req)


def parse(xml_bytes: bytes, category: str, cutoff: datetime) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    items = []
    for e in root.findall(f"{ATOM}entry"):
        published = e.findtext(f"{ATOM}published") or ""
        try:
            pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            continue
        if pub_dt < cutoff:
            continue
        arxiv_url = e.findtext(f"{ATOM}id") or ""
        short = arxiv_url.rsplit("/", 1)[-1]
        # Strip the version suffix (e.g. 2401.12345v2 -> 2401.12345) so ids match the
        # version-less ones minted by hf_papers.py; otherwise the same paper dedups as two.
        short = re.sub(r"v\d+$", "", short)
        items.append(
            make_item(
                id=f"arxiv:{short}",
                category="research",
                title=(e.findtext(f"{ATOM}title") or "").replace("\n", " "),
                url=arxiv_url,
                source=f"arXiv {category}",
                authors=[a.findtext(f"{ATOM}name") for a in e.findall(f"{ATOM}author")],
                published=published,
                raw_summary=(e.findtext(f"{ATOM}summary") or "").replace("\n", " "),
            )
        )
    return items


def main() -> dict:
    import yaml

    cfg = yaml.safe_load((CONFIG / "sources.yaml").read_text())
    categories = cfg.get("research", {}).get("arxiv_categories", [])
    cutoff = datetime.now(timezone.utc) - parse_window(WINDOW)
    batch = SourceBatch("arxiv")
    all_items = {}
    for category in categories:
        for item in batch.fetch(category, lambda cat: parse(fetch(cat, MAX), cat, cutoff), category):
            all_items.setdefault(item["id"], item)
    written = write_items("research", list(all_items.values()))
    print(f"[arxiv] {written} observations written")
    return batch.finish(written)


if __name__ == "__main__":
    main()
