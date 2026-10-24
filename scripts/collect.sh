#!/usr/bin/env bash
# Compatibility entry point; all orchestration lives in radar/.
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v uv >/dev/null 2>&1; then
  exec uv run python -m radar collect "$@"
fi
exec python3 -m radar collect "$@"
