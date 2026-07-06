# 04. Data model

Three schemas run the whole system. Everything else is derived.

## `Item`. The collector output envelope

```jsonc
{
  "id":          "arxiv:2406.01234",        // required. Stable id for dedup. Format: <source>:<native-id>.
  "category":    "research",                // required. One of: research | hardware | releases | social (planned)
  "title":       "…",                       // required. Untrusted string.
  "url":         "https://…",               // required. Primary artifact link. Must be HEAD-checkable.
  "source":      "arXiv cs.LG",             // required. Human-readable source label.
  "authors":     ["…"],                     // optional. Empty array if unknown.
  "published":   "2026-06-03T18:00:00Z",    // required. ISO 8601 UTC. Source-reported publish time.
  "fetched":     "2026-06-04T08:00:00Z",    // required. ISO 8601 UTC. Collector wall time.
  "raw_summary": "…",                       // optional. Abstract or blurb. Untrusted string.
  "signals":     { "hf_upvotes": 0, "gh_stars": 0 },  // required object. Missing signals default to 0.
  "score":       null,                      // set by score.py. Integer 0-5. null on the collector side.
  "focus_match": false,                     // set by focus.py. Boolean. false on the collector side.
  "delta_class": null                       // set by delta.py after state.json diff. Enum below.
}
```

### Field-level rules

- **`id`.** Prefix scheme reserves the source space: `arxiv:`, `hf:`, `gh:`, `hn:`, `blog:<host>:`. New sources add a prefix in [ADR-????](adr/) before shipping.
- **`title`, `raw_summary`.** Treated as adversarial content. Rendered in Markdown, not HTML. Never interpolated into a shell command.
- **`url`.** Must resolve to a primary artifact (arXiv abs page, lab blog post, official repo release). Aggregators are allowed only when no primary exists. Grader `A2 source_integrity` will HEAD-check.
- **`published`.** Source-reported. Used for windowing and freshness. Trusted for ordering, not for uniqueness (see `id` for that).
- **`signals`.** Additive-only. New signal keys are allowed. Removing a key is a breaking change.
- **`delta_class` enum.** `new | climbing | cooled | steady`. First-run corpus is all `new`.

### Backwards compatibility

Consumers (score, focus, delta, synthesize) must tolerate unknown fields. Producers must never remove a required field without a migration. New required fields need a migration in `data/raw/**` for the current retention window; the artifact TTL is 3 days so migrations are cheap.

## `state.json`. The movers snapshot

Written by `distill/delta.py` at the end of every run. Read at the start of the next run.

```jsonc
{
  "as_of": "2026-07-06T12:11:00Z",          // ISO 8601. When this snapshot was taken.
  "digest_date": "2026-07-06",              // For sanity checking against the file name.
  "items": {
    "arxiv:2406.01234": {
      "score":               4,
      "traction_magnitude":  1230,          // hf_upvotes + gh_stars, additive
      "score_tier":          "high",        // low | mid | high (mapped from score)
      "last_seen":           "2026-07-06T12:11:00Z"
    }
  }
}
```

### Rules

- One writer: `distill/delta.py`.
- Two readers: next run of `delta.py`; the site's `radar.astro`.
- Grows unbounded if items never disappear. GC rule: drop entries whose `last_seen` is older than 30 days.
- `traction_magnitude` is chosen additive so a repo doubling stars from 500 to 1000 registers. Rank-based fields (which saturate) are deliberately absent.

## `evals/<YYYY-MM-DD>.json`. The rubric artifact

Written by the grader. Mirrored to `evals/latest.json`.

```jsonc
{
  "date":       "2026-07-06",
  "mode":       "normal",                   // normal | pre-merge | demo
  "digest_url": "https://raw.githubusercontent.com/.../reports/2026-07-06-digest.md",
  "overall":    3.9,
  "quality": {
    "overall": 4.0,
    "A1": { "score": 4, "why": "5 of 8 items add a why-it-matters beyond restating the abstract" },
    "A2": { "score": 5, "why": "23 URLs HEAD-checked, 0 broken, all primary" },
    "A3": { "score": 4, "why": "6 items match interpretability/agents/evals; 1 hardware surprise" },
    "A4": { "score": 3, "why": "What changed lists movers but doesn't say why they climbed" },
    "A5": { "score": 4, "why": "1 missed: DeepMind blog post from 2026-07-06 (see missed_stories)" }
  },
  "experience": {
    "overall": 3.8,
    "X1": { "score": 4, "why": "top row is Anthropic Sonnet-5.1 by score+focus" },
    "X2": { "score": 4, "why": "brief opens with 'signals suggest'; scores dominate visually" },
    "X3": { "score": 5, "why": "digest was 2.1h old at eval time" },
    "X4": { "score": 3, "why": "hf_papers 500 in prior run cascaded a partial main list" },
    "X5": { "score": 3, "why": "reindex.py started importing from score.py; boundary crossed" }
  },
  "broken_urls":    [],
  "missed_stories": [
    { "title": "…", "url": "…", "why": "primary source, not aggregator; adjacent to interpretability" }
  ],
  "improvement_suggestion": {
    "target_repo":     "ai-radar",
    "file_path":       "distill/reindex.py",
    "one_line":        "Stop importing from score.py; re-declare score-tier mapping locally",
    "rationale":       "Crossing the boundary makes reindex non-regenerable without distill state, which violates the coupling invariant.",
    "triggered_by":    "X5"
  }
}
```

### Rules

- Every score has a `why` string. Empty `why` is a grader bug.
- `improvement_suggestion.target_repo` is one of the two known repo names. Enum, not free-form.
- `improvement_suggestion.triggered_by` names the dim that produced the suggestion. Grader that suggests something unrelated to the lowest dim is broken.
- `mode: pre-merge` is reserved for runs that fired before the `evals/` scaffolding merged. Historical only; no new runs should emit it.

## Schema versioning policy

We don't. Yet.

- Fields are additive. Removals require a migration PR that updates every reader.
- If a schema needs a version field, add one and note the reason in an ADR.
- Prefer duck typing over version checks: readers should ignore unknown fields and default missing ones.
