#!/usr/bin/env bash
set -euo pipefail

ENGINE="${CONTAINER_ENGINE:-}"
if [[ -z "$ENGINE" ]]; then
  if command -v finch >/dev/null 2>&1; then
    ENGINE="finch"
  elif command -v docker >/dev/null 2>&1; then
    ENGINE="docker"
  else
    echo "No container engine found. Install Finch or Docker, or set CONTAINER_ENGINE." >&2
    exit 1
  fi
fi

IMAGE="${IMAGE:-kaaval-assurance:local}"
PORT="${PORT:-8080}"

echo "engine=$ENGINE"
echo "image=$IMAGE"
echo "port=$PORT"

"$ENGINE" build -t "$IMAGE" .

cid="$("$ENGINE" run -d \
  -p "${PORT}:8000" \
  -e KAAVAL_LIVE_RUNS_ENABLED=0 \
  "$IMAGE")"

cleanup() {
  "$ENGINE" rm -f "$cid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in {1..40}; do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "health:"
curl -fsS "http://127.0.0.1:${PORT}/api/health"
echo

echo "dashboard label:"
curl -fsS "http://127.0.0.1:${PORT}/api/dashboard" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('label'), 'bundle=', d.get('bundle_id'))"

echo "static app:"
curl -fsS "http://127.0.0.1:${PORT}/" \
  | grep -Eo "<title>[^<]+</title>|/assets/[^\"']+" \
  | head -5

echo "container smoke passed"
