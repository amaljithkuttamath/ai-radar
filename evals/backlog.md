# Improvement backlog

Append-only. Each item is PR-sized and tied to an eval dimension. When a
commit lands that closes an item, move it to `## Done` with a closing date.

Item format:
`- [ ] YYYY-MM-DD · <title> · <file path> — <rationale> — triggered by <dim + score>`

## Open — pipeline (ai-radar)

_(none yet — first daily eval run will populate this.)_

## Open — presentation (amaljithkuttamath.github.io)

- [ ] 2026-07-08 · Avoid authoritative traction numbers in UI · `src/pages/radar.astro` — X2_instrument_honesty: GitHub star counts can be materially wrong vs linked repos at viewing time; UI should label as approximate/observed-at-time or omit hard numbers. — triggered by X2_instrument_honesty 2

- [ ] 2026-07-02 · Surface eval scorecard in `/radar` status bar · `src/pages/radar.astro` — Fetch `evals/latest.json` from ai-radar's raw endpoint and render a `quality` cell alongside `universe`/`active`/`escalating`. This lets a reader assess trust in the board without leaving the page. — triggered by X2 instrument_honesty (bootstrap item)

## Done

_(empty)_

- [ ] 2026-07-07 · Fix/verify traction metrics (stars/upvotes) before publishing · distill/digest.md · Digest included specific GitHub star counts for ponytail and InverseBench that did not match the linked repo pages at evaluation time, reducing trust in instrumentation. Add a lightweight validation step (or remove hard numbers) so traction signals are either correct or clearly labeled as approximate/observed-at-time. · triggered by X2_instrument_honesty 2

## Open. Pipeline (ai-radar)

- [ ] 2026-07-11 · Ground numeric traction claims via API snapshots · reports/latest.md · Add a small machine-readable snapshot (e.g., stars/downloads queried at build time) so the digest can cite exact counts and evaluation can verify them deterministically. This directly reduces "numeric drift" and improves trust in instrumentation. · triggered by A1_signal_density=3 / A2_source_integrity=4
- [ ] 2026-07-11 · Add a lightweight "missed in last 24h" sweep · distill/* (template) · When the window is quiet, proactively add 1–2 extra high-signal items from primary sources to avoid low-coverage days. Keep it optional (omit if none) but make the search step explicit. · triggered by A5_coverage=3
