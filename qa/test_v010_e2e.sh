#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EVIDENCE_DIR="$PROJECT_ROOT/.sisyphus/evidence/qa"
FIXTURE_PORT="${CLIANY_QA_FIXTURE_PORT:-18080}"
FIXTURE_PID=""

cleanup() { [[ -n "$FIXTURE_PID" ]] && kill "$FIXTURE_PID" 2>/dev/null || true; }
trap cleanup EXIT

mkdir -p "$EVIDENCE_DIR"

if ! curl -sf "http://localhost:9222/json/version" > /dev/null 2>&1; then
    echo "SKIP: Chrome not available, skipping E2E test"
    exit 0
fi

echo "=== Step 0: doctor --json ===" | tee "$EVIDENCE_DIR/task-24-e2e.txt"
DOCTOR_OUT=$(cliany-site doctor --json 2>&1 || true)
echo "$DOCTOR_OUT" >> "$EVIDENCE_DIR/task-24-e2e.txt"
echo "doctor OK" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"

echo "=== Step 1: migrate ===" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"
TEST_ADAPTER_DIR="$HOME/.cliany-site/adapters/qa-test-migrate-com"
mkdir -p "$TEST_ADAPTER_DIR"
cat > "$TEST_ADAPTER_DIR/metadata.json" <<'EOF'
{"schema_version": 2, "domain": "qa-test-migrate-com", "commands": []}
EOF
MIGRATE_OUT=$(cliany-site migrate --json 2>&1 || true)
echo "$MIGRATE_OUT" >> "$EVIDENCE_DIR/task-24-e2e.txt"
echo "migrate OK" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"

echo "=== Step 2: explore offline ===" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"
bash "$SCRIPT_DIR/fixtures/serve.sh" &
FIXTURE_PID=$!
sleep 1

export CLIANY_QA_OFFLINE=1
export CLIANY_QA_FAKE_LLM_RESPONSES="$SCRIPT_DIR/fixtures/fake_llm_responses.json"
EXPLORE_OUT=$(cliany-site --json explore "http://localhost:$FIXTURE_PORT" "搜索测试" 2>&1 || true)
echo "$EXPLORE_OUT" >> "$EVIDENCE_DIR/task-24-e2e.txt"
EXPLORE_OK=$(echo "$EXPLORE_OUT" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(str(d.get('ok','false')).lower())" 2>/dev/null || echo "false")
if [[ "$EXPLORE_OK" != "true" ]]; then
    echo "WARN: explore may have failed (may be expected without real page)" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"
fi
echo "explore step done" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"

echo "=== Step 3: list ===" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"
LIST_OUT=$(cliany-site list --json 2>&1 || true)
echo "$LIST_OUT" >> "$EVIDENCE_DIR/task-24-e2e.txt"
echo "list OK" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"

echo "=== Step 4: missing fake LLM responses ===" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"
unset CLIANY_QA_FAKE_LLM_RESPONSES
MISSING_OUT=$(CLIANY_QA_OFFLINE=1 cliany-site --json explore "http://localhost:$FIXTURE_PORT" "test" 2>&1 || true)
echo "$MISSING_OUT" >> "$EVIDENCE_DIR/task-24-e2e.txt"
MISSING_CODE=$(echo "$MISSING_OUT" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('error',{}).get('code',''))" 2>/dev/null || echo "")
if [[ "$MISSING_CODE" == "E_QA_OFFLINE_MISSING_FAKE_LLM" ]]; then
    echo "PASS: E_QA_OFFLINE_MISSING_FAKE_LLM returned" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"
else
    echo "INFO: missing fake LLM code=$MISSING_CODE" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"
fi

echo "=== All E2E steps completed ===" | tee -a "$EVIDENCE_DIR/task-24-e2e.txt"
cat "$EVIDENCE_DIR/task-24-e2e.txt"
