# ADR-0003. Eval loop runs out-of-repo

**Status.** Accepted, 2026-07.

## Context

The eval loop grades the pipeline's output. If a bug in the pipeline suppresses its own criticism (a synthesis prompt regression that also writes "everything is fine" and eval runs downstream of that), the loop has failed its purpose.

Options:

1. Eval as a step inside `distill.yml`.
2. Eval as a separate workflow in the same repo on its own cron.
3. Eval as an external scheduled task with cross-repo write access.

Option 1 fails independence. Option 2 shares the pipeline's runtime and secrets surface, and can't file cross-repo issues cleanly. Option 3 costs one PAT and one scheduled-task credit per day.

## Decision

The daily grader runs as a Perplexity scheduled task at 12:00 UTC. It uses a PAT scoped to `contents: write` + `issues: write` on `ai-radar` and `amaljithkuttamath.github.io`.

Time-based only, not triggered by `distill.yml`. A stale or missing digest produces the same observable signal (a low `X3 freshness` score, or an escalation for a missing digest).

## Consequences

**Positive.**
- A bug in `distill.yml` cannot suppress its own eval.
- Cross-repo issue filing works without hacks.
- Grader task instructions update without a PR to the pipeline.

**Negative.**
- One external dependency for eval.
- One PAT to rotate.
- Compromised grader token could push arbitrary content. Mitigated by rotation runbook and branch protection.

## Freshness edge case

Initial spec said "end silently if digest > 36h old." On 2026-07-04 the grader escalated at exactly 36.0h age. Fix: freshness check uses strict `>`, so exactly 36.0h is fresh. Recorded here so future runs don't rediscover the ambiguity.
