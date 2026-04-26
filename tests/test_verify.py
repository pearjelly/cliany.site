from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli


VALID_V2_METADATA = {
    "schema_version": 2,
    "domain": "test.com",
    "generated_at": "2024-01-01T00:00:00Z",
    "generator_version": "1.0.0",
    "commands": [{"name": "search"}],
}

SAFE_COMMANDS_PY = "import click\n\n@click.group()\ndef cli():\n    pass\n"

UNSAFE_COMMANDS_PY = (
    "import click\n\n@click.group()\ndef cli():\n    eval('1+1')\n"
)


@pytest.fixture()
def adapters_dir(tmp_home):
    d = tmp_home / ".cliany-site" / "adapters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_adapter(adapters_dir, domain: str, metadata: dict, commands_py: str = SAFE_COMMANDS_PY):
    adapter_dir = adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)
    (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (adapter_dir / "commands.py").write_text(commands_py, encoding="utf-8")
    return adapter_dir


def test_verify_no_adapters(tmp_home, no_llm):
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "nonexistent.com"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["domain"] == "nonexistent.com"
    assert data["data"]["results"] == []


def test_verify_ok_adapter(tmp_home, no_llm, adapters_dir):
    _make_adapter(adapters_dir, "test.com", VALID_V2_METADATA, SAFE_COMMANDS_PY)
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "test.com"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    results = data["data"]["results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "ok"
    assert results[0]["domain"] == "test.com"
    assert results[0]["issues"] == []


def test_verify_security_issue(tmp_home, no_llm, adapters_dir):
    _make_adapter(adapters_dir, "evil.com", VALID_V2_METADATA, UNSAFE_COMMANDS_PY)
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "evil.com"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    results = data["data"]["results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "security_issue"
    assert len(results[0]["issues"]) > 0
    assert any("eval(" in issue for issue in results[0]["issues"])


def test_verify_legacy_adapter(tmp_home, no_llm, adapters_dir):
    legacy_metadata = {"domain": "old.com", "commands": []}
    _make_adapter(adapters_dir, "old.com", legacy_metadata, SAFE_COMMANDS_PY)
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "old.com"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    results = data["data"]["results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "legacy_adapter"


def test_verify_all_adapters(tmp_home, no_llm, adapters_dir):
    _make_adapter(adapters_dir, "a.com", VALID_V2_METADATA | {"domain": "a.com"}, SAFE_COMMANDS_PY)
    legacy = {"domain": "b.com", "commands": []}
    _make_adapter(adapters_dir, "b.com", legacy, SAFE_COMMANDS_PY)
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["domain"] == "all"
    domains = {r["domain"] for r in data["data"]["results"]}
    assert "a.com" in domains
    assert "b.com" in domains
