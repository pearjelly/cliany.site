import json
import pytest
from click.testing import CliRunner

from cliany_site.cli import cli


def test_doctor_returns_checks_list(tmp_home, no_llm, monkeypatch):
    """Test that doctor returns checks array in data.checks"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass
        
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")
    
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=True)
    print("Output:", result.output)
    print("Exit code:", result.exit_code)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "data" in data
    assert "checks" in data["data"]
    checks = data["data"]["checks"]
    assert isinstance(checks, list)
    assert len(checks) >= 7
    for check in checks:
        assert "name" in check
        assert "status" in check
        assert "duration_ms" in check
        assert "details" in check or check["details"] is None
        assert check["status"] in ["ok", "fail", "warning"]


def test_doctor_legacy_adapter_warning(tmp_home, no_llm, monkeypatch):
    """Test that legacy adapter triggers warning"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass
        
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")
    
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    legacy_dir = adapters_dir / "test.com"
    legacy_dir.mkdir()
    (legacy_dir / "metadata.json").write_text('{"schema_version": "1", "domain": "test.com", "commands": []}')
    (legacy_dir / "commands.py").write_text("import click\n@click.group()\ndef cli(): pass")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    legacy_check = next(c for c in checks if c["name"] == "legacy_adapters")
    assert legacy_check["status"] == "warning"
    assert legacy_check["details"]["count"] == 1


def test_doctor_healed_pending_warning(tmp_home, no_llm, monkeypatch):
    """Test that healed pending triggers warning"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass
        
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")
    
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    healed_dir = adapters_dir / "test.com"
    healed_dir.mkdir()
    (healed_dir / "metadata.healed.json").write_text('{"schema_version": "2", "domain": "test.com", "commands": []}')

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    healed_check = next(c for c in checks if c["name"] == "healed_pending")
    assert healed_check["status"] == "warning"
    assert healed_check["details"]["count"] == 1


def test_doctor_registry_check_ok(tmp_home, no_llm, monkeypatch):
    """Test registry check is ok with empty adapters dir"""
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
    checks = data["data"]["checks"]
    registry_check = next(c for c in checks if c["name"] == "registry")
    assert registry_check["status"] == "ok"
    assert registry_check["details"]["conflict_count"] == 0


def test_doctor_output_is_envelope(tmp_home, no_llm, monkeypatch):
    """Test that output follows envelope format"""
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
    assert "ok" in data
    assert "version" in data
    assert "command" in data
    assert "data" in data
    assert "error" in data
    assert "meta" in data
    assert data["command"] == "doctor"
    assert data["ok"] is True
    assert "checks" in data["data"]
    checks = data["data"]["checks"]
    assert isinstance(checks, list)
    assert len(checks) >= 7
    for check in checks:
        assert "name" in check
        assert "status" in check
        assert "duration_ms" in check
        assert "details" in check or check["details"] is None
        assert check["status"] in ["ok", "fail", "warning"]


def test_doctor_legacy_adapter_warning(tmp_home, no_llm, monkeypatch):
    """Test that legacy adapter triggers warning"""
    class MockCDP:
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    legacy_dir = adapters_dir / "test.com"
    legacy_dir.mkdir()
    (legacy_dir / "metadata.json").write_text('{"schema_version": "1", "domain": "test.com", "commands": []}')
    (legacy_dir / "commands.py").write_text("import click\n@click.group()\ndef cli(): pass")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    legacy_check = next(c for c in checks if c["name"] == "legacy_adapters")
    assert legacy_check["status"] == "warning"
    assert legacy_check["details"]["count"] == 1


def test_doctor_healed_pending_warning(tmp_home, no_llm, monkeypatch):
    """Test that healed pending triggers warning"""
    class MockCDP:
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    healed_dir = adapters_dir / "test.com"
    healed_dir.mkdir()
    (healed_dir / "metadata.healed.json").write_text('{"schema_version": "2", "domain": "test.com", "commands": []}')

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    healed_check = next(c for c in checks if c["name"] == "healed_pending")
    assert healed_check["status"] == "warning"
    assert healed_check["details"]["count"] == 1


def test_doctor_registry_check_ok(tmp_home, no_llm, monkeypatch):
    """Test registry check is ok with empty adapters dir"""
    class MockCDP:
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    registry_check = next(c for c in checks if c["name"] == "registry")
    assert registry_check["status"] == "ok"
    assert registry_check["details"]["conflict_count"] == 0


def test_doctor_output_is_envelope(tmp_home, no_llm, monkeypatch):
    """Test that output follows envelope format"""
    class MockCDP:
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "ok" in data
    assert "version" in data
    assert "command" in data
    assert "data" in data
    assert "error" in data
    assert "meta" in data
    assert data["command"] == "doctor"
    assert data["ok"] is True
    assert "checks" in data["data"]
    checks = data["data"]["checks"]
    assert isinstance(checks, list)
    assert len(checks) >= 7
    for check in checks:
        assert "name" in check
        assert "status" in check
        assert "duration_ms" in check
        assert "details" in check or check["details"] is None
        assert check["status"] in ["ok", "fail", "warning"]


def test_doctor_legacy_adapter_warning(tmp_home, no_llm, monkeypatch):
    """Test that legacy adapter triggers warning"""
    # Mock CDP
    class MockCDP:
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    legacy_dir = adapters_dir / "test.com"
    legacy_dir.mkdir()
    (legacy_dir / "metadata.json").write_text('{"schema_version": "1", "domain": "test.com", "commands": []}')
    (legacy_dir / "commands.py").write_text("import click\n@click.group()\ndef cli(): pass")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    legacy_check = next(c for c in checks if c["name"] == "legacy_adapters")
    assert legacy_check["status"] == "warning"
    assert legacy_check["details"]["count"] == 1


def test_doctor_healed_pending_warning(tmp_home, no_llm, monkeypatch):
    """Test that healed pending triggers warning"""
    # Mock CDP
    class MockCDP:
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    healed_dir = adapters_dir / "test.com"
    healed_dir.mkdir()
    (healed_dir / "metadata.healed.json").write_text('{"schema_version": "2", "domain": "test.com", "commands": []}')

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    healed_check = next(c for c in checks if c["name"] == "healed_pending")
    assert healed_check["status"] == "warning"
    assert healed_check["details"]["count"] == 1


def test_doctor_registry_check_ok(tmp_home, no_llm, monkeypatch):
    """Test registry check is ok with empty adapters dir"""
    # Mock CDP
    class MockCDP:
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    registry_check = next(c for c in checks if c["name"] == "registry")
    assert registry_check["status"] == "ok"
    assert registry_check["details"]["conflict_count"] == 0


def test_doctor_output_is_envelope(tmp_home, no_llm, monkeypatch):
    """Test that output follows envelope format"""
    # Mock CDP
    class MockCDP:
        async def check_available(self):
            return True
    
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "ok" in data
    assert "version" in data
    assert "command" in data
    assert "data" in data
    assert "error" in data
    assert "meta" in data
    assert data["command"] == "doctor"
    assert data["ok"] is True
    assert "checks" in data["data"]
    checks = data["data"]["checks"]
    assert isinstance(checks, list)
    assert len(checks) >= 7
    for check in checks:
        assert "name" in check
        assert "status" in check
        assert "duration_ms" in check
        assert "details" in check or check["details"] is None
        assert check["status"] in ["ok", "fail", "warning"]


def test_doctor_legacy_adapter_warning(tmp_home, no_llm, mock_cdp):
    """Test that legacy adapter triggers warning"""
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    legacy_dir = adapters_dir / "test.com"
    legacy_dir.mkdir()
    (legacy_dir / "metadata.json").write_text('{"schema_version": "1", "domain": "test.com", "commands": []}')
    (legacy_dir / "commands.py").write_text("import click\n@click.group()\ndef cli(): pass")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    legacy_check = next(c for c in checks if c["name"] == "legacy_adapters")
    assert legacy_check["status"] == "warning"
    assert legacy_check["details"]["count"] == 1


def test_doctor_healed_pending_warning(tmp_home, no_llm, mock_cdp):
    """Test that healed pending triggers warning"""
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    healed_dir = adapters_dir / "test.com"
    healed_dir.mkdir()
    (healed_dir / "metadata.healed.json").write_text('{"schema_version": "2", "domain": "test.com", "commands": []}')

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    healed_check = next(c for c in checks if c["name"] == "healed_pending")
    assert healed_check["status"] == "warning"
    assert healed_check["details"]["count"] == 1


def test_doctor_registry_check_ok(tmp_home, no_llm, mock_cdp):
    """Test registry check is ok with empty adapters dir"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    registry_check = next(c for c in checks if c["name"] == "registry")
    assert registry_check["status"] == "ok"
    assert registry_check["details"]["conflict_count"] == 0


