# ADR-0005. Disjoint commit paths per workflow

**Status.** Accepted, 2026-06.

## Context

Multiple workflows write to `main`. Without a convention, two concurrent runs can race, produce merge conflicts, and require retry logic in every commit step.

Options:

1. Serialise all workflows with a single concurrency group.
2. Give each workflow its own concurrency group and rely on `git pull --rebase` at commit time to handle occasional races.
3. Design write scopes so that concurrent workflows literally cannot collide.

Option 1 is safe but wastes wall-clock time and blocks the reactive `workflow_run` trigger from firing during collect. Option 2 works most of the time but requires believing the rebase logic. Option 3 is a construction proof: if the sets don't overlap, no rebase is ever needed.

## Decision

Each workflow declares its write scope. Sets are disjoint by construction.

- `collect-corpus.yml` writes only `data/seen.json` and uploads the `corpus-raw` artifact.
- `distill.yml` writes only `reports/**` and `data/state.json`.
- Grader writes only `evals/**` (and files issues).

The state-ownership matrix is documented in [`diagrams/state-ownership.svg`](../diagrams/state-ownership.svg). The commit steps still run `git pull --rebase origin main || true` as a defensive line, but the rebase is never load-bearing.

## Consequences

**Positive.**
- Concurrent runs are safe by construction.
- No retry logic needed in commit steps beyond the defensive rebase.
- Reviewers can enforce the invariant by grepping for `git add` in workflow YAMLs.

**Negative.**
- Adding a new workflow requires declaring its write scope up front. Not a real cost; it's forcing a design decision that would need to happen anyway.
- If a future refactor blurs the boundary (say, distill starts writing to `evals/`), the invariant breaks silently. Mitigation: an ADR-mandated review of the ownership matrix on any workflow change.
