"""Tests for the blocked-domain ledger.

The point of these is that the ledger is *consumed*. Before this landed,
config/broken_sources.yaml was whitelisted, in CODEOWNERS, and named in the
coder contract as the A2 remediation path — while no code read it. A test suite
that only checked parsing would have passed against that broken state too, so
the load-bearing test here is test_ledger_is_wired_into_the_write_path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.blocklist import (  # noqa: E402
    filter_items,
    is_blocked,
    load_blocked_domains,
)


def write_ledger(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "broken_sources.yaml"
    p.write_text(body)
    return p


# ── the wiring, which is the whole point ──────────────────────────────────────


def test_ledger_is_wired_into_the_write_path():
    """common.write_items must consult the ledger.

    If this fails, the ledger has silently reverted to decorative: the coder's
    A2 fix would pass every check and change nothing.
    """
    source = (ROOT / "collectors" / "common.py").read_text()
    assert "filter_items" in source, "write_items no longer applies the blocklist"


def test_shipped_ledger_parses():
    """The committed config/broken_sources.yaml must be readable by its reader."""
    assert isinstance(load_blocked_domains(ROOT / "config" / "broken_sources.yaml"), set)


# ── matching ──────────────────────────────────────────────────────────────────


def test_bare_domain_entries(tmp_path):
    p = write_ledger(tmp_path, "blocked_domains:\n  - example.com\n")
    assert load_blocked_domains(p) == {"example.com"}


def test_dict_entries_with_metadata(tmp_path):
    """Agents are asked to cite evidence (I-04), so entries carry metadata."""
    p = write_ledger(
        tmp_path,
        """
blocked_domains:
  - domain: dead.example
    reason: "404 on all URLs"
    blocked: 2026-07-20
""",
    )
    assert load_blocked_domains(p) == {"dead.example"}


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.com/post", True),
        ("https://www.example.com/post", True),  # www stripped
        ("https://EXAMPLE.com/post", True),  # case-insensitive
        ("https://example.com:8443/post", True),  # port stripped
        ("https://blog.example.com/post", True),  # subdomain of a blocked domain
        ("https://notexample.com/post", False),  # substring, not a subdomain
        ("https://example.org/post", False),
        ("", False),
        ("not-a-url", False),
    ],
)
def test_is_blocked(url, expected):
    assert is_blocked(url, {"example.com"}) is expected


def test_filter_drops_only_blocked_items():
    items = [
        {"id": "a", "url": "https://example.com/1"},
        {"id": "b", "url": "https://good.example.org/2"},
        {"id": "c", "url": "https://blog.example.com/3"},
    ]
    assert [i["id"] for i in filter_items(items, {"example.com"})] == ["b"]


# ── fail-open: a bad ledger must never cost a day's digest ────────────────────


def test_missing_ledger_blocks_nothing(tmp_path):
    assert load_blocked_domains(tmp_path / "nope.yaml") == set()


def test_malformed_ledger_fails_open(tmp_path):
    """Unparseable YAML must not raise. The ledger suppresses known-bad sources;
    a typo in it should not take down collection entirely."""
    p = write_ledger(tmp_path, "blocked_domains: [unclosed\n")
    assert load_blocked_domains(p) == set()


def test_wrong_type_fails_open(tmp_path):
    p = write_ledger(tmp_path, "blocked_domains: not-a-list\n")
    assert load_blocked_domains(p) == set()


def test_empty_ledger_is_a_no_op():
    items = [{"id": "a", "url": "https://example.com/1"}]
    assert filter_items(items, set()) == items
