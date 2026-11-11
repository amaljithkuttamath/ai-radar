"""News-page collector for labs that publish no RSS feed. Stdlib only.

Anthropic, Meta AI and Mistral announce major releases on plain HTML news pages. Missing
them is exactly how the radar ends up ranking a week-old GitHub repository above a frontier
model launch. Each configured page (config/sources.yaml, releases.pages) names the URL and
a regular expression for article links; the collector keeps the first `max` matching links
in page order, which on a news index means the newest.

Pages carry no reliable per-item timestamp, so, like the trending collectors, this one
does not filter by date: it re-observes the top of the page each run and lets the novelty
ledger (data/state.json, distill/news.py) tell a new post from one already shown. `max` is
small so a first run cannot flood the radar with a lab's back catalogue.

Run: python -m collectors.lab_pages
"""

from __future__ import annotations

import html
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.common import CONFIG as CONFIG_DIR, make_item, valid_url, write_items
from radar.collection import SourceBatch
from radar.http import fetch_bytes  # noqa: E402

CONFIG = CONFIG_DIR / "sources.yaml"
DEFAULT_MAX = 5
ANCHOR = re.compile(r"<a\b[^>]*?\bhref=\"(?P<href>[^\"]+)\"[^>]*>(?P<body>.*?)</a>", re.S | re.I)
HEADING = re.compile(r"<h[1-6]\b[^>]*>(?P<t>.*?)</h[1-6]>", re.S | re.I)
PARAGRAPH = re.compile(r"<p\b[^>]*>(?P<t>.*?)</p>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")


def load_pages() -> list[dict]:
    import yaml  # declared in pyproject.toml

    cfg = yaml.safe_load(CONFIG.read_text())
    pages = (cfg.get("releases", {}) or {}).get("pages", []) or []
    for page in pages:
        if not {"name", "url", "link_pattern"} <= set(page):
            raise ValueError(f"page entry needs name, url and link_pattern: {page}")
    return pages


def _text(fragment: str) -> str:
    return " ".join(html.unescape(TAG.sub(" ", fragment)).split())


def extract(
    page_html: str, base_url: str, link_pattern: str, exclude=(), limit: int = DEFAULT_MAX
) -> list[dict]:
    """Article links in page order: [{url, title, summary}], deduplicated, at most `limit`."""
    pattern = re.compile(link_pattern)
    excluded = set(exclude or ())
    found: dict[str, dict] = {}
    for m in ANCHOR.finditer(page_html):
        href = html.unescape(m.group("href")).split("#")[0]
        if not pattern.search(href) or href.rstrip("/").rsplit("/", 1)[-1] in excluded:
            continue
        url = urllib.parse.urljoin(base_url, href)
        body = m.group("body")
        heading = HEADING.search(body)
        para = PARAGRAPH.search(body)
        entry = found.setdefault(url, {"url": url, "title": "", "summary": "", "headline": False})
        # The same article is often linked twice (image, then headline). Keep the most
        # informative pieces from either link.
        if heading and not entry["headline"]:
            entry["title"], entry["headline"] = _text(heading.group("t")), True
        elif not entry["title"]:
            entry["title"] = _text(body)[:140]
        if para and not entry["summary"]:
            entry["summary"] = _text(para.group("t"))
    entries = list(found.values())
    # On a news index an article card has a headline; section and category links
    # ("Product", "Partnerships") share the URL shape but not the headline. Prefer cards
    # whenever the page has any.
    if any(e["headline"] for e in entries):
        entries = [e for e in entries if e["headline"]]
    out = [
        {"url": e["url"], "title": e["title"], "summary": e["summary"]}
        for e in entries
        if e["title"] and valid_url(e["url"])
    ]
    return out[:limit]


def fetch_page(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ai-radar/0.2"})
    body = fetch_bytes(req).decode("utf-8", errors="replace")
    if "<a" not in body.lower():
        raise ValueError("response has no links; not a usable news page")
    return body


def main() -> dict:
    batch = SourceBatch("lab_pages")
    items = []

    def fetch_items(page):
        entries = extract(
            fetch_page(page["url"]),
            page["url"],
            page["link_pattern"],
            page.get("exclude", ()),
            int(page.get("max", DEFAULT_MAX)),
        )
        if not entries:
            raise ValueError("no article links matched; the page layout may have changed")
        for e in entries:
            yield make_item(
                id=f"blog:{e['url']}",
                category="releases",
                title=e["title"],
                url=e["url"],
                source=page["name"],
                raw_summary=e["summary"],
            )

    for page in load_pages():
        items.extend(batch.fetch(page["name"], fetch_items, page))
    written = write_items("releases", items)
    print(f"[lab_pages] {written} observations written")
    return batch.finish(written)


if __name__ == "__main__":
    main()
