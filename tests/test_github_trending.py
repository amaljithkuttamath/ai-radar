"""GitHub search must look for new projects, not the all-time most-starred ones."""

from __future__ import annotations

from collectors import github_trending


def test_search_is_bounded_by_creation_date():
    q = github_trending.search_query("llm", "2026-11-06", "2026-10-09")
    assert "created:>2026-10-09" in q and "pushed:>2026-11-06" in q


def test_item_carries_when_the_repository_was_created():
    item = github_trending.to_item(
        {
            "full_name": "a/b",
            "html_url": "https://github.com/a/b",
            "created_at": "2026-11-01T00:00:00Z",
            "pushed_at": "2026-11-07T00:00:00Z",
            "stargazers_count": 900,
        }
    )
    assert item["created"] == "2026-11-01T00:00:00Z"
