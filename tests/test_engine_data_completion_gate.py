# pyright: reportMissingImports=false
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.errors import DataCommandQualityError
from cliany_site.explorer.engine import WorkflowExplorer, _validate_command_partition


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        cdp_port=9222,
        explore_max_steps=2,
        vision_enabled=False,
        screenshot_quality=75,
        screenshot_format="png",
        vision_som_max_labels=50,
        llm_retry_max_attempts=1,
        llm_retry_base_delay=0.01,
        llm_retry_backoff_factor=1.0,
    )


def _tree() -> dict:
    return {
        "url": "https://example.com/search",
        "title": "Example search",
        "selector_map": {"1": {"name": "Search", "role": "button", "attributes": {}}},
        "element_tree": "@1 button Search",
        "screenshot": b"",
    }


def _data_command(action_steps: list[int], *, expects_nonempty: bool = True) -> dict:
    return {
        "name": "search-results",
        "description": "提取搜索结果",
        "args": [],
        "action_steps": action_steps,
        "expects_nonempty": expects_nonempty,
    }


def _extract_action() -> dict:
    return {
        "type": "extract",
        "selector": "article.result",
        "extract_mode": "list",
        "fields": {"title": "h2", "url": "a@href", "snippet": ".snippet"},
        "description": "提取搜索结果",
    }


def _prepare(mocker, parse_results: list[dict], extraction_payloads: list[list[dict]]):
    mocker.patch("cliany_site.explorer.engine.get_config", return_value=_config())
    mocker.patch("cliany_site.explorer.engine._get_llm", return_value=SimpleNamespace(model="mock"))

    browser_session = AsyncMock()
    cdp = mocker.Mock()
    cdp.check_available = AsyncMock(return_value=True)
    cdp.connect = AsyncMock(return_value=browser_session)
    cdp.disconnect = AsyncMock()
    mocker.patch("cliany_site.explorer.engine.CDPConnection", return_value=cdp)
    mocker.patch(
        "cliany_site.explorer.engine.capture_axtree",
        new_callable=AsyncMock,
        return_value=_tree(),
    )
    invoke = mocker.patch(
        "cliany_site.explorer.engine._invoke_llm_with_retry",
        new_callable=AsyncMock,
        side_effect=[SimpleNamespace(content=f"response-{index}") for index in range(len(parse_results))],
    )
    mocker.patch("cliany_site.explorer.engine._parse_llm_response", side_effect=parse_results)

    async def execute(_session, _actions, *, extraction_results, **_kwargs):
        extraction_results.extend(extraction_payloads.pop(0))

    mocker.patch("cliany_site.explorer.engine.execute_action_steps", side_effect=execute)
    mocker.patch("cliany_site.explorer.engine.save_extract_markdown", return_value=None)
    mocker.patch("cliany_site.explorer.engine.build_atom_inventory_section", return_value="")
    mocker.patch("cliany_site.explorer.engine.format_selector_candidates_section", return_value="")
    mocker.patch("cliany_site.explorer.engine.sniff_api_endpoints", return_value=[])
    mocker.patch("cliany_site.explorer.engine.click.echo")
    return invoke


@pytest.mark.asyncio
async def test_data_command_repairs_missing_owned_extract_before_completion(mocker):
    parse_results = [
        {
            "actions": [{"type": "click", "ref": "1", "description": "打开搜索结果"}],
            "commands": [_data_command([0])],
            "done": True,
        },
        {
            "actions": [_extract_action()],
            "commands": [_data_command([0, 1])],
            "done": True,
        },
    ]
    invoke = _prepare(
        mocker,
        parse_results,
        [
            [],
            [
                {
                    "step_index": 0,
                    "extract_mode": "list",
                    "data": [
                        {
                            "title": "Result",
                            "url": "https://example.com/result",
                            "snippet": "A real result",
                        }
                    ],
                }
            ],
        ],
    )

    result = await WorkflowExplorer().explore("https://example.com/search", "搜索结果", record=False)

    assert invoke.await_count == 2
    assert result.commands[0].action_steps == [0, 1]
    second_prompt = invoke.await_args_list[1].args[1]
    assert "数据命令完成门禁" in second_prompt
    assert "search-results: missing_owned_extract" in second_prompt


