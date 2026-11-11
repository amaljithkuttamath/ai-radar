"""News-page collector for labs without RSS (collectors/lab_pages.py)."""

from __future__ import annotations

import pytest

from collectors import lab_pages
from collectors.common import validate_item

PAGE = """
<html><body>
<nav><a href="/news/announcements">Announcements</a><a href="/news/product">Product</a></nav>
<a href="/news/big-model-launch"><img src="x.png"></a>
<a href="/news/big-model-launch"><h3 class="t">Introducing Big Model 5</h3><p>Our most capable model &amp; more.</p></a>
<a href="/news/policy-update#top"><h3>A policy update</h3><p>Details.</p></a>
<a href="https://other.example/news/elsewhere"><h3>Off-site</h3></a>
<a href="/careers"><h3>We are hiring</h3></a>
<a href="/news/third"><h2>Third post</h2></a>
</body></html>
"""


def test_extracts_article_cards_in_page_order():
    got = lab_pages.extract(PAGE, "https://lab.example/news", r"^/news/[a-z0-9-]+$", ["announcements"], 5)
    assert [e["url"] for e in got] == [
        "https://lab.example/news/big-model-launch",
        "https://lab.example/news/policy-update",
        "https://lab.example/news/third",
    ]
    assert got[0]["title"] == "Introducing Big Model 5"
    assert got[0]["summary"] == "Our most capable model & more."


def test_category_links_without_headlines_are_dropped():
    got = lab_pages.extract(PAGE, "https://lab.example/news", r"^/news/", [], 10)
    assert all("product" not in e["url"] for e in got)


def test_limit_caps_back_catalogue():
    assert len(lab_pages.extract(PAGE, "https://lab.example/news", r"^/news/", [], 1)) == 1


def test_main_emits_valid_release_items(monkeypatch):
    monkeypatch.setattr(
        lab_pages,
        "load_pages",
        lambda: [
            {
                "name": "Example Lab News",
                "url": "https://lab.example/news",
                "link_pattern": r"^/news/[a-z-]+$",
            }
        ],
    )
    monkeypatch.setattr(lab_pages, "fetch_page", lambda url: PAGE)
    written = {}
    monkeypatch.setattr(
        lab_pages, "write_items", lambda cat, items: len(written.setdefault(cat, list(items)))
    )
    result = lab_pages.main()
    assert result["status"] == "ok"
    items = written["releases"]
    assert items[0]["id"] == "blog:https://lab.example/news/big-model-launch"
    for item in items:
        validate_item({**item, "score": 0})


def test_a_layout_change_is_reported_not_silent(monkeypatch):
    monkeypatch.setattr(
        lab_pages,
        "load_pages",
        lambda: [{"name": "Lab", "url": "https://lab.example/news", "link_pattern": r"^/articles/"}],
    )
    monkeypatch.setattr(lab_pages, "fetch_page", lambda url: PAGE)
    monkeypatch.setattr(lab_pages, "write_items", lambda *a: 0)
    with pytest.raises(RuntimeError):
        lab_pages.main()


def test_configured_pages_are_well_formed():
    for page in lab_pages.load_pages():
        assert page["url"].startswith("https://")
