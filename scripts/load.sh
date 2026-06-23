#!/usr/bin/env bash
set -euo pipefail

base_url="${BASE_URL:-http://localhost:8080}"
count="${1:-100}"
sleep_s="${SLEEP_S:-0.5}"

usage() {
  cat <<EOF
Usage:
  ./scripts/load.sh [count]

Env:
  BASE_URL   Base URL for demo app (default: http://localhost:8080)
  SLEEP_S    Sleep between requests in seconds (default: 0.5)

Examples:
  ./scripts/load.sh 100
  BASE_URL=http://localhost:8080 SLEEP_S=0.1 ./scripts/load.sh 500
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

endpoints=(users orders slow error)

for ((i=1; i<=count; i++)); do
  endpoint="${endpoints[RANDOM % ${#endpoints[@]}]}"
  curl -sS "${base_url}/api/${endpoint}" > /dev/null || true
  sleep "${sleep_s}"
done

echo "Done: ${count} requests to ${base_url}"
