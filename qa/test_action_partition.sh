#!/bin/bash
# action_steps 分区验证测试
# 覆盖 4 个场景：多命令有效分区 → 单命令回退 → 无效分区回退分配 → 越界索引过滤
PASS=0
FAIL=0

# ─────────────────────────────────────────────────────────────────────────────
# 场景 1：多命令，LLM 提供有效 action_steps
# ─────────────────────────────────────────────────────────────────────────────
echo "=== 场景 1：多命令 + 有效 action_steps ==="

OUTPUT=$(uv run python3 -c "
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult

actions = [
    ActionStep(action_type='click', page_url='https://example.com/', description='step0'),
    ActionStep(action_type='type', page_url='https://example.com/', description='step1'),
    ActionStep(action_type='submit', page_url='https://example.com/', description='step2'),
    ActionStep(action_type='click', page_url='https://example.com/results', description='step3'),
    ActionStep(action_type='type', page_url='https://example.com/results', description='step4'),
    ActionStep(action_type='submit', page_url='https://example.com/results', description='step5'),
]

commands = [
    CommandSuggestion(name='login', description='登录', args=[], action_steps=[0, 1, 2]),
    CommandSuggestion(name='search', description='搜索', args=[], action_steps=[3, 4, 5]),
]

result = ExploreResult(actions=actions, commands=commands)

assert result.commands[0].name == 'login'
assert result.commands[0].action_steps == [0, 1, 2], f'expected [0,1,2] got {result.commands[0].action_steps}'
assert result.commands[1].name == 'search'
assert result.commands[1].action_steps == [3, 4, 5], f'expected [3,4,5] got {result.commands[1].action_steps}'

all_indices = set(range(len(actions)))
assigned = set()
for cmd in result.commands:
    assigned.update(cmd.action_steps)
assert assigned == all_indices, f'coverage mismatch: assigned={assigned} expected={all_indices}'

print(f'ok login_steps={result.commands[0].action_steps} search_steps={result.commands[1].action_steps}')
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景1: 多命令有效分区: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景1: 多命令有效分区: $OUTPUT"
  PASS=$((PASS+1))
fi

# ─────────────────────────────────────────────────────────────────────────────
# 场景 2：单命令，LLM 未提供 action_steps → 回退为全部索引
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== 场景 2：单命令，无 action_steps → 回退全范围 ==="

OUTPUT=$(uv run python3 -c "
import json
from cliany_site.explorer.engine import WorkflowExplorer
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult

actions = [
    ActionStep(action_type='click', page_url='https://example.com/', description='step0'),
    ActionStep(action_type='type', page_url='https://example.com/', description='step1'),
    ActionStep(action_type='submit', page_url='https://example.com/', description='step2'),
]

parsed_commands = [
    {'name': 'run-it', 'description': '执行工作流', 'args': []}
]

result = ExploreResult(actions=actions)

commands_data = parsed_commands
for cmd_data in commands_data:
    raw_action_steps = cmd_data.get('action_steps')
    if isinstance(raw_action_steps, list):
        action_steps = [
            idx for idx in raw_action_steps
            if isinstance(idx, int) and 0 <= idx < len(result.actions)
        ]
    else:
        action_steps = []

    cmd = CommandSuggestion(
        name=cmd_data.get('name', 'command'),
        description=cmd_data.get('description', ''),
        args=cmd_data.get('args', []),
        action_steps=action_steps,
    )
    result.commands.append(cmd)

all_action_indices = set(range(len(result.actions)))
assigned_indices = set()
for cmd in result.commands:
    assigned_indices.update(cmd.action_steps)

if assigned_indices != all_action_indices:
    if len(result.commands) == 1:
        result.commands[0].action_steps = list(range(len(result.actions)))
    else:
        total = len(result.actions)
        n_cmds = len(result.commands)
        per_cmd = total // n_cmds if n_cmds else total
        start = 0
        for i, cmd in enumerate(result.commands):
            end = start + per_cmd if i < n_cmds - 1 else total
            cmd.action_steps = list(range(start, end))
            start = end

assert len(result.commands) == 1
assert result.commands[0].action_steps == [0, 1, 2], f'expected [0,1,2] got {result.commands[0].action_steps}'
print(f'ok single_cmd_steps={result.commands[0].action_steps}')
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景2: 单命令回退全范围: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景2: 单命令回退全范围: $OUTPUT"
  PASS=$((PASS+1))
fi

# ─────────────────────────────────────────────────────────────────────────────
# 场景 3：多命令，LLM 未提供 action_steps → 回退均匀分配
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== 场景 3：多命令，无 action_steps → 回退均匀分配 ==="

OUTPUT=$(uv run python3 -c "
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult

actions = [
    ActionStep(action_type='click', page_url='https://example.com/', description='step0'),
    ActionStep(action_type='type', page_url='https://example.com/', description='step1'),
    ActionStep(action_type='submit', page_url='https://example.com/', description='step2'),
    ActionStep(action_type='click', page_url='https://example.com/p2', description='step3'),
    ActionStep(action_type='type', page_url='https://example.com/p2', description='step4'),
    ActionStep(action_type='submit', page_url='https://example.com/p2', description='step5'),
]

parsed_commands = [
    {'name': 'cmd-a', 'description': 'A', 'args': []},
    {'name': 'cmd-b', 'description': 'B', 'args': []},
]

result = ExploreResult(actions=actions)

for cmd_data in parsed_commands:
    raw = cmd_data.get('action_steps')
    if isinstance(raw, list):
        steps = [i for i in raw if isinstance(i, int) and 0 <= i < len(result.actions)]
    else:
        steps = []
    result.commands.append(
        CommandSuggestion(
            name=cmd_data['name'], description=cmd_data['description'],
            args=[], action_steps=steps,
        )
    )

all_action_indices = set(range(len(result.actions)))
assigned_indices = set()
for cmd in result.commands:
    assigned_indices.update(cmd.action_steps)

if assigned_indices != all_action_indices:
    if len(result.commands) == 1:
        result.commands[0].action_steps = list(range(len(result.actions)))
    else:
        total = len(result.actions)
        n_cmds = len(result.commands)
        per_cmd = total // n_cmds if n_cmds else total
        start = 0
        for i, cmd in enumerate(result.commands):
            end = start + per_cmd if i < n_cmds - 1 else total
            cmd.action_steps = list(range(start, end))
            start = end

assigned_after = set()
for cmd in result.commands:
    assigned_after.update(cmd.action_steps)

assert assigned_after == all_action_indices, f'fallback coverage mismatch: {assigned_after}'
assert result.commands[0].action_steps == [0, 1, 2], f'cmd-a steps={result.commands[0].action_steps}'
assert result.commands[1].action_steps == [3, 4, 5], f'cmd-b steps={result.commands[1].action_steps}'
print(f'ok cmd_a={result.commands[0].action_steps} cmd_b={result.commands[1].action_steps}')
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景3: 多命令无分区回退均匀分配: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景3: 多命令无分区回退均匀分配: $OUTPUT"
  PASS=$((PASS+1))
fi

# ─────────────────────────────────────────────────────────────────────────────
# 场景 4：含越界索引的 action_steps → 过滤后触发回退
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== 场景 4：越界索引过滤 + 回退 ==="

OUTPUT=$(uv run python3 -c "
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult

actions = [
    ActionStep(action_type='click', page_url='https://example.com/', description='step0'),
    ActionStep(action_type='type', page_url='https://example.com/', description='step1'),
    ActionStep(action_type='submit', page_url='https://example.com/', description='step2'),
]

parsed_commands = [
    {'name': 'cmd-x', 'description': 'X', 'args': [], 'action_steps': [0, 1, 99, -1, 2]},
]

result = ExploreResult(actions=actions)

for cmd_data in parsed_commands:
    raw = cmd_data.get('action_steps')
    if isinstance(raw, list):
        steps = [i for i in raw if isinstance(i, int) and 0 <= i < len(result.actions)]
    else:
        steps = []
    result.commands.append(
        CommandSuggestion(
            name=cmd_data['name'], description=cmd_data['description'],
            args=[], action_steps=steps,
        )
    )

all_action_indices = set(range(len(result.actions)))
assigned_indices = set()
for cmd in result.commands:
    assigned_indices.update(cmd.action_steps)

if assigned_indices != all_action_indices:
    if len(result.commands) == 1:
        result.commands[0].action_steps = list(range(len(result.actions)))
    else:
        total = len(result.actions)
        n_cmds = len(result.commands)
        per_cmd = total // n_cmds if n_cmds else total
        start = 0
        for i, cmd in enumerate(result.commands):
            end = start + per_cmd if i < n_cmds - 1 else total
            cmd.action_steps = list(range(start, end))
            start = end

assert result.commands[0].action_steps == [0, 1, 2], \
    f'expected full fallback [0,1,2] got {result.commands[0].action_steps}'
print(f'ok out_of_range_filtered_and_fallback_applied steps={result.commands[0].action_steps}')
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景4: 越界索引过滤+回退: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景4: 越界索引过滤+回退: $OUTPUT"
  PASS=$((PASS+1))
fi

# ─────────────────────────────────────────────────────────────────────────────
# 汇总
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
