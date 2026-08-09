# Invariants

Cross-agent rules. Every agent operating in this repo enforces these. If your task text conflicts with anything here, the file wins. See [`.github/AGENTS.md`](../../.github/AGENTS.md#the-source-of-truth-rule).

## I-01. One writer per state file

Every state file has exactly one writer. Concurrent runs cannot collide by construction.

| State | Writer | Consumers |
|-------|--------|-----------|
| `data/raw/**` | `collect-corpus.yml` (artifact only) | `distill.yml` |
| `data/seen.json` | `collect-corpus.yml` | itself next run |
| `reports/**` | `distill.yml` | grader, site, humans |
| `data/state.json` | `distill.yml` | itself next run, site |
| `data/tracked.json` | `distill.yml` | itself next run |
| `evals/<YYYY-MM-DD>.json`, `evals/latest.json`, `evals/README.md` | grader | site, coder, humans |
| `evals/backlog.md` | grader (append during run) and coder (direct commit for X-axis / manual) | humans |
| `evals/rubric.md` | humans, via PR | grader (read-only) |
| `data/health.json`, the `health:*` block in `README.md` | `health.yml` | status page, `watchdog.yml`, humans |

The `evals/backlog.md` shared-write is the only exception; see [I-02](#i-02-backlogmd-shared-write-rules).

## I-02. `backlog.md` shared-write rules

Both grader and coder append. To prevent lost writes:

- Every append is preceded by a fresh `gh api GET` of the current file (with `sha`), then a `PUT` including that `sha`. If the PUT 409s, refetch and retry once. If the second retry 409s, escalate.
- No agent rewrites existing items. Only appends and status transitions (`[ ]` → `[x]` with a `Done` line, `[ ]` → moved to `## Done`) are allowed.
- The `## Done` section is append-only. Never delete items from it.

## I-03. Draft PRs only

No agent opens a ready-for-review PR. Humans promote.

## I-04. Cite evidence

Every claim in a commit message, PR body, eval justification, or backlog rationale cites a specific artifact: an item id, a URL, a file line, or an `evals/<date>.json` field. No paraphrase, no fabrication.

## I-05. Whitelist compliance

Any file write outside [`whitelist.md`](whitelist.md) is a bug. Abort before the git operation.

## I-06. Escalate on ambiguity

If reality diverges from the contract by more than a rounding error, stop and escalate. Do not guess. See per-role docs for what escalation looks like.

## I-07. Idempotency where possible

An agent's `n`th run against the same input should produce the same output as its `n+1`th run, except for the model-call step in `distill/synthesize.py` and the eval scoring in the grader (both explicitly non-deterministic).

## I-08. Never bypass a safety fence

If a fence blocks progress, escalate. Do not find a workaround. If the fence is wrong, open a PR to change the fence.
