#!/usr/bin/env bash
# qa/atom_e2e.sh — atom 명령 e2e 체인 QA (fixture 경로)
set -euo pipefail

EVIDENCE_DIR=".sisyphus/evidence/qa/atom_e2e"
FIXTURE_PORT="${CLIANY_QA_FIXTURE_PORT:-18080}"
FIXTURE_PID=""

# 1. Chrome CDP 확인
check_chrome() {
    curl -sf "http://localhost:9222/json/version" > /dev/null 2>&1 && return 0 || return 1
}

# 2. fixture 서버 시작
start_fixture() {
    FIXTURE_DIR="$(dirname "$0")/fixtures/site"
    python3 -m http.server "$FIXTURE_PORT" --directory "$FIXTURE_DIR" > /tmp/fixture_server.log 2>&1 &
    FIXTURE_PID=$!
    sleep 1
    # 서버 확인
    curl -sf "http://127.0.0.1:${FIXTURE_PORT}/" > /dev/null || { echo "fixture server failed"; exit 1; }
}

# 3. cleanup
cleanup() {
    if [[ -n "$FIXTURE_PID" ]]; then
        kill "$FIXTURE_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# 4. Chrome 없으면 skip
if ! check_chrome; then
    echo "SKIP: Chrome not available (start with --remote-debugging-port=9222)"
    exit 0
fi

# 5. evidence 디렉토리
mkdir -p "$EVIDENCE_DIR"

# 6. fixture 서버 시작
start_fixture

# 7. atom 명령 체인
FIXTURE_URL="http://127.0.0.1:${FIXTURE_PORT}/"

run_step() {
    local step_name="$1"
    shift
    local output
    output=$(cliany-site --json "$@" 2>&1)
    echo "$output" > "$EVIDENCE_DIR/${step_name}.json"
    local ok_val
    ok_val=$(echo "$output" | jq -r '.ok // .success // false' 2>/dev/null || echo "false")
    if [[ "$ok_val" != "true" ]]; then
        echo "FAIL: $step_name"
        echo "$output"
        exit 1
    fi
    echo "OK: $step_name"
}

# atom 명령들 체인 실행
run_step "01_state" browser state
run_step "02_navigate" browser navigate "$FIXTURE_URL"
run_step "03_wait" browser wait --ms 500
run_step "04_find" browser find "input, button, a"
run_step "05_type" browser type "#search-input" "test query"
run_step "06_wait" browser wait --ms 500
run_step "07_extract" browser extract "제목, 링크" --format markdown
run_step "08_screenshot" browser screenshot

# eval 기본 거부 확인 (exit 1 이 정상)
echo "Verifying eval is blocked by default..."
eval_out=$(cliany-site --json browser eval "document.title" 2>&1 || true)
eval_ok=$(echo "$eval_out" | jq -r '.ok // false' 2>/dev/null || echo "false")
if [[ "$eval_ok" == "true" ]]; then
    echo "FAIL: eval should be blocked by default"
    exit 1
fi
echo "OK: eval correctly blocked" | tee "$EVIDENCE_DIR/eval_blocked.json"

run_step "09_state_after" browser state

echo "PASS: atom_e2e 체인 완료 (evidence: $EVIDENCE_DIR)"
exit 0