#!/usr/bin/env bash
# Obscura Compat Tests — Layer 2 (capability gate validation)
# 目标：验证 explore/navigate/screenshot/login/session gate 在 Obscura 下的行为
# CI：mandatory（利用现有单元测试，无真实浏览器依赖）
# 用法：bash qa/test_obscura_compat.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PASS=0
FAIL=0

_step() {
  local status="$1" step="$2" detail="${3:-}"
  printf '{"status":"%s","step":"%s","detail":"%s"}\n' "$status" "$step" "$detail"
}
pass() { _step "PASS" "$1" "${2:-}"; PASS=$((PASS+1)); }
fail() { _step "FAIL" "$1" "${2:-}"; FAIL=$((FAIL+1)); }

echo "=== Obscura Compat Tests (Layer 2 — gate feature validation) ==="

# ── explore gate: Obscura denied (supports_axtree=False) ─────────────────────
EXPLORE_EXIT=0
EXPLORE_OUT=$(cd "$REPO_ROOT" && uv run pytest -q tests/test_obscura_explore_compat.py 2>&1) || EXPLORE_EXIT=$?
if [ $EXPLORE_EXIT -eq 0 ]; then
  pass "explore_gate_compat" "$(echo "$EXPLORE_OUT" | tail -1)"
else
  fail "explore_gate_compat" "$(echo "$EXPLORE_OUT" | tail -3 | tr '\n' ' ')"
fi

# ── browser.navigate / browser.screenshot gate: Obscura allowed ───────────────
BROWSER_EXIT=0
BROWSER_OUT=$(cd "$REPO_ROOT" && uv run pytest -q tests/test_obscura_browser_commands.py 2>&1) || BROWSER_EXIT=$?
if [ $BROWSER_EXIT -eq 0 ]; then
  pass "browser_commands_compat" "$(echo "$BROWSER_OUT" | tail -1)"
else
  fail "browser_commands_compat" "$(echo "$BROWSER_OUT" | tail -3 | tr '\n' ' ')"
fi

# ── login / session / recording gate ─────────────────────────────────────────
SESSION_EXIT=0
SESSION_OUT=$(cd "$REPO_ROOT" && uv run pytest -q tests/test_obscura_session_recording.py 2>&1) || SESSION_EXIT=$?
if [ $SESSION_EXIT -eq 0 ]; then
  pass "session_recording_compat" "$(echo "$SESSION_OUT" | tail -1)"
else
  fail "session_recording_compat" "$(echo "$SESSION_OUT" | tail -3 | tr '\n' ' ')"
fi

# ── axtree gate: Obscura denied ───────────────────────────────────────────────
AXTREE_EXIT=0
AXTREE_OUT=$(cd "$REPO_ROOT" && uv run pytest -q tests/test_obscura_axtree_gate.py 2>&1) || AXTREE_EXIT=$?
if [ $AXTREE_EXIT -eq 0 ]; then
  pass "axtree_gate_compat" "$(echo "$AXTREE_OUT" | tail -1)"
else
  fail "axtree_gate_compat" "$(echo "$AXTREE_OUT" | tail -3 | tr '\n' ' ')"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
printf '{"summary":{"pass":%d,"fail":%d}}\n' "$PASS" "$FAIL"
echo "COMPAT: $PASS pass, $FAIL fail"
[ $FAIL -eq 0 ] && exit 0 || exit 1
