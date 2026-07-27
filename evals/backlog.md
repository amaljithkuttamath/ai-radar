# Improvement backlog

Append-only. Each item is PR-sized and tied to an eval dimension. When a
commit lands that closes an item, move it to `## Done` with a closing date.

Item format:
`- [ ] YYYY-MM-DD · <title> · <file path> — <rationale> — triggered by <dim + score>`

## Open — pipeline (ai-radar)

- [ ] 2026-07-27 · Spot-check a re-observed count against the rendered page · `distill/track.py` — Re-observation reads the GitHub/HF APIs, which is the source of record, but nothing confirms the number the digest prints matches what a reader sees on the linked page. One spot-check per run would close the loop the X2 findings opened. — triggered by X2_instrument_honesty 2 (follow-on to the three items closed 2026-07-27)

## Open — presentation (amaljithkuttamath.github.io)

- [ ] 2026-07-08 · Avoid authoritative traction numbers in UI · `src/pages/radar.astro` — X2_instrument_honesty: GitHub star counts can be materially wrong vs linked repos at viewing time; UI should label as approximate/observed-at-time or omit hard numbers. — triggered by X2_instrument_honesty 2

- [ ] 2026-07-02 · Surface eval scorecard in `/radar` status bar · `src/pages/radar.astro` — Fetch `evals/latest.json` from ai-radar's raw endpoint and render a `quality` cell alongside `universe`/`active`/`escalating`. This lets a reader assess trust in the board without leaving the page. — triggered by X2 instrument_honesty (bootstrap item)

## Done

- [x] 2026-07-07 · Fix/verify traction metrics (stars/upvotes) before publishing · distill/digest.md · Digest included specific GitHub star counts for ponytail and InverseBench that did not match the linked repo pages at evaluation time, reducing trust in instrumentation. Add a lightweight validation step (or remove hard numbers) so traction signals are either correct or clearly labeled as approximate/observed-at-time. · triggered by X2_instrument_honesty 2
  - Closed 2026-07-27. `distill/track.py` re-reads each tracked item's counters from the GitHub/HF APIs at the start of every distill run, so figures reaching the model were observed during that run. `distill/digest.md` now requires quoting them verbatim rather than rounding them into a vibe.

- [x] 2026-07-11 · Ground numeric traction claims via API snapshots · reports/latest.md · Add a small machine-readable snapshot (e.g., stars/downloads queried at build time) so the digest can cite exact counts and evaluation can verify them deterministically. This directly reduces "numeric drift" and improves trust in instrumentation. · triggered by A1_signal_density=3 / A2_source_integrity=4
  - Closed 2026-07-27. The snapshot is `data/tracked.json`: per-item observed signals plus a magnitude history, committed each run, so a grader can verify a cited count against the same file the digest was built from.

- [x] 2026-07-11 · Add a lightweight "missed in last 24h" sweep · distill/* (template) · When the window is quiet, proactively add 1–2 extra high-signal items from primary sources to avoid low-coverage days. Keep it optional (omit if none) but make the search step explicit. · triggered by A5_coverage=3
  - Closed 2026-07-27, from the other direction: instead of reaching for extra primary sources, the radar falls back on items it is already tracking, with freshly observed traction. `CARRYOVER_SLOTS` widens to `QUIET_FLOOR` when the fresh candidate set is thin. Zero-item main lists (~30% of digests to date) should stop.

## Notes

The three items closed on 2026-07-27 shared one root cause rather than needing three fixes: an
item was collected once and never seen again, so nothing was ever re-checked and a quiet day had
nothing to fall back on. See
[ADR-0004](../docs/architecture/adr/0004-carryover-tracking-ledger.md).
