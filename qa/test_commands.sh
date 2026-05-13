#!/bin/bash
# 验证已生成 adapter 命令的执行
PASS=0; FAIL=0

setup_test_adapter() {
  ADAPTER_DIR=~/.cliany-site/adapters/test.com
  if [ -d "$ADAPTER_DIR" ]; then
    echo "[INFO] test.com adapter 已存在"
  else
    echo "[INFO] 创建 test.com adapter..."
    uv run python -c "
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.explorer.models import ExploreResult, PageInfo, ActionStep, CommandSuggestion
result = ExploreResult(
    pages=[PageInfo(url='https://test.com', title='Test', elements=[])],
    actions=[],
    commands=[CommandSuggestion(name='hello', description='测试命令', args=[], action_steps=[])]
)
gen = AdapterGenerator()
code = gen.generate(result, 'test.com')
save_adapter('test.com', code)
print('adapter 创建成功')
"
  fi
}

test_list() {
  OUTPUT=$(uv run cliany-site list --json 2>/dev/null)
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    echo "[PASS] list exit 0"
    PASS=$((PASS+1))
  else
    echo "[FAIL] list exit $EXIT_CODE"
    FAIL=$((FAIL+1))
  fi
  if echo "$OUTPUT" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); assert d['ok']==True" 2>/dev/null; then
    echo "[PASS] list 返回 ok:true"
    PASS=$((PASS+1))
  else
    echo "[FAIL] list 应返回 ok:true"
    FAIL=$((FAIL+1))
  fi
}

test_adapter_cdp_error() {
  OUTPUT=$(uv run cliany-site test.com hello --json 2>/dev/null)
  EXIT_CODE=$?
  if echo "$OUTPUT" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); assert d['ok']==False" 2>/dev/null; then
    echo "[PASS] test.com hello 无 CDP 时返回 ok:false"
    PASS=$((PASS+1))
  else
    echo "[FAIL] test.com hello 无 CDP 时应返回 ok:false"
    FAIL=$((FAIL+1))
  fi
  if echo "$OUTPUT" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); assert d['error']['code']=='E_CDP_UNAVAILABLE'" 2>/dev/null; then
    echo "[PASS] adapter 命令返回 E_CDP_UNAVAILABLE"
    PASS=$((PASS+1))
  else
    echo "[FAIL] adapter 命令应返回 E_CDP_UNAVAILABLE"
    FAIL=$((FAIL+1))
  fi
}

setup_test_adapter
test_list
test_adapter_cdp_error

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
