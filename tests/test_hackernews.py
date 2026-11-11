"""Hacker News collector: AI stories from the front page only, carrying hn_points."""

from __future__ import annotations

import pytest

from collectors import hackernews
from collectors.common import validate_item


def hit(title, url="https://example.com/post", points=120, oid="42"):
    return {
        "title": title,
        "url": url,
        "points": points,
        "objectID": oid,
        "num_comments": 9,
        "created_at": "2026-11-07T10:00:00Z",
    }


@pytest.mark.parametrize(
    "title",
    ["Show HN: A tiny LLM inference server", "Anthropic releases Claude update", "Fine-tuning on one GPU"],
)
def test_ai_stories_become_valid_items_with_points(title):
    item = hackernews.to_item(hit(title))
    assert item is not None
    validate_item({**item, "score": 0})
    assert item["signals"] == {"hn_points": 120}
    assert item["links"]["discussion"] == "https://news.ycombinator.com/item?id=42"
    assert item["category"] == "releases" and item["source"] == "Hacker News"


@pytest.mark.parametrize(
    "entry",
    [
        hit("A history of the bicycle"),  # not AI
        hit("Our travel agent model of the week"),  # 'agent'/'model' alone are not AI terms
        hit("New LLM benchmark", points=5),  # below the noise floor
        hit("Ask HN: favourite LLM?", url=None),  # no outbound link
        hit(""),
    ],
)
def test_noise_is_dropped(entry):
    assert hackernews.to_item(entry) is None


def test_malformed_response_is_an_error(monkeypatch):
    monkeypatch.setattr(hackernews, "fetch_json", lambda req: {"nope": []})
    with pytest.raises(ValueError):
        hackernews.fetch()


def test_main_writes_only_ai_stories(monkeypatch):
    written = {}
    monkeypatch.setattr(hackernews, "fetch", lambda: [hit("LLM agents in prod"), hit("Gardening tips")])
    monkeypatch.setattr(
        hackernews, "write_items", lambda cat, items: written.setdefault(cat, list(items)) and len(items)
    )
    result = hackernews.main()
    assert [i["title"] for i in written["releases"]] == ["LLM agents in prod"]
    assert result["status"] == "ok"
