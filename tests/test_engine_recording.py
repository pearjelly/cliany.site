# pyright: reportMissingImports=false
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cliany_site.explorer.engine import WorkflowExplorer


def _make_config(max_steps: int) -> SimpleNamespace:
    return SimpleNamespace(
        cdp_port=9222,
        explore_max_steps=max_steps,
        vision_enabled=False,
        screenshot_quality=75,
        screenshot_format="png",
        vision_som_max_labels=50,
        llm_retry_max_attempts=1,
        llm_retry_base_delay=0.01,
        llm_retry_backoff_factor=1.0,
    )


def _make_tree() -> dict:
    return {
        "url": "https://example.com/start",
        "title": "示例页面",
        "selector_map": {
            "1": {
                "name": "搜索按钮",
                "role": "button",
                "attributes": {},
            }
        },
        "element_tree": "@1 button 搜索按钮",
        "screenshot": b"",
    }


def _prepare_explore_mocks(
    mocker,
    *,
    parse_results: list[dict],
    recording_manager: MagicMock | None = None,
    execute_side_effect: Exception | None = None,
) -> dict:
    cfg = _make_config(max_steps=max(len(parse_results), 1) + 2)
    mocker.patch("cliany_site.explorer.engine.get_config", return_value=cfg)
    mocker.patch("cliany_site.explorer.engine._get_llm", return_value=SimpleNamespace(model="mock-model"))

    browser_session = AsyncMock()
    browser_session.navigate_to = AsyncMock()

    cdp_instance = mocker.Mock()
    cdp_instance.check_available = AsyncMock(return_value=True)
    cdp_instance.connect = AsyncMock(return_value=browser_session)
    cdp_instance.disconnect = AsyncMock()
    mocker.patch("cliany_site.explorer.engine.CDPConnection", return_value=cdp_instance)

    capture_axtree_mock = mocker.patch(
        "cliany_site.explorer.engine.capture_axtree",
        new_callable=AsyncMock,
        return_value=_make_tree(),
    )
    capture_screenshot_mock = mocker.patch(
        "cliany_site.explorer.engine.capture_screenshot",
        new_callable=AsyncMock,
        return_value=b"fake-png",
    )

    invoke_responses = [SimpleNamespace(content=f"response-{idx}") for idx, _ in enumerate(parse_results)]
    mocker.patch(
        "cliany_site.explorer.engine._invoke_llm_with_retry",
        new_callable=AsyncMock,
        side_effect=invoke_responses,
    )
    mocker.patch("cliany_site.explorer.engine._parse_llm_response", side_effect=parse_results)

    execute_mock = mocker.patch(
        "cliany_site.explorer.engine.execute_action_steps",
        new_callable=AsyncMock,
    )
    if execute_side_effect is not None:
        execute_mock.side_effect = execute_side_effect

    mocker.patch("cliany_site.explorer.engine.save_extract_markdown", return_value=None)
    mocker.patch("cliany_site.explorer.engine.build_atom_inventory_section", return_value="")
    mocker.patch("cliany_site.explorer.engine.format_selector_candidates_section", return_value="")
    mocker.patch("cliany_site.explorer.engine.click.echo")

    recording_class_mock = mocker.patch("cliany_site.explorer.recording.RecordingManager")
    if recording_manager is not None:
        recording_class_mock.return_value = recording_manager

    return {
        "capture_axtree": capture_axtree_mock,
        "capture_screenshot": capture_screenshot_mock,
        "recording_class": recording_class_mock,
        "execute": execute_mock,
    }


def _one_step_done_result() -> list[dict]:
    return [
        {
            "actions": [
                {
                    "type": "click",
                    "ref": "1",
                    "description": "点击搜索按钮",
                }
            ],
            "commands": [
                {
                    "name": "search",
                    "description": "搜索",
                    "args": [],
                    "action_steps": [0],
                }
            ],
            "done": True,
            "next_url": "",
        }
    ]


