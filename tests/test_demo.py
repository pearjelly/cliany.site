import json
import subprocess
from types import SimpleNamespace

from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.commands import demo
from cliany_site.config import get_config


def _result(rows=None):
    return {"success": True, "data": {"issues": rows if rows is not None else [{"key": "SPARK-1"}]}, "error": None}


def test_demo_runs_pinned_install_verify_and_read_only_query(tmp_home, monkeypatch):
    calls = []
    replies = iter([(True, {"success": True}), (True, {"ok": True}), (True, _result())])

    def run(argv):
        calls.append(argv)
        return next(replies)

    monkeypatch.setattr(demo, "_run_step", run)
    result = CliRunner().invoke(cli, ["demo", "--case-id", "apache-jira-issues", "--json"])
    payload = json.loads(result.stdout)
    assert result.exit_code == 0
    assert payload["ok"] is True
    assert payload["data"]["row_count"] == 1
    assert payload["data"]["result"]["data"]["issues"][0]["key"] == "SPARK-1"
    assert len(calls) == 3
    assert calls[0][2:5] == ["cliany_site", "market", "install"]
    assert "--sha256" in calls[0] and "--force" not in calls[0]
    assert calls[1][2:6] == ["cliany_site", "verify", "issues.apache.org", "--strict"]
    assert calls[2][2:5] == ["cliany_site", "issues.apache.org", "list-issues"]


def test_human_output_summarizes_results_without_terminal_controls(tmp_home, monkeypatch):
    replies = iter([
        (True, {"success": True}),
        (True, {"ok": True}),
        (True, _result([{"key": "SPARK-1", "summary": "Hello\n\x1b[31m"}])),
    ])
    monkeypatch.setattr(demo, "_run_step", lambda argv: next(replies))
    result = CliRunner().invoke(cli, ["demo", "--case-id", "apache-jira-issues"])
    assert result.exit_code == 0
    assert "1 条结果" in result.stdout
    assert '"SPARK-1"' in result.stdout
    assert "\\n\\u001b[31m" in result.stdout
    assert "\x1b[31m" not in result.stdout
    assert "'success': True" not in result.stdout


def test_human_failure_shows_recovery_hint_and_stops(tmp_home, monkeypatch):
    calls = []

    def run(argv):
        calls.append(argv)
        return False, {"success": False, "error": {"code": "INSTALL_FAILED"}}

    monkeypatch.setattr(demo, "_run_step", run)
    result = CliRunner().invoke(cli, ["demo", "--case-id", "apache-jira-issues"])
    assert result.exit_code == 1
    assert "E_DOWNLOAD_FAILED" in result.stdout
    assert "GitHub" in result.stdout
    assert len(calls) == 1


def test_existing_adapter_is_verified_without_reinstall(tmp_home, monkeypatch):
    target = get_config().adapters_dir / "issues.apache.org"
    target.mkdir(parents=True)
    calls = []

    def run(argv):
        calls.append(argv)
        return (True, {"ok": True}) if len(calls) == 1 else (True, _result())

    monkeypatch.setattr(demo, "_run_step", run)
    result = demo.run_demo("apache-jira-issues")
    assert result["ok"] is True
    assert result["data"]["installed_now"] is False
    assert len(calls) == 2 and calls[0][3] == "verify"


def test_existing_broken_adapter_is_not_replaced_or_queried(tmp_home, monkeypatch):
    target = get_config().adapters_dir / "issues.apache.org"
    target.mkdir(parents=True)
    calls = []

    def run(argv):
        calls.append(argv)
        return False, {"ok": False, "error": {"code": "E_VERIFY_STATIC"}}

    monkeypatch.setattr(demo, "_run_step", run)
    result = demo.run_demo("apache-jira-issues")
    assert result["error"]["code"] == "E_VERIFY_STATIC"
    assert target.is_dir()
    assert len(calls) == 1 and calls[0][3] == "verify"


def test_candidate_and_login_cases_cannot_run(tmp_home, monkeypatch):
    calls = []
    monkeypatch.setattr(demo, "_run_step", lambda argv: calls.append(argv))
    assert demo.run_demo("pypi-project-search")["error"]["code"] == "E_INVALID_PARAM"
    assert demo.run_demo("suitecrm-accounts")["error"]["code"] == "E_INVALID_PARAM"
    assert not calls


def test_each_failure_stops_later_steps(tmp_home, monkeypatch):
    for failure_at, code in [(0, "E_DOWNLOAD_FAILED"), (1, "E_VERIFY_STATIC"), (2, "E_UNKNOWN")]:
        calls = []

        def run(argv, calls=calls, failure_at=failure_at):
            calls.append(argv)
            if len(calls) - 1 == failure_at:
                return False, {"error": {"code": "UPSTREAM"}}
            return True, {"success": True}

        monkeypatch.setattr(demo, "_run_step", run)
        result = demo.run_demo("apache-jira-issues")
        assert result["ok"] is False
        assert result["error"]["code"] == code
        assert result["error"]["hint"]
        assert len(calls) == failure_at + 1


def test_empty_result_fails_oracle(tmp_home, monkeypatch):
    replies = iter([(True, {"success": True}), (True, {"ok": True}), (True, _result([]))])
    monkeypatch.setattr(demo, "_run_step", lambda argv: next(replies))
    result = demo.run_demo("apache-jira-issues")
    assert result["ok"] is False
    assert result["error"]["code"] == "E_EMPTY_RESULT"
    assert result["error"]["details"]["stage"] == "oracle"


def test_untrusted_case_command_is_not_run(tmp_home, monkeypatch):
    cases, source, paths = demo._load_cases_manifest()
    case = next(item.copy() for item in cases if item["id"] == "apache-jira-issues")
    case["commands"] = [case["commands"][0], "cliany-site login https://example.com --json"]
    monkeypatch.setattr(demo, "_load_cases_manifest", lambda: ([case], source, paths))
    calls = []
    monkeypatch.setattr(demo, "_run_step", lambda argv: calls.append(argv))
    assert demo.run_demo("apache-jira-issues")["error"]["code"] == "E_INVALID_PARAM"
    assert not calls


def test_step_requires_zero_exit_and_success_envelope(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=1, stdout='{"ok":true}', stderr="",
    ))
    assert demo._run_step(["x"]) == (False, {"ok": True})


def test_step_rejects_non_json_output(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout="done", stderr="",
    ))
    assert demo._run_step(["x"]) == (False, None)
