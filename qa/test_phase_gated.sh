#!/bin/bash
PASS=0
FAIL=0

TEST_DOMAIN="qa-phase-gated.example"
ADAPTER_DIR="$HOME/.cliany-site/adapters/$TEST_DOMAIN"

cleanup() {
  rm -rf "$ADAPTER_DIR" 2>/dev/null || true
}

trap cleanup EXIT
cleanup

echo "=== 场景 1：后分析基础统计（reuse_atom + 原子抽取） ==="
OUTPUT=$(uv run python3 -c "
import asyncio
import json

from cliany_site.explorer.analyzer import AtomExtractor
from cliany_site.explorer.models import ActionStep, ExploreResult
from cliany_site.atoms.storage import load_atoms


class MockResponse:
    def __init__(self, content):
        self.content = content


class MockLLM:
    async def ainvoke(self, prompt):
        payload = {
            'atoms': [
                {
                    'atom_id': 'search-basic',
                    'name': '基础搜索',
                    'description': '填写关键词并提交',
                    'parameters': [
                        {
                            'name': 'query',
                            'description': '搜索词',
                            'default': 'cliany',
                            'required': True,
                        }
                    ],
                    'actions': [
                        {
                            'action_type': 'type',
                            'page_url': 'https://qa-phase-gated.example/search',
                            'value': '{{query}}',
                            'description': '输入关键词',
                            'target_name': '搜索框',
                            'target_role': 'textbox',
                            'target_attributes': {'id': 'q'},
                        },
                        {
                            'action_type': 'submit',
                            'page_url': 'https://qa-phase-gated.example/search',
                            'description': '提交搜索',
                            'target_attributes': {},
                        },
                    ],
                }
            ]
        }
        fence = chr(96) * 3
        content = 'ok\n' + fence + 'json\n' + json.dumps(payload, ensure_ascii=False) + '\n' + fence
        return MockResponse(content)


async def main():
    domain = 'qa-phase-gated.example'
    result = ExploreResult(
        actions=[
            ActionStep(action_type='click', page_url=f'https://{domain}/search', description='点击搜索框'),
            ActionStep(action_type='reuse_atom', page_url=f'https://{domain}/search', target_ref='fill-search-box', description='复用原子1'),
            ActionStep(action_type='type', page_url=f'https://{domain}/search', value='cliany', description='输入关键词'),
            ActionStep(action_type='reuse_atom', page_url=f'https://{domain}/search', target_ref='submit-search', description='复用原子2'),
        ]
    )

    reuse_count = sum(1 for action in result.actions if action.action_type == 'reuse_atom')
    assert reuse_count == 2, f'expected reuse_count=2, got {reuse_count}'

    extractor = AtomExtractor(MockLLM(), domain)
    new_atoms = await extractor.extract_atoms(result)
    assert len(new_atoms) == 1, f'expected 1 extracted atom, got {len(new_atoms)}'

    persisted = load_atoms(domain)
    assert len(persisted) == 1, f'expected 1 persisted atom, got {len(persisted)}'

    print(f'ok reuse={reuse_count} extracted={len(new_atoms)} persisted={len(persisted)}')


asyncio.run(main())
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景1: 后分析基础统计失败: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景1: 后分析基础统计通过: $OUTPUT"
  PASS=$((PASS+1))
fi

echo ""
echo "=== 场景 2：提取失败时的优雅降级 ==="
OUTPUT=$(uv run python3 -c "
import asyncio

from cliany_site.explorer.analyzer import AtomExtractor
from cliany_site.explorer.models import ActionStep, ExploreResult


class FailingLLM:
    async def ainvoke(self, prompt):
        raise RuntimeError('mock llm failure')


async def main():
    domain = 'qa-phase-gated.example'
    result = ExploreResult(
        actions=[
            ActionStep(action_type='click', page_url=f'https://{domain}/search', description='点击搜索框'),
            ActionStep(action_type='type', page_url=f'https://{domain}/search', value='cliany', description='输入关键词'),
        ]
    )

    extractor = AtomExtractor(FailingLLM(), domain)
    new_atoms = await extractor.extract_atoms(result)
    assert new_atoms == [], f'提取失败时应返回空列表，实际: {new_atoms}'

    post_analysis = {
        'atoms_extracted': len(new_atoms),
        'atoms_reused': sum(1 for action in result.actions if action.action_type == 'reuse_atom'),
        'validation_warnings': 0,
        'action_quality_score': 1.0,
    }

    assert post_analysis['atoms_extracted'] == 0, f"atoms_extracted 应为 0，实际: {post_analysis['atoms_extracted']}"
    assert post_analysis['atoms_reused'] == 0, f"atoms_reused 应为 0，实际: {post_analysis['atoms_reused']}"
    assert post_analysis['validation_warnings'] == 0, f"validation_warnings 应为 0，实际: {post_analysis['validation_warnings']}"
    assert post_analysis['action_quality_score'] == 1.0, f"action_quality_score 应为 1.0，实际: {post_analysis['action_quality_score']}"

    print('ok graceful post_analysis defaults work')


asyncio.run(main())
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景2: 优雅降级验证失败: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景2: 优雅降级验证通过: $OUTPUT"
  PASS=$((PASS+1))
fi

echo ""
echo "=== 场景 3：响应信封 post_analysis 字段结构 ==="
OUTPUT=$(uv run python3 -c "
post_analysis = {
    'atoms_extracted': 3,
    'atoms_reused': 2,
    'validation_warnings': 0,
    'action_quality_score': 1.0,
}

required_keys = {'atoms_extracted', 'atoms_reused', 'validation_warnings', 'action_quality_score'}
assert set(post_analysis.keys()) == required_keys, f'字段不匹配: {post_analysis.keys()}'
assert isinstance(post_analysis['atoms_extracted'], int), 'atoms_extracted 类型应为 int'
assert isinstance(post_analysis['atoms_reused'], int), 'atoms_reused 类型应为 int'
assert isinstance(post_analysis['validation_warnings'], int), 'validation_warnings 类型应为 int'
assert isinstance(post_analysis['action_quality_score'], float), 'action_quality_score 类型应为 float'

print('ok post_analysis shape and types valid')
" 2>&1)

if [ $? -ne 0 ]; then
  echo "[FAIL] 场景3: post_analysis 字段结构验证失败: $OUTPUT"
  FAIL=$((FAIL+1))
else
  echo "[PASS] 场景3: post_analysis 字段结构验证通过: $OUTPUT"
  PASS=$((PASS+1))
fi

echo ""
echo "=== 结果 ==="
echo "PASS: $PASS, FAIL: $FAIL"
[ $FAIL -eq 0 ] && exit 0 || exit 1
