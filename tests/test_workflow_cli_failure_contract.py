import json

import click
import pytest
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.envelope import err, ok


@pytest.fixture
def adapter(monkeypatch, tmp_home):
    @click.group("contract.example")
    def group():
        pass

    @group.command("read")
    @click.option("--value", default="good")
    @click.option("--json", "json_mode", is_flag=True)
    @click.pass_context
    def read(ctx, value, json_mode):
        result = err("read", "E_EMPTY_RESULT", "No matching rows") if value == "bad" else ok("read", [value])
        click.echo(json.dumps(result))
        if value == "bad":
            ctx.exit(1)

    monkeypatch.setitem(cli.commands, "contract.example", group)


@pytest.mark.parametrize("mode", ["human", "root_json", "command_json"])
@pytest.mark.parametrize("kind", ["run", "batch"])
def test_failed_workflow_cli_returns_nonzero_and_one_json(tmp_home, adapter, mode, kind):
    if kind == "run":
        path = tmp_home / "workflow.yaml"
        path.write_text("""name: contract
steps:
  - name: first
    adapter: contract.example
    command: read
  - name: second
    adapter: contract.example
    command: read
    params:
      value: bad
""", encoding="utf-8")
        args = ["workflow", "run", str(path)]
        error_code = "WORKFLOW_FAILED"
    else:
        path = tmp_home / "data.csv"
        path.write_text("value\ngood\nbad\n", encoding="utf-8")
        args = ["workflow", "batch", "contract.example", "read", str(path)]
        error_code = "BATCH_PARTIAL_FAILURE"
    if mode == "root_json":
        args.insert(0, "--json")
    elif mode == "command_json":
        args.append("--json")
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 1, result.output
    if mode == "human":
        assert error_code in result.output
    else:
        payload = json.loads(result.stdout)
        assert payload["success"] is False
        assert payload["error"]["code"] == error_code
        details = payload["error"]["details"]
        rows = details["steps"] if kind == "run" else details["results"]
        assert rows[0]["data"] == ["good"]
        assert rows[1]["success"] is False
        assert rows[1]["error"] == "No matching rows"


def test_successful_workflow_keeps_zero_exit_and_data(tmp_home, adapter):
    path = tmp_home / "data.csv"
    path.write_text("value\ngood\n", encoding="utf-8")
    result = CliRunner().invoke(cli, ["workflow", "batch", "contract.example", "read", str(path), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["data"]["results"][0]["data"] == ["good"]
