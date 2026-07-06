<div align="center">

# AI Radar

**A retrieval → scoring → synthesis → evaluation pipeline for tracking AI research and product signals.**

Deterministic corpus collection, model-graded distillation, and a self-evaluating daily digest — all runnable in CI.

[![collect-corpus](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/collect-corpus.yml/badge.svg)](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/collect-corpus.yml)
[![distill](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/distill.yml/badge.svg)](https://github.com/amaljithkuttamath/ai-radar/actions/workflows/distill.yml)
[![latest digest](https://img.shields.io/badge/latest-digest-blue)](reports/latest.md)
[![evals](https://img.shields.io/badge/evals-latest.json-green)](evals/latest.json)

</div>

---

## TL;DR

AI Radar ingests ~30 signal sources (arXiv, HF Daily Papers, lab RSS, GitHub trending, HF trending), stores every item as an append-only JSON record, ranks the corpus with a stdlib heuristic + a personalised FOCUS re-rank, and asks a model to synthesise a dated Markdown digest. A second daily loop grades every digest against a 10-dimension rubric, commits the scores to `evals/`, and appends causal improvement items to a durable backlog. The public presentation layer lives in a separate Astro portfolio that reads `state.json` and `evals/latest.json` at request time — no rebuild required.

---

## Table of contents

- [System diagram](#system-diagram)
- [Design principles](#design-principles)
- [Component reference](#component-reference)
- [Data contracts](#data-contracts)
- [Automation topology](#automation-topology)
- [Evaluation loop](#evaluation-loop)
- [Presentation layer](#presentation-layer)
- [Configuration surfaces](#configuration-surfaces)
- [Local development](#local-development)
- [Operational runbook](#operational-runbook)
- [Roadmap](#roadmap)

---

## System diagram

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                              Stage 1 — Collection                                   │
│                              (cheap, deterministic, idempotent)                     │
│                                                                                     │
│    arXiv API      HF Daily Papers    Lab RSS/Atom    GitHub trending    HF trending │
│        │                │                  │                │                  │    │
│        └────────────────┴──────┬───────────┴────────────────┴──────────────────┘    │
│                                ▼                                                    │
│                     collectors/*.py — normalise to Item schema                      │
│                                │                                                    │
│                                ▼                                                    │
│                data/raw/<category>/<YYYY-MM-DD>/<id>.json   (append-only)           │
│                data/seen.json                              (rolling dedup ledger)   │
└────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │  workflow_run trigger
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│                              Stage 2 — Distillation                                 │
│                              (judgment: heuristic score + model synthesis)          │
│                                                                                     │
│    distill/score.py    →   0–5 traction score per item (stdlib heuristic)           │
│    distill/focus.py    →   FOCUS re-rank boost from config/profile.yaml             │
│    distill/delta.py    →   diff against data/state.json → new / climbing / cooled   │
│    distill/synthesize.py → single model call → reports/<YYYY-MM-DD>-digest.md       │
│    distill/reindex.py  →   reports/README.md + reports/latest.md + prev/next nav    │
│    distill/deliver.py  →   optional SMTP push (no-op if unset)                      │
└────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │  reports/latest.md + data/state.json
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│                              Stage 3 — Evaluation                                   │
│                              (self-grading + causal improvement backlog)            │
│                                                                                     │
│    daily 12:00 UTC (Perplexity scheduled task, out-of-repo)                         │
│      ├─ pulls reports/latest.md + data/state.json + previous digest                 │
│      ├─ HEAD-checks every URL in the Main list                                      │
│      ├─ scores 10 dimensions (5 answer-quality + 5 experience/architecture)         │
│      ├─ commits evals/<date>.json  →  evals/latest.json                             │
│      ├─ regenerates evals/README.md 30-day trend table                              │
│      ├─ appends causal items to evals/backlog.md                                    │
│      └─ opens a throttled GitHub issue when any dim ≤ 2 or broken URLs > 0          │
└────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │  raw.githubusercontent.com (live fetch)
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│                              Stage 4 — Presentation                                 │
│                              (amaljithkuttamath.github.io/radar, Astro static)      │
│                                                                                     │
│    reads state.json + reports/latest.md + evals/latest.json at request time —       │
│    no site rebuild needed for a new digest to appear on the board                   │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Design principles

Five non-negotiables the codebase enforces:

1. **Separate `signal` from `judgment`.** Collectors are stdlib-only, deterministic, and never call a model. The model only participates in the synthesis and enrichment passes. Rerunning the judgment pass on the same corpus must be free of side effects.
2. **Corpus is the durable artifact.** `data/raw/` is gitignored (regenerable, unbounded growth) and passed between workflows as a 3-day-retention artifact. Everything else in the repo can be reconstructed from a corpus snapshot + config.
3. **Precision over recall.** Collectors over-collect; the distiller sets the bar high. `include_threshold: 2` keeps the main list to ~10 items even on high-signal days.
4. **Traction ≠ relevance.** The 0–5 traction score is source-independent and pooled across users. Personalisation is a *re-rank boost* applied after scoring (`focus_match` in the item schema), never mixed into the score itself.
5. **Every commit path is disjoint.** `collect-corpus.yml` writes only `data/seen.json`. `distill.yml` writes only `reports/*.md` + `data/state.json`. Concurrent workflow runs cannot collide by construction.

---

## Component reference

### `collectors/` — normalised source adapters

| File | Source | Fetch strategy | Deps |
|------|--------|----------------|------|
| `arxiv.py` | arXiv API (`cs.LG`, `cs.CL`, `cs.AI`, configurable) | HTTP GET, XML parse | stdlib |
| `hf_papers.py` | huggingface.co/papers (Daily Papers) | HTML endpoint, JSON island | stdlib |
| `lab_blogs.py` | Lab & vendor RSS/Atom (config-driven) | `feedparser` | feedparser |
| `github_trending.py` | GitHub Search API filtered by topic + window | HTTP GET, JSON | stdlib |
| `hf_trending.py` | HF trending models + datasets | HTTP GET, JSON | stdlib |
| `common.py` | Shared: dedup, date windows, atomic writes, Item schema | — | stdlib |

Adding a new source is three edits: add it to `config/sources.yaml`, document it in `routines/<category>.md`, and point a collector at it. Most fit `lab_blogs.py`'s RSS pattern with zero code.

### `distill/` — the judgment pass

| File | Responsibility |
|------|----------------|
| `score.py` | Heuristic 0–5 traction score. Ingests `signals.hf_upvotes` / `signals.gh_stars` / recency / source authority. Deterministic and pure. |
| `focus.py` | FOCUS re-rank. Reads `config/profile.yaml` (alias-aware, lexical). `FOCUS` env override for one-off lenses. `FOCUS_BACKEND=embed` is stubbed for semantic matching. |
| `delta.py` | Diffs the scored set against `data/state.json` → `new` / `climbing` / `cooled` classes. Uses traction-magnitude growth, not `rank_key`, so a repo doubling its stars actually registers. |
| `enrich.py` | Optional per-item brief (one model call per top-N item). Off by default (`RADAR_AGENT=off`). |
| `synthesize.py` | Loads scored items → single model call → `reports/<date>-digest.md`. Backend selectable via `RADAR_MODEL_BACKEND`. |
| `reindex.py` | Regenerates `reports/README.md` (newest-first index), `reports/latest.md` (fixed pointer), and idempotent `prev / index / next` nav on every digest. |
| `deliver.py` | Optional SMTP push. No-op unless `RADAR_EMAIL_TO` + `RADAR_SMTP_*` are set. |
| `digest.md` | The synthesis prompt. Version-controlled and reviewable. |
| `brief_spec.md` | The per-item brief prompt used by `enrich.py`. |

### `evals/` — self-grading

| File | Purpose |
|------|---------|
| `rubric.md` | The 10-dimension scoring spec (5 answer-quality + 5 experience/architecture). Every score in a committed eval carries a one-sentence justification. |
| `<YYYY-MM-DD>.json` | Per-run scored rubric with justifications, broken-URL list, missed-story list. |
| `latest.json` | Overwrites on every run. The presentation layer reads this. |
| `README.md` | Rolling 30-day trend table, regenerated on each run. |
| `backlog.md` | Append-only improvement queue. Every item is tied to the eval dimension that triggered it. |

---

## Data contracts

Every collector emits the same JSON envelope. The distiller depends on this shape and nothing else:

```jsonc
{
  "id":            "arxiv:2406.01234",     // stable, used for dedup
  "category":      "research",             // research | hardware | releases | ...
  "title":         "…",
  "url":           "https://…",            // link to the PRIMARY artifact
  "source":        "arXiv cs.LG",
  "authors":       ["…"],
  "published":     "2026-06-03T18:00:00Z",
  "fetched":       "2026-06-04T08:00:00Z",
  "raw_summary":   "abstract or blurb",
  "signals":       { "hf_upvotes": 0, "gh_stars": 0 },  // observable traction
  "score":         null,                   // 0–5, set by distill/score.py
  "focus_match":   false                   // FOCUS re-rank boost, NOT part of score
}
```

`data/state.json` is the movers snapshot — a tiny map of `id → { score_tier, traction_magnitude }` from the previous run. `delta.py` reads it, writes it, and the digest's *What changed* section is derived from the diff.

`evals/<date>.json` follows a strict schema (see `evals/rubric.md`); the presentation layer treats `evals/latest.json` as a source of truth for the quality cell in the radar status bar.

---

## Automation topology

Three workflows, each owning a disjoint slice of state:

| Workflow | Trigger | Reads | Writes | Purpose |
|----------|---------|-------|--------|---------|
| [`collect-corpus.yml`](.github/workflows/collect-corpus.yml) | `schedule: 0 11 * * *` UTC + manual | source feeds | `data/seen.json` + `corpus-raw` artifact | Deterministic ingestion. No model calls. Idempotent. |
| [`distill.yml`](.github/workflows/distill.yml) | `workflow_run` on collect-corpus success + manual | `corpus-raw` artifact | `reports/*.md`, `data/state.json` | The judgment pass. Model synthesis + optional SMTP. |
| [`radar.yml`](.github/workflows/radar.yml) | manual only | — | — | Deprecated monolithic rollback. Kept one release cycle. |

Key architectural choices:

- **Reactive, not scheduled.** `distill.yml` fires on `workflow_run` when `collect-corpus.yml` completes. No arbitrary "how long does collect take" cron gap; the distill run pulls the fresh artifact via `run-id`.
- **Artifacts, not committed corpus.** `data/raw/` is gitignored. The corpus is passed run-to-run as a 3-day-retention artifact — the repo stays lean while the two workflows share state.
- **`concurrency:` groups per workflow.** Two collects can never overlap. Two distills can never overlap. But a collect and a distill can, because their write sets are disjoint.
- **Rebase-on-push guard.** Both commit steps run `git pull --rebase origin main || true` before pushing — a defensive line, unnecessary given the disjoint write scope, but cheap insurance against future workflow additions.

The evaluation loop lives outside CI, as a Perplexity scheduled task that fires at 12:00 UTC daily and interacts with the repo through the GitHub REST API. This keeps evaluation out of the write path of the pipeline it grades — a deliberate independence property.

---

## Evaluation loop

Every digest is scored on ten dimensions, five per axis, on a 0–5 scale with per-dimension justifications.

### Axis A — Answer quality (the digest itself)

| Dim | Measures | Scoring anchors |
|-----|----------|-----------------|
| **A1** signal_density | Non-obvious insight per paragraph | 5 = every line earns space; 1 = restated abstracts |
| **A2** source_integrity | Primary sources over aggregators, no broken links | Any broken URL caps at 2 |
| **A3** focus_alignment | Serves `profile.yaml` topics without echo chamber | 5 = strong fit + one adjacent surprise |
| **A4** delta_clarity | *What changed* is a real diff, not a restatement | 5 = explicit new/climbing/cooled with reasons |
| **A5** coverage | Inverse of missed important last-24h stories | 0 missed = 5; 3+ missed = 1 |

### Axis X — Experience & architecture (how it reaches the reader)

| Dim | Measures | Scoring anchors |
|-----|----------|-----------------|
| **X1** board_legibility | Cold reader grasps top story in <10 s on `/radar` | 5 = top row is unambiguously the story of the day |
| **X2** instrument_honesty | Synthesis labeled as machine opinion; observed signals dominate | 5 = attribution + observed signals visually dominate |
| **X3** freshness | Hours from digest publish to eval run | <6 h = 5; >36 h = 1 |
| **X4** failure_surface | One 4xx doesn't cascade to digest or page | 5 = isolated try/catch per fetch |
| **X5** coupling | collect / distill / render remain independently regenerable | 5 = strict boundaries |

### Triggers

- Any dimension ≤ 2 → GitHub issue (72-hour throttle across both repos)
- `broken_urls.count > 0` → GitHub issue
- Same dimension ≤ 3 for 3 consecutive days → GitHub issue (persistent regression)
- Every run appends ≥ 1 causal improvement to `evals/backlog.md`

The point of the rubric is not the number — it is the paper trail. Every score cites the specific item, URL, or file line that produced it, so a regression next month can be reasoned about rather than guessed at.

---

## Presentation layer

The public surface at [amaljithkuttamath.github.io/radar](https://amaljithkuttamath.github.io/radar) is an Astro static site living in a separate repo (`amaljithkuttamath.github.io`). It fetches at request time from this repo via `raw.githubusercontent.com`:

- `data/state.json` — the board of active items with scores and traction
- `reports/latest.md` — the current brief
- `evals/latest.json` — the current quality scorecard for the status bar

Because the site reads live, a new digest committed here appears on `/radar` on the next page load. No site rebuild is required. This is the concrete payoff of principle #5 (disjoint commit paths): the presentation layer never needs to know which workflow just wrote.

---

## Configuration surfaces

Three files hold every user-facing dial. Nothing else is configuration.

| File | Purpose | Change frequency |
|------|---------|------------------|
| [`config/sources.yaml`](config/sources.yaml) | Source registry: category → feeds | Weekly (adding sources) |
| [`config/routines.yaml`](config/routines.yaml) | Which collectors run + default distill params (WINDOW / N / FOCUS / MARKET) | Monthly |
| [`config/profile.yaml`](config/profile.yaml) | Personalised FOCUS profile with topic aliases | Quarterly |

Env-var overrides for one-off runs: `WINDOW`, `FOCUS`, `MARKET`, `RADAR_MODEL_BACKEND`, `RADAR_AGENT`, `FOCUS_BACKEND`, `RADAR_EMAIL_TO` + SMTP vars.

---

## Local development

```bash
# Install (uv is the source of truth for deps)
uv sync                                    # or: pip install -e .

# 1. Collect (cheap, idempotent, no model tokens)
python -m collectors.arxiv
python -m collectors.hf_papers
python -m collectors.lab_blogs
python -m collectors.github_trending
python -m collectors.hf_trending

# 2. Distill (the judgment pass)
WINDOW=48h \
FOCUS="interpretability,agents,evals" \
MARKET=on \
RADAR_MODEL_BACKEND=github \              # or: anthropic | ollama | dryrun
bash scripts/distill.sh

# 3. Read
open reports/latest.md
```

Model backends:

- `github` (default in CI) — free inference via `GITHUB_TOKEN`, `models: read` permission
- `anthropic` — reads `ANTHROPIC_API_KEY`
- `ollama` — local model, useful for cheap drafts and offline dev
- `dryrun` — skips the model call, emits a scaffolded digest for pipeline smoke tests

---

## Operational runbook

**A collect run failed.** Look at the workflow logs. Most failures are 4xx / 5xx on a single feed — the collector logs and continues. If `seen.json` didn't advance, no state was polluted; just re-dispatch.

**A distill run produced a "quiet window" digest.** Expected when the artifact download step was skipped (manual `workflow_dispatch` without collect). Not a failure — it is the correct signal for "no fresh corpus."

**Evals scored ≤ 2 on a dimension.** A GitHub issue was opened automatically (throttled to one per 72 h across both repos). Read the linked `evals/<date>.json` for the justification; the fix is usually the improvement item added to `evals/backlog.md` on the same run.

**The `/radar` page shows stale data.** The site reads live from `raw.githubusercontent.com` (CDN'd, ~5 min propagation). Check `reports/latest.md` on GitHub first; if the file is fresh but the page is stale, hard-refresh past the CDN.

**Rolling back a bad digest.** `reports/latest.md` is regenerated from the newest dated file by `distill/reindex.py`. Delete or `git revert` the bad `reports/YYYY-MM-DD-digest.md`, run `python -m distill.reindex`, commit. The `/radar` page catches up on the next request.

---

## Roadmap

**Landed**
- ✅ Two-stage collect / distill split with reactive `workflow_run` triggering
- ✅ Movers view (`new` / `climbing` / `cooled`) via `data/state.json` diff
- ✅ Alias-aware FOCUS profile (`config/profile.yaml`)
- ✅ Optional SMTP delivery (no-op unless configured)
- ✅ 10-dimension eval loop with committed rubric, trend table, and causal backlog
- ✅ HF Daily Papers parser verified against live output; all 5 lab RSS feeds verified

**Open**
- [ ] GitHub star-velocity enricher for `signals.gh_stars` across runs
- [ ] Wire the stubbed `FOCUS_BACKEND=embed` semantic matcher
- [ ] `collect-social.yml` — HN + Reddit + Bluesky every 2 h
- [ ] `fuse-and-detect.yml` — reactive social-heat detector emitting `repository_dispatch`
- [ ] `deep-dive.yml` — reactive on `trigger_fired`, plus manual and labeled-issue entry points
- [ ] Expose `evals/latest.json` in the `/radar` status bar (tracked in the presentation-side backlog)

---

## Non-goals

- **This is not investment advice.** `MARKET=on` maps who is exposed to what, through which mechanism — never buy/sell/hold calls, targets, or sizing.
- **This is not a firehose.** The distiller optimises for six things that matter over forty that don't.
- **This is not a leaderboard.** The rubric grades *this* digest against its rubric, not the digest against other newsletters.

---

## License

See [LICENSE](LICENSE).

<sub>Every commit path here is disjoint on purpose. Every score has a citation. Every URL is HEAD-checked before the digest ships. If any of that stops being true, open an issue.</sub>
