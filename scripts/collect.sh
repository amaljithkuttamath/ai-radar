#!/usr/bin/env bash
# Corpus collection only: arxiv + HF papers + lab blogs + trending.
# Runs on its own cadence (daily) so it doesn't share failure modes with distill.
# Writes: data/raw/**, data/seen_corpus.json (via collectors.common). Does NOT score or distill.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  PY="uv run python"
else
  PY="python"
fi

export WINDOW="${WINDOW:-48h}"
echo "== collect corpus (window=$WINDOW) =="

# Order matters: hf_papers must run BEFORE arxiv. Both mint version-less arxiv: ids for the
# same paper, and write_items dedups by id (first writer wins). HF carries signals.hf_upvotes
# that arxiv lacks, so HF has to write first or that trending signal is lost on overlap.
$PY -m collectors.hf_papers       || echo "  hf_papers collector skipped"
$PY -m collectors.arxiv           || echo "  arxiv collector skipped"
$PY -m collectors.lab_blogs       || echo "  lab_blogs collector skipped"
# Trending collectors: leading indicators of releases that matter (hot tools/models before
# they hit arXiv). Carry gh_stars / hf_likes so the trending heuristic fires without enrich.
$PY -m collectors.github_trending || echo "  github_trending collector skipped"
$PY -m collectors.hf_trending     || echo "  hf_trending collector skipped"

echo "Done. Raw items written to data/raw/."
