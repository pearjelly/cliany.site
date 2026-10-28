import asyncio
import json
from unittest.mock import Mock

import click
import pytest
from click.testing import CliRunner

from cliany_site.cli import SafeGroup


def _cancelling_cli(exception_type):
    @click.group(cls=SafeGroup)
    @click.option("--json", "json_mode", is_flag=True)
    def cli(json_mode):
        pass

    @cli.command()
    def work():
        raise exception_type()

    return cli


@pytest.mark.parametrize(("exception_type", "reason", "exit_code"), [
    (KeyboardInterrupt, "keyboard_interrupt", 130),
    (EOFError, "end_of_input", 1),
    (click.Abort, "aborted", 1),
])
def test_cancelled_cli_returns_structured_nonempty_error(exception_type, reason, exit_code):
    result = CliRunner().invoke(_cancelling_cli(exception_type), ["--json", "work"])
    assert result.exit_code == exit_code
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_CANCELLED"
    assert payload["error"]["message"] == "操作已取消"
    assert payload["error"]["details"]["reason"] == reason


def test_keyboard_interrupt_has_human_message_and_interrupt_exit_code():
    result = CliRunner().invoke(_cancelling_cli(KeyboardInterrupt), ["work"])
    assert result.exit_code == 130
    assert "操作已取消" in result.output
    assert "Traceback" not in result.output


def test_async_cancellation_is_not_swallowed():
    with pytest.raises(asyncio.CancelledError):
        CliRunner().invoke(_cancelling_cli(asyncio.CancelledError), ["--json", "work"], catch_exceptions=False)


def test_cancelled_atom_does_not_invoke_optional_healer(monkeypatch):
    from cliany_site.codegen.runtime_helpers import run_atom

    @click.group(cls=SafeGroup)
    def cli():
        pass

    @cli.command()
    @click.option("--json", "json_mode", is_flag=True)
    def work(json_mode):
        raise KeyboardInterrupt()

    healer = Mock()
    monkeypatch.setattr("cliany_site.cli.cli", cli)
    monkeypatch.setattr("cliany_site.healer.Healer", healer)
    result = run_atom(["work"], heal_on_failure=True)
    assert result["error"]["code"] == "E_CANCELLED"
    healer.assert_not_called()


def test_other_failed_atom_still_invokes_optional_healer(monkeypatch):
    from cliany_site.codegen.runtime_helpers import run_atom

    @click.group(cls=SafeGroup)
    def cli():
        pass

    @cli.command()
    @click.option("--json", "json_mode", is_flag=True)
    def work(json_mode):
        raise click.ClickException("failed")

    healer = Mock()
    monkeypatch.setattr("cliany_site.cli.cli", cli)
    monkeypatch.setattr("cliany_site.healer.Healer", healer)
    result = run_atom(["work"], heal_on_failure=True)
    assert result["error"]["code"] == "E_UNKNOWN"
    healer.return_value.heal.assert_called_once()
