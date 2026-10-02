from cliany_site.explorer.prompts import EXPLORE_PROMPT_TEMPLATE, SYSTEM_PROMPT


def test_explore_prompt_exposes_zero_based_action_boundary():
    prompt = EXPLORE_PROMPT_TEMPLATE.format(
        url="https://example.test",
        title="Example",
        element_tree="tree",
        selector_candidates="candidates",
        workflow_description="search",
        completed_steps="0. Type query\n1. Submit search",
        completed_action_count=2,
    )

    assert "已录制 2 个动作" in prompt
    assert "本轮 actions 的第一个动作编号是 2" in prompt
    assert "0. Type query\n1. Submit search" in prompt
    assert "commands.action_steps 必须覆盖此前及本轮的全部动作编号" in prompt
    assert "json" in SYSTEM_PROMPT.lower()


def test_explore_prompt_allows_declared_zero_match_search():
    assert "搜索、筛选" in SYSTEM_PROMPT
    assert "明确允许零匹配，设为 false" in SYSTEM_PROMPT
    assert "false 仅允许 list/table 提取真正返回空集合" in SYSTEM_PROMPT
    assert "不能掩盖空文本、空属性、字段缺失" in SYSTEM_PROMPT
