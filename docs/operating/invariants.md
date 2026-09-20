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

## I-03. Draft PRs only, outside the auto-merge class

No agent opens a ready-for-review PR. Humans promote.

**Amended by ADR-0009.** One narrow class merges without a human: a change to a single whitelisted, non-executing file, under 20 changed lines, with no tier-0 regression in a pre-merge shadow eval, no other auto-merge inside 72h, and not in a retired edit class. The class is defined in `scripts/automerge.py` — in code, with tests — because a gate written in YAML cannot be unit-tested, and an untested gate is the only thing standing between an agent and `main`.

The trade is stated plainly: throughput, in exchange for a human no longer reading every one-line prompt tweak. It is defensible only alongside I-12 — the change is cheap to undo without a human. Everything outside the class is unchanged: a draft, held, with a comment saying which condition it failed.

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

## I-09. Unknown is omitted, never defaulted

An eval produced without a model (`mode: deterministic`, ADR-0009) omits `quality`, `experience` and `overall` entirely, and names no `grader_model`. It does not write a zero, and it does not enter the quality trend.

A fabricated score is permanent in a way a gap is not: the gap is visibly a gap, while the zero is indistinguishable from a judgement. `evals/README.md` renders the day as an em dash so it is still accounted for — a *missing row* is what let a 69-day outage pass unnoticed twice.

Enforced in `grader/artifacts.py:validate`.

## I-10. The trusted set is out of the planner's reach

A metric is **trusted** — eligible to drive the Goodhart brake or a revert — only if it is computed solely from code and state outside the coder's whitelist.

Gao, Schulman & Hilton (ICML 2023) showed a proxy and its ground truth diverge under optimisation pressure, and that the divergence is detectable only while the ground truth is genuinely out of reach. A metric the planner can move is not a referee; it is another target.

This correctly disqualifies source diversity, novelty and the A2 ceiling, all of which depend on whitelisted config. What survives is `reobservation_rate` and `forecast_accuracy`.

Enforced in `scripts/check_whitelist.py:trusted_disjointness`, on every invocation rather than per-diff: a whitelist that has grown to cover a trusted source has disarmed the brake, and the diff that did it would look perfectly in scope.

## I-11. The evaluator is a fence, and says which version it was

`grader/*` and `evals/rubric.md` are fence paths. No agent may edit the thing that grades it, and every eval records `tier0.module_hash`.

The Darwin Gödel Machine (Zhang et al. 2025) had a variant delete the marker tokens its hallucination detector searched for, scoring a perfect 2.0 while solving nothing — and the authors report objective hacking was *more* frequent when the checking functions were visible to the agent. Visibility cannot be removed here. The edit can, and an edit that evaded the fence is visible in the trend beside the scores it produced.

## I-12. Automatic changes are revertible by one command

Every auto-merged change is a single squashed commit, touches one non-executing file, and is armed with `revert-on-regression.yml`.

This is what makes I-03's amendment defensible. Auto-merge is granted not because the gate is clever but because the change is cheap to undo without a human — and you cannot gate in advance against a divergence whose onset is unpredictable.
