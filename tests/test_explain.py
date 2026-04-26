from click.testing import CliRunner
from cliany_site.cli import cli
import json, jsonschema
from pathlib import Path

SCHEMA_PATH = Path("schemas/explain.v1.json")

def test_explain_schema_valid(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--explain"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(data, schema)

def test_explain_has_commands(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--explain"])
    data = json.loads(result.output)
    assert len(data["commands"]) > 0

def test_explain_has_error_codes(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--explain"])
    data = json.loads(result.output)
    assert len(data["error_codes"]) > 0

def test_explain_error_codes_count_matches_errorcode(tmp_home):
    from cliany_site.envelope import ErrorCode
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--explain"])
    data = json.loads(result.output)
    expected = len([k for k in dir(ErrorCode) if k.startswith("E_")])
    assert len(data["error_codes"]) == expected

def test_explain_has_version(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--explain"])
    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert data["binary"] == "cliany-site"
    assert "version" in data