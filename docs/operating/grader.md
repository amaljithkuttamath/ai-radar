# Grader contract

The grader is a scheduled task at 12:00 UTC (8:00 AM ET). It reads the latest digest, scores it against the 10-dim rubric, commits eval artifacts, and files an issue when quality drops.

Preconditions: [`.github/AGENTS.md`](../../.github/AGENTS.md), [`invariants.md`](invariants.md), [`whitelist.md`](whitelist.md) all loaded and honored.

## Pull

Read via `gh api`:

- `reports/latest.md`. If 404, list `reports/`, pick the newest `YYYY-MM-DD-digest.md`.
- Previous digest for delta.
- `data/state.json`.
- `amaljithkuttamath/amaljithkuttamath.github.io` → `src/pages/radar.astro`.
- Newest 3 files under `evals/` for trend context.
- `evals/backlog.md`.
- `evals/rubric.md` for scoring anchors.

Optional reads (suppress 404): prior evals, backlog, rubric. Only `reports/*` and `data/state.json` are core.

## Freshness

Digest is stale only if age is strictly greater than 36 hours. Exactly 36.0h is fresh. If stale, end silently. Do not email, do not write evals.

## Enrich

- Validate top 5-8 items with `search_web` / `fetch_url`. Add one crisp "why it matters" per item, grounded in a primary source (arXiv abs, lab blog, official repo/release). Aggregators and Twitter only if no primary source exists.
- Find 1-3 stories from the last 24h the digest missed. Omit section if none.
- HEAD-check every URL in Main list. Record broken URLs. Broken URLs cap `A2` at 2.

## Score

Ten dimensions, 0-5 each, one-sentence justification per score. Full anchors in [`evals/rubric.md`](../../evals/rubric.md).

- Answer quality: `A1 signal_density`, `A2 source_integrity`, `A3 focus_alignment`, `A4 delta_clarity`, `A5 coverage`.
- Experience: `X1 board_legibility`, `X2 instrument_honesty`, `X3 freshness`, `X4 failure_surface`, `X5 coupling`.

Aggregates: `quality.overall = mean(A1..A5)`, `experience.overall = mean(X1..X5)`, `overall = mean(quality, experience)`.

## Write

Per [`whitelist.md#grader`](whitelist.md#grader). All writes via `gh api PUT /repos/.../contents/<path>` with fresh `sha`. Committer `radar-eval-bot <radar-eval-bot@users.noreply.github.com>`. Commit message: `evals: <date>. Quality=X.X experience=X.X`.

1. `evals/<YYYY-MM-DD>.json`. Full rubric object per [`../04-data-model.md`](../architecture.md#data-contracts) if it exists, otherwise the schema in the rubric file.
2. `evals/latest.json`. Same object, overwritten.
3. `evals/README.md`. Regenerate the 30-day trend table from `evals/*.json` (exclude `demo/` and `pre-merge/`).
4. `evals/backlog.md`. Append 1-3 causal improvement items derived from the lowest-scoring dims (see [Backlog appends](#backlog-appends)).

## Backlog appends

Every run appends at least one causal item to `evals/backlog.md`. Format:

```
- [ ] YYYY-MM-DD · <title> · <file path> · <2-sentence rationale> · triggered by <dim + score>
```

Causal means: tied to the specific low-scoring dim. Generic wishlist items are a bug.

Sections: `## Open. Pipeline (ai-radar)`, `## Open. Presentation (amaljithkuttamath.github.io)`, `## Done`.

## Issues

File a `[eval]` issue only when:

- Any dimension scores ≤ 2, OR
- `broken_urls.count > 0`, OR
- Same dimension scored ≤ 3 for 3+ consecutive days (read prior evals to detect).

Throttle: at most one issue per 72h across `ai-radar` + `amaljithkuttamath.github.io` combined. Check `gh issue list --author @me --limit 3 --json createdAt,title` on both.

Issue title: `[eval] <dim>: <one-line fix>`. Include the `eval` label so the coder can query for it.

Issue body must include:

- The failing dimension and its score.
- The one-sentence `why` justification from today's `evals/<date>.json`.
- A proposed fix with a file path from the coder's whitelist (so it's actionable).
- Link to today's committed `evals/<date>.json`.

## Deliver

`send_notification` with `channels=["email"]`, `email_args={"template":"generic","subject":"AI Radar , <date> · quality=X.X experience=X.X"}`. Body: the enriched newsletter with sections per the current template. `schedule_description="Daily · 8:00 AM ET"`.

## Escalation

- Missing core input (`reports/*`, `data/state.json`, `rubric.md`): halt and escalate.
- Ambiguous freshness: use `> 36h` strictly. Exact 36.0h is fresh.
- Contract file (`grader.md` or `invariants.md`) unreadable or missing: halt, escalate. Do not fall back to task text.
- If task text conflicts with this file, follow this file and log the diff as a comment on the newest open `[eval]` issue.

## Non-goals

- Never writes code.
- Never opens PRs.
- Never touches `config/**`, `distill/**`, `collectors/**`, `.github/**`, `data/**`, `reports/**`.
- Never files more than one issue per 72h.