@pytest.mark.asyncio
@pytest.mark.parametrize("followup_name", ["read-result", "fetch-result"])
async def test_extract_only_followup_must_include_replay_prerequisites(mocker, tmp_home, followup_name):
    actions = [
        {"type": "type", "ref": "1", "value": "Ada", "description": "输入姓名"},
        {"type": "click", "ref": "1", "description": "应用输入"},
        {"type": "extract", "selector": "output", "extract_mode": "text", "description": "读取结果"},
    ]
    split = [
        {"name": "apply-input", "args": [], "action_steps": [0, 1]},
        {"name": followup_name, "args": [], "action_steps": [2]},
    ]
    combined = [{"name": followup_name, "args": [], "action_steps": [0, 1, 2]}]
    invoke = _prepare(
        mocker,
        [
            {"actions": actions, "commands": split, "done": True},
            {"actions": [], "commands": combined, "done": True},
        ],
        [[{"step_index": 2, "extract_mode": "text", "data": {"text": "Ada"}}], []],
    )

    result = await WorkflowExplorer().explore("https://example.com/search", "输入姓名并读取结果", record=False)

    assert invoke.await_count == 2
    assert [(command.name, command.action_steps) for command in result.commands] == [
        (followup_name, [0, 1, 2]),
    ]
    repair_prompt = invoke.await_args_list[1].args[1]
    assert "missing_replay_prerequisites" in repair_prompt
    assert "从来源 URL 独立重放" in repair_prompt


@pytest.mark.asyncio
async def test_data_command_rejects_partial_extract_after_one_repair(mocker, tmp_home):
    partial_payload = [
        {
            "step_index": 0,
            "extract_mode": "list",
            "data": [{"title": "Only title", "url": "", "snippet": ""}],
        }
    ]
    parse_results = [
        {"actions": [_extract_action()], "commands": [_data_command([0])], "done": True},
        {"actions": [_extract_action()], "commands": [_data_command([1])], "done": True},
    ]
    invoke = _prepare(mocker, parse_results, [partial_payload, partial_payload])

    with pytest.raises(DataCommandQualityError) as exc_info:
        await WorkflowExplorer().explore("https://example.com/search", "搜索结果", record=False)

    assert exc_info.value.details["repair_attempts"] == 1
    failure = exc_info.value.details["data_commands"][0]
    assert failure["reason"] == "extract_quality_failed"
    assert failure["quality"]["status"] == "partial"
    repair_prompt = invoke.await_args_list[1].args[1]
    assert '"url"' in repair_prompt
    assert "若任务未要求且页面无对应值，移除这些字段" in repair_prompt


@pytest.mark.asyncio
async def test_repaired_extract_can_replace_failed_exploration_extract(mocker, tmp_home):
    corrected_extract = {
        **_extract_action(),
        "fields": {"title": "h2"},
    }
    invoke = _prepare(
        mocker,
        [
            {"actions": [_extract_action()], "commands": [_data_command([0])], "done": True},
            {"actions": [corrected_extract], "commands": [_data_command([1])], "done": True},
        ],
        [
            [{"step_index": 0, "extract_mode": "list", "data": [{"title": "Result", "url": "", "snippet": "Text"}]}],
            [{"step_index": 0, "extract_mode": "list", "data": [{"title": "Result"}]}],
        ],
    )

    result = await WorkflowExplorer().explore("https://example.com/search", "读取结果标题", record=False)

    assert result.commands[0].action_steps == [1]
    assert len(result.actions) == 2
    assert "舍弃" in invoke.await_args_list[1].args[1]


@pytest.mark.asyncio
async def test_failed_extract_partition_correction_does_not_repeat_page_actions(mocker, tmp_home):
    corrected_extract = {**_extract_action(), "fields": {"title": "h2"}}
    invoke = _prepare(
        mocker,
        [
            {"actions": [_extract_action()], "commands": [_data_command([0])], "done": True},
            {"actions": [corrected_extract], "commands": [_data_command([0, 1])], "done": True},
            {"actions": [], "commands": [_data_command([1])], "done": True},
        ],
        [
            [{"step_index": 0, "extract_mode": "list", "data": [{"title": "Result", "url": ""}]}],
            [{"step_index": 0, "extract_mode": "list", "data": [{"title": "Result"}]}],
        ],
    )
    result = await WorkflowExplorer().explore("https://example.com/search", "读取结果标题", record=False)

    assert result.commands[0].action_steps == [1]
    assert len(result.actions) == 2
    assert result.partition_repair_attempts == 1
    assert invoke.await_count == 3
    assert "已失败 extract 索引 [0] 必须舍弃" in invoke.await_args_list[2].args[1]


