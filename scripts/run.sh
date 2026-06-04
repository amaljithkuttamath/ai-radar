#!/usr/bin/env bash
# Orchestrate one cycle: collect -> score -> distill.
# Env knobs (all optional): WINDOW, MAX_ITEMS, FOCUS, MARKET, INCLUDE_THRESHOLD,
#                           RADAR_MODEL_BACKEND (dryrun|anthropic|ollama)
set -euo pipefail
cd "$(dirname "$0")/.."

# Prefer uv (resolves deps from pyproject.toml into an ephemeral env); fall back to plain python.
if command -v uv >/dev/null 2>&1; then
  PY="uv run python"
else
  PY="python"
fi

export WINDOW="${WINDOW:-48h}"
echo "== collect (window=$WINDOW) =="
# Order matters: hf_papers must run BEFORE arxiv. Both mint version-less arxiv: ids for the
# same paper, and write_items dedups by id (first writer wins). HF carries signals.hf_upvotes
# that arxiv lacks, so HF has to write first or that trending signal is lost on overlap.
$PY -m collectors.hf_papers  || echo "  hf_papers collector skipped"
$PY -m collectors.arxiv      || echo "  arxiv collector skipped"
$PY -m collectors.lab_blogs  || echo "  lab_blogs collector skipped"

echo "== score =="
$PY -m distill.score

if [ "${RADAR_AGENT:-off}" = "on" ]; then
  echo "== enrich (top ${RADAR_AGENT_TOP_N:-5} items) =="
  $PY -m distill.enrich || echo "  enrich stage failed or skipped (distill continues on scored items)"
fi

echo "== distill =="
$PY -m distill.synthesize

echo "Done. Latest report:"
ls -t reports/*.md 2>/dev/null | head -1 || true
