# Eval schema

Canonical shape for every file the grader writes to `evals/`. Applies to `evals/<YYYY-MM-DD>.json` AND `evals/latest.json`. Both files carry the same object.

If a historical eval doesn't match this schema, it needs a migration PR. The grader may not write a new eval that mixes old and new keys in the same directory: `README.md` regeneration assumes uniformity.

## Schema

```jsonc
{
  "date":                    "YYYY-MM-DD",              // required. UTC calendar date of the digest.
  "mode":                    "normal",                  // required. Enum: normal | recovery | pre-merge | demo
  "digest_url":              "https://raw.githubusercontent.com/amaljithkuttamath/ai-radar/main/reports/latest.md",
  "digest_commit_time_utc":  "2026-07-12T11:53:19Z",    // required. ISO 8601 UTC. Source: git commit time of reports/latest.md.
  "age_hours_at_eval":       0.36,                      // required. float. Hours between digest_commit_time_utc and eval run time.

  "overall":                 4.2,                       // required. mean(quality.overall, experience.overall). 1 decimal.

  "quality": {
    "overall": 4.2,                                     // required. mean(A1..A5). 1 decimal.
    "A1": { "score": 4, "why": "<max 15 words citing item/URL/line>" },
    "A2": { "score": 5, "why": "..." },
    "A3": { "score": 4, "why": "..." },
    "A4": { "score": 4, "why": "..." },
    "A5": { "score": 4, "why": "..." }
  },

  "experience": {
    "overall": 4.2,                                     // required. mean(X1..X5). 1 decimal.
    "X1": { "score": 4, "why": "..." },
    "X2": { "score": 4, "why": "..." },
    "X3": { "score": 5, "why": "..." },
    "X4": { "score": 4, "why": "..." },
    "X5": { "score": 4, "why": "..." }
  },

  "broken_urls": [                                      // required. Array of objects. Empty array if none.
    { "url": "https://...", "status": 404 }
  ],

  "missed_stories": [                                   // required. Array. Empty array if none.
    {
      "title": "...",
      "url":   "https://...",
      "why":   "<max 30 words explaining why the digest should have included it>"
    }
  ]
}
```

## Field rules

### `date`
Calendar date the digest is dated for. Format `YYYY-MM-DD`. **Not** the eval run time. Matches the H1 header of the digest and the filename of the dated `evals/<date>.json`.

### `mode`
Enum. Only these values are valid:

| Value | Meaning |
|-------|---------|
| `normal` | Scheduled 12:00 UTC run against a fresh digest. |
| `recovery` | One-off run triggered because the scheduled run escalated or failed. Same schema as `normal`. |
| `pre-merge` | Legacy. Runs before `evals/` scaffolding merged. Historical only. New runs never emit this. |
| `demo` | Demo/dry-run. Written to `evals/demo/`, never to `evals/<date>.json` or `evals/latest.json`. |

### `digest_commit_time_utc`
ISO 8601 UTC timestamp from `gh api "repos/.../commits?path=reports/latest.md&per_page=1" --jq '.[0].commit.committer.date'`. Required. This is the authoritative freshness source per [`grader.md#freshness`](grader.md#freshness).

### `age_hours_at_eval`
Float, 2 decimals. `(eval_run_time_utc - digest_commit_time_utc) / 3600`. Must be in `[-12.0, 72.0]` or the eval is invalid and the run escalates.

### `overall`, `quality.overall`, `experience.overall`
Floats to 1 decimal. Recomputed from the dim scores on every run. Never edited manually.

### Dim `score`
Integer in `[0, 5]`. No half scores.

### Dim `why`
Maximum 15 words. Must cite concrete evidence: item id, URL, line number in the digest, or field name in state.json/latest.json. Empty or vague `why` is a grader bug.

Dim keys are exactly `A1`..`A5` and `X1`..`X5`. **Never** the long form (`A1_signal_density`). The dim name is implicit in the position; the anchor text lives in `evals/rubric.md`.

### `broken_urls`
Array of `{url, status}` objects, one per URL that HEAD-checked non-2xx. Empty array if none. `status` is the integer HTTP status code observed.

### `missed_stories`
Array of `{title, url, why}` objects. Empty array if none. `why` may be longer than dim justifications (up to 30 words) because it must argue for inclusion.

## Non-fields

These do NOT belong in the schema. If a historical eval has them, drop them during migration.

- `run` (superseded by `mode`)
- `inputs.*` (all inputs are known from `digest_url` and `digest_commit_time_utc`)
- `broken_urls.count`, `broken_urls.items` (flat array now)
- `scores.A1_signal_density`, etc. (use `quality.A1`, etc.)
- `aggregates.*` (aggregates are inline: `overall`, `quality.overall`, `experience.overall`)
- `enriched_top_items` (belongs in the newsletter body, not the eval object)
- `notes` (free-form; not machine-readable; belongs in `evals/backlog.md`)

## Schema versioning

Fields are additive. A new field is a compatible change. Removing or renaming a field is a breaking change and requires:

1. A PR that updates this file with the new shape.
2. A migration PR that rewrites every `evals/<date>.json` and `evals/latest.json` to the new shape.
3. Grader and any reader (`radar.astro`, `README.md` regeneration) updated in the same PR set.

No versioning field on the object. Consumers duck-type: read what's there, ignore unknown fields, default missing ones sensibly. If duck-typing gets ambiguous, add a `schema_version` field and start numbering.

## Example

See `evals/2026-07-12.json` on `main` for the canonical example (both nested schema and terse justifications).
