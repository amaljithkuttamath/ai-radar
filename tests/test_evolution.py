"""Behavioral tests for prompt experiments; model calls are replaced at the boundary."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from distill import synthesize
from distill import evolution


@pytest.fixture(autouse=True)
def configured_model(monkeypatch):
    monkeypatch.setenv("RADAR_SYNTHESIS_MODEL", "openai/gpt-4.1")


USER = 'TODAY=2026-10-22 WINDOW=48h\n[{"url":"https://example.org/paper"}]'
REPORT = "# AI Radar — 2026-10-22\n\n## Research\n\n[Paper](https://example.org/paper)"
CANDIDATE_REPORT = REPORT + "\nA concise, useful explanation."


def test_real_synthesis_captures_the_exact_input(tmp_path, monkeypatch):
    monkeypatch.setattr(synthesize, "ROOT", tmp_path)
    monkeypatch.setattr(synthesize, "BACKEND", "openai")
    monkeypatch.setattr(synthesize, "load_scored", lambda: [])
    monkeypatch.setattr(synthesize, "build_prompt", lambda *a, **kw: ("# Baseline", USER, 1))
    monkeypatch.setattr(synthesize, "call_openai_compat", lambda *a, **kw: REPORT)
    monkeypatch.setattr(synthesize, "save_state", lambda items: None)
    synthesize.main()
    cases = list((tmp_path / "data/evolution/cases").glob("*.json"))
    assert len(cases) == 1
    case = json.loads(cases[0].read_text())
    assert (case["system"], case["user"], case["report"]) == ("# Baseline", USER, REPORT)
    assert case["model"] == evolution.model_name("openai")


def test_capture_failure_does_not_break_publication(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(synthesize, "ROOT", tmp_path)
    monkeypatch.setattr(synthesize, "BACKEND", "openai")
    monkeypatch.setattr(synthesize, "load_scored", lambda: [])
    monkeypatch.setattr(synthesize, "build_prompt", lambda *a, **kw: ("# Baseline", USER, 1))
    monkeypatch.setattr(synthesize, "call_openai_compat", lambda *a, **kw: REPORT)
    monkeypatch.setattr(synthesize, "save_state", lambda items: None)
    (tmp_path / "data/evolution").mkdir(parents=True)
    (tmp_path / "data/evolution/cases").write_text("not a directory")
    synthesize.main()
    assert list((tmp_path / "reports").glob("*.md"))[0].read_text() == REPORT
    assert "capture" in capsys.readouterr().err.lower()


@pytest.fixture
def experiment(tmp_path):
    (tmp_path / "distill").mkdir()
    (tmp_path / "distill/digest.md").write_text("# Baseline\nBe accurate.")
    (tmp_path / "evals").mkdir()
    (tmp_path / "evals/rubric.md").write_text("# Rubric\nReward grounded useful summaries.")
    (tmp_path / "config").mkdir()
    (tmp_path / "config/profile.yaml").write_text("topics: [agents]")
    case = evolution.capture_case(tmp_path, "# Old prompt", USER, REPORT, "openai")
    candidate = tmp_path / "candidate.md"
    candidate.write_text("# Candidate\nBe accurate and concise.")
    return tmp_path, case, candidate


def run(experiment, monkeypatch, votes=("B", "A"), candidate_report=CANDIDATE_REPORT, supplied=True):
    root, case, candidate = experiment
    responses = iter(votes)

    def generate(backend, model, system, user):
        if system == evolution.PROPOSE:
            return json.dumps({"prompt": candidate.read_text(), "hypothesis": "Remove filler."})
        if backend == "anthropic":
            return json.dumps(
                {
                    "winner": next(responses),
                    "reason": "The linked paper is clearer.",
                    "lesson": "Keep actionable detail beside the primary source.",
                }
            )
        return candidate_report if system.startswith("# Candidate") else REPORT

    monkeypatch.setattr(evolution, "generate", generate)
    return evolution.run_experiment(
        root,
        [case],
        backend="openai",
        judge_backend="anthropic",
        candidate_path=candidate if supplied else None,
    )


def test_winner_saved_without_changing_production(experiment, monkeypatch):
    root, _, candidate = experiment
    before = (root / "distill/digest.md").read_text()
    result = run(experiment, monkeypatch)
    assert result["status"] == "keep"
    folder = root / "data/evolution/experiments" / result["id"]
    assert (folder / "candidate.md").read_text() == candidate.read_text()
    assert (folder / "cases/1/baseline.md").read_text() == REPORT
    assert (folder / "cases/1/candidate.md").read_text() == CANDIDATE_REPORT
    assert json.loads((folder / "result.json").read_text())["status"] == "keep"
    assert (root / "distill/digest.md").read_text() == before
    assert not (root / "reports").exists()
    assert not (root / "data/state.json").exists()
    entry = json.loads((root / "data/evolution/experiments.jsonl").read_text())
    assert entry["status"] == "keep"
    assert entry["lessons"]
    assert "+# Candidate" in (folder / "candidate.diff").read_text()


@pytest.mark.parametrize(
    "votes,status", [(("A", "B"), "discard"), (("tie", "tie"), "inconclusive"), (("B", "B"), "inconclusive")]
)
def test_loss_tie_and_position_bias(experiment, monkeypatch, votes, status):
    assert run(experiment, monkeypatch, votes=votes)["status"] == status


def test_rejected_candidate_is_remembered(experiment, monkeypatch):
    bad = REPORT + "\n[Invented](https://invented.example/claim)"
    result = run(experiment, monkeypatch, candidate_report=bad)
    assert result["status"] == "discard"
    assert "unprovided" in " ".join(result["cases"][0]["checks"]["candidate"])


def test_automatic_proposal(experiment, monkeypatch):
    result = run(experiment, monkeypatch, supplied=False)
    assert result["status"] == "keep"
    assert result["hypothesis"] == "Remove filler."
    assert result["model_calls"] == 5


@pytest.mark.parametrize(
    "reply", ["not json", '{"winner":"B"}', '{"winner":"candidate","reason":"x","lesson":"y"}']
)
def test_invalid_judgment_records_error(experiment, monkeypatch, reply):
    root, case, candidate = experiment
    monkeypatch.setattr(
        evolution,
        "generate",
        lambda backend, model, system, user: (
            reply
            if backend == "anthropic"
            else CANDIDATE_REPORT
            if system.startswith("# Candidate")
            else REPORT
        ),
    )
    result = evolution.run_experiment(
        root, [case], backend="openai", judge_backend="anthropic", candidate_path=candidate
    )
    assert result["status"] == "error"
    assert json.loads((root / "data/evolution/experiments.jsonl").read_text())["status"] == "error"


def test_model_failure_preserves_result_and_partial_output(experiment, monkeypatch):
    root, case, candidate = experiment

    def fail(backend, *args):
        if backend == "anthropic":
            raise RuntimeError("service unavailable")
        return CANDIDATE_REPORT if args[1].startswith("# Candidate") else REPORT

    monkeypatch.setattr(evolution, "generate", fail)
    result = evolution.run_experiment(
        root, [case], backend="openai", judge_backend="anthropic", candidate_path=candidate
    )
    assert result["status"] == "error"
    assert "service unavailable" in result["error"]
    assert (root / "data/evolution/experiments" / result["id"] / "cases/1/candidate.md").exists()


def test_same_family_judge_rejected_before_calls(experiment, monkeypatch):
    root, case, candidate = experiment

    def unexpected(*args):
        pytest.fail("must reject before model calls")

    monkeypatch.setattr(evolution, "generate", unexpected)
    with pytest.raises(ValueError, match="family"):
        evolution.run_experiment(
            root,
            [case],
            backend="openai",
            judge_backend="ollama",
            judge_model="gpt-oss:20b",
            candidate_path=candidate,
        )


def test_duplicate_cases_rejected(experiment, monkeypatch):
    root, case, candidate = experiment
    with pytest.raises(ValueError, match="Duplicate"):
        evolution.run_experiment(
            root, [case, case], backend="openai", judge_backend="anthropic", candidate_path=candidate
        )


@pytest.mark.parametrize(
    "report,issue",
    [
        ("# AI Radar — 2026-10-23\n[Paper](https://example.org/paper)", "date"),
        ("# AI Radar — 2026-10-22\nNothing to read.", "link"),
        (REPORT + "\nhttps://invented.example/x", "unprovided"),
    ],
)
def test_deterministic_grounding(report, issue):
    assert issue in " ".join(evolution.check_report(USER, report))


def test_identical_outputs_cannot_be_an_improvement(experiment, monkeypatch):
    result = run(experiment, monkeypatch, candidate_report=REPORT)
    assert result["status"] == "inconclusive"
    assert result["model_calls"] == 2


def test_previous_rejection_reaches_next_proposal(experiment, monkeypatch):
    root, _, candidate = experiment
    run(experiment, monkeypatch, votes=("A", "B"))
    result = run(experiment, monkeypatch, supplied=False)
    payload = json.loads(
        (root / "data/evolution/experiments" / result["id"] / "proposal-input.json").read_text()
    )
    assert len(payload["history"]) == 1
    assert payload["history"][0]["status"] == "discard"
    assert payload["history"][0]["lessons"]


def test_capture_is_idempotent_and_frozen(tmp_path):
    path = evolution.capture_case(tmp_path, "# Original", USER, REPORT, "openai")
    before = path.read_bytes()
    assert evolution.capture_case(tmp_path, "# Original", USER, REPORT, "openai") == path
    assert path.read_bytes() == before


def test_captures_final_request_after_payload_fallback(tmp_path, monkeypatch):
    import urllib.error

    monkeypatch.setattr(synthesize, "ROOT", tmp_path)
    monkeypatch.setattr(synthesize, "BACKEND", "openai")
    monkeypatch.setattr(synthesize, "load_scored", lambda: [])
    monkeypatch.setattr(
        synthesize,
        "build_prompt",
        lambda items, **kw: ("# Prompt", USER + ("\nReduced" if kw else "\nFull"), 1),
    )

    def generate(system, user):
        if user.endswith("Full"):
            raise urllib.error.HTTPError("https://example.org", 413, "too big", {}, None)
        return REPORT

    monkeypatch.setattr(synthesize, "call_openai_compat", generate)
    monkeypatch.setattr(synthesize, "save_state", lambda items: None)
    synthesize.main()
    path = next((tmp_path / "data/evolution/cases").glob("*.json"))
    assert json.loads(path.read_text())["user"].endswith("Reduced")


def test_case_budget_enforced(experiment):
    root, case, candidate = experiment
    with pytest.raises(ValueError, match="one and three"):
        evolution.run_experiment(
            root, [case] * 4, backend="openai", judge_backend="anthropic", candidate_path=candidate
        )


def test_url_as_link_label_is_valid():
    report = "# AI Radar — 2026-10-22\n[https://example.org/paper](https://example.org/paper)"
    assert evolution.check_report(USER, report) == []


@pytest.mark.parametrize(
    "votes,status",
    [
        (("B", "A", "tie", "tie", "B", "A"), "keep"),
        (("B", "A", "A", "B", "B", "A"), "discard"),
        (("B", "A", "B", "B", "B", "A"), "inconclusive"),
    ],
)
def test_three_case_campaign_aggregates_and_stays_bounded(experiment, monkeypatch, votes, status):
    root, first, candidate = experiment
    cases = [first] + [
        evolution.capture_case(root, "# Original", USER + f"\nCase {n}", REPORT, "openai") for n in (2, 3)
    ]
    decisions = iter(votes)

    def generate(backend, model, system, user):
        if system == evolution.PROPOSE:
            return json.dumps({"prompt": candidate.read_text(), "hypothesis": "Be concise."})
        if backend == "anthropic":
            return json.dumps(
                {
                    "winner": next(decisions),
                    "reason": "Source-linked insight.",
                    "lesson": "Use primary evidence.",
                }
            )
        return CANDIDATE_REPORT if system.startswith("# Candidate") else REPORT

    monkeypatch.setattr(evolution, "generate", generate)
    result = evolution.run_experiment(root, cases, backend="openai", judge_backend="anthropic")
    assert result["status"] == status
    assert result["model_calls"] == 13
    assert len(result["cases"]) == 3


def test_fixed_instructions_are_saved_for_audit(experiment, monkeypatch):
    root, _, _ = experiment
    result = run(experiment, monkeypatch, supplied=False)
    folder = root / "data/evolution/experiments" / result["id"]
    assert (folder / "judge-system.txt").read_text() == evolution.JUDGE
    assert (folder / "proposal-system.txt").read_text() == evolution.PROPOSE


def test_proposal_evidence_is_bounded_but_replay_stays_exact(experiment, monkeypatch):
    root, _, candidate = experiment
    large = USER + "\n" + "frozen evidence " * 3000
    cases = [
        evolution.capture_case(
            root,
            "# Old prompt\n" + "instructions " * 2000,
            large + str(n),
            REPORT + "old prose " * 2000,
            "openai",
        )
        for n in range(3)
    ]
    observed = []
    votes = iter(["B", "A"] * 3)

    def generate(backend, model, system, user):
        if system == evolution.PROPOSE:
            assert len(system) + len(user) < 48000
            payload = json.loads(user)
            assert "system" not in payload["cases"][0]
            assert "excerpt" in payload["cases"][0]["user"]
            return json.dumps({"prompt": candidate.read_text(), "hypothesis": "Reduce filler."})
        if backend == "anthropic":
            return json.dumps({"winner": next(votes), "reason": "Evidence", "lesson": "Lesson"})
        observed.append(user)
        return CANDIDATE_REPORT if system.startswith("# Candidate") else REPORT

    monkeypatch.setattr(evolution, "generate", generate)
    result = evolution.run_experiment(root, cases, backend="openai", judge_backend="anthropic")
    assert result["status"] == "keep"
    assert observed == [large + str(n) for n in range(3) for _ in range(2)]
