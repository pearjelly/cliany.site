#!/bin/bash
# 验证失败语义场景（4 个），不依赖 Chrome / LLM API
PASS=0; FAIL=0

test_navigate_page_not_ready() {
  OUTPUT=$(uv run python3 -c "
import asyncio, json
from unittest.mock import AsyncMock, MagicMock, patch
from cliany_site.commands.browser.navigate import _run_navigate

mock_cdp = MagicMock()
mock_cdp.check_available = AsyncMock(return_value=True)
mock_session = AsyncMock()
mock_session.navigate_to = AsyncMock(side_effect=TimeoutError('page timeout'))
mock_cdp.connect = AsyncMock(return_value=mock_session)
mock_cdp.disconnect = AsyncMock()

with patch('cliany_site.commands.browser.navigate.get_config') as mock_cfg:
    mock_cfg.return_value.browser_provider = None
    result = asyncio.run(_run_navigate(mock_cdp, 'http://10.255.255.1/', 'load', 3))

print(json.dumps(result))
" 2>&1)
  JSON_LINE=$(echo "$OUTPUT" | grep '^{' | tail -1)
  if echo "$JSON_LINE" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); assert d.get('ok')==False and d.get('error',{}).get('code')=='E_PAGE_NOT_READY'" 2>/dev/null; then
    echo "[PASS] navigate timeout → E_PAGE_NOT_READY"
    PASS=$((PASS+1))
  else
    echo "[FAIL] navigate timeout 未返回 E_PAGE_NOT_READY: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_extract_parse_failed() {
  OUTPUT=$(uv run python3 -c "
import asyncio, json
from unittest.mock import AsyncMock
from cliany_site.commands.browser.extract import _do_extract

mock_session = AsyncMock()
mock_session.execute_action = AsyncMock(side_effect=RuntimeError('boom'))
result = asyncio.run(_do_extract(mock_session, '#test', 'text'))
print(json.dumps(result))
" 2>&1)
  if echo "$OUTPUT" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); assert d.get('ok')==False and d.get('error',{}).get('code')=='E_PARSE_FAILED'" 2>/dev/null; then
    echo "[PASS] extract RuntimeError → E_PARSE_FAILED"
    PASS=$((PASS+1))
  else
    echo "[FAIL] extract RuntimeError 未返回 E_PARSE_FAILED: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_list_empty_result() {
  OUTPUT=$(uv run python3 -c "
import json, textwrap
from cliany_site.codegen.templates import _render_empty_result_check

check_code = textwrap.dedent(_render_empty_result_check('list-foo'))
results = [{'ok': True, 'data': []}]
failed = None
local_vars = {'results': results, 'failed': failed}
exec(check_code, {}, local_vars)
failed = local_vars.get('failed')
if failed and failed.get('ok') == False and failed.get('error', {}).get('code') == 'E_EMPTY_RESULT':
    print('PASS')
else:
    print('FAIL: ' + json.dumps(failed))
" 2>&1)
  if [[ "$OUTPUT" == "PASS" ]]; then
    echo "[PASS] list-* 空结果 → E_EMPTY_RESULT"
    PASS=$((PASS+1))
  else
    echo "[FAIL] list-* 空结果 未返回 E_EMPTY_RESULT: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_get_empty_result_ok() {
  OUTPUT=$(uv run python3 -c "
import json
from cliany_site.codegen.templates import render_command_block_v2
from cliany_site.explorer.models import CommandSuggestion

cmd = CommandSuggestion(name='get-bar', description='获取数据', args=[], action_steps=[])
code = render_command_block_v2(cmd, [], 0)
if 'E_EMPTY_RESULT' not in code:
    results = [{'ok': True, 'data': []}]
    failed = next((r for r in results if not r.get('ok')), None)
    if failed is None:
        print('PASS')
    else:
        print('FAIL: unexpected failed set')
else:
    print('FAIL: E_EMPTY_RESULT wrongly injected into get-bar')
" 2>&1)
  if [[ "$OUTPUT" == "PASS" ]]; then
    echo "[PASS] get-* 空结果保持 ok=true"
    PASS=$((PASS+1))
  else
    echo "[FAIL] get-* 空结果未保持 ok=true: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_navigate_page_not_ready
test_extract_parse_failed
test_list_empty_result
test_get_empty_result_ok

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