def test_failed_extract_exception_does_not_allow_omitting_other_actions(tmp_home):
    with pytest.raises(RuntimeError, match="命令动作分区无效"):
        _validate_command_partition(
            [{"action_steps": [2]}],
            3,
            discardable_action_indices={1},
        )


@pytest.mark.asyncio
async def test_data_command_allows_real_empty_when_expects_nonempty_is_false(mocker):
    _prepare(
        mocker,
        [{"actions": [_extract_action()], "commands": [_data_command([0], expects_nonempty=False)], "done": True}],
        [[{"step_index": 0, "extract_mode": "list", "data": []}]],
    )

    result = await WorkflowExplorer().explore("https://example.com/search", "确认零结果", record=False)

    assert [command.name for command in result.commands] == ["search-results"]
    assert result.commands[0].expects_nonempty is False


@pytest.mark.asyncio
@pytest.mark.parametrize("actions", [[], [{"type": "click", "ref": "1", "description": "打开页面"}]])
async def test_exhausted_exploration_never_returns_partial_commands(mocker, tmp_home, actions):
    invoke = _prepare(mocker, [{"actions": actions, "done": False}] * 2, [[], []])
    save = mocker.patch("cliany_site.explorer.engine.save_adapter")

    with pytest.raises(RuntimeError, match="尚未确认完成"):
        await WorkflowExplorer().explore("https://example.com/search", "打开页面", record=False)

    assert invoke.await_count == 2
    save.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("partitions", [
    [[0], [2]], [[0, 1], [1, 2]], [[0, 0], [1, 2]], [[0], [1, 3]],
    [[False], [1, 2]], [[0], ["1", 2]], [[1, 0], [2]], [[0, 1, 2], []],
    [[0, 1, 2], None], [[0, 1]],
])
async def test_invalid_command_partition_is_not_guessed(mocker, tmp_home, partitions):
    actions = [{"type": "click", "ref": "1", "description": f"步骤 {i}"} for i in range(3)]
    commands = [{"name": f"action-{i}", "action_steps": steps} for i, steps in enumerate(partitions)]
    _prepare(mocker, [
        {"actions": actions, "commands": commands, "done": True},
        {"actions": [], "commands": commands, "done": True},
    ], [[]])

    with pytest.raises(RuntimeError, match="命令动作分区无效"):
        await WorkflowExplorer().explore("https://example.com/search", "执行两个操作", record=False)


@pytest.mark.asyncio
async def test_invalid_command_partition_gets_one_nonexecuting_repair(mocker, tmp_home):
    actions = [{"type": "click", "ref": "1", "description": f"步骤 {i}"} for i in range(2)]
    invoke = _prepare(mocker, [
        {"actions": actions, "commands": [{"name": "inspect", "action_steps": [1, 0]}], "done": True},
        {"actions": [], "commands": [{"name": "inspect", "action_steps": [0, 1]}], "done": True},
    ], [[]])
    execute = mocker.patch("cliany_site.explorer.engine.execute_action_steps", new_callable=AsyncMock)

    result = await WorkflowExplorer().explore("https://example.com/search", "检查", record=False)

    assert result.commands[0].action_steps == [0, 1]
    assert result.partition_repair_attempts == 1
    assert invoke.await_count == 2
    assert execute.await_count == 1
    repair_prompt = invoke.await_args_list[1].args[1]
    assert "只修正命令分区，不要再次操作页面" in repair_prompt
    assert '"index": 0' in repair_prompt


