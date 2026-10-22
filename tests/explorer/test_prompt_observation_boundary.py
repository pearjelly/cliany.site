import json
import re

import pytest

from cliany_site.explorer.prompts import SYSTEM_PROMPT


@pytest.mark.parametrize("heading", [
    "示例 — 在搜索框中搜索", "示例 — 提取搜索结果列表", "示例 — 提取资讯并保存 Markdown",
])
def test_search_examples_stop_before_unobserved_result(heading):
    section = SYSTEM_PROMPT.split(heading, 1)[1].split("\n示例 —", 1)[0]
    plans = [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", section, re.DOTALL)]
    assert len(plans) == 2
    first, observed = plans
    assert first["done"] is False
    assert first["actions"] and not any(action["type"] == "extract" for action in first["actions"])
    assert observed["actions"]
    if "extract" in heading or "提取" in heading:
        assert all(action["type"] == "extract" for action in observed["actions"])
    assert "下一轮" in section and "观察" in section


def test_observation_policy_preserves_real_targets_and_indices():
    assert "不能在同一轮追加依赖新页面的 extract" in SYSTEM_PROMPT
    assert "不能向不可输入的 link 写值" in SYSTEM_PROMPT
    assert "不能添加占位动作来填补编号" in SYSTEM_PROMPT
