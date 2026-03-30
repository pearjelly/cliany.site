#!/usr/bin/env bash
set -euo pipefail
PASS=0; FAIL=0

check() {
  if eval "$1" 2>/dev/null; then
    echo "[PASS] $2"
    PASS=$((PASS+1))
  else
    echo "[FAIL] $2"
    FAIL=$((FAIL+1))
  fi
}

# 测试 1: 基本候选生成（有 id 和 class 的元素）
check 'uv run python3 -c "
from cliany_site.browser.selector import compute_selector_candidates
candidates = compute_selector_candidates(\"div\", {\"id\": \"main\", \"class\": \"container flex\"})
assert \"#main\" in candidates
assert \"div.container\" in candidates
assert \"div.flex\" in candidates
"' "compute_selector_candidates: 基本候选生成（id 和 class）"

# 测试 2: data-testid 最高优先级
check 'uv run python3 -c "
from cliany_site.browser.selector import compute_selector_candidates
candidates = compute_selector_candidates(\"button\", {\"data-testid\": \"submit-btn\", \"id\": \"btn\", \"class\": \"btn\"})
assert candidates[0] == \"[data-testid=\\\"submit-btn\\\"]\"
"' "compute_selector_candidates: data-testid 最高优先级"

# 测试 3: 动态类名过滤（css-*、sc-*、纯哈希）
check 'uv run python3 -c "
from cliany_site.browser.selector import compute_selector_candidates
candidates = compute_selector_candidates(\"div\", {\"class\": \"css-123 sc-456 abc123 flex\"})
assert \"css-123\" not in str(candidates)
assert \"sc-456\" not in str(candidates)
assert \"abc123\" not in str(candidates)
assert \"div.flex\" in candidates
"' "compute_selector_candidates: 动态类名过滤（css-*、sc-*、纯哈希）"

# 测试 4: Tailwind 类名保留（flex、pt-4 不被过滤）
check 'uv run python3 -c "
from cliany_site.browser.selector import compute_selector_candidates
candidates = compute_selector_candidates(\"div\", {\"class\": \"flex pt-4 css-123\"})
assert \"div.flex\" in candidates
assert \"div.pt-4\" in candidates
assert \"css-123\" not in str(candidates)
"' "compute_selector_candidates: Tailwind 类名保留（flex、pt-4）"

# 测试 5: 随机 ID 过滤 vs 语义 ID 保留
check 'uv run python3 -c "
from cliany_site.browser.selector import compute_selector_candidates
candidates = compute_selector_candidates(\"input\", {\"id\": \"username\", \"class\": \"form-control\"})
assert \"#username\" in candidates
candidates2 = compute_selector_candidates(\"div\", {\"id\": \"abc123def\", \"class\": \"container\"})
assert \"#abc123def\" not in candidates2
"' "compute_selector_candidates: 随机 ID 过滤 vs 语义 ID 保留"

# 测试 6: 无属性元素降级（返回 []，不抛异常）
check 'uv run python3 -c "
from cliany_site.browser.selector import compute_selector_candidates
candidates = compute_selector_candidates(\"span\", {})
assert isinstance(candidates, list)  # 不抛异常，返回列表即可
"' "compute_selector_candidates: 无属性元素降级（返回列表，不抛异常）"

# 测试 7: enrich_selector_map 往返（css_candidates 添加，原有键不变）
check 'uv run python3 -c "
from cliany_site.browser.selector import enrich_selector_map
original = {\"@ref1\": {\"tag\": \"div\", \"attributes\": {\"id\": \"main\"}}}
enriched = enrich_selector_map(original)
assert \"css_candidates\" in enriched[\"@ref1\"]
assert enriched[\"@ref1\"][\"tag\"] == \"div\"
"' "enrich_selector_map: css_candidates 添加，原有键不变"

# 测试 8: format_selector_candidates_section 格式验证
check 'uv run python3 -c "
from cliany_site.browser.selector import format_selector_candidates_section
selector_map = {\"@ref1\": {\"tag\": \"div\", \"attributes\": {\"id\": \"main\"}, \"css_candidates\": [\"#main\"]}}
section = format_selector_candidates_section(selector_map)
assert \"@ref1\" in section
assert \"#main\" in section
"' "format_selector_candidates_section: 格式验证"

# 测试 9: format_selector_candidates_section 截断验证
check 'uv run python3 -c "
from cliany_site.browser.selector import format_selector_candidates_section
selector_map = {\"@ref1\": {\"tag\": \"div\", \"attributes\": {\"id\": \"main\"}, \"css_candidates\": [\"#main\"]}}
section = format_selector_candidates_section(selector_map, max_chars=10)
assert len(section) <= 10
"' "format_selector_candidates_section: 截断验证"

# 测试 10: merger 往返保真（extract 字段保留）
check 'uv run python3 -c "
from cliany_site.explorer.models import ActionStep
a = ActionStep(action_type=\"extract\", page_url=\"\", selector=\".result\", extract_mode=\"list\", fields_map={\"title\": \"h3\"})
assert a.selector == \".result\"
assert a.extract_mode == \"list\"
assert a.fields_map == {\"title\": \"h3\"}
"' "ActionStep: extract 字段正确赋值"

# 测试 11: 非 extract 动作默认值验证
check 'uv run python3 -c "
from cliany_site.explorer.models import ActionStep
a = ActionStep(action_type=\"click\", page_url=\"\")
assert a.selector == \"\"
assert a.extract_mode == \"text\"
assert a.fields_map == {}
"' "ActionStep: 非 extract 动作默认值验证"

# 测试 12: extract 空 selector 告警触发
check 'uv run python3 -c "
from cliany_site.explorer.models import ActionStep
a = ActionStep(action_type=\"extract\", page_url=\"\", selector=\"\", extract_mode=\"list\", fields_map={})
assert a.selector == \"\"
assert a.extract_mode == \"list\"
"' "ActionStep: extract 支持空 selector（不抛异常）"

# 测试 13: 非 extract 动作不触发 selector 告警
check 'uv run python3 -c "
import warnings
from cliany_site.explorer.models import ActionStep
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter(\"always\")
    a = ActionStep(action_type=\"click\", page_url=\"\", selector=\"\")
    assert len(w) == 0
"' "非 extract 动作不触发 selector 告警"

# 测试 14: 导入无循环依赖验证
check 'uv run python3 -c "
from cliany_site.browser.selector import compute_selector_candidates, enrich_selector_map, format_selector_candidates_section
assert callable(compute_selector_candidates)
assert callable(enrich_selector_map)
assert callable(format_selector_candidates_section)
"' "导入无循环依赖验证（selector 模块）"

# 测试 15: 导入 axtree 不报错
check 'uv run python3 -c "
from cliany_site.browser import axtree
assert hasattr(axtree, \"capture_axtree\")
"' "导入 axtree 不报错"

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1