#!/bin/bash
PASS=0
FAIL=0

TEST_DOMAIN="qa-atomgen.example"
ADAPTER_DIR="$HOME/.cliany-site/adapters/$TEST_DOMAIN"
COMMANDS_FILE="$ADAPTER_DIR/commands.py"

cleanup_test_data() {
  rm -rf "$ADAPTER_DIR" 2>/dev/null || true
}

test_generate_atoms_subgroup() {
  cleanup_test_data

  OUTPUT=$(uv run python3 -c "
from datetime import datetime, timezone

from cliany_site.atoms import AtomCommand, AtomParameter, save_atom
from cliany_site.codegen.generator import AdapterGenerator

domain = 'qa-atomgen.example'

atom = AtomCommand(
    atom_id='fill-search-box',
    name='fill-search-box',
    description='填写搜索框并准备提交',
    domain=domain,
    parameters=[
        AtomParameter(
            name='query',
            description='搜索关键词',
            default='cliany-site',
            required=True,
        )
    ],
    actions=[
        {
            'action_type': 'type',
            'page_url': 'https://qa-atomgen.example/search',
            'target_name': 'Search Input',
            'target_role': 'textbox',
            'target_attributes': {
                'id': 'search-input',
                'name': 'q',
            },
            'value': '{{query}}',
            'description': 'ATOM_ACTION_SENTINEL_DO_NOT_INLINE',
        }
    ],
    created_at=datetime.now(timezone.utc).isoformat(),
    source_workflow='QA atom codegen workflow',
)

save_atom(atom)
path = AdapterGenerator(domain).generate_with_atoms()
print(path)
" 2>&1)

  if [ $? -ne 0 ]; then
    echo "[FAIL] 生成带 atoms 子命令的 adapter 失败: $OUTPUT"
    FAIL=$((FAIL+1))
    return
  fi

  if [ ! -f "$COMMANDS_FILE" ]; then
    echo "[FAIL] commands.py 未生成: $COMMANDS_FILE"
    FAIL=$((FAIL+1))
    return
  fi

  if grep -q 'click.Group("atoms", help="原子命令")' "$COMMANDS_FILE" && grep -q '@atoms_group.command("fill-search-box")' "$COMMANDS_FILE"; then
    echo "[PASS] atoms 子命令组与 atom 命令已生成: $OUTPUT"
    PASS=$((PASS+1))
  else
    echo "[FAIL] commands.py 缺少 atoms 子命令组或 atom 命令"
    FAIL=$((FAIL+1))
  fi
}

test_runtime_atom_loading_not_hardcoded() {
  if grep -q 'from cliany_site.atoms.storage import load_atom' "$COMMANDS_FILE" && grep -q 'load_atom(DOMAIN, ' "$COMMANDS_FILE"; then
    echo "[PASS] commands.py 使用 load_atom 运行时加载原子"
    PASS=$((PASS+1))
  else
    echo "[FAIL] commands.py 未使用 load_atom 运行时加载原子"
    FAIL=$((FAIL+1))
  fi

  if grep -q 'ATOM_ACTION_SENTINEL_DO_NOT_INLINE' "$COMMANDS_FILE" || grep -q '{{query}}' "$COMMANDS_FILE"; then
    echo "[FAIL] commands.py 疑似内联了原子 action 字面量"
    FAIL=$((FAIL+1))
  else
    echo "[PASS] commands.py 未内联原子 action 字面量"
    PASS=$((PASS+1))
  fi
}

test_substitute_parameters() {
  OUTPUT=$(uv run python3 -c "
from cliany_site.action_runtime import substitute_parameters

actions = [
    {
        'type': 'type',
        'value': '{{query}}',
        'url': 'https://qa-atomgen.example/search?q={{query}}',
        'description': '输入 {{query}}',
        'target_name': '{{query}} 输入框',
    }
]
params = {'query': 'cliany-site'}

resolved = substitute_parameters(actions, params)
assert resolved[0]['value'] == 'cliany-site'
assert resolved[0]['url'] == 'https://qa-atomgen.example/search?q=cliany-site'
assert resolved[0]['description'] == '输入 cliany-site'
assert resolved[0]['target_name'] == 'cliany-site 输入框'

# 不应修改原始输入
assert actions[0]['value'] == '{{query}}'

print(resolved[0]['value'])
" 2>&1)

  if [ $? -eq 0 ]; then
    echo "[PASS] substitute_parameters 参数替换正确: $OUTPUT"
    PASS=$((PASS+1))
  else
    echo "[FAIL] substitute_parameters 参数替换失败: $OUTPUT"
    FAIL=$((FAIL+1))
  fi
}

test_cleanup() {
  cleanup_test_data
  echo "[PASS] 清理测试数据"
  PASS=$((PASS+1))
}

echo "Running atom codegen tests..."
test_generate_atoms_subgroup
test_runtime_atom_loading_not_hardcoded
test_substitute_parameters
test_cleanup

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
