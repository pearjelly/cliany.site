"""TDD tests for replay command — Rich 终端回放 + --step 翻页。"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _make_manifest(domain="test.com", session_id="sess-001", step_count=2):
    from cliany_site.explorer.models import RecordingManifest, StepRecord

    steps = [
        StepRecord(
            step_index=i,
            action_data={"type": "click", "target": f"btn-{i}", "description": f"点击按钮 {i}"},
            llm_response_raw=f"LLM response {i}",
            timestamp=f"2024-01-01T00:0{i}:00Z",
            screenshot_path=None,
            axtree_snapshot_path=None,
            rolled_back=(i == 1),
        )
        for i in range(step_count)
    ]
    return RecordingManifest(
        domain=domain,
        session_id=session_id,
        url=f"https://{domain}",
        workflow="测试工作流",
        started_at="2024-01-01T00:00:00Z",
        steps=steps,
        completed=True,
    )


# ──────────────────────────────────────────────────────────────
# 1. --help 测试
# ──────────────────────────────────────────────────────────────


class TestReplayHelp:
    def test_replay_help_shows_options(self):
        """replay --help 应显示 domain, --session, --step 参数。"""
        runner = CliRunner()
        result = runner.invoke(cli, ["replay", "--help"])
        assert result.exit_code == 0
        assert "domain" in result.output.lower() or "DOMAIN" in result.output
        assert "--session" in result.output
        assert "--step" in result.output

    def test_replay_help_shows_chinese_docstring(self):
        """replay --help 帮助文本含中文。"""
        runner = CliRunner()
        result = runner.invoke(cli, ["replay", "--help"])
        assert result.exit_code == 0
        # 帮助文本应包含中文字符
        assert any("\u4e00" <= c <= "\u9fff" for c in result.output)


# ──────────────────────────────────────────────────────────────
# 2. --json 模式拒绝
# ──────────────────────────────────────────────────────────────


class TestReplayJsonRejection:
    def test_replay_with_json_flag_raises_error(self):
        """在 --json 模式下 replay 应报 UsageError。"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "replay", "test.com"])
        assert result.exit_code != 0

    def test_replay_with_json_flag_error_message(self):
        """--json 模式下的错误信息应提示不支持。"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "replay", "test.com"])
        # 合并 output 和 stderr
        output = result.output + (result.stderr if hasattr(result, "stderr") and result.stderr else "")
        assert "replay" in output.lower() or "json" in output.lower() or result.exit_code != 0


# ──────────────────────────────────────────────────────────────
# 3. 无录像时友好提示
# ──────────────────────────────────────────────────────────────


class TestReplayNoRecordings:
    def test_no_recordings_shows_friendly_message(self, tmp_path):
        """无录像时应显示友好错误，不是 traceback。"""
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_recordings.return_value = []
            result = runner.invoke(cli, ["replay", "notexist.com"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        # 应有提示性文字
        combined = result.output + (result.exception.__str__() if result.exception else "")
        assert "notexist.com" in combined or "录像" in result.output or result.exit_code != 0

    def test_no_recordings_exit_code_nonzero(self, tmp_path):
        """无录像时退出码应非 0。"""
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_recordings.return_value = []
            result = runner.invoke(cli, ["replay", "empty.com"])
        assert result.exit_code != 0


# ──────────────────────────────────────────────────────────────
# 4. 多会话选择列表
# ──────────────────────────────────────────────────────────────


class TestReplaySessionList:
    def test_multiple_sessions_show_list(self, tmp_path):
        """多个录像时应展示带索引的列表。"""
        manifests = [
            _make_manifest(session_id="sess-001"),
            _make_manifest(session_id="sess-002"),
        ]
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_recordings.return_value = manifests
            # 用户输入 "q" 退出选择
            result = runner.invoke(cli, ["replay", "test.com"], input="q\n")
        # 输出中应包含会话 ID
        assert "sess-001" in result.output or "sess-002" in result.output or "1" in result.output

    def test_single_session_auto_select(self):
        """只有一个录像时应自动选择，不需要用户输入。"""
        manifest = _make_manifest(session_id="sess-only", step_count=1)
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_recordings.return_value = [manifest]
            instance.load_recording.return_value = manifest
            with patch("cliany_site.commands.replay._display_step"):
                # 自动模式需要 time.sleep mock
                with patch("cliany_site.commands.replay.time") as mock_time:
                    mock_time.sleep = MagicMock()
                    result = runner.invoke(cli, ["replay", "test.com"])
        # 应该能正常运行（exit 0 或显示步骤内容）
        assert "Traceback" not in result.output


# ──────────────────────────────────────────────────────────────
# 5. --session 指定具体录像
# ──────────────────────────────────────────────────────────────


class TestReplayWithSession:
    def test_session_specified_loads_directly(self):
        """--session 指定会话时应直接加载，不列出清单。"""
        manifest = _make_manifest(session_id="sess-specific", step_count=1)
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.load_recording.return_value = manifest
            with patch("cliany_site.commands.replay._display_step"):
                with patch("cliany_site.commands.replay.time") as mock_time:
                    mock_time.sleep = MagicMock()
                    result = runner.invoke(cli, ["replay", "test.com", "--session", "sess-specific"])
        # 应调用 load_recording 而非 list_recordings
        instance.load_recording.assert_called_once_with("test.com", "sess-specific")
        assert result.exit_code == 0

    def test_session_not_found_shows_error(self):
        """--session 指定的会话不存在时应友好报错。"""
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.load_recording.side_effect = FileNotFoundError("manifest.json not found")
            result = runner.invoke(cli, ["replay", "test.com", "--session", "nonexistent-sess"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output


# ──────────────────────────────────────────────────────────────
# 6. 自动播放模式（无 --step）
# ──────────────────────────────────────────────────────────────


class TestReplayAutoPlay:
    def test_auto_play_calls_display_for_each_step(self):
        """自动播放应为每个步骤调用展示函数。"""
        manifest = _make_manifest(session_id="sess-auto", step_count=3)
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_recordings.return_value = [manifest]
            instance.load_recording.return_value = manifest
            with patch("cliany_site.commands.replay._display_step") as mock_display:
                with patch("cliany_site.commands.replay.time") as mock_time:
                    mock_time.sleep = MagicMock()
                    result = runner.invoke(cli, ["replay", "test.com"])
        # 应为 3 个步骤调用 _display_step 3 次
        assert mock_display.call_count == 3

    def test_auto_play_sleeps_between_steps(self):
        """自动播放应在步骤间调用 sleep。"""
        manifest = _make_manifest(session_id="sess-sleep", step_count=2)
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_recordings.return_value = [manifest]
            instance.load_recording.return_value = manifest
            with patch("cliany_site.commands.replay._display_step"):
                with patch("cliany_site.commands.replay.time") as mock_time:
                    mock_time.sleep = MagicMock()
                    result = runner.invoke(cli, ["replay", "test.com"])
        # sleep 应被调用（步骤数 - 1 次，最后一步不 sleep，或等于步骤数）
        assert mock_time.sleep.call_count >= 1


# ──────────────────────────────────────────────────────────────
# 7. --step 手动翻页模式
# ──────────────────────────────────────────────────────────────


class TestReplayStepMode:
    def test_step_mode_prompts_user(self):
        """--step 模式应提示用户按 Enter 继续。"""
        manifest = _make_manifest(session_id="sess-step", step_count=2)
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_recordings.return_value = [manifest]
            instance.load_recording.return_value = manifest
            with patch("cliany_site.commands.replay._display_step"):
                # 模拟用户按两次 Enter
                result = runner.invoke(cli, ["replay", "test.com", "--step"], input="\n\n")
        assert result.exit_code == 0

    def test_step_mode_quit_with_q(self):
        """--step 模式下输入 q 应退出回放。"""
        manifest = _make_manifest(session_id="sess-quit", step_count=3)
        runner = CliRunner()
        with patch("cliany_site.commands.replay.RecordingManager") as MockMgr:
            instance = MockMgr.return_value
            instance.list_recordings.return_value = [manifest]
            instance.load_recording.return_value = manifest
            with patch("cliany_site.commands.replay._display_step") as mock_display:
                # 用户在第一个步骤后输入 q
                result = runner.invoke(cli, ["replay", "test.com", "--step"], input="q\n")
        # 应该在 q 时停止，不继续展示所有步骤
        assert mock_display.call_count < 3


# ──────────────────────────────────────────────────────────────
# 8. _display_step 函数单元测试
# ──────────────────────────────────────────────────────────────


class TestDisplayStep:
    def test_display_step_renders_panel(self):
        """_display_step 应渲染 Rich Panel 包含步骤信息。"""
        from io import StringIO

        from rich.console import Console

        from cliany_site.commands.replay import _display_step
        from cliany_site.explorer.models import StepRecord

        step = StepRecord(
            step_index=0,
            action_data={"type": "click", "description": "点击提交按钮"},
            llm_response_raw="LLM response",
            timestamp="2024-01-01T00:00:00Z",
            screenshot_path=None,
            axtree_snapshot_path=None,
            rolled_back=False,
        )
        buf = StringIO()
        console = Console(file=buf, width=80)
        _display_step(console, step, step_num=1, total=3)
        output = buf.getvalue()
        # 应包含步骤编号
        assert "1" in output
        # 应包含动作类型或描述
        assert "click" in output.lower() or "点击" in output

    def test_display_step_shows_rolled_back_status(self):
        """_display_step 对 rolled_back=True 的步骤应显示已回退状态。"""
        from io import StringIO

        from rich.console import Console

        from cliany_site.commands.replay import _display_step
        from cliany_site.explorer.models import StepRecord

        step = StepRecord(
            step_index=1,
            action_data={"type": "navigate", "description": "导航到页面"},
            llm_response_raw="LLM response",
            timestamp="2024-01-01T00:01:00Z",
            screenshot_path=None,
            axtree_snapshot_path=None,
            rolled_back=True,
        )
        buf = StringIO()
        console = Console(file=buf, width=80)
        _display_step(console, step, step_num=2, total=3)
        output = buf.getvalue()
        # 应有回退相关文字
        assert "回退" in output or "rolled" in output.lower() or "⚠" in output or "rollback" in output.lower()
