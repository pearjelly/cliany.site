import json
import pytest
from click.testing import CliRunner

from cliany_site.cli import cli


def test_doctor_has_schema_version(tmp_home, no_llm, monkeypatch):
    """Test that doctor data includes schema_version=3"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr("cliany_site.commands.doctor.Path.cwd", lambda: tmp_home)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "data" in data
    assert "schema_version" in data["data"]
    assert data["data"]["schema_version"] == 3


def test_doctor_has_capability_fields(tmp_home, no_llm, monkeypatch):
    """Test that doctor data includes capability fields"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "data" in data
    required_fields = ["capability_router", "network_capture", "console_capture", "diagnose_llm"]
    for field in required_fields:
        assert field in data["data"]


def test_doctor_no_llm_key_returns_ok(tmp_home, no_llm, monkeypatch):
    """Test that doctor returns ok=True even without LLM key, with llm status=warning"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    # Ensure no LLM keys
    monkeypatch.delenv("CLIANY_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLIANY_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    checks = data["data"]["checks"]
    llm_check = next(c for c in checks if c["name"] == "llm")
    assert llm_check["status"] == "warning"


def test_legacy_adapter_count(tmp_home, no_llm, monkeypatch):
    """Test that legacy_adapter_count counts adapters with schema_version != 3"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    # Create a v2 adapter
    v2_dir = adapters_dir / "test.com"
    v2_dir.mkdir()
    (v2_dir / "metadata.json").write_text('{"schema_version": 2, "domain": "test.com", "commands": []}')
    # Create a v3 adapter
    v3_dir = adapters_dir / "example.com"
    v3_dir.mkdir()
    (v3_dir / "metadata.json").write_text('{"schema_version": 3, "domain": "example.com", "commands": []}')

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "legacy_adapter_count" in data["data"]
    assert data["data"]["legacy_adapter_count"] == 1


def test_agent_md_reports_warning_for_missing_sentinel(tmp_home, no_llm, monkeypatch):
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    class MockPath:
        @classmethod
        def home(cls):
            return tmp_home

        @classmethod
        def cwd(cls):
            return tmp_home

    monkeypatch.setattr("cliany_site.commands.doctor.Path", MockPath)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    agent_check = next(c for c in data["data"]["checks"] if c["name"] == "agent_md")
    assert agent_check["status"] == "warning"
    assert agent_check["details"]["status"] in {"no_sentinel", "missing"}
    assert agent_check["details"]["path"] in {"AGENT.md", "AGENTS.md"}
    assert "cliany-site explore" in (agent_check["details"]["message"] or "")
