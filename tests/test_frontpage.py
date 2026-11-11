"""Reader frontpage: Yesterday (README block), This week, This month.

The properties that matter: a story is "new" only on the day it first appears; recaps
lead with what arrived in the period, not with repeats carried in; the README block is
replaced in place and never written when its markers are missing; tab links resolve from
each page's own folder.
"""

from __future__ import annotations

from datetime import date

import pytest

from distill import frontpage


def digest(day: str, main: list[tuple[str, str, int]], still=(), opening="A quiet day."):
    lines = [
        "<!-- radar:nav -->",
        "`radar` · [index](README.md)",
        "<!-- /radar:nav -->",
        "",
        f"# AI Radar — {day}",
        "",
        opening,
        "",
        "## Main list",
        "",
    ]
    for title, url, score in main:
        lines += [f"**[{title}]({url})** · {score}/5  ", f"{title} does a thing. More detail here.", ""]
    if still:
        lines += ["## Still developing", ""]
        lines += [f"**[{t}]({u})** · {s}/5 — still going." for t, u, s in still]
    return "\n".join(lines) + "\n"


@pytest.fixture
def reports(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    old = ("Evergreen repo", "https://github.com/big/repo", 4)
    (d / "2026-10-20-digest.md").write_text(digest("2026-10-20", [old]))
    (d / "2026-11-05-digest.md").write_text(
        digest("2026-11-05", [old, ("Agent benchmark", "https://arxiv.org/abs/1", 3)])
    )
    (d / "2026-11-06-digest.md").write_text(
        digest("2026-11-06", [old, ("Robot policy", "https://arxiv.org/abs/2", 4)])
    )
    (d / "2026-11-07-digest.md").write_text(
        digest(
            "2026-11-07",
            [("Lab launch", "https://lab.example/launch", 2), ("Robot policy", "https://arxiv.org/abs/2", 4)],
            still=[old],
            opening="A lab shipped something and robots kept moving.",
        )
    )
    (d / "README.md").write_text("# index\n")
    (d / "latest.md").write_text("# AI Radar — 2026-11-07\n")
    return d


def test_parses_items_scores_and_first_sentence(reports):
    d = frontpage.parse_digest(reports / "2026-11-07-digest.md")
    assert [(i["title"], i["score"]) for i in d["main"]] == [("Lab launch", 2), ("Robot policy", 4)]
    assert d["main"][0]["blurb"] == "Lab launch does a thing."
    assert d["still"][0]["url"] == "https://github.com/big/repo"
    assert d["opening"].startswith("A lab shipped")


def test_parses_heading_style_items():
    text = "# AI Radar — 2026-11-07\n\nx\n\n## Main list\n\n### 1. [T](https://e.x/1) · 3/5\nBody one.\n"
    assert frontpage._items(frontpage._section(text, "Main list"))[0]["score"] == 3


def test_generated_pages_are_not_digests(reports):
    (reports / "week.md").write_text("# AI Radar\n")
    assert all(d["path"].name.endswith("-digest.md") for d in frontpage.load_digests(reports))


def test_first_seen_is_the_first_edition_that_linked_it(reports):
    seen = frontpage.first_seen(frontpage.load_digests(reports))
    assert seen["https://github.com/big/repo"] == date(2026, 10, 20)
    assert seen["https://arxiv.org/abs/2"] == date(2026, 11, 6)


def test_yesterday_separates_new_from_still_unfolding(reports):
    digests = frontpage.load_digests(reports)
    block = frontpage.render_yesterday(digests, frontpage.first_seen(digests))
    new, unfolding = block.split("### Still unfolding")
    assert "Lab launch" in new and "Robot policy" in new  # first seen within two days
    assert "Evergreen repo" not in new
    assert "Evergreen repo" in unfolding and "day 19" in unfolding
    assert block.startswith("**Yesterday** · [This week](reports/week.md) · [This month](reports/month.md)")
    assert "[Read the full briefing](reports/2026-11-07-digest.md)" in block


def test_week_leads_with_stories_that_arrived_this_week(reports):
    digests = frontpage.load_digests(reports)
    page = frontpage.render_period(digests, frontpage.first_seen(digests), 7, "This week")
    stories = page.split("### The stories that mattered")[1].split("###")[0]
    assert "Evergreen repo" not in stories  # carried in from October
    assert stories.index("Robot policy") < stories.index("Agent benchmark")  # 2 editions x 4 beats 1 x 3
    assert "[Yesterday](../README.md) · **This week** · [This month](month.md)" in page


def test_month_reports_topic_moves_and_a_chart(reports):
    digests = frontpage.load_digests(reports)
    page = frontpage.render_period(digests, frontpage.first_seen(digests), 30, "This month")
    assert "### Stories with staying power" in page
    assert "**This month**" in page


def test_topic_changes_need_enough_mentions_and_report_direction():
    cur = [{"text": "robot robot robot agent"}]
    prev = [{"text": "agent"}]
    rows = {r["topic"]: r for r in frontpage.topic_changes(cur, prev)}
    assert frontpage.describe_change(rows["Robotics"]["ratio"]).startswith("Up")
    assert frontpage.describe_change(rows["Agents"]["ratio"]) == "Steady"
    assert "Diffusion models" not in rows  # never mentioned: not a trend
    assert frontpage.describe_change(0.4) == "Down 60%"


def test_readme_block_is_replaced_in_place_and_idempotent(tmp_path, reports):
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# Top\n\n{frontpage.README_START}\nSTALE-BLOCK\n{frontpage.README_END}\n\n## Footer\n"
    )
    frontpage.main(reports, readme)
    first = readme.read_text()
    assert first.startswith("# Top") and first.rstrip().endswith("## Footer")
    assert "STALE-BLOCK" not in first and "Lab launch" in first
    frontpage.main(reports, readme)
    assert readme.read_text() == first
    assert (reports / "week.md").exists() and (reports / "month.md").exists()


def test_readme_without_markers_is_left_alone(tmp_path, reports):
    readme = tmp_path / "README.md"
    readme.write_text("# Someone's fork\n")
    frontpage.main(reports, readme)
    assert readme.read_text() == "# Someone's fork\n"


def test_reindex_builds_the_frontpage(reports, monkeypatch):
    from distill import reindex

    monkeypatch.setattr(reindex, "REPORTS", reports)
    reindex.main()
    assert "Lab launch" in (reports / "week.md").read_text()


def test_no_digests_is_a_no_op(tmp_path):
    empty = tmp_path / "reports"
    empty.mkdir()
    frontpage.main(empty, tmp_path / "README.md")
    assert not (empty / "week.md").exists()
