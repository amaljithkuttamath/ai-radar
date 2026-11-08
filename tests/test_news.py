"""News ordering: importance x freshness x relevance (distill/news.py).

The defect this exists to prevent is the one the archive shows: an evergreen repository
clears the lifetime-traction checks every day and led edition after edition, while a
frontier lab's own announcement (no stars, no upvotes) scored 1/5 and sat in the
watch-list. The integer score must stay untouched; only the order changes.
"""

from __future__ import annotations

from datetime import date

import pytest

from distill import news, synthesize

TODAY = date(2026, 11, 7)


def _item(iid, score, **kw):
    return {"id": iid, "score": score, "title": iid, "source": kw.pop("source", "arXiv"), **kw}


def test_freshness_follows_gravity_and_never_reaches_zero():
    assert news.freshness(0) == pytest.approx(1.0)
    assert news.freshness(1) == pytest.approx((2 / 3) ** 1.8)
    assert news.freshness(1) < 0.5 < news.freshness(0)
    assert 0 < news.freshness(30) < news.freshness(7) < news.freshness(3)


def test_age_is_zero_for_unknown_or_future_first_seen():
    assert news.age_days(None, TODAY) == 0
    assert news.age_days("not a date", TODAY) == 0
    assert news.age_days("2026-11-09", TODAY) == 0
    assert news.age_days("2026-10-24", TODAY) == 14


def test_momentum_counts_gain_not_lifetime_totals():
    big_flat = {"signals": {"gh_stars": 168_000}}
    flat_history = [news.magnitude(big_flat)] * 5
    assert news.momentum(big_flat, flat_history) == 0.0
    assert news.momentum(big_flat, None) == 0.0
    climbing = {"signals": {"gh_stars": 5_000}}
    assert news.momentum(climbing, [news.magnitude({"signals": {"gh_stars": 500}})]) > 0
    viral = {"signals": {"gh_stars": 10**9}}
    assert news.momentum(viral, [0.0]) == news.MOMENTUM_CAP


@pytest.mark.parametrize(
    "item,expected",
    [
        ({"id": "blog:x", "source": "OpenAI Blog"}, True),
        ({"id": "blog:x", "source": "Google DeepMind"}, True),
        ({"id": "blog:x", "source": "Microsoft Research"}, True),
        ({"id": "blog:https://www.anthropic.com/news/x", "source": "Anthropic News"}, True),  # lab_pages
        ({"id": "blog:x", "source": "TechCrunch AI"}, False),  # press, not first-hand
        ({"id": "blog:x", "source": "Simon Willison"}, False),
        ({"id": "arxiv:1", "source": "arXiv", "authors": ["OpenAI"]}, False),  # a paper, not a release
    ],
)
def test_lab_release_means_a_labs_own_announcement(item, expected):
    assert news.is_lab_release(item) is expected


def test_fresh_lab_announcement_outranks_evergreen_repo():
    evergreen = _item("ghrepo:huggingface/transformers", 4, signals={"gh_stars": 168_000})
    lab_post = _item("blog:https://openai.com/x", 1, source="OpenAI Blog")
    state = {
        evergreen["id"]: {
            "first_seen": "2026-10-24",
            "mag_history": [news.magnitude(evergreen)] * 7,
        }
    }
    news.annotate([evergreen, lab_post], state, TODAY)
    assert lab_post["news_rank"] > evergreen["news_rank"]
    assert evergreen["seen_before"] and evergreen["days_on_radar"] == 15
    assert lab_post["new_to_radar"] and not lab_post["seen_before"]
    # The score itself is evidence, and evidence does not change with ordering.
    assert (evergreen["score"], lab_post["score"]) == (4, 1)


def test_focus_match_is_a_multiplier_not_a_trump_card():
    a = _item("arxiv:a", 3, focus_match=True)
    b = _item("arxiv:b", 3)
    c = _item("arxiv:c", 5)
    news.annotate([a, b, c], {}, TODAY)
    assert c["news_rank"] > a["news_rank"] > b["news_rank"]


