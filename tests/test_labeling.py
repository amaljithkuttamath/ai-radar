"""Tests for the labeling pipeline: Atom parsing, the train/holdout split, validation.

The network call itself is not exercised here — `collectors/arxiv.py` already talks to
the same endpoint in CI. What these cover is everything that can silently corrupt a
training set without failing loudly: an entry matched to the wrong id, a holdout row
drifting into training, or a malformed label being coerced into a plausible one.
"""

from __future__ import annotations

import json

from labeling import fetch_abstracts as fetch
from labeling import teacher_label as teacher

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.11111v2</id>
    <title>A Study of
      Wrapped Titles</title>
    <summary>First
      abstract text.</summary>
    <published>2024-01-20T00:00:00Z</published>
    <category term="cs.LG"/>
    <category term="stat.ML"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.22222</id>
    <title>No Abstract Here</title>
    <summary>   </summary>
    <published>2024-01-21T00:00:00Z</published>
    <category term="cs.CL"/>
  </entry>
</feed>"""


def test_strip_version():
    assert fetch.strip_version("2401.12345v2") == "2401.12345"
    assert fetch.strip_version("2401.12345") == "2401.12345"


def test_parse_keys_by_versionless_id_and_unwraps_text():
    records = fetch.parse_batch(ATOM.encode())
    assert "2401.11111" in records, "version suffix must be stripped to match seen.json"
    record = records["2401.11111"]
    assert record["title"].startswith("A Study of") and "Wrapped Titles" in record["title"]
    assert "\n" not in record["title"] and "\n" not in record["abstract"]
    assert record["primary_category"] == "cs.LG"


def test_parse_drops_entries_with_no_abstract():
    records = fetch.parse_batch(ATOM.encode())
    assert "2401.22222" not in records, "an empty abstract is nothing to label"


def test_missing_ids_are_unresolved_not_misaligned():
    """arXiv omits unknown ids, so results must be looked up by id, never by position."""
    records = fetch.parse_batch(ATOM.encode())
    requested = ["2401.00000", "2401.11111"]
    resolved = [i for i in requested if i in records]
    assert resolved == ["2401.11111"]


def test_done_ids_tolerates_a_torn_final_line(tmp_path):
    path = tmp_path / "out.jsonl"
    path.write_text('{"id": "a"}\n{"id": "b"}\n{"id": "c"')
    assert teacher.done_ids(path) == {"a", "b"}


def test_holdout_split_is_deterministic_and_disjoint():
    ids = [f"24{n:02d}.{n:05d}" for n in range(2000)]
    first = {i for i in ids if teacher.is_holdout(i, 15)}
    second = {i for i in ids if teacher.is_holdout(i, 15)}
    assert first == second, "the split must not move between runs"
    train = {i for i in ids if not teacher.is_holdout(i, 15)}
    assert first & train == set(), "train and holdout must be provably disjoint"
    assert 0 < len(first) < len(ids) * 0.05


def test_holdout_membership_is_stable_as_the_corpus_grows():
    """New papers arriving daily must not move an existing row from eval into train."""
    before = {i: teacher.is_holdout(i, 15) for i in ("2401.00001", "2401.00002")}
    after = {i: teacher.is_holdout(i, 15) for i in
             ("2401.00001", "2401.00002", "2409.99999", "2409.88888")}
    assert all(after[i] == before[i] for i in before)


def test_extract_json_survives_fences_and_preamble():
    assert teacher.extract_json('Here you go:\n```json\n{"score": 3}\n```') == {"score": 3}


def test_validate_accepts_a_well_formed_label():
    label = teacher.validate(
        {"score": 4, "topic": "agents", "relevant": True, "score_why": "x"},
        ["agents"],
    )
    assert label["score"] == 4 and label["topic"] == "agents" and label["relevant"] is True


def test_validate_rejects_out_of_range_and_wrong_types():
    for bad in ({"score": 6, "topic": "agents", "relevant": True},
                {"score": "4", "topic": "agents", "relevant": True},
                {"score": True, "topic": "agents", "relevant": True},
                {"score": 4, "topic": "astrology", "relevant": True},
                {"score": 4, "topic": "agents", "relevant": "yes"}):
        try:
            teacher.validate(bad, ["agents"])
        except ValueError:
            continue
        raise AssertionError(f"validate accepted a malformed label: {bad}")


def test_validate_allows_none_topic():
    assert teacher.validate(
        {"score": 1, "topic": "none", "relevant": False}, ["agents"])["topic"] == "none"


def test_prompt_carries_the_abstract_and_every_option():
    prompt = teacher.build_prompt(
        {"title": "T", "abstract": "A body of text"}, ["agents", "evals"])
    assert "A body of text" in prompt
    assert "agents" in prompt and "evals" in prompt and "none" in prompt
    assert json.dumps(["agents", "evals", "none"]) in prompt
