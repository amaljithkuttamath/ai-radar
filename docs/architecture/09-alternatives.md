# 09. Alternatives considered

The honest section. What we didn't do and why.

## Pipeline shape

### Alt A: single monolithic workflow

Do collect + score + distill + deliver in one job.

**Rejected because.** Collector failures would consume model tokens on partial data. Manual re-distill would re-collect. Retry semantics conflate two different concerns.

**Kept.** `radar.yml` retained as a deprecated manual rollback for one release cycle.

### Alt B: three-stage pipeline (collect → score → distill)

Split scoring into its own workflow.

**Rejected because.** Scoring is cheap, deterministic, and stateless. Running it in its own job adds an artifact hop and a checkout for no benefit. It fits inside distill.

### Alt C: event-driven per-source workflows

One workflow per source, each firing on its own cadence.

**Rejected because.** Adds N workflow YAMLs for the sake of parallelism the workload doesn't need. Also increases the surface area for `permissions` misconfiguration.

## State storage

### Alt A: commit `data/raw/` to git

Never delete the corpus. Full history.

**Rejected because.** Grows unbounded. `data/raw/` at current cadence adds ~150 MB/year. Merge conflicts on `main` become likely as more workflows write there.

### Alt B: external object store (S3, R2)

Move the corpus and artifacts to object storage.

**Rejected because.** Adds a cloud account and credentials as dependencies. The 3-day artifact retention on GitHub Actions is sufficient for the pipeline's needs, and the eval loop doesn't need historical raw data.

### Alt C: dedicated database (SQLite, Postgres)

Store items in a real database.

**Rejected because.** No query workload justifies it. The distiller reads the day's JSON once. Adding a database means adding a schema migration story, a backup story, and a "what if the DB is down" story for no upside.

## Eval loop location

### Alt A: eval as a step inside `distill.yml`

Score the digest right after it's written.

**Rejected because.** A pipeline bug could suppress its own criticism. Independence is the whole point. See [ADR-0003](adr/0003-eval-loop-out-of-repo.md).

### Alt B: eval as a separate workflow inside this repo

`eval.yml` on its own cron.

**Rejected because.** Still shares the same runtime and secrets surface as the pipeline. Also, the grader needs to file issues, which requires a PAT (workflow tokens can't cross-repo). Running it in Perplexity's scheduled-task runtime keeps the credential surface small and clean.

### Alt C: human-only eval

Read the digest, grade it manually.

**Rejected because.** Requires daily discipline. Human eval is inconsistent across days. Missing dimensions (freshness, coupling) that a machine grader catches for free.

## Personalisation

### Alt A: bake FOCUS into the traction score

Add a "focus boost" to `score.py`.

**Rejected because.** Score becomes user-specific, so multi-user reads of the same digest need per-user scoring. Also destroys the invariant that `score` is a shared frame of reference.

### Alt B: full semantic FOCUS matcher on day one

Ship with embeddings.

**Rejected because.** Adds a dep (`sentence-transformers` or a network call). Lexical + aliases covers 90% of the value. `FOCUS_BACKEND=embed` is stubbed for when someone wants it.

## Digest delivery

### Alt A: RSS feed

Publish a `/feed.xml`.

**Deferred.** Not rejected. Trivial to add via the reindex step once we know readers want it.

### Alt B: newsletter platform (Substack, Beehiiv)

Push to a hosted newsletter.

**Rejected because.** Adds an external account and drift between the platform's rendering and the git-hosted source. SMTP is optional and covers the "email me" use case without lock-in.

## Presentation

### Alt A: server-rendered site

Node/Next.js server that reads from the repo and serves.

**Rejected because.** Adds always-on compute. The static + live-fetch pattern is cheaper, faster, and has no server to keep running.

### Alt B: rebuild the Astro site on every commit

Trigger a build when `main` updates.

**Rejected because.** Build latency is minutes; live fetch is seconds. Site content isn't structurally new per digest, only its data is. See [ADR-0004](adr/0004-astro-live-fetch-vs-rebuild.md).

## Workflow triggers

### Alt A: cron-based distill (`schedule: 0 13 * * *`)

Fire distill at 13:00 UTC, 2 hours after collect.

**Rejected because.** The 2-hour gap is arbitrary. If collect takes 3 hours (large window, slow feeds), distill runs against an incomplete corpus. `workflow_run` removes the guess. See [ADR-0002](adr/0002-reactive-workflow-run-trigger.md).

### Alt B: distill polls for a "ready" file

Check every N minutes for a corpus completion marker.

**Rejected because.** Polling burns Actions minutes for nothing. `workflow_run` is push, not pull.
