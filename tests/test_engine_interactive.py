# pyright: reportMissingImports=false
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cliany_site.explorer.engine import WorkflowExplorer
from cliany_site.explorer.interactive import DecisionType, InteractiveDecision
from tests.test_engine_recording import _prepare_explore_mocks


def _done_result_with_actions(actions: list[dict], action_steps: list[int] | None = None) -> dict:
    return {
        "actions": actions,
        "commands": [
            {
                "name": "search",
                "description": "搜索",
                "args": [],
                "action_steps": action_steps if action_steps is not None else list(range(len(actions))),
            }
        ],
        "done": True,
        "next_url": "",
    }


class TestWorkflowExplorerInteractive:
    @pytest.mark.asyncio
    async def test_interactive_false_does_not_instantiate_controller(self, mocker):
        parse_results = [
            _done_result_with_actions(
                [{"type": "click", "ref": "1", "description": "点击"}],
                [0],
            )
        ]
        _prepare_explore_mocks(mocker, parse_results=parse_results)
        interactive_cls = mocker.patch("cliany_site.explorer.interactive.InteractiveController")

        explorer = WorkflowExplorer(interactive=False)
        await explorer.explore("https://example.com/start", "非交互模式", record=False)

        interactive_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_interactive_confirm_executes_all_actions(self, mocker):
        parse_results = [
            _done_result_with_actions(
                [{"type": "click", "ref": "1", "description": "点击"}],
                [0],
            )
        ]
        mocks = _prepare_explore_mocks(mocker, parse_results=parse_results)

        interactive_ctrl = MagicMock()
        interactive_ctrl.prompt_action_confirmation = AsyncMock(
            return_value=InteractiveDecision(decision_type=DecisionType.CONFIRM)
        )
        interactive_ctrl.ask_continue_after_done = None
        mocker.patch(
            "cliany_site.explorer.interactive.InteractiveController",
            return_value=interactive_ctrl,
        )

        explorer = WorkflowExplorer(interactive=True)
        result = await explorer.explore("https://example.com/start", "确认执行", record=False)

        interactive_ctrl.prompt_action_confirmation.assert_awaited_once()
        mocks["execute"].assert_awaited_once()
        assert len(result.actions) == 1

    @pytest.mark.asyncio
    async def test_interactive_skip_does_not_record_or_execute_step_actions(self, mocker):
        parse_results = [
            _done_result_with_actions(
                [{"type": "click", "ref": "1", "description": "将被跳过"}],
                [0],
            ),
            _done_result_with_actions([], []),
        ]
        mocks = _prepare_explore_mocks(mocker, parse_results=parse_results)

        interactive_ctrl = MagicMock()
        interactive_ctrl.prompt_action_confirmation = AsyncMock(
            side_effect=[
                InteractiveDecision(decision_type=DecisionType.SKIP),
                InteractiveDecision(decision_type=DecisionType.CONFIRM),
            ]
        )
        interactive_ctrl.ask_continue_after_done = None
        mocker.patch(
            "cliany_site.explorer.interactive.InteractiveController",
            return_value=interactive_ctrl,
        )

        explorer = WorkflowExplorer(interactive=True)
        result = await explorer.explore("https://example.com/start", "跳过动作", record=False)

        assert len(result.actions) == 0
        assert mocks["execute"].await_count == 1
        assert mocks["execute"].await_args.args[1] == []

    @pytest.mark.asyncio
    async def test_interactive_modify_value_applies_before_execution(self, mocker):
        parse_results = [
            _done_result_with_actions(
                [{"type": "type", "ref": "1", "value": "old", "description": "输入关键词"}],
                [0],
            )
        ]
        mocks = _prepare_explore_mocks(mocker, parse_results=parse_results)

        interactive_ctrl = MagicMock()
        interactive_ctrl.prompt_action_confirmation = AsyncMock(
            return_value=InteractiveDecision(
                decision_type=DecisionType.MODIFY,
                field="value",
                new_value="new-keyword",
            )
        )
        interactive_ctrl.ask_continue_after_done = None
        mocker.patch(
            "cliany_site.explorer.interactive.InteractiveController",
            return_value=interactive_ctrl,
        )

        explorer = WorkflowExplorer(interactive=True)
        result = await explorer.explore("https://example.com/start", "修改输入", record=False)

        executed_actions = mocks["execute"].await_args.args[1]
        assert executed_actions[0]["value"] == "new-keyword"
        assert result.actions[0].value == "new-keyword"

    @pytest.mark.asyncio
    async def test_turn_snapshot_created_before_each_llm_turn(self, mocker):
        parse_results = [
            {
                "actions": [{"type": "click", "ref": "1", "description": "第一步"}],
                "commands": [],
                "done": False,
                "next_url": "",
            },
            _done_result_with_actions(
                [{"type": "click", "ref": "1", "description": "第二步"}],
                [0, 1],
            ),
        ]
        _prepare_explore_mocks(mocker, parse_results=parse_results)

        snapshots: list[SimpleNamespace] = []

        def _capture_snapshot(**kwargs):
            snapshot = SimpleNamespace(**kwargs)
            snapshots.append(snapshot)
            return snapshot

        mocker.patch("cliany_site.explorer.engine.TurnSnapshot", side_effect=_capture_snapshot)

        explorer = WorkflowExplorer(interactive=False)
        await explorer.explore("https://example.com/start", "快照创建时机", record=False)

        assert len(snapshots) == 2
        assert [s.turn_index for s in snapshots] == [0, 1]
        assert [s.actions_before_count for s in snapshots] == [0, 1]
        assert [s.pages_before_count for s in snapshots] == [0, 1]

    @pytest.mark.asyncio
    async def test_done_true_can_continue_when_controller_allows(self, mocker):
        parse_results = [
            _done_result_with_actions(
                [{"type": "click", "ref": "1", "description": "第一轮完成"}],
                [0],
            ),
            _done_result_with_actions(
                [{"type": "click", "ref": "1", "description": "第二轮完成"}],
                [0, 1],
            ),
        ]
        mocks = _prepare_explore_mocks(mocker, parse_results=parse_results)

        interactive_ctrl = MagicMock()
        interactive_ctrl.prompt_action_confirmation = AsyncMock(
            return_value=InteractiveDecision(decision_type=DecisionType.CONFIRM)
        )
        interactive_ctrl.ask_continue_after_done = AsyncMock(side_effect=[True, False])
        mocker.patch(
            "cliany_site.explorer.interactive.InteractiveController",
            return_value=interactive_ctrl,
        )

        explorer = WorkflowExplorer(interactive=True)
        result = await explorer.explore("https://example.com/start", "完成后继续", record=False)

        assert interactive_ctrl.ask_continue_after_done.await_count == 2
        assert mocks["capture_axtree"].await_count == 2
        assert len(result.actions) == 2


