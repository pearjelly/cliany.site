#!/bin/bash
# 验证 explore 命令的错误处理
PASS=0; FAIL=0
UV_BIN=$(command -v uv)

test_explore_no_cdp() {
  OUTPUT=$("$UV_BIN" run cliany-site explore "https://example.com" "test workflow" --json 2>/dev/null)
  EXIT_CODE=$?
  JSON_PART=$(echo "$OUTPUT" | python3 -c "
import sys, json
content = sys.stdin.read()
start = content.find('{')
if start == -1:
    print('')
    sys.exit(1)
brace_count = 0
end = start
for i in range(start, len(content)):
    if content[i] == '{':
        brace_count += 1
    elif content[i] == '}':
        brace_count -= 1
        if brace_count == 0:
            end = i + 1
            break
print(content[start:end])
" 2>/dev/null)
  if [ $EXIT_CODE -ne 0 ]; then
    echo "[PASS] explore 无 CDP 时 exit 非 0"
    PASS=$((PASS+1))
  else
    echo "[FAIL] explore 无 CDP 时应 exit 非 0（实际 exit $EXIT_CODE）"
    FAIL=$((FAIL+1))
  fi
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); success = d.get('ok', d.get('success', True)); assert not success" 2>/dev/null; then
    echo "[PASS] explore 无 CDP 时返回 success:false"
    PASS=$((PASS+1))
  else
    echo "[FAIL] explore 无 CDP 时应返回 success:false"
    FAIL=$((FAIL+1))
  fi
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); assert d['error']['code']=='E_UNKNOWN'" 2>/dev/null; then
    echo "[PASS] explore 返回 E_UNKNOWN 错误码"
    PASS=$((PASS+1))
  else
    echo "[FAIL] explore 应返回 E_UNKNOWN 错误码"
    FAIL=$((FAIL+1))
  fi
}

test_explore_no_llm() {
  SAVE_KEY="$ANTHROPIC_API_KEY"
  SAVE_OPENAI="$OPENAI_API_KEY"
  unset ANTHROPIC_API_KEY OPENAI_API_KEY
  OUTPUT=$("$UV_BIN" run cliany-site explore "https://example.com" "test" --json 2>/dev/null)
  EXIT_CODE=$?
  if [ $EXIT_CODE -ne 0 ]; then
    echo "[PASS] explore 无环境配置时 exit 非 0"
    PASS=$((PASS+1))
  else
    echo "[FAIL] explore 无环境配置时应 exit 非 0"
    FAIL=$((FAIL+1))
  fi
  [ -n "$SAVE_KEY" ] && export ANTHROPIC_API_KEY="$SAVE_KEY"
  [ -n "$SAVE_OPENAI" ] && export OPENAI_API_KEY="$SAVE_OPENAI"
}

test_explore_help() {
  OUTPUT=$("$UV_BIN" run cliany-site explore --help 2>&1)
  if echo "$OUTPUT" | grep -q "Usage:"; then
    echo "[PASS] explore --help 正确显示"
    PASS=$((PASS+1))
  else
    echo "[FAIL] explore --help 未显示 Usage"
    FAIL=$((FAIL+1))
  fi
}

test_explore_no_cdp
test_explore_no_llm
test_explore_help

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
