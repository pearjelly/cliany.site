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
