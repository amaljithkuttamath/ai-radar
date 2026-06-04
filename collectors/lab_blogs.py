"""RSS/Atom collector for lab & vendor newsrooms. Config-driven from config/sources.yaml
(hardware.rss + releases.rss). Requires feedparser (see requirements.txt).

Run: python -m collectors.lab_blogs
"""
from __future__ import annotations
import os, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import make_item, write_items, parse_window  # noqa: E402

WINDOW = os.environ.get("WINDOW", "48h")
CONFIG = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"


def load_feeds() -> list[tuple[str, str, str]]:
    """Return (category, name, url). Requires pyyaml."""
    import yaml  # in requirements.txt
    cfg = yaml.safe_load(CONFIG.read_text())
    feeds = []
    for category in ("hardware", "releases"):
        for f in (cfg.get(category, {}) or {}).get("rss", []):
            feeds.append((category, f["name"], f["url"]))
    return feeds


def parse_feed(url: str):
    """Yield (id, title, link, summary, published_dt) using feedparser.
    Caller imports feedparser once up front so a missing dep fails loudly, not per-feed."""
    import feedparser  # in requirements.txt
    d = feedparser.parse(url)
    for e in d.entries:
        pub = None
        if getattr(e, "published_parsed", None):
            pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        yield (e.get("id") or e.get("link"), e.get("title", ""),
               e.get("link", ""), e.get("summary", ""), pub)


def main() -> None:
    cutoff = datetime.now(timezone.utc) - parse_window(WINDOW)
    try:
        import feedparser  # noqa: F401  fail loudly here, not silently per-feed below
    except ImportError:
        print("[blogs] feedparser not installed; run `pip install -r requirements.txt`",
              file=sys.stderr)
        return
    try:
        feeds = load_feeds()
    except Exception as ex:
        print(f"[blogs] cannot load config ({ex}); is pyyaml installed?", file=sys.stderr)
        return
    by_cat: dict[str, list[dict]] = {}
    for category, name, url in feeds:
        try:
            for _id, title, link, summary, pub in parse_feed(url):
                if pub and pub < cutoff:
                    continue
                by_cat.setdefault(category, []).append(make_item(
                    id=f"blog:{_id}", category=category, title=title, url=link,
                    source=name, published=pub.isoformat() if pub else None,
                    raw_summary=summary,
                ))
        except Exception as ex:
            print(f"[blogs] {name} failed: {ex}", file=sys.stderr)
    total = 0
    for category, items in by_cat.items():
        total += write_items(category, items)
    print(f"[blogs] {total} new written across {len(by_cat)} categories (window={WINDOW})")


if __name__ == "__main__":
    main()
