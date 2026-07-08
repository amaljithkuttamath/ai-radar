# Improvement backlog

Append-only. Each item is PR-sized and tied to an eval dimension. When a
commit lands that closes an item, move it to `## Done` with a closing date.

Item format:
`- [ ] YYYY-MM-DD · <title> · <file path> — <rationale> — triggered by <dim + score>`

## Open — pipeline (ai-radar)

_(none yet — first daily eval run will populate this.)_

## Open — presentation (amaljithkuttamath.github.io)

- [ ] 2026-07-02 · Surface eval scorecard in `/radar` status bar · `src/pages/radar.astro` — Fetch `evals/latest.json` from ai-radar's raw endpoint and render a `quality` cell alongside `universe`/`active`/`escalating`. This lets a reader assess trust in the board without leaving the page. — triggered by X2 instrument_honesty (bootstrap item)

## Done

_(empty)_

- [ ] 2026-07-07 · Fix/verify traction metrics (stars/upvotes) before publishing · distill/digest.md · Digest included specific GitHub star counts for ponytail and InverseBench that did not match the linked repo pages at evaluation time, reducing trust in instrumentation. Add a lightweight validation step (or remove hard numbers) so traction signals are either correct or clearly labeled as approximate/observed-at-time. · triggered by X2_instrument_honesty 2
