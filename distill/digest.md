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
3. Items carried over from prior runs arrive pre-marked (`carryover: true`) with re-observed
   traction → "Still developing", one line. Do not re-introduce them as new.
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
This is a CHANGE-LOG, not a preview of the main list. Each line is **the title as a clickable
markdown link to the item's primary URL** (from the MOVERS block's `url` field), optionally
followed by a 3-5 word tag — e.g. `- [Title of paper](https://arxiv.org/abs/...) — new benchmark`.
Never a full New/Matters write-up: the detail lives once, in the main list below. Links are
non-negotiable here just as they are in the main list; a bare title with no URL is a bug.
At most 4-5 items per group; if a "New today" item is also a top main-list item, it's fine to
name it here in one line, but DO NOT repeat its description. Never duplicate prose across sections.
Keep it to the items that actually matter; do not list every mover. This section is what makes
the report a radar rather than a standalone newsletter.

**Main list** (ranked, ≤MAX_ITEMS).

Write this like a sharp human curator briefing a smart friend — a normal, readable summary,
NOT a filled-in form. You decide the presentation: prose, a short paragraph per item, or a
tight list, whatever reads best for the actual items in front of you. The goal is something a
busy engineer can skim in under a minute and immediately know what to click. Vary your
sentences. Do not stamp every item into the same rigid shape.

Two hard rules (everything else is your call):

1. **LINKS ARE MANDATORY AND MUST BE VISIBLE.** Every item carries a primary `url` and may
   carry a `links` object with `github` and/or `project` URLs. Surface ALL of them as distinct
   clickable markdown links — make the title itself a link to the primary artifact, and add the
   repo / project links inline (e.g. `[paper](url) · [code](github) · [project](project)`).
   Never bury a link or drop one you were given. A reader should never have to guess the URL.

2. **Ground every factual claim in the item's fields.** Say what it actually is and why it's
   worth a reader's time, in plain language. Name the system/method, not "this paper". When an
   item has real traction figures (HF upvotes, GitHub stars, HN points), mention them naturally
   (e.g. "412 stars" or "trending on HF"); when it has none, just don't mention traction —
   don't write boilerplate like "no tracked traction signal". Skip the per-item "why surfaced"
   provenance line entirely; it reads as machine exhaust. Let relevance show through the writing.

Cover, in whatever form fits: what it is, what's genuinely new about it, and who should care.
Keep the score visible somewhere lightweight (e.g. a trailing `· 3/5`) so ranking is legible,
but don't make it the headline.

*Grouping.* If a TOPIC CLUSTERS block is provided AND the themes are genuinely clarifying, you
may group items under short `###` theme headers (2-4 word Title Case phrases like
`### Video World Models`) with an optional one-line lead-in. Headers must be real themes, never
a bare item type (`Model`, `Method`) or a fragment with stray punctuation. If the clusters
don't add clarity, just use a flat ranked list — a clean flat list beats forced grouping.

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

**Still developing** (1 line each) — items the radar is already tracking. These arrive in the
candidate JSON with `carryover: true`, plus `runs_tracked`, `first_seen` and `traction_delta`.
Their traction numbers were **re-read from the source moments ago**, so quote them as current.
One line each: what it is in a half-sentence, then where its traction has gone since
`first_seen` — e.g. `- [Title](url) — 3rd run, 186 → 402 stars.` Never call a carryover new,
never re-tell its full write-up (it had one on the day it landed). A carryover whose
`traction_delta` is strongly positive belongs in the main list instead; say plainly that it is
a continuing story rather than a new arrival.

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
- Every traction figure in the candidate JSON was read from its source during this run. Quote
  those numbers verbatim — do not round them into a vibe ("thousands of stars"), and never
  supply a figure the item didn't give you.
- Market exposure is mechanism-mapping only; this is not a licensed advisor.
