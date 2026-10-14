import json
import subprocess
import sys
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.commands import demo


@pytest.mark.parametrize("script,reason", [
    ("print('not-json')", "invalid_json"),
    ("print('[]')", "invalid_envelope"),
    ("import sys; sys.stdout.buffer.write(bytes([255])); sys.stdout.flush()", "invalid_utf8"),
])
def test_actual_child_output_failure_keeps_safe_reason(tmp_home, script, reason):
    passed, payload = demo._run_step([sys.executable, "-c", script])
    assert not passed
    assert payload["error"]["code"] == "E_PARSE_FAILED"
    assert payload["error"]["details"]["reason"] == reason
    assert "stdout" not in payload["error"]["details"]
    assert "stderr" not in payload["error"]["details"]


@pytest.mark.parametrize("kind,reason,code", [
    ("timeout", "timeout", "E_TIMEOUT"),
    ("start", "start_failed", "E_UNKNOWN"),
])
def test_child_failure_does_not_publish_exception_or_output(tmp_home, monkeypatch, kind, reason, code):
    secret = "PRIVATE_SENTINEL_DO_NOT_PUBLISH"

    def fail(*args, **kwargs):
        if kind == "timeout":
            raise subprocess.TimeoutExpired([secret], 90, output=secret, stderr=secret)
        raise OSError(secret)

    monkeypatch.setattr(subprocess, "run", fail)
    passed, payload = demo._run_step([secret])
    assert not passed
    assert payload["error"]["code"] == code
    assert payload["error"]["details"]["reason"] == reason
    assert secret not in json.dumps(payload)
    if kind == "timeout":
        assert payload["error"]["details"]["timeout_seconds"] == 90


def test_malformed_json_preserves_exit_code_not_raw_streams(tmp_home, monkeypatch):
    secret = "PRIVATE_SENTINEL_DO_NOT_PUBLISH"
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=17, stdout=secret, stderr=secret,
    ))
    passed, payload = demo._run_step(["not-executed"])
    assert not passed
    assert payload["error"]["details"] == {"reason": "invalid_json", "returncode": 17}
    assert secret not in json.dumps(payload)


def test_python_child_uses_explicit_utf8_in_both_directions(tmp_home, monkeypatch):
    seen = {}

    def run(*args, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(returncode=0, stdout='{"ok":true,"data":{"title":"\u6587\u6863"}}', stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    passed, payload = demo._run_step(["not-executed"])
    assert passed and payload["data"]["title"] == "\u6587\u6863"
    assert seen["encoding"] == "utf-8"
    assert seen["env"]["PYTHONUTF8"] == "1"
    assert seen["env"]["PYTHONIOENCODING"] == "utf-8"
    assert seen["timeout"] == 90


def test_actual_child_json_survives_inherited_non_utf8_stdio(tmp_home, monkeypatch):
    monkeypatch.setenv("PYTHONUTF8", "0")
    monkeypatch.setenv("PYTHONIOENCODING", "ascii")
    passed, payload = demo._run_step([
        sys.executable, "-c",
        "import json; print(json.dumps({'ok': True, 'data': {'title': '\\u6587\\u6863'}}, ensure_ascii=False))",
    ])
    assert passed and payload["data"]["title"] == "\u6587\u6863"


def test_valid_upstream_error_is_preserved(tmp_home, monkeypatch):
    upstream = {"ok": False, "error": {"code": "E_EMPTY_RESULT", "details": {"row_count": 0}}}
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=1, stdout=json.dumps(upstream), stderr="",
    ))
    assert demo._run_step(["not-executed"]) == (False, upstream)


@pytest.mark.parametrize("failure_at,stage,code", [
    (0, "install", "E_DOWNLOAD_FAILED"),
    (1, "verify", "E_VERIFY_STATIC"),
    (2, "query", "E_UNKNOWN"),
])
def test_cli_keeps_phase_after_actual_invalid_child_encoding(tmp_home, monkeypatch, failure_at, stage, code):
    actual_run = demo._run_step
    calls = []

    def step(argv):
        calls.append(argv)
        if len(calls) - 1 == failure_at:
            return actual_run([
                sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes([255])); sys.stdout.flush()"
            ])
        return True, {"ok": True}

    monkeypatch.setattr(demo, "_run_step", step)
    result = CliRunner().invoke(cli, ["demo", "--case-id", "apache-jira-issues", "--json"])
    payload = json.loads(result.stdout)
    assert result.exit_code == 1 and payload["ok"] is False
    assert payload["error"]["code"] == code
    assert payload["error"]["details"]["stage"] == stage
    assert payload["error"]["details"]["upstream_error"]["details"]["reason"] == "invalid_utf8"
    assert len(calls) == failure_at + 1
