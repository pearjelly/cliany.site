#!/bin/bash
# 验证结构化错误输出和 --retry 标志
PASS=0; FAIL=0

test_action_execution_error_import() {
  OUTPUT=$(uv run python3 -c "
from cliany_site.action_runtime import ActionExecutionError
err = ActionExecutionError(
    error_type='test_type',
    action_index=1,
    action={'type': 'click'},
    message='test message',
    suggestion='test suggestion'
)
result = err.to_dict()
expected_keys = {'error_type', 'action_index', 'action', 'message', 'suggestion'}
if set(result.keys()) == expected_keys and result['error_type'] == 'test_type':
    print('PASS')
else:
    print('FAIL')
" 2>&1)
  if [[ "$OUTPUT" == "PASS" ]]; then
    echo "[PASS] ActionExecutionError import and to_dict"
    PASS=$((PASS+1))
  else
    echo "[FAIL] ActionExecutionError import/to_dict failed: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_generated_code_has_retry() {
  OUTPUT=$(uv run python3 -c "
from cliany_site.codegen.generator import AdapterGenerator
from cliany_site.explorer.models import ExploreResult, PageInfo, ActionStep, CommandSuggestion
result = ExploreResult(
    pages=[PageInfo(url='https://test.com', title='Test', elements=[])],
    actions=[],
    commands=[CommandSuggestion(name='test-cmd', description='测试命令', args=[], action_steps=[])]
)
gen = AdapterGenerator()
code = gen.generate(result, 'test.com')
if '--retry' in code and 'retry: bool' in code:
    print('PASS')
else:
    print('FAIL')
" 2>&1)
  if [[ "$OUTPUT" == "PASS" ]]; then
    echo "[PASS] Generated code contains --retry option"
    PASS=$((PASS+1))
  else
    echo "[FAIL] Generated code missing --retry: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_action_execution_error_raise() {
  OUTPUT=$(uv run python3 -c "
from cliany_site.action_runtime import ActionExecutionError, execute_action_steps
import asyncio

async def test():
    try:
        # This should raise ActionExecutionError for invalid URL
        await execute_action_steps(None, [{'type': 'navigate', 'url': ''}], continue_on_error=False)
    except ActionExecutionError as e:
        if e.error_type == 'execution_error' and e.action_index == 0:
            print('PASS')
        else:
            print('FAIL: wrong error type or index')
    except Exception as e:
        print(f'FAIL: wrong exception type: {type(e)}')

asyncio.run(test())
" 2>&1)
  if [[ "$OUTPUT" == "PASS" ]]; then
    echo "[PASS] ActionExecutionError raised correctly"
    PASS=$((PASS+1))
  else
    echo "[FAIL] ActionExecutionError not raised correctly: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_action_execution_error_import
test_generated_code_has_retry
test_action_execution_error_raise

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1