def test_doctor_output_is_envelope(tmp_home, no_llm, mock_cdp):
    """Test that output follows envelope format"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "ok" in data
    assert "version" in data
    assert "command" in data
    assert "data" in data
    assert "error" in data
    assert "meta" in data
    assert data["command"] == "doctor"
    assert data["ok"] is True
    assert "checks" in data["data"]
    checks = data["data"]["checks"]
    assert isinstance(checks, list)
    assert len(checks) >= 7
    for check in checks:
        assert "name" in check
        assert "status" in check
        assert "duration_ms" in check
        assert "details" in check or check["details"] is None
        assert check["status"] in ["ok", "fail", "warning"]


def test_doctor_legacy_adapter_warning(tmp_home):
    """Test that legacy adapter triggers warning"""
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    legacy_dir = adapters_dir / "test.com"
    legacy_dir.mkdir()
    (legacy_dir / "metadata.json").write_text('{"schema_version": "1", "domain": "test.com", "commands": []}')
    (legacy_dir / "commands.py").write_text("import click\n@click.group()\ndef cli(): pass")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    legacy_check = next(c for c in checks if c["name"] == "legacy_adapters")
    assert legacy_check["status"] == "warning"
    assert legacy_check["details"]["count"] == 1


def test_doctor_healed_pending_warning(tmp_home):
    """Test that healed pending triggers warning"""
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    healed_dir = adapters_dir / "test.com"
    healed_dir.mkdir()
    (healed_dir / "metadata.healed.json").write_text('{"schema_version": "2", "domain": "test.com", "commands": []}')

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    healed_check = next(c for c in checks if c["name"] == "healed_pending")
    assert healed_check["status"] == "warning"
    assert healed_check["details"]["count"] == 1


def test_doctor_registry_check_ok(tmp_home):
    """Test registry check is ok with empty adapters dir"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    registry_check = next(c for c in checks if c["name"] == "registry")
    assert registry_check["status"] == "ok"
    assert registry_check["details"]["conflict_count"] == 0


def test_doctor_output_is_envelope(tmp_home):
    """Test that output follows envelope format"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "ok" in data
    assert "version" in data
    assert "command" in data
    assert "data" in data
    assert "error" in data
    assert "meta" in data
    assert data["command"] == "doctor"
    assert data["ok"] is True
    assert "checks" in data["data"]