class TestWorkflowExplorerRecording:
    @pytest.mark.asyncio
    async def test_step_limit_finalizes_recording_as_incomplete(self, mocker, tmp_home):
        manager = MagicMock()
        manifest = manager.start_recording.return_value
        _prepare_explore_mocks(
            mocker, parse_results=[{"actions": [], "done": False}], recording_manager=manager,
        )
        mocker.patch("cliany_site.explorer.engine.get_config", return_value=_make_config(1))

        with pytest.raises(RuntimeError, match="尚未确认完成"):
            await WorkflowExplorer().explore("https://example.com/start", "测试工作流", record=True)

        manager.finalize.assert_called_once_with(manifest, completed=False)

    @pytest.mark.asyncio
    async def test_record_true_calls_start_recording(self, mocker):
        recording_manager = MagicMock()
        recording_manager.start_recording.return_value = MagicMock()
        _prepare_explore_mocks(
            mocker,
            parse_results=_one_step_done_result(),
            recording_manager=recording_manager,
        )

        explorer = WorkflowExplorer()
        await explorer.explore("https://example.com/start", "测试工作流", record=True)

        recording_manager.start_recording.assert_called_once()
        domain, start_url, workflow, session_id = recording_manager.start_recording.call_args.args
        assert domain == "example.com"
        assert start_url == "https://example.com/start"
        assert workflow == "测试工作流"
        assert isinstance(session_id, str)
        assert session_id.startswith("sess-")

    @pytest.mark.asyncio
    async def test_save_step_called_after_each_step(self, mocker):
        recording_manager = MagicMock()
        recording_manager.start_recording.return_value = MagicMock()
        parse_results = [
            {
                "actions": [{"type": "click", "ref": "1", "description": "第一步点击"}],
                "commands": [],
                "done": False,
                "next_url": "",
            },
            {
                "actions": [{"type": "click", "ref": "1", "description": "第二步点击"}],
                "commands": [
                    {
                        "name": "search",
                        "description": "搜索",
                        "args": [],
                        "action_steps": [0, 1],
                    }
                ],
                "done": True,
                "next_url": "",
            },
        ]
        _prepare_explore_mocks(mocker, parse_results=parse_results, recording_manager=recording_manager)

        explorer = WorkflowExplorer()
        await explorer.explore("https://example.com/start", "两步工作流", record=True)

        assert recording_manager.save_step.call_count == 2
        step_indices = [call.kwargs["step_record"].step_index for call in recording_manager.save_step.call_args_list]
        assert step_indices == [0, 1]

    @pytest.mark.asyncio
    async def test_finalize_completed_true_on_success(self, mocker):
        recording_manager = MagicMock()
        recording_manager.start_recording.return_value = MagicMock()
        _prepare_explore_mocks(
            mocker,
            parse_results=_one_step_done_result(),
            recording_manager=recording_manager,
        )

        explorer = WorkflowExplorer()
        await explorer.explore("https://example.com/start", "测试 finalize", record=True)

        recording_manager.finalize.assert_called_once()
        assert recording_manager.finalize.call_args.kwargs["completed"] is True

    @pytest.mark.asyncio
    async def test_save_step_ioerror_does_not_interrupt_explore(self, mocker):
        recording_manager = MagicMock()
        recording_manager.start_recording.return_value = MagicMock()
        recording_manager.save_step.side_effect = IOError("disk full")
        _prepare_explore_mocks(
            mocker,
            parse_results=_one_step_done_result(),
            recording_manager=recording_manager,
        )

        explorer = WorkflowExplorer()
        result = await explorer.explore("https://example.com/start", "录像失败降级", record=True)

        assert len(result.actions) == 1
        recording_manager.finalize.assert_called_once()
        assert recording_manager.finalize.call_args.kwargs["completed"] is True

    @pytest.mark.asyncio
    async def test_record_false_does_not_instantiate_recording_manager(self, mocker):
        mocks = _prepare_explore_mocks(mocker, parse_results=_one_step_done_result())

        explorer = WorkflowExplorer()
        await explorer.explore("https://example.com/start", "关闭录像", record=False)

        mocks["recording_class"].assert_not_called()
        assert mocks["capture_screenshot"].await_count == 0

    @pytest.mark.asyncio
    async def test_exception_path_finalize_completed_false(self, mocker):
        recording_manager = MagicMock()
        recording_manager.start_recording.return_value = MagicMock()
        _prepare_explore_mocks(
            mocker,
            parse_results=_one_step_done_result(),
            recording_manager=recording_manager,
            execute_side_effect=RuntimeError("执行动作失败"),
        )

        explorer = WorkflowExplorer()
        with pytest.raises(RuntimeError, match="执行动作失败"):
            await explorer.explore("https://example.com/start", "异常路径", record=True)

        recording_manager.finalize.assert_called_once()
        assert recording_manager.finalize.call_args.kwargs["completed"] is False
