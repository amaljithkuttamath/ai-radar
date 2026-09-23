# AI Radar

Daily AI newsletter, built from ~30 sources, scored by a model, graded by a rubric.

Today's: [reports/latest.md](reports/latest.md) · Board: [amaljithkuttamath.github.io/radar](https://amaljithkuttamath.github.io/radar) · Score: [evals/latest.json](evals/latest.json) · Health: [status page](https://amaljithkuttamath.github.io/ai-radar/)

## Pipeline health

<!-- health:start -->

| signal | status | detail |
|---|---|---|
| [Daily digest](https://github.com/amaljithkuttamath/ai-radar/blob/main/reports/latest.md) | 🟡 warn | last digest committed 27h ago |
| [Model synthesis](https://github.com/amaljithkuttamath/ai-radar/blob/main/reports/latest.md) | 🟢 ok | latest digest carries model synthesis |
| [Eval loop](https://github.com/amaljithkuttamath/ai-radar/blob/main/evals/latest.json) | 🟡 warn | grader last committed 27h ago · tier 0 only, no model judgement |
| [Self-healing loop](https://github.com/amaljithkuttamath/ai-radar/issues?q=is%3Aissue+is%3Aopen+label%3Awatchdog) | 🟢 ok | no unanswered alarms |
| [Collect corpus](https://github.com/amaljithkuttamath/ai-radar/actions/runs/35880079700) | 🟢 ok | last run success |
| [Distill digest](https://github.com/amaljithkuttamath/ai-radar/actions/runs/35880133169) | 🟡 warn | 1 consecutive failures |
| [Watchdog](https://github.com/amaljithkuttamath/ai-radar/actions/runs/35904910591) | 🟢 ok | last run success |

Generated 2026-09-23 19:15 UTC by `scripts/health.py`.

<!-- health:end -->

Regenerated daily by [`scripts/health.py`](scripts/health.py) via [`health.yml`](.github/workflows/health.yml). Full reading in [`data/health.json`](data/health.json); rendered live on the [status page](https://amaljithkuttamath.github.io/ai-radar/).

## Eval trend (latest)

| date | quality | experience | overall | mode |
|---|---:|---:|---:|---|
| 2026-07-13 | 3.8 | 4.2 | 4.0 | recovery |
| 2026-07-12 | 4.2 | 4.2 | 4.2 | recovery |
| 2026-07-11 | 3.6 | 4.2 | 3.9 | recovery |
| 2026-07-07 | 3.8 | 3.6 | 3.7 | recovery |
[![collect](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/collect-corpus.yml/badge.svg)](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/collect-corpus.yml)
[![distill](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/distill.yml/badge.svg)](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/distill.yml)

## Architecture

![architecture](docs/architecture.svg)

Four stages, one repo, one writer per state.

1. **Collect.** stdlib fetchers pull arXiv, HF Daily Papers, lab RSS, GitHub trending, HF trending. Every item lands as JSON in `data/raw/`, deduped against `data/seen.json`. Daily at 11:00 UTC. No model calls, so a bad feed can't burn tokens.
2. **Distill.** Score the corpus (0–5 heuristic, stdlib), re-read traction for everything already on the radar, re-rank against `profile.yaml` topics, diff against yesterday to find movers, apply diversity filters, one model call to write `reports/<date>-digest.md`. Fires on `workflow_run` when collect finishes.
3. **Grade.** A cascade ([ADR-0009](docs/architecture/adr/0009-self-evolving-loop.md)). **Tier 0** is deterministic, stdlib-only and model-free — link statuses, section structure, main-list parse, and the traction re-observation rate — and runs in CI after every distill, so it cannot silently stop. **Tier 1** is the one model call that scores the eight judged dimensions, run by a separate daily task at 12:00 UTC on a different model family. If tier 1 is unavailable for any reason the eval is still written, as `mode: deterministic`, with the judged dimensions *omitted* rather than zeroed. Losing the model costs the eval's resolution, never its existence — before this, one unset variable produced no eval for 69 days, twice.

   The grader refuses to run at all if its model family matches the one that wrote the digest. Judgement lives outside CI so it can't rescue a pipeline it just criticised ([ADR-0003](docs/architecture/adr/0003-eval-loop-out-of-repo.md)); the code lives here so it can be tested and seen to have stopped ([ADR-0007](docs/architecture/adr/0007-grader-implementation-in-repo.md)).
4. **Present.** The Astro site reads `state.json`, `reports/latest.md`, and `evals/latest.json` live from `raw.githubusercontent.com`. New digest here shows up on next page load. No rebuild.

Watching all four: `health.py` writes one reading to `data/health.json` daily at 16:00 UTC, after every other stage has had its slot. The status page renders it; `watchdog.yml` escalates on it. The reporter never repairs and the escalator never measures — [ADR-0005](docs/architecture/adr/0005-artifact-freshness-monitoring.md).

Watching the watcher: one of those signals is the loop itself. Detecting a fault and closing one are different events, and measuring only the first is how an alarm rang unanswered for 41 days with every component reporting itself correctly. `Self-healing loop` reads the age of the oldest open `watchdog` issue — green when nothing is outstanding, red once an alarm outlives the coder's own 72h cooldown. [docs/self-healing.md](docs/self-healing.md#is-the-loop-closing) has the post-mortem.

Details in [docs/architecture.md](docs/architecture.md). Decisions in [docs/architecture/adr/](docs/architecture/adr/).

## Invariants

- Collectors never call a model.
- `data/raw/` is regenerable and gitignored.
- Traction and relevance are different numbers.
- Each workflow writes a disjoint set of paths.
- Every eval score cites the item, URL, or file line that produced it.
- A traction number in the digest was read from its source during that run.
- "Climbing" means two observations of the same counter, not two guesses.
- Unknown is omitted, never defaulted — a missing score is a gap, not a zero.
- A metric may referee an improvement only if the improver cannot edit its source.
- No agent edits the thing that grades it.

## The radar part

A newsletter tells you what happened today. A radar tells you what is still moving.

Items that make the digest go on the radar (`data/tracked.json`, capped at 60). Every run
re-reads their actual counters — GitHub stars, HF likes, HF paper upvotes — and re-enters them
as candidates scored against *current* signals. That is what makes "Climbing", "Cooled",
"Still developing" and "Story arcs" real: each one is backed by two observations of the same
number, days apart. Items leave the radar on a TTL, after three unreachable fetches, or once
traction goes flat for five runs.

It also means a quiet collection day still has something to say. Before this existed, roughly
30% of digests shipped with an empty main list, because the only candidates were the handful of
items first seen that morning.

Why it needed building: `data/seen.json` dedups an item forever and `data/raw/` is rebuilt from
scratch in CI, so an item was collected once and never seen again — every "since last run" diff
compared two disjoint sets. [ADR-0004](docs/architecture/adr/0004-carryover-tracking-ledger.md)
has the details.

## Layout

```
config/         sources.yaml, routines.yaml, profile.yaml (the three dials)
collectors/     source adapters, stdlib only
distill/        score, focus, track, delta, diversity, enrich, synthesize, reindex, deliver
grader/         the eval loop: deterministic (tier 0), forecast, trusted, archive,
                freshness, links, separation fence, judge, artifacts
tests/          pytest suite; no network, no model, no secrets
evals/          rubric, backlog, per-day JSON, latest.json, attempts + forecasts
                (jsonl), archive.json (derived)
data/           raw/ (gitignored), seen.json, state.json, tracked.json, health.json
reports/        dated digests, README index, latest.md
scripts/        collect.sh, distill.sh, run.sh, health.py, check_whitelist.py,
                automerge.py (the auto-merge gate)
site/           status page (static; reads data/health.json live)
.github/        collect-corpus.yml, distill.yml, test.yml, health.yml, watchdog.yml,
                eval-deterministic.yml, auto-improve.yml, revert-on-regression.yml
docs/           architecture.svg + architecture.md + adr/
```

## Run it locally

```bash
uv sync

python -m collectors.arxiv
python -m collectors.hf_papers
python -m collectors.lab_blogs
python -m collectors.github_trending
python -m collectors.hf_trending

WINDOW=48h \
FOCUS="interpretability,agents,evals" \
RADAR_MODEL_BACKEND=auto \
bash scripts/distill.sh

open reports/latest.md
```

Backends: `auto` (default in CI — `anthropic` if `ANTHROPIC_API_KEY`, else `openai` if `OPENAI_API_KEY`, else `template`), `anthropic`, `openai`, `ollama`, `template` (no model, deterministic), `dryrun`. `github` is retired and redirects to `auto` — see [ADR-0006](docs/architecture/adr/0006-model-backend-after-github-models.md).

**One provider, both stages.** Synthesis and the grader share a single key and endpoint ([`llm.py`](llm.py)) — providers are not divided by responsibility. What has to differ is the model *family*, not the account: a model grading its own family self-enhances by ~10–25%, so [`grader/separation.py`](grader/separation.py) checks the model id and refuses if the two match. A gateway serving many families through one OpenAI-compatible URL therefore satisfies the fence on one free key:

```bash
RADAR_LLM_API_KEY=sk-or-...    # that is the entire setup
```

The endpoint is inferred from the key prefix, so OpenRouter costs one variable rather than two — two-variable setups are how a key ends up pointed at the wrong endpoint. Set `RADAR_LLM_BASE_URL` explicitly for any other provider; it always wins.

**You don't have to pick models at all.** A role with no pinned id resolves itself from the provider's live catalogue at run time: free models only (both prompt and completion priced at zero — absent pricing counts as *not* free), skipping any family the other role is pinned to, deterministic so a stable catalogue gives a stable choice. The id is recorded on every eval, so drift stays auditable.

That fallback exists because every provider profile in [`llm.py`](llm.py) ships `GRADER: ""` — no provider can promise a second family will still be free and un-throttled tomorrow. The result was that the grader had no model unless a human pinned one by hand, and for 69 days nobody did. Resolution is only responsible enough to attempt because the failure beneath it is now graceful: if the catalogue is unreachable or serves no second family, the run writes a tier-0 eval instead of stopping.

To see or pin the choice:

```bash
python3 -m llm --resolve          # print the pair it would use; --any to include metered
python3 -m llm --catalog          # everything served, with families and free/paid marked
```

Pin `RADAR_SYNTHESIS_MODEL` / `RADAR_GRADER_MODEL` as repository variables if you want a fixed pair — a pinned id is never overridden. `RADAR_AUTO_MODEL=0` disables resolution; `RADAR_ALLOW_METERED=1` lets it consider paid models when no free second family exists.

**Surviving the free tier.** Free models are routinely rate-limited upstream, often several at once. So resolution returns a *list* — one model per family, best first — and the grader fails over on `429`, `402` and `5xx` until one answers. A configuration fault (`401`, `404`) is never retried, since the next model would fail identically. A *pinned* model is never failed over from either: a pin is a decision, and substituting for it would make each eval's `grader_model` a record of what happened to be free rather than of what was chosen.

No OpenRouter model ids are hardcoded, deliberately: its free variants carry a `:free` suffix while the bare id is metered, so a plausible-looking default is a 402 that degrades to the template digest and reads exactly like the pipeline is still broken.

Single-family providers can't do both roles: Perplexity serves only `sonar`, Groq and Google AI Studio are effectively one family each. They're fine for synthesis, but the grader then needs a second family — which is what the gateway buys you.

The pipeline makes about **two model calls a day**, so free tiers clear it by orders of magnitude.

## Tests

```bash
uv run --group dev pytest
```

No network, no model, no secrets — every fetch the pipeline makes is injected, so the suite
can't be flaked by a slow feed. `tests/test_pipeline.py` runs three simulated days through
score → track → synthesize under the exact CI conditions (empty `data/raw/`, everything
already in `seen.json`) that used to leave the radar with nothing to say.

## Runbook

**Where to look first.** The [status page](https://amaljithkuttamath.github.io/ai-radar/) or the health table at the top of this README. If the page says *Monitor stale*, believe that over everything below it — `health.yml` has stopped and every reading on the page is history.

**Status page shows a workflow as `unknown`.** Nobody looked; the Actions API read failed. Not a pipeline fault. Check `health.yml`'s own run.

**Digest stale but distill is green.** Worse than a red distill: the run succeeded and committed nothing. Check the "Commit digest" step — most likely `git diff --cached --quiet` found no change because synthesis wrote an identical file, or the push was rejected.

**Digest says "Degraded run — no model synthesis".** The synthesis backend failed permanently or no `ANTHROPIC_API_KEY` is set. The digest is real — scored items, observed traction — but has no top-line read or insights. Set the key to restore synthesis; the banner disappears on the next run. See [ADR-0006](docs/architecture/adr/0006-model-backend-after-github-models.md).

**Collector 500s.** Log will show which feed. Others continued.

**"Quiet window" digest.** Manual dispatch of `distill` without a preceding `collect`. Expected. The main list should still carry tracked carryovers; a genuinely empty one means `data/tracked.json` is empty too.

**Nothing in "Still developing" / "Story arcs".** Check `data/tracked.json`. Empty means nothing has scored ≥3 since it was last pruned. Populated but every `streak` is 1 means re-observation is failing — the `[track]` line in the distill log gives `observed`/`missed` counts, and a high `missed` usually means a rate limit or an expired `GITHUB_TOKEN`.

**Eval scored ≤ 2.** Issue was opened automatically. `evals/<date>.json` has the justification. Fix is usually already in `evals/backlog.md`.

**Bad digest went out.** `git revert` the digest commit, run `python -m distill.reindex`, commit. Board catches up on next page load.

## Not this

Not investment advice. `MARKET=on` maps exposure, never suggests trades.

Not a firehose. Six items that matter beat forty that don't.

Not a leaderboard. The rubric grades this digest against itself over time.

## Self-evolving, and what that is allowed to mean

The loop grades itself, files its own findings, and merges a narrow class of its own fixes.
It stalled twice before it could do any of that — for 28 days and then 41 more — and both
times every individual component reported itself correctly. The design that came out of
those two incidents is [ADR-0009](docs/architecture/adr/0009-self-evolving-loop.md); the
short version is four properties, each of which exists because its absence caused an outage.

**It degrades instead of stopping.** Evaluation is a cascade. Tier 0 is arithmetic over
committed artifacts and needs no model; tier 1 is the judgement. Losing the model costs the
eval's resolution, never its existence. Before this, one unset environment variable produced
no eval, so no issue, so an empty queue, for 69 days.

**It knows what its changes did.** Every eval records the revisions of the tunable files
that produced the digest, so `change → outcome` is expressible and
[`evals/archive.json`](evals/archive.json) is derived from the eval history rather than
maintained beside it. Verdicts are used to *retire* what harms, not to select what helps —
one sample a day cannot support selection, and pretending otherwise is how you overfit to
noise.

**It is graded partly by the future.** When a digest says *Climbing* it makes a falsifiable
claim; `data/tracked.json` settles it three runs later. That is the one signal here that is
not a model's opinion and that no wording change can move, which is exactly what makes it
usable as a brake ([Gao et al., 2023](https://arxiv.org/abs/2210.10760)). A metric qualifies
as *trusted* only if it is computed from paths the improver cannot edit —
`scripts/check_whitelist.py` enforces that, on every run.

**It cannot edit its own examiner, and says which examiner it had.** `grader/*` and
`evals/rubric.md` are fence paths, and every eval carries a hash of the deterministic
checker. The [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) had a variant delete
the marker tokens its own detector searched for and score a perfect 2.0 while solving
nothing — with objective hacking *more* frequent when the checker was visible to the agent.
Visibility can't be removed here. The edit can.

What it is **not**: an evolutionary search. AlphaEvolve and the DGM work because their
objectives are exactly gradable millions of times in parallel. This produces one newsletter
a day and its objective is partly taste, so the machinery is attribution and retirement, not
population search. And a model of a different family still reads the prose, because
[self-preference is causal](https://arxiv.org/abs/2404.13076) and nothing above replaces
that fence.
