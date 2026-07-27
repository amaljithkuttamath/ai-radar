"""Delivery: which file actually gets emailed.

`reports/` holds three kinds of `.md`: dated digests, the generated `README.md` index, and
`latest.md`. Only the first kind is a report, and picking the wrong one sends a table of
contents to every subscriber.
"""
from __future__ import annotations

import pytest

from distill import deliver


@pytest.fixture
def reports(tmp_path, monkeypatch):
    monkeypatch.setattr(deliver, "REPORTS", tmp_path)
    monkeypatch.delenv("RADAR_REPORT_PATH", raising=False)
    return tmp_path


def test_the_newest_dated_digest_is_the_report(reports):
    for day in ("2026-07-25", "2026-07-26", "2026-07-27"):
        (reports / f"{day}-digest.md").write_text(f"# AI Radar — {day}\n")
    assert deliver.latest_report().name == "2026-07-27-digest.md"


def test_the_generated_index_is_never_the_report(reports):
    """README.md sorts above every dated digest, so a plain `*.md` glob picked the index
    whenever reindex hadn't (or couldn't) leave a latest.md behind."""
    (reports / "2026-07-27-digest.md").write_text("# AI Radar — 2026-07-27\n")
    (reports / "README.md").write_text("# AI Radar — report index\n")
    assert deliver.latest_report().name == "2026-07-27-digest.md"


def test_latest_md_is_not_mistaken_for_a_digest(reports):
    """latest.md is a copy of the newest digest; sending the copy works by accident, but
    only while it exists and is current."""
    (reports / "2026-07-26-digest.md").write_text("# AI Radar — 2026-07-26\n")
    (reports / "latest.md").write_text("# AI Radar — 2026-07-20\n")  # stale copy
    assert deliver.latest_report().name == "2026-07-26-digest.md"


def test_no_digests_means_nothing_to_send(reports):
    (reports / "README.md").write_text("# AI Radar — report index\n")
    assert deliver.latest_report() is None


def test_an_explicit_path_wins(reports, monkeypatch):
    (reports / "2026-07-27-digest.md").write_text("# AI Radar — 2026-07-27\n")
    monkeypatch.setenv("RADAR_REPORT_PATH", str(reports / "hand-written.md"))
    assert deliver.latest_report().name == "hand-written.md"


def test_main_is_a_clean_no_op_when_email_is_not_configured(reports, monkeypatch, capsys):
    """An unconfigured delivery must never fail the pipeline — the digest is already written."""
    monkeypatch.delenv("RADAR_EMAIL_TO", raising=False)
    deliver.main()
    assert "not configured" in capsys.readouterr().out
