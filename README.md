# AI Radar

Daily AI newsletter, built from ~30 sources, scored by a model, graded by a rubric.

Read today's: [reports/latest.md](reports/latest.md) · Live board: [amaljithkuttamath.github.io/radar](https://amaljithkuttamath.github.io/radar) · Latest score: [evals/latest.json](evals/latest.json)

[![collect](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/collect-corpus.yml/badge.svg)](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/collect-corpus.yml)
[![distill](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/distill.yml/badge.svg)](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/distill.yml)

## Architecture

![AI Radar architecture](docs/architecture.svg)

Four stages. Each one owns the state it writes.

1. **Collect.** stdlib fetchers pull arXiv, HF Daily Papers, lab RSS, GitHub trending, HF trending. Every item lands as a JSON record in `data/raw/`, deduped against `data/seen.json`. Runs daily at 11:00 UTC. No model calls, so a bad feed can't burn tokens.
2. **Distill.** Score the corpus (0–5, heuristic, stdlib), re-rank against your `profile.yaml` topics, diff against yesterday to find movers, then one model call to write `reports/<date>-digest.md`. Fires on `workflow_run` when collect finishes, so there is no scheduled gap between the two.
3. **Grade.** A separate daily task at 12:00 UTC reads the digest, HEAD-checks every URL, scores 10 rubric dimensions, commits `evals/<date>.json`, and files an issue if any dimension drops below 2. The grader lives outside CI on purpose so it can't rescue a pipeline it just criticised.
4. **Present.** The Astro site at `amaljithkuttamath.github.io/radar` reads `state.json`, `reports/latest.md`, and `evals/latest.json` live from `raw.githubusercontent.com`. New digest committed here shows up on the next page load. No rebuild.

## Design invariants

Five things the code enforces. If one of these stops being true, something is wrong.

- Collectors never call a model. Scoring is deterministic.
- `data/raw/` is regenerable. It is gitignored and passed between workflows as a 3-day artifact.
- Traction and relevance are different numbers. `score` is what everyone sees. `focus_match` is what you see.
- Each workflow writes a disjoint set of paths. Concurrent runs can't collide.
- Every eval score has a citation to the item, URL, or file line that produced it.

## Item schema

Every collector emits the same envelope. The distiller only reads this shape.

```json
{
  "id":          "arxiv:2406.01234",
  "category":    "research",
  "title":       "...",
  "url":         "https://...",
  "source":      "arXiv cs.LG",
  "authors":     ["..."],
  "published":   "2026-06-03T18:00:00Z",
  "fetched":     "2026-06-04T08:00:00Z",
  "raw_summary": "...",
  "signals":     { "hf_upvotes": 0, "gh_stars": 0 },
  "score":       null,
  "focus_match": false
}
```

## Layout

```
config/         sources.yaml, routines.yaml, profile.yaml (the three dials)
collectors/     source adapters, stdlib only
distill/        score, focus, delta, synthesize, reindex, deliver
evals/          rubric.md, backlog.md, per-day JSON, latest.json
data/           raw/ (gitignored), seen.json, state.json
reports/        dated digests, README index, latest.md pointer
scripts/        collect.sh, distill.sh, run.sh
.github/        collect-corpus.yml, distill.yml
```

## Workflows

| Workflow | Trigger | Writes |
|----------|---------|--------|
| `collect-corpus.yml` | daily 11:00 UTC | `data/seen.json`, `corpus-raw` artifact |
| `distill.yml` | `workflow_run` on collect success | `reports/*.md`, `data/state.json` |
| daily grader (external) | daily 12:00 UTC | `evals/<date>.json`, `evals/latest.json`, `evals/backlog.md`, `evals/README.md` |

The distill trigger is reactive, not scheduled. There is no arbitrary gap between collect and distill, and the artifact download uses the triggering run's ID directly.

## Rubric

Ten dimensions, five per axis, 0–5, with a one-sentence justification per score. Full anchors in [`evals/rubric.md`](evals/rubric.md).

**Answer quality.** `signal_density`, `source_integrity` (broken URL caps at 2), `focus_alignment`, `delta_clarity`, `coverage`.

**Experience.** `board_legibility`, `instrument_honesty`, `freshness`, `failure_surface`, `coupling`.

An issue gets filed if any dimension hits 2 or below, if a URL is broken, or if the same dimension scores 3 or lower three days running. Throttled to one issue per 72 hours across both repos.

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
RADAR_MODEL_BACKEND=github \
bash scripts/distill.sh

open reports/latest.md
```

Model backends: `github` (free, uses `GITHUB_TOKEN`), `anthropic` (reads `ANTHROPIC_API_KEY`), `ollama` (local), `dryrun` (skip the model call).

## Configuration

Three files. Nothing else is user-facing configuration.

- [`config/sources.yaml`](config/sources.yaml). Category to feeds. Where you add sources.
- [`config/routines.yaml`](config/routines.yaml). Which collectors run, plus default `WINDOW`, `MARKET`, `max_items`.
- [`config/profile.yaml`](config/profile.yaml). Your topics with aliases. Drives FOCUS re-rank.

## Runbook

**A collector 500s.** Look at the log. It will have skipped that feed and continued. `seen.json` didn't advance for that source, so re-dispatch is safe.

**Distill wrote a "quiet window" digest.** That is the correct output when the artifact download step was skipped, which happens on a manual dispatch without a preceding collect run.

**Eval scored a dimension at 2 or below.** An issue was opened automatically. The linked `evals/<date>.json` has the justification. The fix is usually already in `evals/backlog.md` from the same run.

**`/radar` looks stale.** The site reads live from a CDN with about 5 minutes of propagation. Hard refresh, then check `reports/latest.md` on GitHub.

**Bad digest went out.** `git revert` the `reports/<date>-digest.md`, run `python -m distill.reindex`, commit. The board catches up on the next page load.

## Roadmap

Done: two-stage collect and distill, movers, alias-aware FOCUS, SMTP delivery, 10-dimension eval loop with committed rubric and trend table.

Open: GitHub star-velocity enricher, semantic FOCUS backend, `collect-social.yml` for HN + Reddit + Bluesky, `fuse-and-detect.yml` for social-heat triggers, exposing `evals/latest.json` in the `/radar` status bar.

## Not this

Not investment advice. `MARKET=on` maps exposure and mechanism. It never suggests trades.

Not a firehose. Six items that matter beat forty that don't. That is what the include threshold is for.

Not a leaderboard. The rubric grades this digest against itself over time, not against other newsletters.
