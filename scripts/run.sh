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
$PY -m collectors.hf_papers      || echo "  hf_papers collector skipped"
$PY -m collectors.arxiv          || echo "  arxiv collector skipped"
$PY -m collectors.lab_blogs      || echo "  lab_blogs collector skipped"
# Trending collectors: leading indicators of releases that matter (hot tools/models before
# they hit arXiv). Carry gh_stars / hf_likes so the trending heuristic fires without enrich.
$PY -m collectors.github_trending || echo "  github_trending collector skipped"
$PY -m collectors.hf_trending     || echo "  hf_trending collector skipped"

echo "== score =="
$PY -m distill.score

if [ "${RADAR_AGENT:-off}" = "on" ]; then
  echo "== enrich (top ${RADAR_AGENT_TOP_N:-5} items) =="
  $PY -m distill.enrich || echo "  enrich stage failed or skipped (distill continues on scored items)"
fi

echo "== distill =="
$PY -m distill.synthesize

echo "== reindex (reports/README.md + latest.md + per-digest nav) =="
$PY -m distill.reindex || echo "  reindex skipped"

# Optional email delivery: no-op unless RADAR_EMAIL_TO + SMTP_* env are set (see distill/deliver.py).
# Runs after reindex so the emailed digest reflects the freshly-built nav/index.
if [ -n "${RADAR_EMAIL_TO:-}" ]; then
  echo "== deliver (email) =="
  $PY -m distill.deliver || echo "  delivery failed (digest already written)"
fi

echo "Done. Latest report:"
ls -t reports/*-digest.md 2>/dev/null | head -1 || true
