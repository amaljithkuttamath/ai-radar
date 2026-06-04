# AI Radar

A two-stage pipeline for tracking AI developments. **Collect** raw signals from many
sources into organized folders, then **distill** the accumulated corpus into insights
and action items on demand.

```
 sources ──► collect ──► data/raw/<category>/<date>/*.json ──► score ──► distill ──► reports/
            (cheap,                  (durable corpus)        (heuristic)  (judgment    (dated
          deterministic)                                                  + a model)   digest)
```

## Why two stages

Collection and judgment have different cost and cadence profiles, so they shouldn't be
coupled:

- **Collection is cheap and deterministic.** Hit dated feeds (arXiv API, HF Daily Papers,
  RSS), write one JSON record per item into a category folder, dedup against a seen-list.
  Run it often and idempotently — no model tokens required.
- **Distillation is the expensive judgment pass.** Score the corpus, then have a model
  synthesize the report. Run it when you want a read — and re-run it with different lenses
  (window, focus area, market on/off) **without re-fetching anything.**

The corpus in `data/raw/` is the durable asset. Everything downstream is regenerable.

## Layout

```
ai-radar/
├── config/
│   ├── sources.yaml      # the source registry — category → feeds. This is the dial you turn most.
│   └── routines.yaml     # which collectors run + default distill params (WINDOW/N/FOCUS/MARKET)
├── routines/             # human-readable spec for each collector (what it pulls, how it scores)
│   ├── research.md
│   └── hardware.md
├── collectors/           # deterministic fetchers → data/raw/
│   ├── common.py         # IO, dedup/seen-list, date windows, item schema  (stdlib only)
│   ├── arxiv.py          # arXiv API collector (runnable)
│   ├── hf_papers.py      # Hugging Face Daily Papers collector (runnable)
│   └── lab_blogs.py      # RSS/Atom collector for lab & vendor newsrooms (config-driven)
├── distill/
│   ├── digest.md         # the distillation routine (the prompt that turns folders → report)
│   ├── score.py          # heuristic 0–5 traction score (FOCUS kept separate)
│   └── synthesize.py     # loads scored items, calls a model, writes reports/<date>-digest.md
├── data/
│   ├── raw/<category>/<date>/<id>.json   # append-only collected items
│   ├── scored/                            # items after the scoring pass
│   └── seen.json                          # rolling seen-list for cross-run dedup
├── reports/              # final dated digests
├── scripts/run.sh        # orchestrate: collect → score → distill
└── requirements.txt
```

## Data model

Every collector writes the same record so the distiller doesn't care where an item came from:

```json
{
  "id": "arxiv:2406.01234",          // stable id, used for dedup
  "category": "research",
  "title": "...",
  "url": "https://...",               // link to the PRIMARY artifact
  "source": "arXiv cs.LG",
  "authors": ["..."],
  "published": "2026-06-03T18:00:00Z",
  "fetched":   "2026-06-04T08:00:00Z",
  "raw_summary": "abstract or blurb",
  "signals": { "hf_upvotes": 0, "gh_stars": 0 },  // observable traction, filled opportunistically
  "score": null,                       // 0–5 traction, set by distill/score.py
  "focus_match": false                 // FOCUS relevance — a re-rank boost, NOT in the score
}
```

## Routines (collectors)

Each category is a folder + a spec. To add a source you edit `config/sources.yaml`;
the routine spec in `routines/` documents intent and the scoring nuances for that category
(e.g. hardware scores on perf-per-$ / perf-per-watt deltas and real ship dates, not keynotes; FOCUS is a re-rank boost applied after scoring, never part of the 0–5 number).

Add a new category in three steps: add it to `sources.yaml`, write a `routines/<name>.md`
spec, and point a collector at it (most fit `lab_blogs.py`'s RSS pattern).

## Distillation

`distill/digest.md` is the routine prompt. `synthesize.py` loads scored items for the
window, feeds them to a model, and writes a report with:

- **Top-line** — the one thing that matters + the window's theme
- **Main list** — scored, ranked, with primary links
- **Watch-list** — promising but unverified
- **Market exposure** — *optional, MARKET=on* — mechanism mapping, see note below
- **Insights** — patterns across items
- **Action items** — read / try / track, e.g. "pull this model to test locally," "watch this benchmark"

## Running

```bash
pip install -r requirements.txt

# 1. collect (cheap, idempotent — safe to run on a schedule)
python -m collectors.arxiv
python -m collectors.hf_papers
python -m collectors.lab_blogs

# 2. score + 3. distill (the judgment pass)
WINDOW=48h FOCUS="interpretability,agents,evals" MARKET=on bash scripts/run.sh
```

The model call in `synthesize.py` is backend-agnostic: set `RADAR_MODEL_BACKEND=anthropic`
(reads `ANTHROPIC_API_KEY` from env) for the synthesis pass, or `=ollama` to run a local
model for cheap scoring/drafts. Deterministic fetching never calls a model.

## Design decisions & non-goals

- **Market exposure is mechanism-mapping, not investment advice.** The pipeline maps who is
  exposed, through what mechanism, in which direction, and the counter-argument — never
  buy/sell/hold calls, targets, or sizing. A single item rarely moves a stock durably and is
  often already priced. You draw the conclusions.
- **Market is a lens, not a collector.** Earnings and chip launches are collected under
  `hardware`/`releases`; the *market read* is an enrichment applied during distillation to
  high-impact items only. Keeps the everyday corpus clean.
- **Model-agnostic by construction.** Code does the deterministic work; a model you choose
  does the judgment. Swap freely.
- **Precision over recall.** Better to surface six things that matter than forty that don't.
  Collectors over-collect; the distiller is where the bar is high.

## Roadmap

- [ ] Verify the HF Daily Papers endpoint shape in `hf_papers.py` against live output
- [ ] Fill `config/sources.yaml` lab/vendor RSS URLs (placeholders included)
- [ ] GitHub Action to run collectors daily and open a PR with the digest
- [ ] Optional: GitHub stars-velocity enricher for `signals.gh_stars`
