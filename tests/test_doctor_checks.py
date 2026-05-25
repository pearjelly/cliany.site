import json
import sys

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli


class MockCDP:
    def __init__(self, cdp_url=None, headless=None):
        pass

    async def check_available(self):
        return True


def test_versions_check_present(tmp_home, no_llm, monkeypatch):
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    versions_check = next((c for c in checks if c["name"] == "versions"), None)
    assert versions_check is not None
    assert versions_check["status"] == "ok"
    assert versions_check["duration_ms"] == 0
    details = versions_check["details"]
    assert "python" in details
    assert "cliany_site" in details
    assert "click" in details


def test_versions_check_python_value(tmp_home, no_llm, monkeypatch):
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    versions_check = next(c for c in checks if c["name"] == "versions")
    expected_python = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    assert versions_check["details"]["python"] == expected_python


def test_versions_check_pkg_not_installed(tmp_home, no_llm, monkeypatch):
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    import importlib.metadata as importlib_metadata

    original_version = importlib_metadata.version

    def mock_version(pkg):
        if pkg == "openai":
            raise importlib_metadata.PackageNotFoundError(pkg)
        return original_version(pkg)

    monkeypatch.setattr(importlib_metadata, "version", mock_version)
    monkeypatch.setattr("cliany_site.commands.doctor.importlib_metadata", importlib_metadata)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    versions_check = next(c for c in checks if c["name"] == "versions")
    assert versions_check["details"]["openai"] == "not installed"


def test_adapter_stats_check_present_empty(tmp_home, no_llm, monkeypatch):
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    adapter_check = next((c for c in checks if c["name"] == "adapter_stats"), None)
    assert adapter_check is not None
    assert adapter_check["status"] == "ok"
    assert adapter_check["duration_ms"] == 0
    details = adapter_check["details"]
    assert "adapter_count" in details
    assert "command_count" in details
    assert details["adapter_count"] == 0
    assert details["command_count"] == 0


def test_adapter_stats_counts_adapters(tmp_home, no_llm, monkeypatch):
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)

    a_dir = adapters_dir / "a.com"
    a_dir.mkdir()
    (a_dir / "metadata.json").write_text(json.dumps({
        "schema_version": 3, "domain": "a.com",
        "commands": {"search": {}, "view": {}}
    }))

    b_dir = adapters_dir / "b.com"
    b_dir.mkdir()
    (b_dir / "metadata.json").write_text(json.dumps({
        "schema_version": 3, "domain": "b.com",
        "commands": {"login": {}}
    }))

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    adapter_check = next(c for c in checks if c["name"] == "adapter_stats")
    assert adapter_check["details"]["adapter_count"] == 2
    assert adapter_check["details"]["command_count"] == 3


def test_adapter_stats_no_commands_field(tmp_home, no_llm, monkeypatch):
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)

    with_cmds = adapters_dir / "with.com"
    with_cmds.mkdir()
    (with_cmds / "metadata.json").write_text(json.dumps({
        "schema_version": 3, "domain": "with.com",
        "commands": {"cmd1": {}, "cmd2": {}}
    }))

    no_cmds = adapters_dir / "no-cmds.com"
    no_cmds.mkdir()
    (no_cmds / "metadata.json").write_text(json.dumps({
        "schema_version": 3, "domain": "no-cmds.com"
    }))

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    adapter_check = next(c for c in checks if c["name"] == "adapter_stats")
    assert adapter_check["details"]["adapter_count"] == 2
    assert adapter_check["details"]["command_count"] == 2
