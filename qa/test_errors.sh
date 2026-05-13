#!/bin/bash
# 验证错误处理
PASS=0; FAIL=0
UV_BIN=$(command -v uv)

test_unknown_command() {
  OUTPUT=$("$UV_BIN" run cliany-site nonexistent-xyz --json 2>&1)
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
    echo "[PASS] 未知命令 exit 非 0"
    PASS=$((PASS+1))
  else
    echo "[FAIL] 未知命令应 exit 非 0"
    FAIL=$((FAIL+1))
  fi
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); success = d.get('ok', d.get('success', True)); assert not success and 'error' in d and d['error']['code']=='E_INVALID_PARAM'" 2>/dev/null; then
    echo "[PASS] 未知命令返回 JSON 错误 E_INVALID_PARAM"
    PASS=$((PASS+1))
  else
    echo "[FAIL] 未知命令应返回 JSON 错误 E_INVALID_PARAM"
    FAIL=$((FAIL+1))
  fi
}

test_doctor_fail_exit_code() {
  SAVE_KEY="$ANTHROPIC_API_KEY"
  SAVE_OPENAI="$OPENAI_API_KEY"
  unset ANTHROPIC_API_KEY OPENAI_API_KEY
  OUTPUT=$("$UV_BIN" run cliany-site doctor --json 2>&1)
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    echo "[PASS] doctor 无环境配置时 exit 0（warning 级别）"
    PASS=$((PASS+1))
  else
    echo "[FAIL] doctor 无环境配置时应 exit 0（实际 exit $EXIT_CODE）"
    FAIL=$((FAIL+1))
  fi
  [ -n "$SAVE_KEY" ] && export ANTHROPIC_API_KEY="$SAVE_KEY"
  [ -n "$SAVE_OPENAI" ] && export OPENAI_API_KEY="$SAVE_OPENAI"
}

test_json_structure() {
  OUTPUT=$("$UV_BIN" run cliany-site doctor --json 2>&1)
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
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
success = d.get('ok', d.get('success', True))
assert 'data' in d, 'missing data'
assert 'error' in d, 'missing error'
if not success:
    assert d['error'] is not None, 'error should not be null on failure'
    assert 'code' in d['error'], 'missing error.code'
    assert 'message' in d['error'], 'missing error.message'
" 2>/dev/null; then
    echo "[PASS] doctor 错误响应结构正确"
    PASS=$((PASS+1))
  else
    echo "[FAIL] doctor 错误响应结构不正确"
    FAIL=$((FAIL+1))
  fi
}

test_login_no_chrome_binary() {
  # With auto-launch, CDP_UNAVAILABLE only happens when Chrome binary is not found
  OUTPUT=$(PATH="/usr/bin:/bin" "$UV_BIN" run cliany-site login "https://example.com" --json 2>&1)
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    echo "[PASS] login 无 Chrome 二进制时 exit 0（延迟检查）"
    PASS=$((PASS+1))
  else
    echo "[FAIL] login 无 Chrome 二进制时应 exit 0（实际 exit $EXIT_CODE）"
    FAIL=$((FAIL+1))
  fi
}

test_unknown_command
test_doctor_fail_exit_code
test_json_structure
test_login_no_chrome_binary

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
