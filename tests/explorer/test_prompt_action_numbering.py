from cliany_site.explorer.prompts import EXPLORE_PROMPT_TEMPLATE, SYSTEM_PROMPT


def test_extract_fields_must_be_observed_on_page():
    assert "不要仅因是搜索/筛选结果就添加不存在的 url、snippet" in SYSTEM_PROMPT
    assert "若某字段在页面上不存在，就省略该字段" in SYSTEM_PROMPT
    assert "可变化的结果集合应使用 list 或 table 提取" in SYSTEM_PROMPT
    assert "expects_nonempty=false 不允许空 text 掩盖提取错误" in SYSTEM_PROMPT


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
