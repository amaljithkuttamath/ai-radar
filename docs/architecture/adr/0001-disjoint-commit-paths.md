# ADR-0001. Disjoint commit paths (two-stage pipeline)

**Status.** Accepted, 2026-06.

## Context

Signal ingestion and editorial synthesis have different cost profiles, cadence needs, and failure modes. Bundling them in one workflow means a rate limit on one RSS feed can consume model tokens on a partial corpus; a manual re-distill has to re-collect; and retry semantics conflate two concerns.

Splitting means multiple workflows write to `main`. Without a convention, they race, produce merge conflicts, and force retry logic in every commit step.

## Decision

Two workflows plus one external grader. Each declares its write scope. Sets are disjoint by construction.

- `collect-corpus.yml` writes only `data/seen.json` and uploads the `corpus-raw` artifact.
- `distill.yml` writes only `reports/**` and `data/state.json`.
- Grader writes only `evals/**` (and files issues).

Concurrency groups prevent a workflow from racing itself. Disjoint write sets prevent workflows from racing each other. See [`../diagrams/state-ownership.svg`](../diagrams/state-ownership.svg).

## Consequences

**Positive.**
- Rerunning distill against the same corpus is free of fetch cost.
- A failing feed cannot cost model tokens.
- Concurrent runs are safe by construction. No retry logic in commit steps beyond a defensive `git pull --rebase`.
- Reviewers enforce the invariant by grepping for `git add` in workflow YAMLs.

**Negative.**
- Two workflows and one external task instead of one.
- Adding a new workflow requires declaring its write scope up front. Not a real cost; it's forcing a design decision that would need to happen anyway.
- If a future refactor blurs the boundary (say, distill writes to `evals/`), the invariant breaks silently. Mitigation: this ADR is the review checklist.
- Manual `workflow_dispatch` on distill without a preceding collect produces a "quiet window" digest. Correct behaviour; documented in the flow diagram in [`../../architecture.md`](../../architecture.md#daily-flow).
