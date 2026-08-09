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

Exit codes:
  0  eval written, or the digest was stale and the run ended silently as specified
  1  escalation: a CORE input missing, an unbelievable age, a separation violation,
     a malformed verdict, or a schema failure
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from grader import artifacts, freshness, judge, links
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
    args = ap.parse_args(argv)

    reports = ROOT / "reports"
    digest_path = reports / "latest.md"

    # --- pull. Only two inputs are CORE; missing either halts. -------------
    digest = _read(digest_path)
    if digest is None:
        dated = sorted(reports.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-digest.md"))
        if not dated:
            print("[grader] ESCALATE: no digest found in reports/", file=sys.stderr)
            return 1
        digest_path = dated[-1]
        digest = _read(digest_path) or ""
        print(f"[grader] latest.md missing; graded {digest_path.name}", file=sys.stderr)

    if not (ROOT / "data" / "state.json").exists():
        print("[grader] ESCALATE: data/state.json is missing (CORE input)", file=sys.stderr)
        return 1

    # --- freshness ---------------------------------------------------------
    try:
        published, age_h = freshness.resolve(digest, root=ROOT)
    except freshness.Escalate as ex:
        print(f"[grader] ESCALATE: {ex}", file=sys.stderr)
        return 1

    print(f"[grader] digest published {published:%Y-%m-%d %H:%M}Z, age {age_h}h")

    if freshness.is_stale(age_h) and not args.force:
        # Ends silently and successfully. A stale digest is the pipeline's failure to
        # publish, not the grader's to score; writing a low eval would put the grader's
        # opinion of an absence into the trend. Detecting the absence is watchdog.yml's job.
        print(f"[grader] digest is stale ({age_h}h > {freshness.STALE_AFTER_H}h); "
              "ending silently without writing an eval.")
        return 0

    # --- enrich: observed link statuses before any model sees anything ------
    urls = links.extract(digest)
    broken = links.check(urls)
    ceiling = links.a2_ceiling(broken)
    unreachable = sum(1 for b in broken if b["status"] == 0)
    print(f"[grader] {len(urls)} links checked · {len(broken) - unreachable} broken · "
          f"{unreachable} unreachable from this runner · A2 ceiling {ceiling}")

    # --- score -------------------------------------------------------------
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
        print(f"[grader] ESCALATE: model separation violated.\n  {ex}", file=sys.stderr)
        return 1
    except judge.JudgeError as ex:
        print(f"[grader] ESCALATE: {ex}", file=sys.stderr)
        return 1

    # --- assemble + validate ----------------------------------------------
    date = (freshness.h1_date(digest) or published).strftime("%Y-%m-%d")
    ev = artifacts.assemble(
        date=date, mode=args.mode, grader_model=model,
        digest_commit_time=published, age_h=age_h, verdict=verdict,
        x3=freshness.x3_score(age_h), a2_ceiling=ceiling, broken=broken)

    try:
        artifacts.validate(ev)
    except artifacts.SchemaError as ex:
        print(f"[grader] ESCALATE: assembled eval fails the schema: {ex}", file=sys.stderr)
        return 1

    print(f"[grader] quality={ev['quality']['overall']} "
          f"experience={ev['experience']['overall']} overall={ev['overall']} "
          f"(grader_model={model})")

    if args.dry_run:
        print(json.dumps(ev, indent=2, ensure_ascii=False))
        return 0

    # --- write -------------------------------------------------------------
    written = artifacts.write_eval(ev)
    history = artifacts.load_history()
    (ROOT / "evals" / "README.md").write_text(artifacts.render_readme(history))
    appended = artifacts.append_backlog(artifacts.backlog_items(ev, date))
    print(f"[grader] wrote {', '.join(p.name for p in written)}, README.md"
          f"{', backlog.md' if appended else ''}")

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
