#!/bin/bash
# 验证 Obscura 下 explore/login 返回友好中文错误文案
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

test_explore() {
  OUTPUT=$(CLIANY_BROWSER_PROVIDER=obscura "$UV_BIN" run cliany-site explore "https://example.com" "test" --json 2>&1)
  JSON_PART=$(extract_json "$OUTPUT" 2>/dev/null)
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
error = d["error"]
assert error["code"] == "E_MISSING_CAPABILITY"
assert len(error["message"]) > 20
assert "obscura-experimental-guide.md" in error["details"]["doc_url"]
' 2>/dev/null; then
    echo "[PASS] explore 在 Obscura 下返回友好错误"
    PASS=$((PASS+1))
  else
    echo "[FAIL] explore 在 Obscura 下错误断言失败"
    FAIL=$((FAIL+1))
  fi
}

test_login() {
  OUTPUT=$(CLIANY_BROWSER_PROVIDER=obscura "$UV_BIN" run python - 2>&1 <<'PYEOF'
import json
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from cliany_site.config import reset_config
from cliany_site.providers.capabilities import CapabilitySnapshot

reset_config()
snap = CapabilitySnapshot(
    provider="obscura",
    version="0.1.0",
    supports_axtree=False,
    supports_navigation=False,
    supports_screenshot=True,
    supports_cookies=True,
    supports_network_events=True,
    supports_console_events=True,
)
mock_prov = MagicMock()
mock_prov.get_capability_snapshot.return_value = snap

with patch("cliany_site.providers.factory.get_provider", return_value=mock_prov):
    from cliany_site.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "login", "https://example.com"], catch_exceptions=False)

print(result.output)
PYEOF
)
  JSON_PART=$(extract_json "$OUTPUT" 2>/dev/null)
  if [ -n "$JSON_PART" ] && echo "$JSON_PART" | python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
error = d["error"]
assert error["code"] == "E_MISSING_CAPABILITY"
assert len(error["message"]) > 20
assert "obscura-experimental-guide.md" in error["details"]["doc_url"]
' 2>/dev/null; then
    echo "[PASS] login 在 Obscura 下返回友好错误"
    PASS=$((PASS+1))
  else
    echo "[FAIL] login 在 Obscura 下错误断言失败"
    FAIL=$((FAIL+1))
  fi
}

test_explore
test_login

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
