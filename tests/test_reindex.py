"""Reading aids: nav headers, the index table, and the stable latest.md pointer.

reindex runs after every distill, so the property that matters most is idempotency — a nav
block that stacked on each run would corrupt every digest in the folder within a week.
"""
from __future__ import annotations

import pytest

from distill import reindex


@pytest.fixture
def reports(tmp_path, monkeypatch):
    d = tmp_path / "reports"
    d.mkdir()
    monkeypatch.setattr(reindex, "REPORTS", d)
    for day in ("2026-07-01", "2026-07-02", "2026-07-03"):
        (d / f"{day}-digest.md").write_text(
            f"# AI Radar — {day}\n\nThe window is quiet on {day}.\n\n## Main list\n\n- a thing\n")
    return d


def test_digests_are_listed_oldest_first(reports):
    assert [p.name for p in reindex.digest_files()] == [
        "2026-07-01-digest.md", "2026-07-02-digest.md", "2026-07-03-digest.md"]


def test_generated_files_are_not_mistaken_for_digests(reports):
    (reports / "README.md").write_text("# index")
    (reports / "latest.md").write_text("# AI Radar — 2026-07-03")
    assert all(p.name not in ("README.md", "latest.md") for p in reindex.digest_files())


def test_nav_links_neighbours_and_marks_the_ends(reports):
    reindex.write_nav(reindex.digest_files())
    oldest = (reports / "2026-07-01-digest.md").read_text()
    middle = (reports / "2026-07-02-digest.md").read_text()
    newest = (reports / "2026-07-03-digest.md").read_text()
    assert "← _oldest_" in oldest and "2026-07-02-digest.md" in oldest
    assert "2026-07-01-digest.md" in middle and "2026-07-03-digest.md" in middle
    assert "_newest_ →" in newest


def test_nav_is_idempotent(reports):
    for _ in range(3):
        reindex.write_nav(reindex.digest_files())
    body = (reports / "2026-07-02-digest.md").read_text()
    assert body.count(reindex.NAV_START) == 1
    assert body.count("# AI Radar — 2026-07-02") == 1


def test_topline_skips_the_heading_and_the_nav(reports):
    reindex.write_nav(reindex.digest_files())
    assert reindex.topline_of(reports / "2026-07-02-digest.md") == \
        "The window is quiet on 2026-07-02."


def test_latest_points_at_the_newest_digest(reports):
    reindex.main()
    assert "2026-07-03" in (reports / "latest.md").read_text()


def test_index_is_newest_first(reports):
    reindex.main()
    body = (reports / "README.md").read_text()
    assert body.index("2026-07-03") < body.index("2026-07-01")


def test_reindex_on_an_empty_folder_is_a_no_op(tmp_path, monkeypatch):
    monkeypatch.setattr(reindex, "REPORTS", tmp_path / "reports")
    reindex.main()
    assert not (tmp_path / "reports" / "README.md").exists()
