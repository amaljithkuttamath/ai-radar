# Distillation routine: corpus -> digest

Input: scored items in `data/scored/` within {WINDOW}. Output: a dated report in `reports/`.
This is the prompt `synthesize.py` sends to the model, with the scored items appended.

## Objective
Turn the collected corpus into a high-precision read: what matters, what to do about it.
Precision over recall — surface the few things that count; skip the rest, don't pad.

## Parameters (from config/routines.yaml, overridable by env)
WINDOW · MAX_ITEMS · FOCUS (re-rank boost) · MARKET (off/on) · INCLUDE_THRESHOLD.

## Steps
1. Load scored items in WINDOW. Drop score ≤1.
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
- methodologically novel or challenges a common assumption (model-judged)

FOCUS is a **re-rank boost applied after scoring**, never added to the number — keep "is this
big" (score) separate from "is this relevant to me" (focus).

Routing: **score ≥3 → main list · 2 → watch-list · ≤1 → drop.**

## Output format

**Top-line** (2–3 sentences) — the single most important development + the window's theme.
If quiet, say so plainly (and note that you widened the window).

**Main list** (ranked, ≤MAX_ITEMS). Per item:
- **Title** — [model | method | paper | release | infra/hardware] · score X/5
- Source — org/authors + venue · [link to PRIMARY artifact]
- New — one sentence
- Matters — one sentence
- Signal — authority + traction evidence + **confidence** ("single source, unverified" if so).
  Keep traction and confidence separate: a high score with low confidence is normal and useful.
- Market exposure — *only if MARKET=on and score ≥4* (see below)

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
