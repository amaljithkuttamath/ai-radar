# ADR-0002. Reactive `workflow_run` trigger for distill

**Status.** Accepted, 2026-06.

## Context

Given [ADR-0001](0001-disjoint-commit-paths.md), distill needs to run after collect finishes. Options:

1. Cron distill at a fixed offset after collect (e.g. `0 13 * * *`, two hours later).
2. Poll for a completion marker in the repo.
3. Trigger distill on `workflow_run` when collect completes.

Option 1 requires guessing how long collect takes. If sources are slow one day, distill sees a partial corpus. Option 2 burns Actions minutes on polling. Option 3 is push, not pull.

## Decision

Distill uses `on.workflow_run` with `workflows: ["collect-corpus"]` and `types: [completed]`. It gates on `github.event.workflow_run.conclusion == 'success'` for automatic runs, and always runs on `workflow_dispatch`.

The artifact download uses `run-id: ${{ github.event.workflow_run.id }}` so distill grabs the artifact from the triggering run, not any historical one.

## Consequences

**Positive.**
- No arbitrary gap between collect and distill.
- Artifact provenance is exact.
- No third-party action for cross-workflow artifact discovery.
- Manual `workflow_dispatch` still works for re-distilling without re-collecting.

**Negative.**
- `workflow_run` events don't appear in the "Actions" filter UI as clearly as scheduled ones. Workflow header comments direct on-call to look at collect first.
- A manual `workflow_dispatch` against a fresh checkout with no local `data/raw/` produces a "quiet window" digest. Correct, but surprising the first time you see it.
