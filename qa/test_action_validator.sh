#!/bin/bash
# ActionValidator 单元测试 — 3 个场景，纯逻辑无 CDP 依赖
PASS=0
FAIL=0

cleanup() {
  :
}
trap cleanup EXIT

# ─────────────────────────────────────────────────────────────────────────────
# 场景 1：导航动作检测 URL 变化
# ─────────────────────────────────────────────────────────────────────────────
echo "=== 场景 1：导航动作检测 URL 变化 ==="

OUTPUT=$(uv run python3 -c "
from cliany_site.explorer.models import ActionStep
from cliany_site.explorer.validator import ActionValidator

v = ActionValidator()
step = ActionStep(
    action_type='navigate',
    page_url='https://qa-validator.example/page-a',
    target_url='https://qa-validator.example/page-b',
    description='导航到 page-b',
)
result = v.validate_step(
    step,
    before_url='https://qa-validator.example/page-a',
    after_url='https://qa-validator.example/page-b',
)
assert result.changes, f'changes 应非空，实际: {result.changes}'
assert any('URL' in c for c in result.changes), f'changes 应包含 URL 字样，实际: {result.changes}'
assert result.success, f'success 应为 True，实际: {result.success}'
assert not result.warnings, f'warnings 应为空，实际: {result.warnings}'
print(f'ok changes={result.changes}')
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景1: 导航 URL 变化检测失败: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景1: 导航动作检测到 URL 变化: $OUTPUT"
  PASS=$((PASS+1))
fi

# 场景1 补充：URL 未变化时产生警告
OUTPUT=$(uv run python3 -c "
from cliany_site.explorer.models import ActionStep
from cliany_site.explorer.validator import ActionValidator

v = ActionValidator()
step = ActionStep(
    action_type='navigate',
    page_url='https://qa-validator.example/same',
    target_url='https://qa-validator.example/same',
    description='导航未变化',
)
result = v.validate_step(
    step,
    before_url='https://qa-validator.example/same',
    after_url='https://qa-validator.example/same',
)
assert result.warnings, f'URL 未变化时 warnings 应非空，实际: {result.warnings}'
assert not result.changes, f'URL 未变化时 changes 应为空，实际: {result.changes}'
print(f'ok warnings={result.warnings}')
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景1补充: URL 未变化未产生警告: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景1补充: URL 未变化时产生警告: $OUTPUT"
  PASS=$((PASS+1))
fi

# ─────────────────────────────────────────────────────────────────────────────
# 场景 2：元素未找到产生警告且 success=False
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== 场景 2：元素未找到产生警告 ==="

OUTPUT=$(uv run python3 -c "
from cliany_site.explorer.models import ActionStep
from cliany_site.explorer.validator import ActionValidator

v = ActionValidator()
step = ActionStep(
    action_type='click',
    page_url='https://qa-validator.example/',
    target_ref='@999999',
    target_name='nonexistent-button',
    description='点击不存在的按钮',
)
result = v.validate_step(step, element_found=False)
assert not result.success, f'success 应为 False，实际: {result.success}'
assert result.warnings, f'warnings 应非空，实际: {result.warnings}'
assert any(
    'nonexistent' in w.lower() or '未找到' in w or '找不到' in w
    for w in result.warnings
), f'warnings 应包含元素名称，实际: {result.warnings}'
print(f'ok success={result.success} warnings={result.warnings}')
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景2: 元素未找到验证失败: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景2: 元素未找到产生正确警告: $OUTPUT"
  PASS=$((PASS+1))
fi

# ─────────────────────────────────────────────────────────────────────────────
# 场景 3：验证失败不中断序列
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== 场景 3：验证失败不中断序列 ==="

OUTPUT=$(uv run python3 -c "
from cliany_site.explorer.models import ActionStep
from cliany_site.explorer.validator import ActionValidator

v = ActionValidator()

step1_ok = ActionStep(
    action_type='click',
    page_url='https://qa-validator.example/',
    target_name='submit-btn',
    description='点击提交按钮',
)
step2_fail = ActionStep(
    action_type='click',
    page_url='https://qa-validator.example/',
    target_ref='@999999',
    target_name='missing-element',
    description='点击缺失元素',
)
step3_ok = ActionStep(
    action_type='click',
    page_url='https://qa-validator.example/',
    target_name='confirm-btn',
    description='点击确认按钮',
)

steps = [step1_ok, step2_fail, step3_ok]
elements_found = [True, False, True]
results = v.validate_sequence(steps, elements_found=elements_found)

assert len(results) == 3, f'应返回 3 个结果，实际: {len(results)}'
assert results[1].warnings, f'step2 应有 warnings，实际: {results[1].warnings}'
assert not results[1].success, f'step2 success 应为 False，实际: {results[1].success}'
assert not results[0].warnings, f'step1 warnings 应为空，实际: {results[0].warnings}'
assert results[0].success, f'step1 success 应为 True'
assert not results[2].warnings, f'step3 warnings 应为空，实际: {results[2].warnings}'
assert results[2].success, f'step3 success 应为 True'
print(f'ok len={len(results)} step2_warnings={results[1].warnings}')
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景3: 序列验证中断或结果不正确: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景3: 验证失败不中断序列，全部步骤均处理: $OUTPUT"
  PASS=$((PASS+1))
fi

# ─────────────────────────────────────────────────────────────────────────────
# 汇总
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