@pytest.mark.asyncio
async def test_partition_repair_rejects_new_actions_without_execution(mocker, tmp_home):
    actions = [{"type": "click", "ref": "1", "description": "检查"}]
    _prepare(mocker, [
        {"actions": actions, "commands": [{"name": "inspect", "action_steps": [1]}], "done": True},
        {"actions": actions, "commands": [{"name": "inspect", "action_steps": [0]}], "done": True},
    ], [[]])
    execute = mocker.patch("cliany_site.explorer.engine.execute_action_steps", new_callable=AsyncMock)

    with pytest.raises(RuntimeError, match="修正响应必须完成且不得新增动作"):
        await WorkflowExplorer().explore("https://example.com/search", "检查", record=False)

    assert execute.await_count == 1


@pytest.mark.asyncio
async def test_explicit_uneven_partition_preserves_command_ownership(mocker, tmp_home):
    actions = [{"type": "click", "ref": "1", "description": f"步骤 {i}"} for i in range(3)]
    commands = [{"name": "open", "action_steps": [0]}, {"name": "apply", "action_steps": [1, 2]}]
    _prepare(mocker, [{"actions": actions, "commands": commands, "done": True}], [[]])

    result = await WorkflowExplorer().explore("https://example.com/search", "执行两个操作", record=False)

    assert [(command.name, command.action_steps) for command in result.commands] == [
        ("open", [0]), ("apply", [1, 2]),
    ]
    assert result.partition_repair_attempts == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("commands", [[], None, {}, "run-workflow"])
async def test_completed_actions_require_explicit_commands(mocker, tmp_home, commands):
    _prepare(mocker, [{
        "actions": [{"type": "click", "ref": "1", "description": "打开页面"}],
        "commands": commands, "done": True,
    }], [[]])

    with pytest.raises(RuntimeError, match="命令"):
        await WorkflowExplorer().explore("https://example.com/search", "读取数据", record=False)


@pytest.mark.asyncio
async def test_malformed_response_after_action_cannot_complete_workflow(mocker, tmp_home):
    import json

    from cliany_site.explorer.engine import _parse_llm_response

    first = {"actions": [{"type": "click", "ref": "1", "description": "打开页面"}], "done": False}
    invoke = _prepare(mocker, [first, {}], [[]])
    invoke.side_effect = [SimpleNamespace(content=json.dumps(first)), SimpleNamespace(content="broken response")]
    mocker.patch("cliany_site.explorer.engine._parse_llm_response", side_effect=_parse_llm_response)
    save = mocker.patch("cliany_site.explorer.engine.save_adapter")

    with pytest.raises(ValueError, match="解析失败"):
        await WorkflowExplorer().explore("https://example.com/search", "读取数据", record=False)

    assert invoke.await_count == 2
    save.assert_not_called()


@pytest.mark.asyncio
async def test_parameter_inference_is_scoped_to_owning_command(mocker, tmp_home):
    actions = [
        {"type": "type", "ref": "1", "value": "first"},
        {"type": "type", "ref": "1", "value": "second"},
    ]
    commands = [{"name": "first", "action_steps": [0]}, {"name": "second", "action_steps": [1]}]
    _prepare(mocker, [{"actions": actions, "commands": commands, "done": True}], [[]])

    result = await WorkflowExplorer().explore("https://example.com/search", "执行两个输入任务", record=False)

    assert [(command.args[0]["action_index"], command.args[0]["default"]) for command in result.commands] == [
        (0, "first"), (1, "second"),
    ]
    assert all(len(command.args) == 1 for command in result.commands)

    from click.testing import CliRunner

    from cliany_site.codegen.generator import AdapterGenerator, save_adapter
    from cliany_site.loader import load_adapter

    dispatched = []

    def execute(steps, *args, **kwargs):
        dispatched.append(steps)
        return []

    mocker.patch("cliany_site.codegen.runtime_helpers.execute_steps_via_atoms", side_effect=execute)
    save_adapter("example.com", AdapterGenerator().generate(result, "example.com"), explore_result=result)
    cli = load_adapter("example.com")
    assert cli is not None
    for command, value in zip(result.commands, ["changed-first", "changed-second"], strict=True):
        invocation = CliRunner().invoke(cli, [command.name, f"--{command.args[0]['name']}", value, "--json"])
        assert invocation.exit_code == 0, invocation.output
    assert [[step.get("value") for step in steps] for steps in dispatched] == [["changed-first"], ["changed-second"]]
