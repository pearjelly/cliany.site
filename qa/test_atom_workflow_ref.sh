#!/bin/bash
PASS=0
FAIL=0

TEST_DOMAIN="qa-atomref.example"
ADAPTER_DIR="$HOME/.cliany-site/adapters/$TEST_DOMAIN"
COMMANDS_FILE="$ADAPTER_DIR/commands.py"
METADATA_FILE="$ADAPTER_DIR/metadata.json"

cleanup_test_data() {
  rm -rf "$ADAPTER_DIR" 2>/dev/null || true
}

test_workflow_with_reuse_atom_generates_load_atom() {
  cleanup_test_data

  OUTPUT=$(uv run python3 -c "
import json
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.codegen.generator import AdapterGenerator, save_adapter

domain = 'qa-atomref.example'

actions = [
    ActionStep(
        action_type='navigate',
        page_url='',
        target_ref='',
        target_url='https://qa-atomref.example/',
        value='',
        description='导航到首页',
    ),
    ActionStep(
        action_type='reuse_atom',
        page_url='https://qa-atomref.example/',
        target_ref='fill-search',
        target_url='',
        value='',
        description='复用填写搜索框原子',
        target_attributes={'query': 'browser-use'},
    ),
    ActionStep(
        action_type='click',
        page_url='https://qa-atomref.example/',
        target_ref='42',
        target_url='',
        value='',
        description='点击搜索按钮',
    ),
]

commands = [
    CommandSuggestion(
        name='search',
        description='搜索仓库',
        args=[{'name': 'query', 'description': '搜索关键词', 'required': True}],
        action_steps=[0, 1, 2],
    )
]

explore_result = ExploreResult(
    pages=[PageInfo(url='https://qa-atomref.example/', title='QA Test')],
    actions=actions,
    commands=commands,
)

gen = AdapterGenerator(domain)
code = gen.generate(explore_result, domain)
path = save_adapter(domain, code, explore_result=explore_result)
print(path)
" 2>&1)

  if [ $? -ne 0 ]; then
    echo "[FAIL] 生成含 reuse_atom 的工作流 adapter 失败: $OUTPUT"
    FAIL=$((FAIL+1))
    return
  fi

  if [ ! -f "$COMMANDS_FILE" ]; then
    echo "[FAIL] commands.py 未生成"
    FAIL=$((FAIL+1))
    return
  fi

  echo "[PASS] 生成含 reuse_atom 的工作流 adapter: $OUTPUT"
  PASS=$((PASS+1))
}

test_commands_py_contains_load_atom() {
  if grep -q 'from cliany_site.atoms.storage import load_atom' "$COMMANDS_FILE"; then
    echo "[PASS] commands.py 包含 load_atom 导入"
    PASS=$((PASS+1))
  else
    echo "[FAIL] commands.py 缺少 load_atom 导入"
    FAIL=$((FAIL+1))
  fi

  if grep -q 'load_atom(DOMAIN, ' "$COMMANDS_FILE"; then
    echo "[PASS] commands.py 包含 load_atom 调用"
    PASS=$((PASS+1))
  else
    echo "[FAIL] commands.py 缺少 load_atom 调用"
    FAIL=$((FAIL+1))
  fi

  if grep -q '_normalize_atom_actions' "$COMMANDS_FILE"; then
    echo "[PASS] commands.py 包含 _normalize_atom_actions"
    PASS=$((PASS+1))
  else
    echo "[FAIL] commands.py 缺少 _normalize_atom_actions"
    FAIL=$((FAIL+1))
  fi

  if grep -q 'substitute_parameters' "$COMMANDS_FILE"; then
    echo "[PASS] commands.py 包含 substitute_parameters"
    PASS=$((PASS+1))
  else
    echo "[FAIL] commands.py 缺少 substitute_parameters"
    FAIL=$((FAIL+1))
  fi
}

test_metadata_contains_atom_refs() {
  if [ ! -f "$METADATA_FILE" ]; then
    echo "[FAIL] metadata.json 未生成"
    FAIL=$((FAIL+1))
    return
  fi

  ATOM_REFS=$(uv run python3 -c "
import json
with open('$METADATA_FILE') as f:
    meta = json.load(f)
cmds = meta.get('commands', [])
for cmd in cmds:
    refs = cmd.get('atom_refs', [])
    if refs:
        print(','.join(refs))
" 2>&1)

  if echo "$ATOM_REFS" | grep -q 'fill-search'; then
    echo "[PASS] metadata.json commands 包含 atom_refs: $ATOM_REFS"
    PASS=$((PASS+1))
  else
    echo "[FAIL] metadata.json commands 缺少 atom_refs (got: $ATOM_REFS)"
    FAIL=$((FAIL+1))
  fi
}

test_inline_actions_still_generated() {
  if grep -q 'json.loads(' "$COMMANDS_FILE"; then
    echo "[PASS] commands.py 保留了内联 action 的 json.loads"
    PASS=$((PASS+1))
  else
    echo "[FAIL] commands.py 缺少内联 action 的 json.loads"
    FAIL=$((FAIL+1))
  fi
}

test_pure_inline_workflow_unchanged() {
  PURE_DOMAIN="qa-atomref-pure.example"
  PURE_DIR="$HOME/.cliany-site/adapters/$PURE_DOMAIN"
  PURE_FILE="$PURE_DIR/commands.py"
  rm -rf "$PURE_DIR" 2>/dev/null || true

  OUTPUT=$(uv run python3 -c "
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.codegen.generator import AdapterGenerator, save_adapter

domain = 'qa-atomref-pure.example'

actions = [
    ActionStep(
        action_type='click',
        page_url='https://qa-atomref-pure.example/',
        target_ref='10',
        value='',
        description='点击按钮',
    ),
    ActionStep(
        action_type='type',
        page_url='https://qa-atomref-pure.example/',
        target_ref='20',
        value='hello',
        description='输入文字',
    ),
]

commands = [
    CommandSuggestion(
        name='do-thing',
        description='执行操作',
        args=[],
        action_steps=[0, 1],
    )
]

explore_result = ExploreResult(
    pages=[PageInfo(url='https://qa-atomref-pure.example/', title='Pure Test')],
    actions=actions,
    commands=commands,
)

gen = AdapterGenerator(domain)
code = gen.generate(explore_result, domain)
path = save_adapter(domain, code, explore_result=explore_result)
print(path)
" 2>&1)

  if [ $? -ne 0 ]; then
    echo "[FAIL] 纯内联工作流生成失败: $OUTPUT"
    FAIL=$((FAIL+1))
    rm -rf "$PURE_DIR" 2>/dev/null || true
    return
  fi

  if grep -q 'load_atom' "$PURE_FILE"; then
    echo "[FAIL] 纯内联工作流不应包含 load_atom"
    FAIL=$((FAIL+1))
  else
    echo "[PASS] 纯内联工作流不含 load_atom"
    PASS=$((PASS+1))
  fi

  if grep -q 'json.loads(' "$PURE_FILE"; then
    echo "[PASS] 纯内联工作流保留 json.loads 内联 actions"
    PASS=$((PASS+1))
  else
    echo "[FAIL] 纯内联工作流缺少 json.loads 内联 actions"
    FAIL=$((FAIL+1))
  fi

  rm -rf "$PURE_DIR" 2>/dev/null || true
}

test_cleanup() {
  cleanup_test_data
  echo "[PASS] 清理测试数据"
  PASS=$((PASS+1))
}

echo "Running atom workflow ref tests..."
test_workflow_with_reuse_atom_generates_load_atom
test_commands_py_contains_load_atom
test_metadata_contains_atom_refs
test_inline_actions_still_generated
test_pure_inline_workflow_unchanged
test_cleanup

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
