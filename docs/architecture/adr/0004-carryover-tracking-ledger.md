# ADR-0004. Carryover tracking ledger with traction re-observation

**Status.** Accepted, 2026-07.

## Context

The digest advertises four change-over-time features: "Climbing", "Cooled", "Still developing", and "Story arcs". None of them had ever produced output.

The cause is structural, not a bug in `delta.py`. Collection dedups an item forever against `data/seen.json`, and `data/raw/` is gitignored and rebuilt from scratch in every CI run. So an item is collected once, scored once, and never appears again. `compute_delta` diffs today's scored set against `data/state.json` — the *previous* run's scored set — and the two are disjoint by construction. The intersection is always empty, so:

- `streak` was 1 on every item in all 20 committed state snapshots;
- `story_arcs()` requires `streak >= 3` and had therefore never returned a row;
- "Still developing" was empty in all 37 digests carrying the section;
- and on a quiet collection day the candidate pool was just the handful of items first seen that day, which is why roughly 30% of digests shipped with zero main-list items.

A second, related problem: traction figures were whatever the collector captured at first sight. The eval loop flagged this twice (`X2_instrument_honesty`, 2026-07-07 and 2026-07-08) after star counts in the digest failed to match the linked repos at reading time.

Options considered:

1. **Stop dedupping** — let collectors re-emit items inside the window. Rejected: `seen.json` is what keeps a busy feed from re-publishing the same paper daily, and it would put the growth signal in the collector, which is forbidden from doing per-item lookups.
2. **Commit `data/raw/`** — keep the corpus so items stay in-window. Rejected: the corpus is regenerable by design (ADR-0001), and committing 250+ items a day makes the repo grow without bound.
3. **Carry state forward without re-checking** — increment `streak` for entries already in `state.json`. Rejected: it manufactures a streak out of nothing. An item's streak would measure how long ago we saw it, not whether it is still moving, and "Climbing" would be a claim we never verified.
4. **Re-observe a bounded set of tracked items each run.**

## Decision

Option 4, in a new module `distill/track.py` owning a new state file `data/tracked.json`.

- **Promote.** After a digest is successfully written, items scoring `>= TRACK_MIN_SCORE` (3) enter the ledger. Only items with a re-fetchable counter are eligible — a vendor blog post has nothing to watch, so tracking it would be theatre.
- **Re-observe.** Each run, every live entry is re-read from its source of record: GitHub stars via the repos API, HF likes/downloads via the models/datasets API, HF paper upvotes via the papers API. The observation is appended to a rolling magnitude history. A failed fetch records a miss and leaves the history untouched — an unreadable source is not evidence of cooling.
- **Re-enter.** Live entries are re-scored against their *current* signals and written back into `data/scored/`, so the rest of the pipeline consumes them with no special-casing. Today's set and the previous snapshot now overlap, which is what makes `compute_delta` meaningful.
- **Prune.** TTL since first sighting (14 days), consecutive-miss cap (3), flat-traction cap (5 runs without a gain), and a hard size cap (60, keeping the highest peaks).
- **Bound.** Carryovers get a small reserved slice of the candidate set (`CARRYOVER_SLOTS`, 4) so the digest stays mostly about what is new — widened to `QUIET_FLOOR` when today's collection was thin.

Promotion happens only after a digest is actually written. A run that failed to publish must not leave the ledger claiming it saw those items.

## Consequences

**Positive.**
- The four change-over-time features work, for the first time.
- A quiet collection day produces a digest about what the radar is already watching, instead of an empty one.
- Traction figures reaching the model are read from the source during the run, which closes the `X2_instrument_honesty` findings.
- Growth is measured, not asserted: a "climbing" claim is backed by two observations of the same counter.

**Negative.**
- Up to `TRACK_REFRESH_BUDGET` (60) HTTP calls per distill run, where there were none. Unauthenticated HF endpoints and the authenticated GitHub API both absorb this comfortably, and the budget is a hard ceiling. The refresh order is highest-peak-first, so exhausting the budget costs the least interesting rows.
- A fourth committed state file. It is capped at 60 entries, so it stays small.
- `distill.yml`'s write scope grows by one path. It remains disjoint from `collect-corpus.yml`'s, so ADR-0001 holds.
- The collectors' "never call a model, never do per-item lookups" invariant is untouched: re-observation happens in `distill/`, after scoring, and calls no model.

## Note on `data/state.json`

`state.json` keeps its existing role — a snapshot of the run's scored set, used for the new/climbing/cooled diff. It is replaced each run and is not the radar's memory. `tracked.json` is. `delta.story_arcs()` now reads the ledger, because the streak counter in `state.json` cannot mean anything for the reason described above.
