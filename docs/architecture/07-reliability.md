# 07. Reliability

## SLIs and SLOs

The system's job is a daily newsletter, so the SLOs are worded in terms of "digest quality" not "uptime."

| SLI | Definition | SLO |
|-----|------------|-----|
| Freshness | Hours from collect start to grader-observed digest publish | ≤ 6h on 95% of days |
| Coverage | 1 − (missed stories / important stories from last 24h) | ≥ 0.75 rolling 30-day mean |
| Source integrity | (URLs that HEAD-check 200) / (URLs in Main list) | ≥ 0.98 rolling 30-day mean |
| Rubric floor | min score across all 10 dims | ≥ 3.0 on 90% of days |
| Broken issue backlog | Open issues authored by `radar-eval-bot` | ≤ 3 at any time |

The grader emits these directly. Trend in [`evals/README.md`](../../evals/README.md).

## Failure modes and blast radius

Structured as (mode, cause, blast radius, detection, response).

### F1. Single-source collect failure

**Cause.** Feed is 500ing, hit rate limit, or shape changed.

**Blast radius.** That source's items are missing for the day. Other sources unaffected.

**Detection.** Grader `A5 coverage` drops if the missed items were important.

**Response.** No action for a one-day blip. Persistent regression (3 days ≤ 3) files an issue via the grader.

### F2. Collect commit conflict

**Cause.** Race between `collect-corpus` and `distill` on `main`. Should be impossible given disjoint write paths; this documents the defensive line.

**Blast radius.** One commit rejected. Next run picks up.

**Detection.** Workflow log.

**Response.** `git pull --rebase` in the commit step is the mitigation. If a conflict actually occurs, it's a bug in the write-scope contract; file it and fix the offending path.

### F3. Distill model call fails

**Cause.** Provider 5xx, rate limit, timeout.

**Blast radius.** No digest for the day. Previous digest remains authoritative on the site.

**Detection.** Workflow fails. GitHub Actions email to owner.

**Response.** Rerun `distill.yml` via `workflow_dispatch`. If persistent, swap `RADAR_MODEL_BACKEND` to `anthropic` or `ollama` and rerun.

### F4. Distill produces a bad digest

**Cause.** Prompt regression, model hallucination, upstream data poisoning.

**Blast radius.** Public site shows the bad digest until reverted.

**Detection.** Grader `A1 signal_density` or `A2 source_integrity` scores low; issue filed. Also human eyeball.

**Response.** `git revert <digest commit>`, `python -m distill.reindex`, commit. Site catches up on next page load.

### F5. Grader escalation

**Cause.** Ambiguous instruction or a genuinely blocking condition (missing core input, spec conflict).

**Blast radius.** No `evals/<date>.json` for the day. Trend table has a gap.

**Detection.** Escalation notification to owner.

**Response.** Resolve the ambiguity, patch the task instructions, dispatch a one-off recovery run. Historical example: [the 36h freshness edge case on 2026-07-04](../../evals/backlog.md).

### F6. Grader token expired or revoked

**Cause.** Manual revocation, expiry, or scope change.

**Blast radius.** No `evals/**` writes until fixed.

**Detection.** Two consecutive `[BACKGROUND CRON FAILED]` escalations. Auto-cancel after that per the task-scheduling contract.

**Response.** Regenerate token in GitHub settings, update the Perplexity task's credential, resume.

### F7. Site cannot fetch from `raw.githubusercontent.com`

**Cause.** GitHub raw-content incident or CDN edge failure.

**Blast radius.** Reader sees a spinner or a fallback message. Pipeline unaffected.

**Detection.** Site's client-side error handling. Grader `X4 failure_surface` scores low if the client cascades a partial fetch.

**Response.** Client should isolate each fetch. If it doesn't, that's a presentation-side backlog item.

## Degradation strategy

The system fails degraded, not off.

- **Missing feed** → digest ships without those items. Grader flags.
- **Missing model backend** → operator swaps backend via env, reruns.
- **Missing digest** → site keeps yesterday's; grader still runs and scores `X3 freshness` low.
- **Missing eval** → digest still ships; only the scorecard is missing that day.
- **Missing site** → repo is still the authoritative record.

Nothing is a hard dependency of everything else. Each layer can be down without cascading.

## Historical incidents

**2026-07-04. 36h freshness boundary.** Grader escalated because the spec said "end silently if >36h" and the actual age was exactly 36.0h. Root cause: ambiguous inequality. Fix: freshness check now uses `>` strictly; exact-36h is fresh. Documented in [ADR-0003](adr/0003-eval-loop-out-of-repo.md#freshness-edge-case).

**2026-07-04. Evals/ directory 404.** Grader treated a missing `evals/` as an error before the bootstrap PR merged. Root cause: not distinguishing OPTIONAL reads from CORE reads. Fix: OPTIONAL reads are now wrapped `2>/dev/null || true`. CORE reads still halt. Documented in the grader task spec.
