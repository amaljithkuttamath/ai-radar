#!/usr/bin/env bash
# Distill only: score → (optional enrich) → synthesize → reindex → (optional deliver).
# Runs on its own cadence (daily, after collection). Reads whatever the collectors and
# any deep-dive runs have written to data/raw/ and data/dives/. Never re-fetches.
#
# Env knobs: WINDOW, MAX_ITEMS, FOCUS, MARKET, INCLUDE_THRESHOLD,
#            RADAR_MODEL_BACKEND (dryrun|github|anthropic|ollama), RADAR_AGENT (on|off),
#            RADAR_EMAIL_TO (+ SMTP_* to actually email)
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  PY="uv run python"
else
  PY="python"
fi

export WINDOW="${WINDOW:-48h}"

echo "== score =="
$PY -m distill.score

if [ "${RADAR_AGENT:-off}" = "on" ]; then
  echo "== enrich (top ${RADAR_AGENT_TOP_N:-5} items) =="
  $PY -m distill.enrich || echo "  enrich stage failed or skipped (distill continues on scored items)"
fi

echo "== distill =="
$PY -m distill.synthesize

echo "== reindex =="
$PY -m distill.reindex || echo "  reindex skipped"

# Optional email delivery: no-op unless RADAR_EMAIL_TO + SMTP_* env are set.
if [ -n "${RADAR_EMAIL_TO:-}" ]; then
  echo "== deliver (email) =="
  $PY -m distill.deliver || echo "  delivery failed (digest already written)"
fi

echo "Done. Latest report:"
ls -t reports/*-digest.md 2>/dev/null | head -1 || true
