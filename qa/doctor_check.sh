#!/bin/bash
# 验证 cliany-site 安装和基础环境
PASS=0; FAIL=0
UV_BIN=$(command -v uv)

check_installed() {
  if command -v cliany-site &>/dev/null; then
    echo "[PASS] cliany-site 已安装"
    PASS=$((PASS+1))
  else
    echo "[FAIL] cliany-site 未安装"
    FAIL=$((FAIL+1))
  fi
}

check_version() {
  OUTPUT=$("$UV_BIN" run cliany-site --version 2>&1)
  if echo "$OUTPUT" | grep -q "0\."; then
    echo "[PASS] cliany-site --version 输出: $OUTPUT"
    PASS=$((PASS+1))
  else
    echo "[FAIL] cliany-site --version 失败: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

check_doctor_json() {
  OUTPUT=$("$UV_BIN" run cliany-site doctor --json 2>&1)
  # 使用 Python 提取 JSON 部分
  JSON_PART=$(echo "$OUTPUT" | python3 -c "
import sys, json
content = sys.stdin.read()
# 找到第一个 { 并匹配括号
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
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -m json.tool &>/dev/null; then
    echo "[PASS] doctor --json 输出有效 JSON"
    PASS=$((PASS+1))
  else
    echo "[FAIL] doctor --json 未返回有效 JSON"
    FAIL=$((FAIL+1))
  fi
  # 验证返回 JSON 格式（有 ok 或 success 字段，向后兼容）
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); assert 'ok' in d or 'success' in d" 2>/dev/null; then
    echo "[PASS] doctor 返回包含 'ok' 或 'success' 字段"
    PASS=$((PASS+1))
  else
    echo "[FAIL] doctor 返回缺少 'ok' 或 'success' 字段"
    FAIL=$((FAIL+1))
  fi
}

check_dirs() {
  if [ -d ~/.cliany-site/adapters ] && [ -d ~/.cliany-site/sessions ]; then
    echo "[PASS] ~/.cliany-site/ 目录结构正确"
    PASS=$((PASS+1))
  else
    echo "[FAIL] ~/.cliany-site/ 目录不完整"
    FAIL=$((FAIL+1))
  fi
}

check_installed
check_version
check_doctor_json
check_dirs

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
