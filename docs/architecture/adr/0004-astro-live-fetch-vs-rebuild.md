# ADR-0004. Astro site uses live fetch, not rebuild-on-commit

**Status.** Accepted, 2026-06.

## Context

The site at `amaljithkuttamath.github.io/radar` renders the current digest and the board of active items. Two ways to keep it fresh:

1. Trigger an Astro rebuild every time this repo commits to `main`. Rebuild fetches the latest `state.json`, `latest.md`, `evals/latest.json`, and generates a new static bundle.
2. Ship a static site once; fetch the three files client-side at request time from `raw.githubusercontent.com`.

Option 1 has propagation latency of minutes (build + deploy). It re-generates HTML for content that hasn't structurally changed. It also couples the site's deploy pipeline to this repo's commit rhythm.

Option 2 has propagation latency of ~5 minutes at the CDN, but the fetch itself is instantaneous.

## Decision

Live fetch. The site's `radar.astro` reads `state.json`, `reports/latest.md`, and `evals/latest.json` from `raw.githubusercontent.com` at request time.

## Consequences

**Positive.**
- No coupling between this repo and the site's deploy pipeline.
- New digest becomes visible on the next page load. No rebuild queue.
- Site can be forked or replaced without touching this repo.

**Negative.**
- Site is offline if `raw.githubusercontent.com` is down. Same availability as GitHub raw content.
- Site cannot pre-render digest markup (the digest is fetched client-side and rendered in the browser). Grader `X4 failure_surface` flags cascading fetch failures if the client doesn't isolate them.
- Structural changes to the schemas require a site update. Mitigated by the additive-only field policy in [04-data-model.md](../04-data-model.md).
