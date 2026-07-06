# ADR-0001. Two-stage pipeline (collect / distill)

**Status.** Accepted, 2026-06.

## Context

Signal ingestion and editorial synthesis have different cost profiles, cadence needs, and failure modes.

- Fetching arXiv, HF Daily Papers, and RSS feeds is cheap and deterministic. It should happen often and be safe to rerun.
- Scoring the corpus and asking a model to synthesise a digest is the expensive, judgment-heavy step. It should happen once per interesting window and be replayable without repaying for the fetch.

Bundling both into one workflow means: a rate limit on one RSS feed can consume model tokens on a partial corpus; a manual re-distill has to re-collect; and the retry story conflates two concerns.

## Decision

Split the pipeline into two workflows.

- `collect-corpus.yml` fetches sources, normalises to the Item schema, dedups via `seen.json`, and uploads `data/raw/` as an artifact. No model calls.
- `distill.yml` reads the artifact, scores, re-ranks, diffs, synthesises, reindexes, and optionally emails.

## Consequences

**Positive.**
- Rerunning distill against the same corpus is free of fetch cost.
- A failing feed cannot cost model tokens.
- Retry semantics per workflow are clean.
- The corpus stays gitignored; the repo doesn't grow with raw items.

**Negative.**
- Two workflow YAMLs instead of one.
- Cross-workflow artifact handoff needs a design decision (addressed in [ADR-0002](0002-reactive-workflow-run-trigger.md)).
- Manual `workflow_dispatch` on distill without a preceding collect will produce a "quiet window" digest. Documented in [05-flows.md](../05-flows.md#flow-2--manual-re-distill-no-re-collect).
