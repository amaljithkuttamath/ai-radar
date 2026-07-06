# ADR-0003. Eval loop runs out-of-repo

**Status.** Accepted, 2026-07.

## Context

The eval loop grades the pipeline's output. If a bug in the pipeline suppresses its own criticism (for example: a synthesis prompt regression that also writes "everything is fine" into the digest and eval is a downstream step), the loop has failed its purpose.

Options:

1. Eval as a step inside `distill.yml`.
2. Eval as a separate workflow in the same repo (`eval.yml`) on its own cron.
3. Eval as an external scheduled task with cross-repo write access.

Option 1 fails the independence requirement. Option 2 shares the same runtime, same permission surface, and same failure modes; it also can't file cross-repo issues cleanly (workflow tokens don't cross repos). Option 3 costs one PAT and one scheduled-task credit per day but preserves independence.

## Decision

The daily grader runs as a Perplexity scheduled task at 12:00 UTC. It uses a PAT scoped to `contents: write` + `issues: write` on `ai-radar` and `amaljithkuttamath.github.io`.

The grader is not triggered by `distill.yml`. Time-based only, so a stale or missing digest produces the same observable signal (a low `X3 freshness` score, or an escalation for a missing digest).

## Consequences

**Positive.**
- Bug in `distill.yml` cannot suppress its own eval.
- Cross-repo issue filing works without hacks.
- Grader can be updated (task instructions) without a PR to the pipeline.

**Negative.**
- One external dependency for the eval to run.
- One PAT to rotate.
- The grader has full context of the repo, so a compromised grader token could push arbitrary content. Mitigated by rotation runbook and by branch-protection review on any human-visible commits.

## Freshness edge case

The initial spec said "end silently if digest > 36h old." On 2026-07-04, the grader escalated at exactly 36.0h age. The fix: freshness check uses strict `>`, so exactly 36.0h is fresh. Documented here so future runs don't rediscover the ambiguity.
