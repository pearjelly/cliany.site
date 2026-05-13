import os
import pytest
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.config import ClanySiteConfig, load_config, reset_config
from cliany_site.envelope import ErrorCode


@pytest.fixture(autouse=True)
def _reset_config():
    reset_config()
    yield
    reset_config()


def test_config_has_browser_provider_field():
    config = ClanySiteConfig()
    assert hasattr(config, "browser_provider")
    assert config.browser_provider == ""


def test_config_has_obscura_fields():
    config = ClanySiteConfig()
    assert hasattr(config, "obscura_port")
    assert config.obscura_port == 9223
    assert hasattr(config, "obscura_version")
    assert config.obscura_version == ""
    assert hasattr(config, "obscura_ready_timeout")
    assert config.obscura_ready_timeout == 30.0
    assert hasattr(config, "obscura_auto_upgrade")
    assert config.obscura_auto_upgrade is False


def test_load_config_reads_browser_provider_from_env(monkeypatch):
    monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
    config = load_config()
    assert config.browser_provider == "obscura"


def test_load_config_reads_obscura_port_from_env(monkeypatch):
    monkeypatch.setenv("CLIANY_OBSCURA_PORT", "9300")
    config = load_config()
    assert config.obscura_port == 9300


def test_load_config_auto_upgrade_default_false():
    config = load_config()
    assert config.obscura_auto_upgrade is False


def test_error_codes_exist():
    assert hasattr(ErrorCode, "E_UNSUPPORTED_PLATFORM")
    assert hasattr(ErrorCode, "E_MISSING_CAPABILITY")
    assert hasattr(ErrorCode, "E_PROVIDER_NOT_FOUND")
    assert hasattr(ErrorCode, "E_PROVIDER_VERSION_TOO_OLD")
    assert hasattr(ErrorCode, "E_BINARY_NOT_FOUND")
    assert hasattr(ErrorCode, "E_STALE_PID")
    assert hasattr(ErrorCode, "E_PORT_CONFLICT")
    assert hasattr(ErrorCode, "E_DOWNLOAD_FAILED")
    assert hasattr(ErrorCode, "E_VERSION_MISMATCH")


def test_cli_has_obscura_group():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "obscura" in result.output


def test_default_provider_is_empty_string():
    config = load_config()
    assert config.browser_provider == ""