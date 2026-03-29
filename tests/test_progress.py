import io
import json

from cliany_site.progress import (
    NdjsonProgressReporter,
    NullProgressReporter,
    RichProgressReporter,
)


class TestNullProgressReporter:
    def test_all_callbacks_are_noop(self):
        r = NullProgressReporter()
        r.on_explore_start("https://example.com", "test", 10)
        r.on_explore_step_start(0, 10)
        r.on_explore_llm_start(0)
        r.on_explore_llm_done(0, 3)
        r.on_explore_step_done(0, 3, 123.4)
        r.on_explore_done(1, 3, 1, 500.0)
        r.on_execute_start(5, "example.com", "search")
        r.on_execute_step_start(0, 5, "click", "点击按钮")
        r.on_execute_step_done(0, 5, True, 100.0)
        r.on_execute_step_done(1, 5, False, 200.0, "element not found")
        r.on_execute_done(4, 1, 5, 1000.0)


class TestNdjsonProgressReporter:
    def _make_reporter(self) -> tuple[NdjsonProgressReporter, io.StringIO]:
        buf = io.StringIO()
        return NdjsonProgressReporter(file=buf), buf

    def _parse_lines(self, buf: io.StringIO) -> list[dict]:
        buf.seek(0)
        return [json.loads(line) for line in buf if line.strip()]

    def test_explore_start_emits_event(self):
        r, buf = self._make_reporter()
        r.on_explore_start("https://example.com", "search workflow", 10)
        events = self._parse_lines(buf)
        assert len(events) == 1
        assert events[0]["event"] == "explore_start"
        assert events[0]["url"] == "https://example.com"
        assert events[0]["workflow"] == "search workflow"
        assert events[0]["max_steps"] == 10
        assert "ts" in events[0]

    def test_explore_step_lifecycle(self):
        r, buf = self._make_reporter()
        r.on_explore_step_start(0, 10)
        r.on_explore_llm_start(0)
        r.on_explore_llm_done(0, 3)
        r.on_explore_step_done(0, 3, 456.7)
        events = self._parse_lines(buf)
        assert len(events) == 4
        assert events[0]["event"] == "explore_step_start"
        assert events[0]["step"] == 0
        assert events[1]["event"] == "explore_llm_start"
        assert events[2]["event"] == "explore_llm_done"
        assert events[2]["actions_count"] == 3
        assert events[3]["event"] == "explore_step_done"
        assert events[3]["elapsed_ms"] == 456.7

    def test_explore_done_emits_summary(self):
        r, buf = self._make_reporter()
        r.on_explore_done(3, 8, 2, 5000.0)
        events = self._parse_lines(buf)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "explore_done"
        assert e["total_steps"] == 3
        assert e["total_actions"] == 8
        assert e["total_commands"] == 2
        assert e["elapsed_ms"] == 5000.0

    def test_execute_start_emits_event(self):
        r, buf = self._make_reporter()
        r.on_execute_start(5, "github.com", "search")
        events = self._parse_lines(buf)
        assert len(events) == 1
        assert events[0]["event"] == "execute_start"
        assert events[0]["total_actions"] == 5
        assert events[0]["domain"] == "github.com"
        assert events[0]["command"] == "search"

    def test_execute_step_success(self):
        r, buf = self._make_reporter()
        r.on_execute_step_start(0, 5, "click", "点击搜索按钮")
        r.on_execute_step_done(0, 5, True, 150.3)
        events = self._parse_lines(buf)
        assert len(events) == 2
        assert events[0]["event"] == "execute_step_start"
        assert events[0]["action_type"] == "click"
        assert events[0]["description"] == "点击搜索按钮"
        assert events[1]["event"] == "execute_step_done"
        assert events[1]["success"] is True
        assert events[1]["elapsed_ms"] == 150.3
        assert "error" not in events[1]

    def test_execute_step_failure_includes_error(self):
        r, buf = self._make_reporter()
        r.on_execute_step_done(2, 5, False, 300.0, "element not found")
        events = self._parse_lines(buf)
        assert len(events) == 1
        assert events[0]["success"] is False
        assert events[0]["error"] == "element not found"

    def test_execute_done_emits_summary(self):
        r, buf = self._make_reporter()
        r.on_execute_done(4, 1, 5, 2000.0)
        events = self._parse_lines(buf)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "execute_done"
        assert e["succeeded"] == 4
        assert e["failed"] == 1
        assert e["total"] == 5
        assert e["elapsed_ms"] == 2000.0

    def test_elapsed_ms_rounded(self):
        r, buf = self._make_reporter()
        r.on_explore_step_done(0, 2, 123.456789)
        events = self._parse_lines(buf)
        assert events[0]["elapsed_ms"] == 123.5

    def test_full_explore_sequence(self):
        r, buf = self._make_reporter()
        r.on_explore_start("https://example.com", "login", 5)
        for step in range(3):
            r.on_explore_step_start(step, 5)
            r.on_explore_llm_start(step)
            r.on_explore_llm_done(step, 2)
            r.on_explore_step_done(step, 2, 1000.0)
        r.on_explore_done(3, 6, 1, 3500.0)
        events = self._parse_lines(buf)
        assert len(events) == 14
        assert events[0]["event"] == "explore_start"
        assert events[-1]["event"] == "explore_done"

    def test_full_execute_sequence(self):
        r, buf = self._make_reporter()
        r.on_execute_start(3, "test.com", "run")
        r.on_execute_step_start(0, 3, "navigate", "打开首页")
        r.on_execute_step_done(0, 3, True, 500.0)
        r.on_execute_step_start(1, 3, "click", "点击按钮")
        r.on_execute_step_done(1, 3, True, 200.0)
        r.on_execute_step_start(2, 3, "type", "输入文本")
        r.on_execute_step_done(2, 3, False, 100.0, "timeout")
        r.on_execute_done(2, 1, 3, 850.0)
        events = self._parse_lines(buf)
        assert len(events) == 8
        assert events[0]["event"] == "execute_start"
        assert events[-1]["event"] == "execute_done"
        assert events[-1]["succeeded"] == 2
        assert events[-1]["failed"] == 1


