import json
from pathlib import Path

import pytest

from cliany_site.report import ActionStepResult, ExecutionReport, save_execution_log, save_report


@pytest.fixture()
def _use_tmp_home(tmp_path, monkeypatch):
    from cliany_site.config import reset_config

    reset_config()

    from cliany_site import config as _cfg

    monkeypatch.setattr(_cfg, "_config", _cfg.ClanySiteConfig(home_dir=tmp_path))
    yield
    reset_config()


def _make_report(steps: list[ActionStepResult] | None = None) -> ExecutionReport:
    if steps is None:
        steps = [
            ActionStepResult(
                step_index=0,
                action_type="navigate",
                description="go to home",
                success=True,
                timestamp="2026-01-01T00:00:00Z",
                page_url="https://example.com",
                elapsed_ms=150.5,
            ),
            ActionStepResult(
                step_index=1,
                action_type="click",
                description="click button",
                success=False,
                error_message="element not found",
                timestamp="2026-01-01T00:00:01Z",
                page_url="https://example.com/page",
                elapsed_ms=320.7,
            ),
        ]
    return ExecutionReport(
        adapter_domain="example.com",
        command_name="search",
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:02Z",
        total_steps=len(steps),
        succeeded_steps=sum(1 for s in steps if s.success),
        failed_steps=sum(1 for s in steps if not s.success),
        repaired_steps=0,
        step_results=steps,
    )


class TestActionStepResultEnhanced:
    def test_page_url_default(self):
        result = ActionStepResult(step_index=0, action_type="click", description="btn", success=True)
        assert result.page_url == ""
        assert result.elapsed_ms == 0.0

    def test_page_url_set(self):
        result = ActionStepResult(
            step_index=0,
            action_type="click",
            description="btn",
            success=True,
            page_url="https://example.com",
            elapsed_ms=123.4,
        )
        assert result.page_url == "https://example.com"
        assert result.elapsed_ms == 123.4


class TestSaveReportEnhanced:
    def test_report_includes_page_url_and_elapsed(self, _use_tmp_home, tmp_path):
        report = _make_report()
        path_str = save_report(report, "example.com")
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
        steps = data["step_results"]
        assert steps[0]["page_url"] == "https://example.com"
        assert steps[0]["elapsed_ms"] == 150.5
        assert steps[1]["page_url"] == "https://example.com/page"
        assert steps[1]["elapsed_ms"] == 320.7


class TestSaveExecutionLog:
    def test_creates_log_file(self, _use_tmp_home, tmp_path):
        report = _make_report()
        path_str = save_execution_log(report, "example.com")
        assert path_str.endswith(".log.json")
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
        assert data["adapter_domain"] == "example.com"
        assert data["command_name"] == "search"
        assert data["status"] == "partial_success"

    def test_log_summary(self, _use_tmp_home, tmp_path):
        report = _make_report()
        path_str = save_execution_log(report, "example.com")
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
        assert data["summary"]["total"] == 2
        assert data["summary"]["succeeded"] == 1
        assert data["summary"]["failed"] == 1

    def test_log_steps_detail(self, _use_tmp_home, tmp_path):
        report = _make_report()
        path_str = save_execution_log(report, "example.com")
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
        steps = data["steps"]
        assert len(steps) == 2
        assert steps[0]["page_url"] == "https://example.com"
        assert steps[0]["elapsed_ms"] == 150.5
        assert "error" not in steps[0]
        assert steps[1]["error"] == "element not found"

    def test_log_dir_created(self, _use_tmp_home, tmp_path):
        report = _make_report()
        save_execution_log(report, "example.com")
        assert (tmp_path / "logs").is_dir()

    def test_all_success_report(self, _use_tmp_home, tmp_path):
        steps = [
            ActionStepResult(
                step_index=0,
                action_type="click",
                description="btn",
                success=True,
                page_url="https://x.com",
                elapsed_ms=100.0,
            )
        ]
        report = _make_report(steps)
        path_str = save_execution_log(report, "x.com")
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
        assert data["status"] == "success"
        assert data["summary"]["failed"] == 0
