#!/usr/bin/env bash
# CI-only Git publication. Commit first, then rebase; never hide a failed rebase.
set -euo pipefail
cd "$(dirname "$0")/.."
kind="${1:?Usage: publish.sh collect|distill}"
branch="${RADAR_PUBLISH_BRANCH:-main}"
paths=()
case "$kind" in
  collect) paths=(data/seen.json) ;;
  distill)
    shopt -s nullglob
    paths=(reports/*.md data/state.json data/tracked.json data/publication.json)
    ;;
  *) echo "Unknown publication kind: $kind" >&2; exit 2 ;;
esac
for path in "${paths[@]}"; do
  if [ ! -f "$path" ]; then
    echo "Missing publication artifact: $path" >&2
    exit 1
  fi
done
git config user.name "radar-bot"
git config user.email "radar-bot@users.noreply.github.com"
git add -- "${paths[@]}"
if git diff --cached --quiet; then
  echo "No $kind changes to commit."
  exit 0
fi
git commit -m "radar: $kind artifacts for $(date -u +%Y-%m-%d)"
for attempt in 1 2 3; do
  git pull --rebase origin "$branch"
  if git push origin "HEAD:$branch"; then
    exit 0
  fi
  echo "Push raced with another writer; retry $attempt/3." >&2
done
echo "Publication push failed after three attempts." >&2
exit 1
