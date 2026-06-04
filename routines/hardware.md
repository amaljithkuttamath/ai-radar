# Routine: hardware

Collects chip / compute-infrastructure news. Writes to `data/raw/hardware/<date>/`.
Sources in `config/sources.yaml: hardware`.

## Pull
- Vendor newsroom RSS/Atom (NVIDIA, AMD, Intel, Google TPU, AWS Trainium, MS Maia,
  Broadcom, Cerebras, Groq).
- Earnings releases/calls when in-window.

## Score — traction 0–5, with hardware-specific reads of two criteria
- **Concrete result** = a real **perf-per-$ or perf-per-watt** delta vs. prior gen — not a
  keynote claim.
- **Usable artifact** = an actual **ship date / order availability**, not an announcement
  ("announced" ≠ "released" — a keynote alone does not clear the bar).

## Market note
Hardware items most often carry market consequences, but the **market read is an enrichment
done during distillation** (MARKET=on, score ≥4), not part of collection. It maps exposure and
mechanism only — never trade calls. Analysts (e.g. SemiAnalysis) and supply chain (TSMC, HBM)
are consulted by hand at that step. See `distill/digest.md`.
