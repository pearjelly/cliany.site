import json
import importlib

import click
import pytest

from cliany_site.codegen.runtime_helpers import run_atom
from cliany_site.envelope import err, ok


@pytest.mark.parametrize("payload,exit_code,stderr,expected", [
    (ok("inspect", {"name": "Ada"}), 0, "diagnostic", True),
    (err("inspect", "E_EMPTY_RESULT", "No rows"), 0, "diagnostic", False),
    (ok("inspect", {}), 1, "", False),
    ([], 0, "", False),
    (None, 0, "", False),
    ({"ok": "true"}, 0, "", False),
    ({"ok": 1}, 0, "", False),
])
def test_atom_validates_real_click_result(monkeypatch, payload, exit_code, stderr, expected):
    @click.group()
    def cli():
        pass

    @cli.command()
    @click.option("--json", "json_mode", is_flag=True)
    @click.pass_context
    def inspect(ctx, json_mode):
        if stderr:
            click.echo(stderr, err=True)
        click.echo(json.dumps(payload))
        ctx.exit(exit_code)

    monkeypatch.setattr(importlib.import_module("cliany_site.cli"), "cli", cli)
    result = run_atom(["inspect"])
    assert result["ok"] is expected
    if expected:
        assert result["data"] == {"name": "Ada"}
    elif isinstance(payload, dict) and payload.get("ok") is False:
        assert result["error"]["code"] == "E_EMPTY_RESULT"
    else:
        assert result["error"]["code"] == "E_UNKNOWN"
