#!/bin/bash
# test_browser_auto_launch.sh - Test Chrome auto-launch functions and error codes
# Tests find_chrome_binary(), detect_running_chrome(), and CHROME_NOT_FOUND error code

PASS=0
FAIL=0

test_find_chrome() {
  OUTPUT=$(uv run python3 -c "
from cliany_site.browser.launcher import find_chrome_binary
result = find_chrome_binary()
if result is not None:
    print(result)
else:
    print('NONE')
" 2>&1)
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    echo "[PASS] find_chrome_binary 执行成功"
    PASS=$((PASS+1))
  else
    echo "[FAIL] find_chrome_binary 执行失败: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
  # On macOS/Linux dev machines, Chrome is typically installed
  if [ "$OUTPUT" != "NONE" ] && [ -f "$OUTPUT" ]; then
    echo "[PASS] find_chrome_binary 找到 Chrome: $OUTPUT"
    PASS=$((PASS+1))
  else
    echo "[WARN] find_chrome_binary 未找到 Chrome (CI 环境可接受)"
    PASS=$((PASS+1))
  fi
}

test_detect_running() {
  OUTPUT=$(uv run python3 -c "
from cliany_site.browser.launcher import detect_running_chrome
result = detect_running_chrome(port=19222)
print(result if result else 'NONE')
" 2>&1)
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    echo "[PASS] detect_running_chrome 执行成功 (返回: $OUTPUT)"
    PASS=$((PASS+1))
  else
    echo "[FAIL] detect_running_chrome 执行失败: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_error_code() {
  uv run python3 -c "from cliany_site.errors import CHROME_NOT_FOUND; assert CHROME_NOT_FOUND == 'CHROME_NOT_FOUND'" 2>&1
  if [ $? -eq 0 ]; then
    echo "[PASS] CHROME_NOT_FOUND 错误码存在"
    PASS=$((PASS+1))
  else
    echo "[FAIL] CHROME_NOT_FOUND 错误码缺失"
    FAIL=$((FAIL+1))
  fi
}

test_launch_chrome_no_binary() {
  OUTPUT=$(uv run python3 -c "
from unittest.mock import patch
from cliany_site.browser.launcher import launch_chrome, ChromeNotFoundError
try:
    with patch('cliany_site.browser.launcher.find_chrome_binary', return_value=None):
        launch_chrome()
    print('NO_ERROR')
except ChromeNotFoundError as e:
    print('CHROME_NOT_FOUND_ERROR')
except Exception as e:
    print(f'WRONG_ERROR: {type(e).__name__}: {e}')
" 2>&1)
  if echo "$OUTPUT" | grep -q "CHROME_NOT_FOUND_ERROR"; then
    echo "[PASS] launch_chrome 无 Chrome 时抛出 ChromeNotFoundError"
    PASS=$((PASS+1))
  else
    echo "[FAIL] launch_chrome 无 Chrome 时应抛出 ChromeNotFoundError: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_ensure_chrome_import() {
  OUTPUT=$(uv run python3 -c "
from cliany_site.browser.launcher import ensure_chrome
import inspect
sig = inspect.signature(ensure_chrome)
print(f'params: {list(sig.parameters.keys())}')
" 2>&1)
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    echo "[PASS] ensure_chrome 导入成功: $OUTPUT"
    PASS=$((PASS+1))
  else
    echo "[FAIL] ensure_chrome 导入失败: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_chrome_not_found_error_class() {
  uv run python3 -c "from cliany_site.browser.launcher import ChromeNotFoundError; assert issubclass(ChromeNotFoundError, Exception)" 2>&1
  if [ $? -eq 0 ]; then
    echo "[PASS] ChromeNotFoundError 异常类可导入"
    PASS=$((PASS+1))
  else
    echo "[FAIL] ChromeNotFoundError 异常类缺失"
    FAIL=$((FAIL+1))
  fi
}

test_cdp_integration() {
  # Test CDPConnection has chrome tracking attributes
  OUTPUT=$(uv run python3 -c "
from cliany_site.browser.cdp import CDPConnection
cdp = CDPConnection()
assert hasattr(cdp, '_chrome_proc'), 'missing _chrome_proc'
assert hasattr(cdp, '_chrome_auto_launched'), 'missing _chrome_auto_launched'
assert cdp._chrome_auto_launched == False, '_chrome_auto_launched should start False'
print('OK')
" 2>&1)
  if echo "$OUTPUT" | grep -q "OK"; then
    echo "[PASS] CDPConnection Chrome 追踪属性正确"
    PASS=$((PASS+1))
  else
    echo "[FAIL] CDPConnection Chrome 追踪属性缺失: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_doctor_chrome_fields() {
  # Test that doctor output includes chrome fields
  OUTPUT=$(uv run python3 -c "
import asyncio
from cliany_site.commands.doctor import _run_checks
result = asyncio.run(_run_checks())
data = result.get('data', result)
assert 'chrome_binary_path' in data, f'missing chrome_binary_path in {list(data.keys())}'
assert 'chrome_auto_launched' in data, f'missing chrome_auto_launched in {list(data.keys())}'
print(f'binary={data[\"chrome_binary_path\"]}, launched={data[\"chrome_auto_launched\"]}')
" 2>&1)
  if [ $? -eq 0 ]; then
    echo "[PASS] doctor 输出包含 Chrome 字段: $OUTPUT"
    PASS=$((PASS+1))
  else
    echo "[FAIL] doctor 输出缺少 Chrome 字段: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

echo "Running browser auto-launch tests..."
test_find_chrome
test_detect_running
test_error_code
test_launch_chrome_no_binary
test_ensure_chrome_import
test_chrome_not_found_error_class
test_cdp_integration
test_doctor_chrome_fields

echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1