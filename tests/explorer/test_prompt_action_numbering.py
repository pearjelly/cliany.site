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
