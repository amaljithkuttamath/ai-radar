"""RSS/Atom collector for lab & vendor newsrooms. Config-driven from config/sources.yaml
(hardware.rss + releases.rss). Requires feedparser (declared in pyproject.toml).

Run: python -m collectors.lab_blogs
"""

from __future__ import annotations
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, write_items, parse_window, CONFIG as CONFIG_DIR
from radar.collection import SourceBatch
from radar.http import fetch_bytes  # noqa: E402

WINDOW = os.environ.get("WINDOW", "48h")
CONFIG = CONFIG_DIR / "sources.yaml"


def load_feeds() -> list[tuple[str, str, str]]:
    """Return (category, name, url). Requires pyyaml."""
    import yaml  # declared in pyproject.toml

    cfg = yaml.safe_load(CONFIG.read_text())
    feeds = []
    for category in ("hardware", "releases"):
        for f in (cfg.get(category, {}) or {}).get("rss", []):
            feeds.append((category, f["name"], f["url"]))
    return feeds


def parse_feed(url: str):
    """Yield (id, title, link, summary, published_dt) using feedparser.
    Caller imports feedparser once up front so a missing dep fails loudly, not per-feed."""
    import feedparser  # declared in pyproject.toml

    request = urllib.request.Request(url, headers={"User-Agent": "ai-radar/0.2"})
    d = feedparser.parse(fetch_bytes(request))
    if not d.version or (d.bozo and not d.entries):
        raise ValueError("response is not a usable RSS or Atom feed")
    for e in d.entries:
        pub = None
        if getattr(e, "published_parsed", None):
            pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        yield (e.get("id") or e.get("link"), e.get("title", ""), e.get("link", ""), e.get("summary", ""), pub)


def main() -> dict:
    cutoff = datetime.now(timezone.utc) - parse_window(WINDOW)
    batch = SourceBatch("lab_blogs")
    by_category = {}

    def fetch_items(category, name, url):
        for native_id, title, link, summary, published in parse_feed(url):
            if published and published < cutoff:
                continue
            yield make_item(
                id=f"blog:{native_id}",
                category=category,
                title=title,
                url=link,
                source=name,
                published=published.isoformat() if published else None,
                raw_summary=summary,
            )

    for category, name, url in load_feeds():
        by_category.setdefault(category, []).extend(batch.fetch(name, fetch_items, category, name, url))
    written = sum(write_items(category, items) for category, items in by_category.items())
    print(f"[lab_blogs] {written} observations written")
    return batch.finish(written)


if __name__ == "__main__":
    main()