def test_carryover_is_never_new_to_radar():
    item = _item("arxiv:old", 3, carryover=True, first_seen="2026-11-01")
    news.annotate([item], {}, TODAY)
    assert not item["new_to_radar"]
    assert item["seen_before"]


def test_prompt_order_and_fields_follow_news_rank(monkeypatch):
    monkeypatch.setattr(synthesize, "_load_state", lambda: {})
    monkeypatch.setattr(synthesize, "compute_delta", lambda items: {"first_run": True})
    monkeypatch.setattr(synthesize, "story_arcs", lambda: [])
    old = _item("ghrepo:old/repo", 4, category="releases", url="https://github.com/old/repo")
    new = _item("arxiv:new", 2, category="research", url="https://arxiv.org/abs/1")
    old.update(news_rank=0.1, first_seen="2026-10-01", days_on_radar=38, seen_before=True)
    new.update(news_rank=2.0, first_seen="2026-11-07", days_on_radar=1, new_to_radar=True)
    _, user, n = synthesize.build_prompt([old, new])
    assert n == 2
    assert user.index('"arxiv:new"') < user.index('"ghrepo:old/repo"')
    assert '"seen_before": true' in user and '"days_on_radar": 38' in user
    assert "lab_release=true" in user  # the routing rule reaches the model


def test_template_fallback_routes_lab_releases_like_the_model_does():
    import json

    rows = [
        {
            "id": "blog:lab",
            "title": "Lab ships model",
            "url": "https://lab.example/a",
            "source": "OpenAI Blog",
            "category": "releases",
            "score": 1,
            "lab_release": True,
        },
        {
            "id": "blog:press",
            "title": "Press piece",
            "url": "https://press.example/b",
            "source": "TechCrunch AI",
            "category": "releases",
            "score": 1,
            "lab_release": False,
        },
    ]
    report = synthesize.call_template("", "CANDIDATES_JSON\n" + json.dumps(rows))
    main, watch = report.split("**Watch-list**")
    assert "Lab ships model" in main
    assert "Press piece" in watch and "Lab ships model" not in watch


def test_an_item_shown_in_an_earlier_digest_is_not_new_even_if_state_forgot_it():
    item = _item("ghrepo:a/b", 3, url="https://github.com/a/b")
    news.annotate([item], {}, TODAY, shown={"https://github.com/a/b": date(2026, 10, 1)})
    assert not item["new_to_radar"] and item["seen_before"]
    assert item["first_seen"] == "2026-10-01"
    fresh = _item("ghrepo:c/d", 3, url="https://github.com/c/d")
    news.annotate([fresh], {}, TODAY, shown={"https://github.com/a/b": date(2026, 10, 1)})
    assert fresh["new_to_radar"]


def test_an_old_project_that_starts_trending_is_not_news():
    """The example run: novu, FastGPT and CopilotKit were 'new to radar' and took the top
    of the page, though each repository is years old. Age counts from when the project was
    created, not from when the radar happened to notice it."""
    old_repo = _item("ghrepo:novuhq/novu", 3, created="2021-09-27T00:00:00Z")
    new_repo = _item("ghrepo:someone/fresh-agent", 3, created="2026-11-05T00:00:00Z")
    lab_post = _item("blog:https://lab.example/a", 1, source="Anthropic News")
    news.annotate([old_repo, new_repo, lab_post], {}, TODAY)
    assert old_repo["new_to_radar"]  # it is new to the radar...
    assert old_repo["days_on_radar"] == 1  # ...and the radar clock is unchanged
    assert old_repo["project_age_days"] > 1000
    # ...but it is not news, so it sinks under both a fresh project and a lab post.
    assert min(new_repo["news_rank"], lab_post["news_rank"]) > 10 * old_repo["news_rank"]
