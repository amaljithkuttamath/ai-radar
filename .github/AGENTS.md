# AGENTS.md

Read this before doing anything else in this repo.

## Who this is for

Any autonomous or semi-autonomous agent operating on `amaljithkuttamath/ai-radar`: the daily grader, the self-healing coder, one-off maintenance runs, and any future agent added to the loop. Humans reviewing agent PRs should also read this.

## The source-of-truth rule

The repo is authoritative. If your scheduled-task text, prompt, or memory says something that conflicts with a file in this repo, the repo wins. Escalate the diff instead of silently following stale instructions.

Concretely: before acting, read your role contract from the repo.

- Grader loads [`docs/operating/grader.md`](../docs/operating/grader.md) on every run.
- Coder loads [`docs/operating/coder.md`](../docs/operating/coder.md) on every run.
- Both load [`docs/operating/invariants.md`](../docs/operating/invariants.md) and [`docs/operating/whitelist.md`](../docs/operating/whitelist.md).

If the doc is missing or malformed, halt and escalate. Do not fall back to task-text instructions.

## Non-negotiables

1. **One writer per state file.** See [`docs/operating/invariants.md`](../docs/operating/invariants.md). No exceptions.
2. **Whitelist compliance.** Any file write outside [`docs/operating/whitelist.md`](../docs/operating/whitelist.md) is a bug. Abort before the git operation.
3. **Draft PRs only.** No agent opens a ready-for-review PR. Humans promote.
4. **Cite evidence.** Every claim in a commit message, PR body, or eval justification cites a specific artifact (an item id, a URL, a file line, an `evals/<date>.json` field). No paraphrase, no fabrication.
5. **Escalate on ambiguity.** If reality diverges from the contract by more than a rounding error, stop and escalate. Do not guess.

## What escalation looks like

- **Grader**: end silently, log the ambiguity as a comment on the most recent open `[eval]` issue if one exists.
- **Coder**: append a `[manual]` item to `evals/backlog.md` describing the ambiguity, close the source issue with a link to the backlog item, end silently.
- **Any agent**: if you would need to violate a non-negotiable to make progress, don't. Escalate.

## What changes require a PR

Any change to:

- `docs/operating/**` (agent contracts)
- `.github/AGENTS.md` (this file)
- `.github/CODEOWNERS`
- `evals/rubric.md`

goes through a PR reviewed by the owner. Direct commits are for backlog appends and eval artifacts only, as declared in the per-agent contracts.

## Changing an agent's behavior

The right sequence:

1. Open a PR editing the relevant `docs/operating/<role>.md`.
2. Owner reviews the behavior change on its own, without also parsing scheduled-task diffs.
3. On merge, the agent's next run picks up the new contract automatically because it loads the file at runtime.
4. Only touch the scheduled-task shim if the shim itself needs to change (rare).

## Adding a new agent

1. Write `docs/operating/<new-role>.md` following the pattern of the existing contracts.
2. Update [`docs/operating/invariants.md`](../docs/operating/invariants.md) if the new agent introduces or consumes state.
3. Update [`docs/operating/whitelist.md`](../docs/operating/whitelist.md) with any paths the new agent may write.
4. Update [`.github/CODEOWNERS`](CODEOWNERS) if the whitelist grew.
5. Open a PR with all of the above.
6. Only create the scheduled task after the PR merges.

## Prior art in this repo

- [`docs/self-healing.md`](../docs/self-healing.md). Human-facing overview of how the two agents fit together.
- [`docs/architecture.md`](../docs/architecture.md). The rest of the system.
- [`docs/architecture/adr/`](../docs/architecture/adr/). Load-bearing decisions. If your task would violate an ADR, escalate.
