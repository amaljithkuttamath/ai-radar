# ADR-0009. Self-evolution: a degrading evaluator, a deferred ground truth, and bounded autonomy

**Status.** Accepted and implemented, 2026-09. Extends ADR-0003, ADR-0005 and ADR-0007. Amends invariant I-03.

## Context

The loop described in [`docs/self-healing.md`](../../self-healing.md) has stalled twice, for 28 days and then 41 more. Neither stall involved a broken component. Both times every part reported itself correctly and the system as a whole did nothing.

Read against the reference architecture for self-adaptive systems — MAPE-K, *Monitor, Analyze, Plan, Execute over shared Knowledge* ([Kephart & Chess 2003](https://ieeexplore.ieee.org/document/1160055)) — the shape of the failure is legible:

| | what this repo has | state |
|---|---|---|
| **Monitor** | `health.py`, `watchdog.yml`, artifact freshness, loop-latency signal | strong |
| **Analyze** | the grader: 10 rubric dims, 2 of them deterministic | **single point of failure** |
| **Plan** | a static failing-dim → allowed-edit table | no memory |
| **Execute** | draft PR, merged by a human | **human in the critical path** |
| **Knowledge** | `evals/*.json`, `evals/backlog.md` | records scores, not *causes* |

The K is the part that barely exists, and it is the part the whole idea of self-evolution rests on. Nothing in this repo can answer "did that change help?" — a merged PR moves the scores, and the pairing is never written down.

Five defects follow, each with evidence from this repo's own history:

1. **The evaluator fails stopped, not degraded.** `RADAR_GRADER_MODEL` was unset after the GitHub Models retirement, so `python -m grader` escalates and writes *nothing*: `ESCALATE: no grader model configured`, exit 1. Sixty-nine days with no eval, therefore no issue, therefore an empty coder queue. One missing environment variable took out Analyze, Plan and Execute together. The pipeline already solved this class of problem for synthesis in ADR-0006 — a degraded digest is still a digest — and the fix was never carried across to the grader.
2. **No causal memory.** `evals/<date>.json` records what the digest scored and, since ADR-0007, which model judged it. It does not record which revision of `distill/digest.md`, `config/profile.yaml` or `config/sources.yaml` produced the digest. The one link a self-improving system needs — *change → outcome* — is the one link not stored.
3. **The planner optimises the generator against the judge.** The coder edits `distill/digest.md`; the grader scores the digest that prompt writes. That is proxy-reward optimisation, and [Gao, Schulman & Hilton (2023)](https://arxiv.org/abs/2210.10760) measured what it does: past some optimisation pressure, proxy score keeps rising while ground truth falls. There is currently no ground truth to fall, so the divergence would be invisible.
4. **Autonomy is all-or-nothing, and it is set to nothing.** Every improvement, however small and however reversible, waits on a human merge. PR #35 waited 40 days. The safety fences are good; the throughput is zero.
5. **Liveness and blockage are indistinguishable.** A deleted scheduled task and a task that runs daily and escalates produce the identical observable: no new artifact. Diagnosing stall #2 required running the grader by hand.

### What the literature says not to do

The prior art is mostly cautionary, and it argues against the obvious designs:

- **Do not let one model grade its own work.** [Panickssery et al. (NeurIPS 2024)](https://arxiv.org/abs/2404.13076) show LLM evaluators score their own generations higher than humans rate them, and that the bias is *causally* driven by self-recognition — fine-tune self-recognition up or down and self-preference follows. This validates `grader/separation.py`, and validates separating by model **family** rather than by vendor or account: self-recognition tracks generation fingerprints, not billing. The fence is the single best thing this repo already has. [Zheng et al. (2023)](https://arxiv.org/abs/2306.05685) independently name self-enhancement alongside position and verbosity bias, while finding a strong judge can still reach ~80% human agreement — the same rate humans reach with each other. So model judgement is worth having, and worth never trusting alone.
- **Do not expect a model to fix itself from its own opinion.** [Huang et al. (ICLR 2024)](https://arxiv.org/abs/2310.01798) found intrinsic self-correction — revising with no external signal — leaves performance flat or *worse*. Improvement tracks the quality of the external feedback, not the eloquence of the critique. The two deterministic dims (X3 arithmetic, A2 observed HTTP status) are therefore not a detail of ADR-0007; they are the load-bearing part, and there should be more of them.
- **An agent that can see the checker will eventually edit the checker.** In the [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) (Zhang, Clune et al., 2025) a variant tasked with reducing hallucination deleted the marker tokens the detector searched for, scoring a perfect 2.0 while solving nothing. The authors report objective hacking was *more frequent when the checking functions were visible to the agent*. This is not a hypothetical for a repo whose coder edits prompts scored by a rubric.
- **Evolutionary search needs a machine-gradable objective.** [AlphaEvolve](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) (2025) works because matrix-multiplication rank and kernel latency are cheap to evaluate exactly, millions of times, in parallel. The DGM works because SWE-bench runs tests. Neither condition holds for a daily newsletter: one sample per day, and the objective is partly taste.

Everything above points the same way. **The leverage is not a cleverer optimiser. It is more and better external, deterministic signal, kept out of the optimiser's reach.**

## Decision

Five changes. They are ordered so that each is independently useful and none grants autonomy before the ability to measure and undo it exists.

### 1. The evaluator degrades instead of stopping

Split evaluation into a cascade, in AlphaEvolve's sense — cheap deterministic checks first, the expensive model call last:

- **Tier 0 — `grader/deterministic.py`, no model, stdlib only.** Digest age (X3, already arithmetic). Observed HTTP status of every link (A2 ceiling, already measured). Structural completeness of the digest's sections. Main-list item count and score parse. Degraded-banner presence. Traction re-observation rate from `data/tracked.json`. Corpus volume.
- **Tier 1 — the model.** The eight judged dimensions, exactly as today.

If tier 1 is unavailable for any reason — no model configured, provider down, separation fence refusing — **tier 0 still runs and the eval is still committed**, with `mode: "deterministic"` (a new member of `VALID_MODES`).

The constraint that makes this safe is the one ADR-0005 already established for the monitor: **a missing reading must never serialise as a score.** A deterministic eval omits `quality.overall` and the eight judged dims rather than defaulting them. It does not enter the quality trend. It does what the 69-day gap could not: prove the grader ran, record what was objectively true that day, and keep the loop's input non-empty.

This ends the outage class that has now happened twice, and it is the only change here that is urgent.

### 2. An outcome archive — the missing K

`evals/archive.jsonl`, append-only, written by the grader only (preserving I-01):

```json
{"change_id": "pr-41", "merged": "2026-09-22T19:04:00Z",
 "files": ["distill/digest.md"], "target_dim": "A1",
 "prompt_rev": "a1b2c3d", "config_rev": "a1b2c3d",
 "before": {"window": "7d", "A1": 3.1, "trusted": {"reobs_rate": 0.72, "forecast": 0.61}},
 "after":  {"window": "7d", "A1": 3.6, "trusted": {"reobs_rate": 0.71, "forecast": 0.63}},
 "verdict": "helped"}
```

Every eval additionally records `prompt_rev` and `config_rev` — the git revisions of the whitelisted files that produced the digest — so *change → outcome* is finally expressible. The planner reads the archive instead of a static table: an edit class with two consecutive `harmed` verdicts is retired until a human re-enables it.

This is DGM's archive and AlphaEvolve's program database, deliberately scaled down. Those systems keep a *population* and branch it; ai-radar publishes one newsletter a day and cannot evaluate variants in parallel. So this is a **lineage with attribution**, not a search. It buys the ability to stop doing what does not work — which, at one sample per day, is most of the value a population would have bought anyway.

### 3. A trusted set the planner cannot reach, and a deferred ground truth

The Goodhart brake needs a signal outside the optimised system. This repo can define one mechanically:

> **A metric is *trusted* iff it is computed solely from code and state outside the coder's whitelist.**

That rule is checkable, and `scripts/check_whitelist.py` will check it: the tier-0 module's declared inputs must not intersect the whitelist. It also disqualifies the obvious candidates, correctly. Source diversity and novelty depend on `config/profile.yaml` and `config/sources.yaml`; the A2 ceiling depends on `config/broken_sources.yaml`. All three are whitelisted, so all three are legitimate *targets* of optimisation and cannot also be the referee.

What survives is small, which is the point:

- **Freshness.** A function of the clock and git. Nothing the planner writes can move it.
- **Re-observation rate.** The fraction of `data/tracked.json` whose counters were actually re-read this run. Owned by `distill/track.py` and the collectors, neither whitelisted.
- **Forecast accuracy — the deferred check.** This is the strongest signal available and it is currently thrown away. When a digest labels an item *Climbing* or *Still developing*, it makes a falsifiable claim about the future. `data/tracked.json` keeps `mag_history`, so three days later the repo knows whether the claim held. Scoring yesterday's *predictions* against today's *observations* yields a ground truth that no prompt wording can fabricate, because it is graded by events that had not happened when the prompt ran.

The brake: **if the rubric score rises over a 14-day window while a trusted metric falls, revert the most recent accepted change and file `[goodhart]`.** That is Gao et al.'s optimal-stopping result made operational — you cannot predict the divergence point, but you can detect the divergence.

And the DGM lesson, made mechanical rather than aspirational, in two parts.

First, **the evaluator becomes a fence path.** `scripts/check_whitelist.py` already distinguishes two kinds of violation: *out of scope* (a path this role may not touch) and *fence* (a path no agent may touch, the I-08 class). `FENCE_PATHS` currently lists the workflows, `CODEOWNERS`, `AGENTS.md`, `docs/operating/*` and the checker itself. It does not list `grader/*` or `evals/rubric.md` — so today, an agent editing the thing that grades it trips the weaker of the two checks. Adding those two globs is a two-line change that moves the rubric and the judge into the category the repo already treats as inviolable.

Second, **`grader/deterministic.py` is hashed into every eval.** A silently modified checker then shows up as a hash change in the permanent trend, next to the scores it produced. The fence stops the edit; the hash catches the edit the fence missed.

### 4. Bounded autonomy: auto-merge a narrow, reversible class

Invariant I-03 becomes: *agents never open ready-for-review PRs **outside the auto-merge class***, where the class is defined in code, not prose. A PR auto-merges only if **all** hold:

1. every changed path is whitelisted, and the change is config or prompt text only — never Python;
2. the diff is under a size bound (one file, ≤ 20 changed lines);
3. a **pre-merge shadow eval** — `--mode pre-merge`, already in `VALID_MODES` — shows no tier-0 regression against the PR's branch;
4. no other auto-merge in the last 72h;
5. `revert-on-regression` is armed: if any trusted metric degrades over the following 7 days, the merge commit is reverted automatically and the archive records `harmed`.

Everything else stays a draft for a human, and the escalation ladder answers the 41-day problem: the `Self-healing loop` health signal (added 2026-09-20) already measures alarm latency; at 7 days an unanswered alarm escalates from an issue to a README banner.

This is the one place the design trades safety for throughput, and it is deliberately the narrowest trade available: reversible changes, to non-executing files, verified before merge, capped in rate, and automatically undone if the trusted set moves against them. DGM's own posture — sandboxing plus human oversight — is preserved in proportion, rather than abandoned or applied uniformly to changes that do not need it.

### 5. The grader records the attempt, not only the result

`evals/attempts.jsonl`, appended on **every** invocation including escalation: timestamp, mode, tier-0 outcome, tier-1 outcome or the reason it was skipped, grader model, deterministic-module hash.

This is explicitly *not* the heartbeat `watchdog.yml` rejects, and that reasoning stands: a success-ping on a healthy component cannot detect a failed independent one, so artifact staleness remains the detective signal. An attempt record is **diagnostic**: it separates *the scheduled task is gone* (no record) from *the task ran and was blocked* (a record with a reason). Stall #2 needed a human at a terminal to tell those apart.

## Alternatives rejected

**Population-based evolutionary search over digest variants** (true DGM/AlphaEvolve). Needs a cheap machine-gradable objective and parallel evaluation. This repo produces one sample per day and its objective is partly taste; the search would take months to produce signal. Mis-sized, not wrong in principle.

**Drop the separate grader; have the synthesis model critique its own digest.** Cheaper, one model, no fence. Rejected on Panickssery et al. (self-preference is causal, not incidental) and Huang et al. (intrinsic self-correction does not improve anything). This is precisely what the family fence exists to prevent.

**Let the coder tune `evals/rubric.md` when scores plateau.** Closes the loop on itself: the system would optimise the measurement rather than the product. The judge must sit outside the optimised system — the same reason ADR-0003 puts execution outside the repo.

**Full autonomy on all whitelisted paths.** The whitelist bounds *blast radius*, not *correctness*. DGM's marker-deletion exploit happened inside a legitimate edit surface.

**A liveness heartbeat as the primary detector.** Already rejected in `watchdog.yml` for sound reasons, and re-rejected here; §5 is diagnostic only.

## Consequences

**Positive.**

- The failure that has now recurred twice becomes structurally impossible: losing the model degrades the eval's *resolution*, not its *existence*.
- "Did that change help?" becomes answerable for the first time, and the planner can stop repeating edits that did not.
- The system gains a ground truth that is not a model's opinion — yesterday's forecasts, scored by today's observations.
- Improvements that are small, reversible and machine-verifiable stop waiting on a human, while everything else still waits on a human.
- Tampering with the checker is visible in the permanent record rather than silent.

**Negative.**

- More moving parts in the component whose reliability the whole loop depends on. Mitigated by tier 0 being stdlib-only and independently testable, the same discipline as `scripts/health.py`.
- The forecast metric needs ≥ 3 days of `tracked.json` history before it says anything, and is uninformative on quiet days.
- Auto-merge is a real loosening of I-03. Mitigated by the five conjunctive conditions and auto-revert, but it is a loosening and should be reviewed after 30 days.
- Archive verdicts on 7-day windows over a single daily sample are statistically weak. They are treated as a *retirement* signal (stop doing what harms) rather than a *selection* signal (do more of what helps), which is the direction that survives the weak statistics.

**New invariants.**

- **I-09.** A deterministic eval never writes a judged dimension. Unknown is omitted, never defaulted.
- **I-10.** Every trusted metric is computed only from paths outside the coder whitelist; `check_whitelist.py` enforces the disjointness.
- **I-11.** `grader/*` and `evals/rubric.md` are fence paths, and the deterministic evaluator's hash is recorded in every eval.
- **I-12.** Every auto-merged change is revertible by a single `git revert` and is armed with a regression trigger.

## Rollout

Staged, because autonomy must come last:

| stage | what | unblocks |
|---|---|---|
| **1** | tier-0 cascade + `mode: deterministic` + attempt record | today's 69-day outage; loop survives a missing model |
| **2** | `prompt_rev`/`config_rev` in evals; `archive.jsonl`; planner reads it | attribution |
| **3** | forecast scoring; trusted set + `check_whitelist` disjointness; Goodhart brake | ground truth and a brake |
| **4** | pre-merge shadow eval; bounded auto-merge; revert-on-regression | throughput |

Stage 1 is worth doing whether or not stages 2–4 ever ship, and it is the one that fixes what is broken right now. Stage 4 is worth doing only if stages 1–3 shipped, because it is the stage that acts without asking.

## References

- Kephart & Chess, [*The Vision of Autonomic Computing*](https://ieeexplore.ieee.org/document/1160055), IEEE Computer, 2003 — the MAPE-K reference model.
- Panickssery, Bowman & Feng, [*LLM Evaluators Recognize and Favor Their Own Generations*](https://arxiv.org/abs/2404.13076), NeurIPS 2024.
- Zheng et al., [*Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*](https://arxiv.org/abs/2306.05685), NeurIPS 2023.
- Huang et al., [*Large Language Models Cannot Self-Correct Reasoning Yet*](https://arxiv.org/abs/2310.01798), ICLR 2024.
- Gao, Schulman & Hilton, [*Scaling Laws for Reward Model Overoptimization*](https://arxiv.org/abs/2210.10760), ICML 2023.
- Zhang, Hu, Lu, Lange & Clune, [*Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents*](https://arxiv.org/abs/2505.22954), 2025.
- Novikov et al., [*AlphaEvolve: A coding agent for scientific and algorithmic discovery*](https://arxiv.org/abs/2506.13131), 2025.

## Implementation notes

Shipped 2026-09-20, all four stages. Three deliberate deviations from the design above,
each because building it surfaced something the design had not:

**The archive is a derived view, not an append-only ledger.** §2 proposed
`evals/archive.jsonl`, appended at merge time. Everything it needs is already in the eval
history, because `provenance.py` stamps each eval with the tunable files' revisions — so a
change event is a *transition* in those stamps, and `grader/archive.py` recomputes the
archive from the evals instead of maintaining a copy. One writer instead of two (I-01), no
possibility of disagreeing with the evals it summarises, and — the reason that matters most
here — it cannot silently stop, because a ledger that stops being appended looks exactly like
a period with no changes. It is also retroactive: improving the attribution rule re-attributes
every past change rather than only future ones.

**`Still developing` is not a forecast.** §3 named it as a source of claims. Reading the real
digests, its entries routinely say "traction flat" — the section asserts continued attention,
not continued rise. Scoring it as "up" would have manufactured a stream of wrong verdicts
against claims the digest never made, and a corrupted ground truth is worse than none: the
brake would be measuring the fiction it exists to catch. `Climbing`, `Story arcs` and `Cooled`
remain.

**Tier 0 also runs in CI.** Not in the original design, and the larger call. `eval-deterministic.yml`
runs the deterministic half reactively after each distill. This does not contradict ADR-0003,
whose reasoning is about *judgement*: tier 0 is arithmetic over committed artifacts and
imports nothing from `distill`, so a distill bug cannot reach in and soften a number. The
judged half stays external, on its own credential, clock and model family. What it buys is a
producer that cannot silently cease to exist — a workflow's absence is a missing run in a
list and its failure is a red badge, both of which `health.py` already watches. Two runners
over one path are reconciled by monotonicity rather than locking: `write_eval` refuses to
replace a judged eval with a deterministic one, so no landing order can lose information.

**Still open.** `RADAR_GRADER_MODEL` remains unset, so tier 1 does not run and the trend is
deterministic-only until a grader model is configured. That is now a degradation rather than
an outage, which was the point — but it is not the same as the loop being whole.
