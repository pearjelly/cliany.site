#!/bin/bash
# 验证 doctor 的 agent_md 三态逻辑
PASS=0
FAIL=0
UV_BIN=$(command -v uv)

extract_json() {
  echo "$1" | python3 -c '
import sys, json
content = sys.stdin.read()
start = content.find("{")
if start == -1:
    print("")
    raise SystemExit(1)
brace_count = 0
end = start
for i in range(start, len(content)):
    if content[i] == "{":
        brace_count += 1
    elif content[i] == "}":
        brace_count -= 1
        if brace_count == 0:
            end = i + 1
            break
print(content[start:end])
'
}

test_repo_root() {
  OUTPUT=$("$UV_BIN" run cliany-site doctor --json 2>&1)
  JSON_PART=$(extract_json "$OUTPUT" 2>/dev/null)
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
agent_md = next(item for item in d["data"]["checks"] if item.get("name") == "agent_md")
assert agent_md["status"] != "missing"
assert agent_md["details"]["path"] == "AGENTS.md"
' 2>/dev/null; then
    echo "[PASS] 仓库根目录 agent_md 识别为 AGENTS.md 且非 missing"
    PASS=$((PASS+1))
  else
    echo "[FAIL] 仓库根目录 agent_md 断言失败"
    FAIL=$((FAIL+1))
  fi
}

test_empty_dir() {
  TMPDIR_EMPTY="/tmp/cliany-doctor-empty-$$"
  mkdir -p "$TMPDIR_EMPTY"
  : > "$TMPDIR_EMPTY/AGENT.md"
  OUTPUT=$(cd "$TMPDIR_EMPTY" && "$UV_BIN" run cliany-site doctor --json 2>&1)
  JSON_PART=$(extract_json "$OUTPUT" 2>/dev/null)
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
agent_md = next(item for item in d["data"]["checks"] if item.get("name") == "agent_md")
assert agent_md["status"] == "warning"
assert agent_md["details"]["status"] == "no_sentinel"
' 2>/dev/null; then
    echo "[PASS] 空目录 agent_md 返回 warning 且包含提示"
    PASS=$((PASS+1))
  else
    echo "[FAIL] 空目录 agent_md 断言失败"
    FAIL=$((FAIL+1))
  fi
}

test_repo_root
test_empty_dir

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
