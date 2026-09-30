import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import click
import pytest
from click.testing import CliRunner

from cliany_site.codegen import runtime_helpers


@pytest.mark.parametrize("owns_browser", [True, False])
def test_generated_steps_reuse_one_browser_and_only_close_owned_process(monkeypatch, owns_browser):
    launched = []
    process = MagicMock() if owns_browser else None
    monkeypatch.setattr(
        "cliany_site.browser.launcher.ensure_chrome",
        lambda port, headless: launched.append((port, headless)) or ("ws://localhost:9222/devtools/browser", process),
    )
    invocations = []

    class FakeRunner:
        def invoke(self, command, args, catch_exceptions):  # noqa: ARG002
            invocations.append(args)
            return SimpleNamespace(stdout=json.dumps({"ok": True, "command": "browser step"}), exit_code=0)

    monkeypatch.setattr(runtime_helpers, "CliRunner", FakeRunner)
    results = runtime_helpers.execute_steps_via_atoms(
        [{"type": "click", "target_name": "Search", "target_role": "button"}],
        "https://example.com",
        "example.com",
    )

    assert len(results) == 2
    assert all(result["ok"] for result in results)
    assert len(launched) == 1
    assert len(invocations) == 2
    assert all(args[:2] == ["--cdp-url", "http://localhost:9222"] for args in invocations)
    if process is not None:
        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=5)


def test_owned_browser_closes_when_first_step_fails(monkeypatch):
    process = MagicMock()
    monkeypatch.setattr(
        "cliany_site.browser.launcher.ensure_chrome",
        lambda port, headless: ("ws://localhost:9222/devtools/browser", process),  # noqa: ARG005
    )

    class FakeRunner:
        def invoke(self, command, args, catch_exceptions):  # noqa: ARG002
            return SimpleNamespace(stdout=json.dumps({"ok": False, "error": {"code": "E_PAGE_NOT_READY"}}), exit_code=1)

    monkeypatch.setattr(runtime_helpers, "CliRunner", FakeRunner)
    results = runtime_helpers.execute_steps_via_atoms([], "https://example.com", "example.com")

    assert len(results) == 1
    assert results[0]["error"]["code"] == "E_PAGE_NOT_READY"
    process.terminate.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=5)


def test_explicit_cdp_url_is_not_terminated_by_generated_steps(monkeypatch):
    checked_ports = []
    monkeypatch.setattr(
        "cliany_site.browser.launcher.ensure_chrome",
        lambda port, headless: checked_ports.append(port) or ("ws://localhost:48770/devtools/browser", None),
    )
    invocations = []

    class FakeRunner:
        def invoke(self, command, args, catch_exceptions):  # noqa: ARG002
            invocations.append(args)
            return SimpleNamespace(stdout=json.dumps({"ok": True, "command": "browser navigate"}), exit_code=0)

    monkeypatch.setattr(runtime_helpers, "CliRunner", FakeRunner)

    @click.command()
    def command():
        result = runtime_helpers.execute_steps_via_atoms([], "https://example.com", "example.com")
        assert result[0]["ok"] is True

    result = CliRunner().invoke(command, obj={"cdp_url": "http://localhost:48770"})
    assert result.exit_code == 0, result.output
    assert checked_ports == [48770]
    assert invocations[0][:2] == ["--cdp-url", "http://localhost:48770"]
