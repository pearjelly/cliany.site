# pyright: reportMissingImports=false
from __future__ import annotations

import pytest

from cliany_site.action_runtime import ActionExecutionError, execute_action_steps
from cliany_site.envelope import ErrorCode


class _FailingPage:
    async def evaluate(self, _expression: str):
        raise RuntimeError("page evaluation failed")


class _BrowserSession:
    async def get_current_page(self):
        return _FailingPage()


@pytest.mark.asyncio
async def test_extract_failure_is_recorded_when_continue_on_error(mocker):
    mocker.patch("cliany_site.action_runtime.asyncio.sleep", new=mocker.AsyncMock())
    extraction_results: list[dict] = []

    await execute_action_steps(
        _BrowserSession(),
        [{"type": "extract", "selector": "article.result", "extract_mode": "list"}],
        continue_on_error=True,
        extraction_results=extraction_results,
    )

    assert extraction_results[0]["ok"] is False
    assert extraction_results[0]["error"]["step_index"] == 0


@pytest.mark.asyncio
async def test_extract_failure_raises_without_continue_on_error(mocker):
    mocker.patch("cliany_site.action_runtime.asyncio.sleep", new=mocker.AsyncMock())

    with pytest.raises(ActionExecutionError, match="提取步骤失败"):
        await execute_action_steps(
            _BrowserSession(),
            [{"type": "extract", "selector": "article.result", "extract_mode": "list"}],
            extraction_results=[],
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("selector", [None, "", "  "])
async def test_extract_without_selector_is_recorded_as_failure(mocker, selector):
    mocker.patch("cliany_site.action_runtime.asyncio.sleep", new=mocker.AsyncMock())
    extraction_results: list[dict] = []

    await execute_action_steps(
        _BrowserSession(),
        [{"type": "extract", "selector": selector, "extract_mode": "list"}],
        continue_on_error=True,
        extraction_results=extraction_results,
    )

    assert extraction_results == [
        {
            "ok": False,
            "error": {
                "code": ErrorCode.E_PARSE_FAILED,
                "message": "extract 动作缺少 selector",
                "step_index": 0,
                "selector": None,
            },
        }
    ]


@pytest.mark.asyncio
async def test_extract_without_selector_raises_by_default(mocker):
    mocker.patch("cliany_site.action_runtime.asyncio.sleep", new=mocker.AsyncMock())

    with pytest.raises(ActionExecutionError, match="提取步骤失败: extract 动作缺少 selector"):
        await execute_action_steps(
            _BrowserSession(),
            [{"type": "extract", "extract_mode": "list"}],
        )
