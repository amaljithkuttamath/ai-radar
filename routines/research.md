# Routine: research

Collects new papers/methods likely to gain traction. Writes to `data/raw/research/<date>/`.

## Pull (date-bounded, deterministic)
- **Hugging Face Daily Papers** — curated + upvote-ranked; the primary traction feed.
  Capture `signals.hf_upvotes`. **Always capture the item's date** — don't trust a "trending"
  list position as a recency signal; an undated item goes to the watch-list, not the main list.
- **arXiv recent** — categories from `config/sources.yaml: research.arxiv_categories`,
  filtered to the window via the API `submittedDate` range.

## Score — traction 0–5 (see distill/digest.md), observable signals only
+1 each: frontier/strong-group authorship · concrete result (SOTA / clear benchmark delta) ·
usable artifact (weights/code/dataset/API) · trending in ≥1 concrete Tier-2 signal (HF upvotes,
GH star velocity, HN) · novel / challenges a common assumption (model-judged).
FOCUS is a re-rank boost applied later, not part of the score.

## Notes
- One record per development; collapse duplicate coverage to the primary artifact.
- Capture the link to the PRIMARY artifact, not a news rehash.
- Over-collect here; the distiller enforces the bar.
