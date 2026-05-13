#!/bin/bash
# 验证 extract 功能各层实现（模型、JS构建器、运行时、提示词、代码生成）
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

# 测试 1: ActionStep 模型字段验证
check 'uv run python3 -c "
from cliany_site.explorer.models import ActionStep
import dataclasses
fields = {f.name for f in dataclasses.fields(ActionStep)}
assert \"selector\" in fields
assert \"extract_mode\" in fields
assert \"fields_map\" in fields
a = ActionStep(action_type=\"extract\", page_url=\"\")
assert a.selector == \"\"
assert a.extract_mode == \"text\"
assert a.fields_map == {}
"' "ActionStep 包含 extract 字段且默认值正确"

# 测试 2: JS 构建器 text 模式
check 'uv run python3 -c "
from cliany_site.extract import build_extract_js
js = build_extract_js(\".title\", \"text\")
assert \"=>\" in js and \"querySelector\" in js
assert \"{text:\" in js, \"text 模式应返回 {text: ...} 对象\"
"' "build_extract_js text 模式生成箭头函数并返回 {text} 对象"

# 测试 3: JS 构建器 list 模式
check 'uv run python3 -c "
from cliany_site.extract import build_extract_js
js = build_extract_js(\".item\", \"list\", {\"title\": \"h3\", \"url\": \"a@href\"})
assert \"=>\" in js and \"querySelectorAll\" in js and \"getAttribute\" in js
"' "build_extract_js list 模式含 @attr 语法"

# 测试 4: JS 构建器 attribute 模式
check 'uv run python3 -c "
from cliany_site.extract import build_extract_js
js = build_extract_js(\"a.link\", \"attribute\")
assert \"=>\" in js and \"Object.fromEntries\" in js and \"attributes\" in js
js2 = build_extract_js(\"a.link\", \"attribute\", {\"href\": \"@href\"})
assert \"getAttribute\" in js2
"' "build_extract_js attribute 模式（纯 CSS + fields_map）"

# 测试 5: JS 构建器 table 模式
check 'uv run python3 -c "
from cliany_site.extract import build_extract_js
js = build_extract_js(\"table\", \"table\")
assert \"=>\" in js and \"tr\" in js
assert \"td,th\" in js, \"无 fields_map 的 table 模式应使用 td,th 生成 2D 数组\"
assert \"record\" not in js, \"无 fields_map 时不应生成对象数组\"
"' "build_extract_js table 模式（无 fields_map → 2D 数组）"

# 测试 6: JS 构建器错误处理
check 'uv run python3 -c "
from cliany_site.extract import build_extract_js
try:
    build_extract_js(\"\", \"text\")
    exit(1)
except ValueError:
    pass
try:
    build_extract_js(\".el\", \"unknown_mode\")
    exit(1)
except ValueError:
    pass
"' "build_extract_js 空 selector 和未知 mode 抛 ValueError"

# 测试 7: 运行时 extraction_results 参数
check 'uv run python3 -c "
from cliany_site.action_runtime import execute_action_steps
import inspect
sig = inspect.signature(execute_action_steps)
params = list(sig.parameters.keys())
assert \"extraction_results\" in params
dry_run_idx = params.index(\"dry_run\")
extraction_idx = params.index(\"extraction_results\")
assert extraction_idx == dry_run_idx + 1
"' "execute_action_steps 包含 extraction_results 参数（位于 dry_run 之后）"

# 测试 8: 运行时 extract 在动作类型白名单中
check 'uv run python3 -c "
import ast, pathlib
src = pathlib.Path(\"src/cliany_site/action_runtime.py\").read_text()
assert \"extract\" in src
assert \"\\\"extract\\\"\" in src or \"'"'"'extract'"'"'\" in src
"' "action_runtime.py 包含 extract 动作类型"

# 测试 9: SYSTEM_PROMPT 包含 extract 关键词
check 'uv run python3 -c "
from cliany_site.explorer.prompts import SYSTEM_PROMPT
assert \"extract\" in SYSTEM_PROMPT
assert \"extract_mode\" in SYSTEM_PROMPT
assert \"fields\" in SYSTEM_PROMPT
assert \"click / type / select / navigate / submit / reuse_atom / extract\" in SYSTEM_PROMPT
"' "SYSTEM_PROMPT 包含 extract 类型和字段说明"

# 测试 10: 代码生成序列化 extract 字段
check 'uv run python3 -c "
import json
from cliany_site.codegen.templates import render_action_data_literal
from cliany_site.explorer.models import ActionStep
actions = [ActionStep(action_type=\"extract\", page_url=\"\", selector=\".result\", extract_mode=\"list\", fields_map={\"title\": \"h3\"})]
literal = render_action_data_literal([0], actions)
data = json.loads(literal)
assert data[0][\"type\"] == \"extract\"
assert data[0][\"selector\"] == \".result\"
assert data[0][\"extract_mode\"] == \"list\"
assert data[0][\"fields\"] == {\"title\": \"h3\"}
"' "render_action_data_literal 正确序列化 extract 字段（fields_map → fields）"

# 测试 11: 代码生成注入 _extraction_results
check 'uv run python3 -c "
from cliany_site.codegen.templates import render_execution_blocks
from cliany_site.explorer.models import ActionStep
actions = [
    ActionStep(action_type=\"navigate\", page_url=\"\", target_url=\"https://example.com\"),
    ActionStep(action_type=\"extract\", page_url=\"\", selector=\".result\", extract_mode=\"list\"),
]
blocks = render_execution_blocks([0, 1], actions, [])
assert \"_extraction_results\" in blocks
"' "render_execution_blocks 在有 extract 步骤时注入 _extraction_results"

# 测试 12: 代码生成 success_response 包含 results
check 'uv run python3 -c "
from cliany_site.codegen.templates import render_command_block
from cliany_site.explorer.models import ActionStep, CommandSuggestion
actions = [ActionStep(action_type=\"extract\", page_url=\"\", selector=\".result\", extract_mode=\"text\")]
cmd = CommandSuggestion(name=\"get-data\", description=\"获取数据\", args=[], action_steps=[0])
code = render_command_block(cmd, actions, 0)
assert \"results\" in code
assert \"_extraction_results\" in code
"' "render_command_block 在有 extract 时包含 results 字段"

# 测试 13: 向后兼容 — 不含 extract 的命令正常生成
check 'uv run python3 -c "
from cliany_site.codegen.templates import render_command_block
from cliany_site.explorer.models import ActionStep, CommandSuggestion
actions = [ActionStep(action_type=\"click\", page_url=\"\", target_ref=\"42\")]
cmd = CommandSuggestion(name=\"do-click\", description=\"点击操作\", args=[], action_steps=[0])
code = render_command_block(cmd, actions, 0)
assert \"_extraction_results\" not in code
assert \"results\" not in code
compile(code, \"<test>\", \"exec\")
"' "不含 extract 的命令不注入 _extraction_results（向后兼容）"

# 测试 14: 含 extract 的生成代码可编译
check 'uv run python3 -c "
from cliany_site.codegen.templates import render_command_block
from cliany_site.explorer.models import ActionStep, CommandSuggestion
actions = [ActionStep(action_type=\"extract\", page_url=\"\", selector=\".item\", extract_mode=\"list\", fields_map={\"title\": \"h3\"})]
cmd = CommandSuggestion(name=\"list-items\", description=\"列出项目\", args=[], action_steps=[0])
code = render_command_block(cmd, actions, 0)
compile(code, \"<test_extract>\", \"exec\")
"' "含 extract 的生成代码语法合法（compile 通过）"

# 测试 15: ExploreResult.to_dict() 正确序列化新字段
check 'uv run python3 -c "
from cliany_site.explorer.models import ActionStep, ExploreResult
import dataclasses
a = ActionStep(action_type=\"extract\", page_url=\"\", selector=\".r\", extract_mode=\"list\", fields_map={\"k\": \"v\"})
d = dataclasses.asdict(a)
assert d[\"selector\"] == \".r\"
assert d[\"extract_mode\"] == \"list\"
assert d[\"fields_map\"] == {\"k\": \"v\"}
"' "ActionStep dataclasses.asdict() 包含 extract 新字段"

# 测试 16: save_adapter 白名单包含 extract 字段
check 'uv run python3 -c "
import pathlib
src = pathlib.Path(\"src/cliany_site/codegen/generator.py\").read_text()
assert \"selector\" in src and \"extract_mode\" in src and \"fields_map\" in src
"' "generator.py save_adapter 白名单包含 extract 字段"

# 测试 17: _normalize_atom_actions 包含 fields_map 映射
check 'uv run python3 -c "
import pathlib
src = pathlib.Path(\"src/cliany_site/codegen/generator.py\").read_text()
count = src.count(\"fields_map\")
assert count >= 3, f\"generator.py 应至少包含 3 处 fields_map 引用，实际 {count} 处\"
"' "_normalize_atom_actions 两处模板和白名单都包含 fields_map"

# 测试 18: extract 结果 JSON 字符串可回转为结构化数据（避免 markdown 出现 \uXXXX）
check 'uv run python3 -c "
from cliany_site.action_runtime import _coerce_json_like_extract_data
raw = \"[{\\\"title\\\": \\\"\\\\u5f20\\\\u96ea\\\\u5cf0\\\", \\\"url\\\": \\\"\\\"}]\"
data = _coerce_json_like_extract_data(raw)
assert isinstance(data, list)
assert \"\\\\u\" not in data[0][\"title\"]
"' "_coerce_json_like_extract_data 可解析 JSON 字符串并恢复中文"

# 测试 19: href/src 提取包含回退策略（querySelector -> direct -> closest）
check 'uv run python3 -c "
from cliany_site.extract import build_extract_js
js = build_extract_js(\".card\", \"list\", {\"url\": \"a@href\"})
assert \".closest(\" in js
assert \".href\" in js
assert \"getAttribute(\" in js
"' "build_extract_js 的 href 提取包含回退链路"

# 测试 20: 提示词约束包含 title/url/snippet 三字段要求
check 'uv run python3 -c "
from cliany_site.explorer.prompts import SYSTEM_PROMPT
assert \"title:\" in SYSTEM_PROMPT
assert \"url:\" in SYSTEM_PROMPT
assert \"snippet:\" in SYSTEM_PROMPT
assert \"严禁把 title 映射成\" in SYSTEM_PROMPT
assert \"a@href\" in SYSTEM_PROMPT
"' "SYSTEM_PROMPT 包含标题/链接/摘要提取约束"

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
