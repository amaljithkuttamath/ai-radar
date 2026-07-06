# 05. Flows

Three sequence diagrams. Everything else is one of these composed with itself.

## Flow 1. Daily happy path

```mermaid
sequenceDiagram
  autonumber
  participant Cron as GH Cron
  participant Collect as collect-corpus.yml
  participant Sources as public sources
  participant Repo as git repo (main)
  participant Distill as distill.yml
  participant Model as LLM provider
  participant Site as radar.astro
  participant PC as Perplexity cron
  participant Grader as daily grader
  participant Reader as public reader

  Note over Cron: 11:00 UTC
  Cron->>Collect: fire schedule
  Collect->>Sources: HTTP GET (arXiv, HF, RSS, GH, HF trending)
  Sources-->>Collect: JSON / XML / HTML
  Collect->>Collect: normalise to Item, dedup vs seen.json
  Collect->>Repo: commit data/seen.json
  Collect->>Distill: workflow_run event + corpus-raw artifact

  Note over Distill: reactive trigger
  Distill->>Distill: score.py -> focus.py -> delta.py
  Distill->>Model: one synthesis call
  Model-->>Distill: markdown digest
  Distill->>Distill: reindex.py (latest.md + README + nav)
  Distill->>Repo: commit reports/**, data/state.json

  Note over PC: 12:00 UTC
  PC->>Grader: fire schedule
  Grader->>Repo: gh api GET reports/latest.md, state.json, evals/**
  Repo-->>Grader: content
  Grader->>Grader: HEAD-check URLs, score 10 dims
  Grader->>Repo: gh api PUT evals/<date>.json, latest.json, README.md, backlog.md

  loop when reader visits
    Reader->>Site: HTTPS GET /radar
    Site->>Repo: raw.githubusercontent.com fetch (state.json, latest.md, evals/latest.json)
    Repo-->>Site: content
    Site-->>Reader: rendered page
  end
```

## Flow 2. Manual re-distill (no re-collect)

Used when the digest needs to be rebuilt without paying to refetch. Example: tweaked the synthesis prompt.

```mermaid
sequenceDiagram
  autonumber
  participant Owner as repo owner
  participant Distill as distill.yml
  participant Repo as git repo (main)
  participant Model as LLM provider

  Owner->>Distill: workflow_dispatch (window, focus, backend)
  Note over Distill: no workflow_run source -> skip artifact download
  Distill->>Distill: run score/focus/delta on whatever raw/ exists locally
  Note over Distill: fresh checkout -> data/raw/ is empty
  Distill->>Model: synthesis call
  Model-->>Distill: "quiet window" markdown
  Distill->>Repo: commit reports/**, state.json
```

Design note: the fresh checkout on `workflow_dispatch` yields an empty `data/raw/`. That produces a "quiet window" digest, which is the correct signal for a manual re-distill without a preceding collect. It is not a bug. If you want a full re-distill, dispatch `collect-corpus.yml` first and let its `workflow_run` trigger fire naturally.

## Flow 3. Eval finds a regression, files an issue

```mermaid
sequenceDiagram
  autonumber
  participant PC as Perplexity cron
  participant Grader as daily grader
  participant Repo as git repo (main)
  participant Search as search_web / fetch_url
  participant GH as GitHub API (issues)

  PC->>Grader: fire schedule (12:00 UTC)
  Grader->>Repo: gh api GET reports/latest.md, state.json, evals/**
  Grader->>Grader: HEAD-check every URL in Main list
  Note over Grader: 2 URLs 404
  Grader->>Grader: A2 source_integrity capped at 2
  Grader->>Search: search for last-24h stories in focus topics
  Search-->>Grader: candidate list
  Grader->>Grader: score 10 dims with justifications
  Grader->>Repo: gh api PUT evals/2026-07-06.json + latest.json
  Grader->>Repo: gh api PUT evals/backlog.md (append 1-3 items)
  Grader->>Repo: gh api PUT evals/README.md (regenerate trend)

  alt no bot issue in last 72h
    Grader->>GH: gh issue create --title "[eval] A2: HEAD-check URLs pre-commit"
    GH-->>Grader: issue url
  else within 72h throttle
    Note over Grader: skip issue creation
  end
```

## Concurrency

- `collect-corpus` and `distill` never run in parallel with themselves (concurrency groups).
- `collect-corpus` and `distill` can run in parallel with each other. Write sets are disjoint (see [`diagrams/state-ownership.svg`](diagrams/state-ownership.svg)).
- Grader runs alone in its own runtime. Cannot collide with either workflow.
- Reader traffic is idempotent. No coordination needed with any writer.

## Retry model

Each container has its own retry semantics.

| Container | On failure |
|-----------|------------|
| `collect-corpus` | GitHub Actions no auto-retry. Next scheduled run backfills. |
| `distill` | GitHub Actions no auto-retry. Manual dispatch to re-run. |
| grader | Escalates on ambiguity; retries on transient `gh api` errors with exponential backoff. |
| site | Reader-side. Retries are up to the reader's browser. |
