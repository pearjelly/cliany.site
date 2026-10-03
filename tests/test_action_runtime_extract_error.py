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
async def test_extract_preflight_failure_propagates_with_continue_on_error(mocker):
    page = mocker.AsyncMock()
    session = mocker.AsyncMock()
    session.get_current_page.return_value = page

    async def reject(_session, _action, _index):
        raise ValueError("selector not grounded")

    with pytest.raises(ValueError, match="selector not grounded"):
        await execute_action_steps(
            session,
            [{"type": "extract", "selector": "#guessed", "extract_mode": "text"}],
            continue_on_error=True,
            before_extract=reject,
        )

    page.evaluate.assert_not_awaited()


@pytest.mark.asyncio
async def test_extract_failure_is_recorded_when_continue_on_error(mocker):
    mocker.patch("cliany_site.action_runtime.asyncio.sleep", new=mocker.AsyncMock())
    mocker.patch("cliany_site.action_runtime._wait_for_list_settle", new=mocker.AsyncMock(return_value=True))
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
    mocker.patch("cliany_site.action_runtime._wait_for_list_settle", new=mocker.AsyncMock(return_value=True))

    with pytest.raises(ActionExecutionError, match="提取步骤失败"):
        await execute_action_steps(
            _BrowserSession(),
            [{"type": "extract", "selector": "article.result", "extract_mode": "list"}],
            extraction_results=[],
        )


@pytest.mark.asyncio
async def test_list_settle_failure_is_recorded_as_page_not_ready():
    extraction_results: list[dict] = []

    await execute_action_steps(
        _BrowserSession(),
        [{"type": "extract", "selector": "article.result", "extract_mode": "list"}],
        continue_on_error=True,
        extraction_results=extraction_results,
    )

    assert extraction_results[0]["ok"] is False
    assert extraction_results[0]["error"]["code"] == ErrorCode.E_PAGE_NOT_READY


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