class TestKeyboardInterrupt:
    """Ctrl-C 优雅中断：保存部分结果 + 截断录像"""

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_saves_partial_result(self, mocker):
        """第 N 步 LLM 抛 KeyboardInterrupt，验证 AdapterGenerator.generate() 被调用含部分结果"""
        # 第一步正常返回，第二步 LLM 抛 KeyboardInterrupt
        parse_results = [
            {
                "actions": [{"type": "click", "ref": "1", "description": "第一步点击"}],
                "commands": [],
                "done": False,
                "next_url": "",
            },
        ]
        _prepare_explore_mocks(mocker, parse_results=parse_results)

        # 让第二次 LLM 调用抛 KeyboardInterrupt
        invoke_mock = mocker.patch(
            "cliany_site.explorer.engine._invoke_llm_with_retry",
            new_callable=AsyncMock,
            side_effect=[
                SimpleNamespace(content="response-0"),
                KeyboardInterrupt(),
            ],
        )

        generator_mock = MagicMock()
        mocker.patch(
            "cliany_site.explorer.engine.AdapterGenerator",
            return_value=generator_mock,
        )

        explorer = WorkflowExplorer(interactive=False)
        with pytest.raises(KeyboardInterrupt):
            await explorer.explore("https://example.com/start", "中断测试", record=False)

        # 验证 AdapterGenerator().generate() 被调用，且包含部分结果
        generator_mock.generate.assert_called_once()
        call_kwargs = generator_mock.generate.call_args
        partial_result = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("result")
        assert partial_result is not None
        assert len(partial_result.actions) == 1  # 只有第一步的 action

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_finalizes_recording(self, mocker):
        """第 N 步 LLM 抛 KeyboardInterrupt，验证 RecordingManager.finalize 以 completed=False 调用"""
        parse_results = [
            {
                "actions": [{"type": "click", "ref": "1", "description": "第一步点击"}],
                "commands": [],
                "done": False,
                "next_url": "",
            },
        ]

        recording_manager = MagicMock()
        recording_manager.start_recording.return_value = MagicMock()

        _prepare_explore_mocks(mocker, parse_results=parse_results, recording_manager=recording_manager)

        # 让第二次 LLM 调用抛 KeyboardInterrupt
        mocker.patch(
            "cliany_site.explorer.engine._invoke_llm_with_retry",
            new_callable=AsyncMock,
            side_effect=[
                SimpleNamespace(content="response-0"),
                KeyboardInterrupt(),
            ],
        )

        mocker.patch("cliany_site.explorer.engine.AdapterGenerator", return_value=MagicMock())

        explorer = WorkflowExplorer(interactive=False)
        with pytest.raises(KeyboardInterrupt):
            await explorer.explore("https://example.com/start", "录像截断测试", record=True)

        # finalize 只调用一次，且 completed=False
        recording_manager.finalize.assert_called_once()
        assert recording_manager.finalize.call_args.kwargs["completed"] is False
