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
PLATFORM="${PLATFORM:-linux/amd64}"
tmp_dir="$(mktemp -d)"

echo "engine=$ENGINE"
echo "image=$IMAGE"
echo "port=$PORT"
echo "platform=$PLATFORM"

"$ENGINE" build --platform "$PLATFORM" -t "$IMAGE" .

cid="$("$ENGINE" run -d \
  -p "${PORT}:8000" \
  -e KAAVAL_LIVE_RUNS_ENABLED=1 \
  -e KAAVAL_ALLOW_BYOK=1 \
  -e KAAVAL_ALLOW_PAID_REMOTE=0 \
  -e KAAVAL_ALLOW_ARTIFACT_EXPORT=0 \
  -e KAAVAL_ALLOW_DIAGNOSTIC_RAW=0 \
  "$IMAGE")"

cleanup() {
  "$ENGINE" rm -f "$cid" >/dev/null 2>&1 || true
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

for _ in {1..40}; do
  if curl --max-time 1 -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  if ! "$ENGINE" inspect "$cid" >/dev/null 2>&1; then
    echo "container disappeared before health check" >&2
    exit 1
  fi
  sleep 0.5
done

echo "health:"
if ! curl --max-time 3 -fsS "http://127.0.0.1:${PORT}/api/health" > "$tmp_dir/health.json"; then
  "$ENGINE" logs "$cid" >&2 || true
  exit 1
fi
cat "$tmp_dir/health.json"
echo
python3 -c "import json; d=json.load(open('$tmp_dir/health.json')); assert d['live_runs_enabled']; assert d['byok_allowed']; assert d['deployment_mode']=='local'; assert not d['paid_remote_allowed']; assert not d['artifact_export_allowed']; assert not d['diagnostic_raw_allowed']"

echo "runtime capabilities:"
curl -fsS "http://127.0.0.1:${PORT}/api/capabilities" > "$tmp_dir/capabilities.json"
python3 -c "import json; d=json.load(open('$tmp_dir/capabilities.json')); assert d['byok_allowed']; assert {'fireworks','ollama','vllm'} <= set(d['providers']); print(','.join(d['providers']))"

echo "dashboard label:"
curl -fsS "http://127.0.0.1:${PORT}/api/dashboard" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('comparison'); assert d['comparison']['comparison']['remote_calls_avoided']==14; print(d.get('label'), 'bundle=', d.get('bundle_id'), 'remote_calls_avoided=14')"

echo "static app:"
curl -fsS "http://127.0.0.1:${PORT}/" \
  | grep -Eo "<title>[^<]+</title>|/assets/[^\"']+" \
  | head -5

echo "single decision:"
curl -fsS -H 'Content-Type: application/json' \
  -d '{"task_input":"Core router dropped all BGP sessions; customer impact confirmed.","contract_id":"telecom.severity_classification","local_provider":"mock","remote_provider":"mock"}' \
  "http://127.0.0.1:${PORT}/api/runs" > "$tmp_dir/run.json"
python3 -c "import json; d=json.load(open('$tmp_dir/run.json')); assert d['result']['status']=='accepted'; assert d['result']['answer']; print(d['result']['status'])"

echo "fail-closed double rejection:"
curl -fsS -H 'Content-Type: application/json' \
  -d '{"task_input":"Refund request for order 88231.","contract_id":"support.refund_decision","local_provider":"mock","remote_provider":"mock","failure_mode":"out_of_range","remote_failure_mode":"out_of_range"}' \
  "http://127.0.0.1:${PORT}/api/runs" > "$tmp_dir/rejected.json"
python3 -c "import json; d=json.load(open('$tmp_dir/rejected.json')); assert d['result']['status']=='no_safe_answer'; assert d['result']['answer'] is None; assert all(not r['raw_text'] and r['raw_text_withheld'] for r in d['trajectory']); print(d['result']['status'])"

echo "agent workflow:"
curl -fsS -H 'Content-Type: application/json' \
  -d '{"task_input":"Core router CR-04 dropped all BGP sessions; region south lost upstream connectivity and customer impact is confirmed.","local_provider":"mock","remote_provider":"mock"}' \
  "http://127.0.0.1:${PORT}/api/agent-runs" > "$tmp_dir/agent.json"
python3 -c "import json; d=json.load(open('$tmp_dir/agent.json')); assert d['status']=='completed'; assert len(d['steps'])==4; print(d['status'], len(d['steps']))"

echo "paid remote gate:"
status="$(curl -sS -o "$tmp_dir/paid.json" -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -d '{"task_input":"test","contract_id":"support.refund_decision","local_provider":"mock","remote_provider":"fireworks","confirm_spend":true}' \
  "http://127.0.0.1:${PORT}/api/runs")"
test "$status" = "403"

echo "runtime user:"
test "$("$ENGINE" run --rm "$IMAGE" id -u)" = "10001"
echo "10001 (non-root)"

echo "container smoke passed"
