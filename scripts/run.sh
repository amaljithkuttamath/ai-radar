#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v uv >/dev/null 2>&1; then
  exec uv run python -m radar run "$@"
fi
exec python3 -m radar run "$@"