class TestRichProgressReporter:
    def test_explore_lifecycle_no_crash(self):
        from rich.console import Console

        console = Console(file=io.StringIO(), stderr=False)
        r = RichProgressReporter(console=console)

        r.on_explore_start("https://example.com", "workflow", 5)
        r.on_explore_step_start(0, 5)
        r.on_explore_llm_start(0)
        r.on_explore_llm_done(0, 2)
        r.on_explore_step_done(0, 2, 500.0)
        r.on_explore_done(1, 2, 1, 600.0)

    def test_execute_lifecycle_no_crash(self):
        from rich.console import Console

        console = Console(file=io.StringIO(), stderr=False)
        r = RichProgressReporter(console=console)

        r.on_execute_start(3, "test.com", "run")
        r.on_execute_step_start(0, 3, "navigate", "打开首页")
        r.on_execute_step_done(0, 3, True, 300.0)
        r.on_execute_step_start(1, 3, "click", "点击")
        r.on_execute_step_done(1, 3, False, 100.0, "error")
        r.on_execute_done(1, 1, 2, 500.0)

    def test_explore_done_output_contains_summary(self):
        from rich.console import Console

        buf = io.StringIO()
        console = Console(file=buf, stderr=False, width=120)
        r = RichProgressReporter(console=console)

        r.on_explore_start("https://example.com", "test", 5)
        r.on_explore_done(3, 8, 2, 5000.0)

        output = buf.getvalue()
        assert "探索完成" in output
        assert "3 步" in output
        assert "8 动作" in output
        assert "2 命令" in output

    def test_execute_done_output_contains_summary(self):
        from rich.console import Console

        buf = io.StringIO()
        console = Console(file=buf, stderr=False, width=120)
        r = RichProgressReporter(console=console)

        r.on_execute_start(5, "test.com", "run")
        r.on_execute_done(4, 1, 5, 2000.0)

        output = buf.getvalue()
        assert "执行完成" in output
        assert "成功 4" in output
        assert "失败 1" in output

    def test_execute_all_success_shows_green(self):
        from rich.console import Console

        buf = io.StringIO()
        console = Console(file=buf, stderr=False, width=120)
        r = RichProgressReporter(console=console)

        r.on_execute_start(3, "test.com", "run")
        r.on_execute_done(3, 0, 3, 1000.0)

        output = buf.getvalue()
        assert "执行完成" in output
        assert "失败 0" in output

    def test_default_console_is_stderr(self):
        r = RichProgressReporter()
        assert r._console.stderr is True
