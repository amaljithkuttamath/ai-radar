"""Orchestration: `python -m grader`.

Runs the sequence `docs/operating/grader.md` describes — pull, freshness, enrich, score,
write — with the deterministic steps in code and exactly one model call for the eight
judgement dimensions.

This is a runner, not a scheduler. ADR-0003 keeps the eval loop's *execution* outside this
repo so a distill bug cannot suppress its own criticism, and that is unchanged: the
external scheduled task now invokes this instead of reconstructing the whole contract from
prose each morning. What moved in-repo is the implementation, which was the part that could
not be versioned, tested, or reviewed — and which nobody noticed had stopped running for
26 days.

Since ADR-0009 the scoring runs as a cascade. Tier 0 is deterministic, model-free and always
runs; tier 1 is the single model call. **Losing tier 1 degrades the eval's resolution, never
its existence.** Before that change, an unset `RADAR_GRADER_MODEL` produced no eval at all,
and so no issue, and so an empty coder queue — for 69 days, twice.

Exit codes:
  0  eval written (judged or deterministic), or the digest was stale and the run ended
     silently as specified
  1  escalation: a CORE input missing, an unbelievable age, or a schema failure. A missing
     model is NOT an escalation any more — it is a deterministic eval.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from grader import (archive, artifacts, attempts, deterministic, forecast, freshness,
                    judge, links, provenance, trusted)
from grader.separation import SeparationViolation

ROOT = Path(__file__).resolve().parent.parent


def _read(path: Path) -> str | None:
    try:
        return path.read_text()
    except OSError:
        return None


def previous_digest(reports: Path, current: Path) -> str | None:
    """The digest before today's, for A4. OPTIONAL per grader.md: absent is a valid state
    on a first run, and A4 falls back to scoring today's internal consistency."""
    dated = sorted(reports.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-digest.md"))
    dated = [p for p in dated if p.resolve() != current.resolve()]
    return _read(dated[-1]) if dated else None


def run(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="grader", description=__doc__)
    ap.add_argument("--mode", default="normal", choices=artifacts.VALID_MODES)
    ap.add_argument("--dry-run", action="store_true",
                    help="score and print, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="score a stale digest (>36h). Cannot reach past 72h: "
                         "eval-schema.md bounds age_hours_at_eval to [-12, 72], so no "
                         "valid eval exists for a digest older than that and the run "
                         "escalates instead. Use --mode recovery with this.")
    ap.add_argument("--tier0-only", action="store_true",
                    help="skip the model call entirely and write a deterministic eval. "
                         "What `eval-deterministic.yml` runs in CI, and what a pre-merge "
                         "shadow eval uses.")
    args = ap.parse_args(argv)

    def _log_attempt(**kw) -> None:
        """Record the attempt before returning, on every path except --dry-run.

        Wrapped so no early return can forget it: an attempt log with holes in it is worse
        than none, because the holes look like downtime.
        """
        if args.dry_run:
            return
        try:
            attempts.append(attempts.record(mode=args.mode, **kw))
        except (OSError, ValueError) as ex:      # never fail a run over its own logging
            print(f"[grader] could not record attempt: {ex}", file=sys.stderr)

    reports = ROOT / "reports"
    digest_path = reports / "latest.md"

    # --- pull. Only two inputs are CORE; missing either halts. -------------
    digest = _read(digest_path)
    if digest is None:
        dated = sorted(reports.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-digest.md"))
        if not dated:
            print("[grader] ESCALATE: no digest found in reports/", file=sys.stderr)
            _log_attempt(outcome="escalated", reason="no digest found in reports/")
            return 1
        digest_path = dated[-1]
        digest = _read(digest_path) or ""
        print(f"[grader] latest.md missing; graded {digest_path.name}", file=sys.stderr)

    if not (ROOT / "data" / "state.json").exists():
        print("[grader] ESCALATE: data/state.json is missing (CORE input)", file=sys.stderr)
        _log_attempt(outcome="escalated", reason="data/state.json missing (CORE input)")
        return 1

    # --- freshness ---------------------------------------------------------
    try:
        published, age_h = freshness.resolve(digest, root=ROOT)
    except freshness.Escalate as ex:
        print(f"[grader] ESCALATE: {ex}", file=sys.stderr)
        _log_attempt(outcome="escalated", reason=str(ex))
        return 1

    print(f"[grader] digest published {published:%Y-%m-%d %H:%M}Z, age {age_h}h")

    if freshness.is_stale(age_h) and not args.force:
        # Ends silently and successfully. A stale digest is the pipeline's failure to
        # publish, not the grader's to score; writing a low eval would put the grader's
        # opinion of an absence into the trend. Detecting the absence is watchdog.yml's job.
        print(f"[grader] digest is stale ({age_h}h > {freshness.STALE_AFTER_H}h); "
              "ending silently without writing an eval.")
        _log_attempt(outcome="stale", reason=f"digest age {age_h}h exceeds "
                                             f"{freshness.STALE_AFTER_H}h")
        return 0

    # --- enrich: observed link statuses before any model sees anything ------
    urls = links.extract(digest)
    broken = links.check(urls)
    ceiling = links.a2_ceiling(broken)
    unreachable = sum(1 for b in broken if b["status"] == 0)
    print(f"[grader] {len(urls)} links checked · {len(broken) - unreachable} broken · "
          f"{unreachable} unreachable from this runner · A2 ceiling {ceiling}")

    # --- tier 0: deterministic, model-free, always runs ---------------------
    tier0 = deterministic.evaluate(digest, age_h=age_h, broken=broken, link_count=len(urls))
    print(deterministic.summary_line(tier0))

    date = (freshness.h1_date(digest) or published).strftime("%Y-%m-%d")
    revs = provenance.revs()

    # --- the deferred check ------------------------------------------------
    # Settle the claims earlier digests made, then record today's. Runs before tier 1 and
    # independently of it: the one ground truth here must not depend on a model being
    # reachable, or it would go missing in exactly the weeks it is most needed.
    tracked = deterministic.load_tracked()
    if args.dry_run:
        fc = {"claims_recorded": len(forecast.open_claims(digest, tracked, date)),
              "claims_pending": None, "claims_settled": None,
              "forecast_accuracy": forecast.accuracy(
                  [c for c in forecast.load() if c.get("verdict")])}
    else:
        fc = forecast.update(digest, tracked, date)
    tier0["metrics"]["forecast_accuracy"] = fc["forecast_accuracy"]
    tier0["metrics"]["claims_open"] = fc["claims_recorded"]
    print(f"[grader] forecasts: {fc['claims_recorded']} recorded · accuracy "
          f"{'n/a' if fc['forecast_accuracy'] is None else format(fc['forecast_accuracy'], '.0%')}"
          f" over {fc['claims_settled'] or 0} settled claims")

    # --- tier 1: the one model call ----------------------------------------
    # Every failure here degrades to a deterministic eval instead of halting. The three
    # causes are not equivalent to a human — no model configured, a fence refusal, a
    # malformed verdict — so the reason is carried into the eval and the attempt log
    # rather than collapsed into "the grader didn't run".
    verdict, model, degraded_reason = None, "", ""
    if args.tier0_only:
        degraded_reason = "--tier0-only: model call skipped by request"
    else:
        rubric = _read(ROOT / "evals" / "rubric.md")
        if rubric is None:
            # OPTIONAL per grader.md: the contract embeds fallback anchors precisely so a
            # missing rubric degrades instead of halting.
            rubric = "(rubric.md unavailable — use the anchors embedded in the instructions)"
            print("[grader] rubric.md missing; using embedded anchors", file=sys.stderr)
        try:
            verdict, model = judge.judge(
                digest, rubric, age_h, broken,
                previous_digest(reports, digest_path))
        except SeparationViolation as ex:
            # Still not an escalation, and emphatically not a reason to grade anyway: the
            # fence refusing is the fence working (I-08). Panickssery et al. (2024) measured
            # what a same-family judge does to its own family's output.
            degraded_reason = f"separation fence refused: {ex}"
            print(f"[grader] DEGRADED: {degraded_reason}", file=sys.stderr)
        except judge.JudgeError as ex:
            degraded_reason = str(ex)
            print(f"[grader] DEGRADED: tier 1 unavailable — {degraded_reason}",
                  file=sys.stderr)

    # --- assemble + validate ----------------------------------------------
    trusted_reading = trusted.reading(tier0, fc)
    if verdict is None:
        ev = artifacts.assemble_deterministic(
            date=date, mode=artifacts.DETERMINISTIC, digest_commit_time=published,
            age_h=age_h, broken=broken, tier0=tier0, revs=revs,
            reason=degraded_reason, trusted=trusted_reading)
    else:
        ev = artifacts.assemble(
            date=date, mode=args.mode, grader_model=model,
            digest_commit_time=published, age_h=age_h, verdict=verdict,
            x3=freshness.x3_score(age_h), a2_ceiling=ceiling, broken=broken,
            tier0=tier0, revs=revs, trusted=trusted_reading)

    try:
        artifacts.validate(ev)
    except artifacts.SchemaError as ex:
        print(f"[grader] ESCALATE: assembled eval fails the schema: {ex}", file=sys.stderr)
        _log_attempt(outcome="escalated", reason=f"schema: {ex}", tier0=tier0)
        return 1

    if artifacts.is_judged(ev):
        print(f"[grader] quality={ev['quality']['overall']} "
              f"experience={ev['experience']['overall']} overall={ev['overall']} "
              f"(grader_model={model})")
    else:
        print(f"[grader] deterministic eval (no model judgement): {degraded_reason}")

    if args.dry_run:
        print(json.dumps(ev, indent=2, ensure_ascii=False))
        return 0

    # --- write -------------------------------------------------------------
    try:
        written = artifacts.write_eval(ev)
    except artifacts.Downgrade as ex:
        # Not an error: the judged runner already landed today. Exit 0 having logged the
        # attempt, so the CI tier-0 job stays green and the trend keeps the better eval.
        print(f"[grader] {ex}")
        _log_attempt(outcome="deterministic", reason=f"ratchet: {ex}", tier0=tier0)
        return 0
    history = artifacts.load_history()
    (ROOT / "evals" / "README.md").write_text(artifacts.render_readme(history))
    appended = artifacts.append_backlog(artifacts.backlog_items(ev, date))
    print(f"[grader] wrote {', '.join(p.name for p in written)}, README.md"
          f"{', backlog.md' if appended else ''}")

    # --- attribution + the brake -------------------------------------------
    # Rebuilt from the eval history rather than appended to, so it cannot drift from the
    # evals it summarises and cannot silently stop being written.
    arch = archive.build(history)
    retired_classes = archive.retired(arch)
    archive.write(arch, retired_classes)
    print(f"[grader] archive: {archive.render(arch, retired_classes)}")

    if finding := trusted.divergence(history):
        # Reported, never acted on here (ADR-0005's reporter/escalator split). Acting is
        # `scripts/automerge.py`'s job, which is also the only thing that can revert.
        print(f"[grader] GOODHART: {finding['detail']}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
                fh.write(f"goodhart={finding['metric']}\n")

    _log_attempt(outcome="judged" if artifacts.is_judged(ev) else "deterministic",
                 reason=degraded_reason, grader_model=model, tier0=tier0)
    prior = attempts.load()
    if prior:
        print(f"[grader] {attempts.summary(prior)}")

    reason = artifacts.should_file_issue(ev, history)
    if reason:
        # Filing is left to the caller: it needs a token and an issue API, and grader.md
        # throttles to one issue per 72h across two repos — state this runner does not
        # have. Emitting the reason on stdout keeps the decision auditable either way.
        print(f"[grader] ISSUE-WORTHY: {reason}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
                fh.write(f"issue_reason={reason}\n")
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
