# Distillation routine: corpus -> digest

Input: scored items in `data/scored/` within {WINDOW}. Output: a dated report in `reports/`.
This is the prompt `synthesize.py` sends to the model, with the scored items appended.

## Objective
Turn the collected corpus into a high-precision read: what matters, what to do about it.
Precision over recall — surface the few things that count; skip the rest, don't pad.

## Parameters (from config/routines.yaml, overridable by env)
WINDOW · MAX_ITEMS · FOCUS (re-rank boost) · MARKET (off/on) · INCLUDE_THRESHOLD.

## Steps
1. Load scored items in WINDOW. Drop score ≤0.
2. **If the window is quiet, widen it** (48h → 72h → 7d) until there's real signal, and say
   you did. A rigid window that returns nothing is the failure mode this avoids.
3. Dedup against prior runs (seen-list). Items still trending → "Still developing", one line.
4. Apply FOCUS as a re-rank boost (ordering + relevance), then write the report.

## Scoring — traction score, 0–5 (observable signals only)
+1 each:
- frontier / strong-group / major-vendor authorship
- concrete result — research: SOTA or clear benchmark delta; hardware: real perf-per-$ or
  perf-per-watt delta (not a keynote claim) — not incremental
- usable artifact available — research: weights/code/dataset/API; hardware: a real ship date
- trending in ≥1 concrete Tier-2 signal (HF upvotes, GitHub star velocity, HN front page)
- strong traction in Tier-2 signals (e.g. ≥150 HN points, ≥80 GitHub stars) OR
  methodologically novel or challenges a common assumption (model-judged)

FOCUS is a **re-rank boost applied after scoring**, never added to the number — keep "is this
big" (score) separate from "is this relevant to me" (focus).

Routing: **score ≥2 → main list · 1 → watch-list · ≤0 → drop.**

## Output format

**Header** — start with `# AI Radar — {TODAY}` using the TODAY date from the user message.
Never infer the date from the items or your training data.

**Top-line** (2–3 sentences) — the single most important development + the window's theme.
If quiet, say so plainly (and note that you widened the window).

**What changed** (skip entirely if the MOVERS block has first_run=true) — a short "since last
run" delta from the MOVERS block in the user message. Three one-line groups, omit any that are
empty:
- **New today** — items not present last run (the freshest signal).
- **Climbing** — items whose traction rose; cite the direction, e.g. "up".
- **Cooled** — items that lost traction or fell off.
This is a CHANGE-LOG, not a preview of the main list. Each line is **title only** (optionally a
3-5 word tag), never a full New/Matters write-up — the detail lives once, in the main list below.
At most 4-5 items per group; if a "New today" item is also a top main-list item, it's fine to
name it here in one line, but DO NOT repeat its description. Never duplicate prose across sections.
Keep it to the items that actually matter; do not list every mover. This section is what makes
the report a radar rather than a standalone newsletter.

**Main list** (ranked, ≤MAX_ITEMS).

*Cluster headers.* When a TOPIC CLUSTERS block is provided, group items under it using a
`###` theme header that is a SHORT, HUMAN-READABLE THEME PHRASE (2-4 words, Title Case), e.g.
`### Video World Models`, `### Agent Evaluation`. NEVER emit a single bare word, a word with
trailing punctuation (`Model)`), or a category name like `Model` / `Method` as a header —
those are item *types*, not themes. If the provided cluster label looks like junk (one word,
contains punctuation, or is a generic type), rewrite it into a clean theme phrase yourself
from the items it groups. Put a one-line *italic* theme summary directly under each header.
Items not assigned to any cluster keep their natural position. Degrade to a flat list (no
headers) when clusters are absent or don't add clarity.

*Per-item template — follow this EXACTLY, same fields, same order, same punctuation, every time:*

```
**{Title}** · `{type}` · **{score}/5**
- **Source** — {org/authors}, {venue} · [{primary artifact}]({url})
- **New** — {the actual contribution: technique / model size / dataset / number}
- **Matters** — {who is affected + the concrete mechanism}
- **Signal** — {traction figures} · {confidence}
- **Why surfaced** — {grounded provenance line}    ← omit this whole line if provenance is empty
```

Field rules:
- `{type}` is one of: model · method · paper · release · infra/hardware. Lowercase, in backticks.
- Put one blank line between items so they render as separate blocks, never run together.
- **New** — never restate the title. Release: what shipped + the capability delta. Hardware:
  the claimed perf-per-watt / bandwidth / ship-date figure.
- **Matters** — "Practitioners doing X can now do Y" is good. "A significant advance" is not.
- **Signal** — PRINT the figures from the item's structured fields, do not prose them:
  `N HF upvotes · N GitHub stars · N HN points` (omit any that are 0; if all 0, write
  "no tracked traction signal"). Then confidence: "single source" if one signal and no
  independent corroboration, else "corroborated by N signals". Traction and confidence are
  separate: a high score with low confidence is normal and useful.
- **Why surfaced** — grounded ONLY in the item's `provenance` field (e.g.
  "frontier author · 412 gh_stars · matches FOCUS:agents · concrete result claimed"). If
  `provenance` is absent or empty, omit this line entirely. Never invent reasons.
- **Market exposure** — append *only if MARKET=on and score ≥4* (see below).

The candidate set may include hardware and releases items that score below research papers;
include them at their actual score (watch-list is fine for a bare vendor announcement). Do
not drop them just for scoring lower than research.

## Banned phrases — never write these
- "growing interest" / "increasing interest" / "notable interest"
- "confidence is moderate" (use "single source" or "corroborated by N signals")
- "this work" / "this paper" as a subject — name the system or method
- "in the field of" / "in the realm of"
- restating the title as the New line

**Story arcs** (optional subsection; skip entirely when the STORY ARCS block is absent or
empty) — items whose traction has risen across ≥3 consecutive runs. One line each:
"*Title* — seen {streak} runs, traction +{mag_pct_change}% since first seen on {first_seen}."
Do not embellish; ground every claim in the provided arc fields.

**Watch-list** (1 line each) — promising but unverified / not-yet-trending. Park here anything
whose recency you can't confirm, rather than risk surfacing stale items as new.

**Still developing** (1 line each) — active carryovers from prior runs.

**Insights** (2–4 bullets) — patterns ACROSS items the per-item view misses.

**Action items** — concrete: Read / Try / Track, tied to why it's relevant.

## Market exposure block (MARKET=on)
Mechanism mapping — **not** investment advice, not a price forecast:
- **Exposed names** — companies/tickers + the one-line mechanism for each.
- **Direction** — plausibly raises/lowers demand or widens/narrows a moat for X *because* Y.
  Direction only, never magnitude or a target.
- **Counter-mechanism** — state the opposing read where one exists (e.g. cheaper inference
  looks bearish for compute demand, but Jevons paradox says it can expand total usage).
- **Priced vs. speculative** — what the market likely already reflects.
- **Read** — calibrated, non-prescriptive. No buy/sell/hold.

## Honesty constraints
- Link only to artifacts actually present in the corpus — never fabricate.
- "Released" ≠ "announced/teased" — label which.
- Report only signals actually observed; don't infer trending you didn't check.
- Market exposure is mechanism-mapping only; this is not a licensed advisor.
