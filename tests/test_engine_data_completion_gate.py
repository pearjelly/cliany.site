# pyright: reportMissingImports=false
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.errors import DataCommandQualityError
from cliany_site.explorer.engine import WorkflowExplorer


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
async def test_data_command_rejects_partial_extract_after_one_repair(mocker):
    partial_payload = [
        {
            "step_index": 0,
            "extract_mode": "list",
            "data": [{"title": "Only title", "url": "", "snippet": ""}],
        }
    ]
    parse_results = [
        {"actions": [_extract_action()], "commands": [_data_command([0])], "done": True},
        {"actions": [_extract_action()], "commands": [_data_command([0, 1])], "done": True},
    ]
    _prepare(mocker, parse_results, [partial_payload, partial_payload])

    with pytest.raises(DataCommandQualityError) as exc_info:
        await WorkflowExplorer().explore("https://example.com/search", "搜索结果", record=False)

    assert exc_info.value.details["repair_attempts"] == 1
    failure = exc_info.value.details["data_commands"][0]
    assert failure["reason"] == "extract_quality_failed"
    assert failure["quality"]["status"] == "partial"


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
