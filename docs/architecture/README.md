# AI Radar. Architecture

This is the design doc set. Reading order below. Each file stands alone; skim what you need.

| # | Doc | What it covers | Read if |
|---|-----|----------------|---------|
| 00 | [Context (C4 L1)](00-context.md) | System in its environment, actors, external systems, trust boundaries | You're new to the repo |
| 01 | [Containers (C4 L2)](01-containers.md) | Deployable units, tech stack per unit, protocols between them | You're planning a change that crosses a container |
| 02 | [Distill internals (C4 L3)](02-components-distill.md) | Module DAG inside the distill container, per-module invariants | You're touching `distill/` |
| 03 | [Eval internals (C4 L3)](03-components-eval.md) | Grader state machine, rubric internals, artifact schema | You're touching `evals/` or the grader task |
| 04 | [Data model](04-data-model.md) | Item envelope, state.json, evals/<date>.json, schema versioning policy | You're adding a field or a collector |
| 05 | [Flows](05-flows.md) | Sequence diagrams for the three flows that matter (daily cycle, manual re-distill, eval + backlog) | You're debugging a run |
| 06 | [Deployment](06-deployment.md) | Runtime topology, secrets, IAM surface, quotas, cost envelope | You're setting up a fork or another environment |
| 07 | [Reliability](07-reliability.md) | SLIs and SLOs, failure modes, blast radius, degradation strategy | You're on-call for the pipeline |
| 08 | [Security](08-security.md) | Threat model (STRIDE), attack surface, defenses, explicit out-of-scope | You're evaluating this for wider use |
| 09 | [Alternatives considered](09-alternatives.md) | Options rejected and why | You want to know why it isn't done differently |
| 10 | [ADRs](adr/) | Immutable decision log | You're proposing a departure from an existing decision |

## Conventions

- Diagrams are Mermaid where possible so they render on GitHub without a build step. Two SVGs are hand-drawn because the layout beats what Mermaid produces: [`../architecture.svg`](../architecture.svg) (system overview) and [`diagrams/state-ownership.svg`](diagrams/state-ownership.svg).
- ADRs follow the Michael Nygard template. Once an ADR is `Accepted`, it's not edited. A change means a new ADR that supersedes it.
- "Container" and "component" are used in the C4 sense. Nothing here runs in Docker.
- Section headings that start with a verb (`Fetch`, `Score`, `Grade`) describe a step. Nouns (`Item`, `Corpus`, `Rubric`) describe an artifact.

## Non-goals of this doc set

- It doesn't teach C4, Mermaid, or GitHub Actions. Links are provided where the reader needs a primer.
- It doesn't repeat the top-level README. That's the pitch. This is the reference.
- It doesn't cover the presentation site's internals. That lives in [`amaljithkuttamath.github.io`](https://github.com/amaljithkuttamath/amaljithkuttamath.github.io); see [00-context.md](00-context.md) for the seam.
