import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cliany_site.explorer.interactive import InteractiveController
from cliany_site.explorer.models import ExploreResult, PageInfo, TurnSnapshot


def _make_snapshot(actions=1, pages=1):
    return TurnSnapshot(
        turn_index=0,
        actions_before_count=actions,
        pages_before_count=pages,
        browser_history_index=0,
    )


def _make_result(pages=1):
    result = ExploreResult()
    for i in range(pages):
        result.pages.append(PageInfo(url=f"https://example.com/page{i}", title=f"Page {i}"))
    return result


def _make_controller():
    return InteractiveController(console=MagicMock())


@pytest.mark.asyncio
async def test_browser_back_failure_logs_step_context(caplog):
    controller = _make_controller()
    snapshot = _make_snapshot(actions=2, pages=1)
    result = _make_result(pages=1)
    browser_session = MagicMock()

    with patch.object(
        controller,
        "_try_browser_back",
        new=AsyncMock(side_effect=RuntimeError("cdp failed")),
    ):
        with patch(
            "cliany_site.explorer.interactive.capture_axtree",
            new=AsyncMock(),
        ):
            with caplog.at_level(logging.WARNING, logger="cliany_site.explorer.interactive"):
                await controller.handle_rollback(snapshot, result, browser_session)

    matching = [r for r in caplog.records if getattr(r, "step", None) == "browser_back"]
    assert matching, "期望找到 step='browser_back' 的日志记录，但未找到"
    assert "cdp failed" in matching[0].getMessage()


@pytest.mark.asyncio
async def test_capture_axtree_failure_logs_step_context(caplog):
    controller = _make_controller()
    snapshot = _make_snapshot(actions=2, pages=1)
    result = _make_result(pages=1)
    browser_session = MagicMock()

    with patch.object(
        controller,
        "_try_browser_back",
        new=AsyncMock(),
    ):
        with patch(
            "cliany_site.explorer.interactive.capture_axtree",
            new=AsyncMock(side_effect=RuntimeError("axtree error")),
        ):
            with caplog.at_level(logging.WARNING, logger="cliany_site.explorer.interactive"):
                await controller.handle_rollback(snapshot, result, browser_session)

    matching = [r for r in caplog.records if getattr(r, "step", None) == "capture_axtree"]
    assert matching, "期望找到 step='capture_axtree' 的日志记录，但未找到"
    assert "axtree error" in matching[0].getMessage()


@pytest.mark.asyncio
async def test_mark_rolled_back_failure_logs_step_context(caplog):
    controller = _make_controller()
    snapshot = _make_snapshot(actions=2, pages=1)
    result = _make_result(pages=1)
    browser_session = MagicMock()

    recording_manager = MagicMock()
    recording_manager.mark_rolled_back.side_effect = RuntimeError("recording error")
    recording_manifest = MagicMock()

    with patch.object(controller, "_try_browser_back", new=AsyncMock()):
        with patch("cliany_site.explorer.interactive.capture_axtree", new=AsyncMock()):
            with caplog.at_level(logging.WARNING, logger="cliany_site.explorer.interactive"):
                await controller.handle_rollback(
                    snapshot,
                    result,
                    browser_session,
                    recording_manager=recording_manager,
                    recording_manifest=recording_manifest,
                )

    matching = [r for r in caplog.records if getattr(r, "step", None) == "mark_rolled_back"]
    assert matching, "期望找到 step='mark_rolled_back' 的日志记录，但未找到"


@pytest.mark.asyncio
async def test_log_url_context_is_fallback_url(caplog):
    controller = _make_controller()
    snapshot = _make_snapshot(actions=2, pages=1)
    result = _make_result(pages=1)
    expected_url = result.pages[0].url
    browser_session = MagicMock()

    with patch.object(
        controller,
        "_try_browser_back",
        new=AsyncMock(side_effect=RuntimeError("cdp failed")),
    ):
        with patch("cliany_site.explorer.interactive.capture_axtree", new=AsyncMock()):
            with caplog.at_level(logging.WARNING, logger="cliany_site.explorer.interactive"):
                await controller.handle_rollback(snapshot, result, browser_session)

    matching = [r for r in caplog.records if getattr(r, "step", None) == "browser_back"]
    assert matching, "期望找到 step='browser_back' 的日志记录"
    assert getattr(matching[0], "url", None) == expected_url
