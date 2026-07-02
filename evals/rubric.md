# Radar eval rubric

Two axes, five dimensions each, scored 0–5. Every score in a committed eval
file must carry a one-sentence justification citing concrete evidence (a
specific item id, URL, or file line). The point is not a number — it's the
paper trail that lets future runs reason about *why* the number moved.

Scores are produced by the daily eval loop and committed to
`evals/<YYYY-MM-DD>.json` + mirrored to `evals/latest.json`.

## Axis A — Answer quality (the digest itself)

| Dim | Name | What it measures | Scoring anchors |
|-----|------|------------------|-----------------|
| A1 | signal_density | Non-obvious insight per paragraph; no filler. | 5 = every line earns its space; 3 = mixed; 1 = mostly restated abstracts. |
| A2 | source_integrity | Primary sources over aggregators; no broken links. | Any broken URL caps this at 2. 5 = every claim links to a primary source (arXiv abs, lab blog, official repo/release). |
| A3 | focus_alignment | Items align with `config/profile.yaml` topics without becoming a narrow echo chamber. | 5 = strong topic fit + at least one adjacent-field surprise. 1 = drift or echo chamber. |
| A4 | delta_clarity | "What changed" is a real diff vs yesterday, not a restatement. | 5 = explicit new/climbing/cooled with reasons; 1 = same items relisted. |
| A5 | coverage | Inverse of important last-24h stories the digest missed. | 0 missed = 5; 1 = 4; 2 = 3; 3 = 2; 4+ = 1. |

## Axis X — Experience & architecture (how it reaches the reader)

| Dim | Name | What it measures | Scoring anchors |
|-----|------|------------------|-----------------|
| X1 | board_legibility | A cold reader identifies the top story from `radar.astro`'s board in <10 s. | 5 = top row is unambiguously the story of the day; 1 = requires reading the brief to know. |
| X2 | instrument_honesty | Synthesis is labeled machine opinion; observed signals dominate. | 5 = attribution + observed signals visually dominate; 1 = brief presented as fact. |
| X3 | freshness | Hours between digest publish time and eval run. | <6 h = 5, 6–12 = 4, 12–24 = 3, 24–36 = 2, >36 = 1. |
| X4 | failure_surface | One broken feed / one 4xx does not break the digest or the page. | 5 = independent try/catch per fetch, quiet-window fallback works; 1 = a single failure cascades. |
| X5 | coupling | collect / distill / render remain independently regenerable (repo's stated design principle). | 5 = strict boundaries; 1 = imports cross the boundary. |

## Aggregates

- `quality.overall` = mean(A1..A5)
- `experience.overall` = mean(X1..X5)
- `overall` = mean(quality.overall, experience.overall)

## Thresholds that trigger action

- Any dimension ≤ 2 → GitHub issue (subject to 72-hour throttle across both repos).
- `broken_urls.count > 0` → GitHub issue.
- Same dimension ≤ 3 for 3 consecutive days → GitHub issue (persistent regression).
- Every run appends at least one causal improvement to `evals/backlog.md`, tied to the lowest-scoring dimension of the day.
