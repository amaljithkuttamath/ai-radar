"""arXiv collector. Pulls recent papers in configured categories within the window.
Uses the public arXiv API (Atom). Stdlib only.

Run: python -m collectors.arxiv
"""
from __future__ import annotations
import os, sys, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, write_items, parse_window  # noqa: E402

API = "http://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
CATEGORIES = ["cs.LG", "cs.CL", "cs.AI", "stat.ML"]   # mirror config/sources.yaml
WINDOW = os.environ.get("WINDOW", "48h")
MAX = int(os.environ.get("ARXIV_MAX", "120"))


def fetch(category: str, max_results: int) -> bytes:
    q = urllib.parse.urlencode({
        "search_query": f"cat:{category}",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    })
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "ai-radar/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


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
        items.append(make_item(
            id=f"arxiv:{short}",
            category="research",
            title=(e.findtext(f"{ATOM}title") or "").replace("\n", " "),
            url=arxiv_url,
            source=f"arXiv {category}",
            authors=[a.findtext(f"{ATOM}name") for a in e.findall(f"{ATOM}author")],
            published=published,
            raw_summary=(e.findtext(f"{ATOM}summary") or "").replace("\n", " "),
        ))
    return items


def main() -> None:
    cutoff = datetime.now(timezone.utc) - parse_window(WINDOW)
    all_items, seen_ids = [], set()
    for cat in CATEGORIES:
        try:
            data = fetch(cat, MAX)
        except Exception as ex:
            print(f"[arxiv] fetch failed for {cat}: {ex}", file=sys.stderr)
            continue
        for it in parse(data, cat, cutoff):
            if it["id"] not in seen_ids:
                seen_ids.add(it["id"])
                all_items.append(it)
    n = write_items("research", all_items)
    print(f"[arxiv] {len(all_items)} in-window, {n} new written (window={WINDOW})")


if __name__ == "__main__":
    main()
