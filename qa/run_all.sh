#!/bin/bash
# 串行执行所有 QA 脚本并汇总结果
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOTAL_PASS=0; TOTAL_FAIL=0

run_script() {
  local script="$1"
  local name="$(basename "$script")"
  echo ""
  echo "========================================"
  echo "运行: $name"
  echo "========================================"
  bash "$script"
  local exit_code=$?
  if [ $exit_code -eq 0 ]; then
    echo "[SUITE PASS] $name"
    TOTAL_PASS=$((TOTAL_PASS+1))
  else
    echo "[SUITE FAIL] $name (exit $exit_code)"
    TOTAL_FAIL=$((TOTAL_FAIL+1))
  fi
}

echo "========================================"
echo "运行: pytest 单元测试"
echo "========================================"
uv run pytest -q --tb=short 2>&1
_pytest_exit=$?
if [ $_pytest_exit -eq 0 ] || [ $_pytest_exit -eq 5 ]; then
  echo "[SUITE PASS] pytest"
  TOTAL_PASS=$((TOTAL_PASS+1))
else
  echo "[SUITE FAIL] pytest"
  TOTAL_FAIL=$((TOTAL_FAIL+1))
fi

FIXTURE_PID=""
if [ -f "$SCRIPT_DIR/fixtures/serve.sh" ]; then
  bash "$SCRIPT_DIR/fixtures/serve.sh" &
  FIXTURE_PID=$!
  sleep 1
fi

run_script "$SCRIPT_DIR/doctor_check.sh"
run_script "$SCRIPT_DIR/test_errors.sh"
run_script "$SCRIPT_DIR/test_commands.sh"
run_script "$SCRIPT_DIR/test_explore.sh"
run_script "$SCRIPT_DIR/test_extract.sh"
run_script "$SCRIPT_DIR/test_selector.sh"
run_script "$SCRIPT_DIR/test_extract_writer.sh"
run_script "$SCRIPT_DIR/test_interactive_smoke.sh"
run_script "$SCRIPT_DIR/test_replay_smoke.sh"
run_script "$SCRIPT_DIR/test_extend_smoke.sh"

echo ""
echo "========================================"
echo "=== 总计汇总 ==="
echo "PASS: $TOTAL_PASS, FAIL: $TOTAL_FAIL"
echo "========================================"
[ -n "$FIXTURE_PID" ] && kill "$FIXTURE_PID" 2>/dev/null
[ $TOTAL_FAIL -eq 0 ] && exit 0 || exit 1
