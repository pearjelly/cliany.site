import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def cache_root(tmp_path):
    return tmp_path / "obscura-cache"


def _invoke(runner, args):
    result = runner.invoke(cli, args, catch_exceptions=False)
    return result


def _json(result):
    return json.loads(result.output)


def test_status_empty_cache(runner, tmp_path):
    cache_root = tmp_path / "cache"
    with patch("cliany_site.commands.obscura.CacheManager") as MockCM, \
         patch("cliany_site.commands.obscura.ProcessManager") as MockPM:
        cm = MagicMock()
        cm.get_active_version.return_value = None
        cm.list_versions.return_value = []
        MockCM.return_value = cm

        pm = MagicMock()
        status = MagicMock()
        status.state = "stopped"
        status.pid = None
        pm.return_value.get_status.return_value = status
        MockPM.return_value = pm.return_value

        result = _invoke(runner, ["obscura", "status", "--json"])
        assert result.exit_code == 0
        data = _json(result)
        assert data["ok"] is True
        assert data["data"]["active_version"] is None
        assert data["data"]["installed_versions"] == []


def test_install_success_mocked(runner, tmp_path):
    fake_binary = tmp_path / "0.1.2" / "obscura"
    fake_binary.parent.mkdir(parents=True)
    fake_binary.write_text("fake")

    with patch("cliany_site.commands.obscura.CacheManager") as MockCM, \
         patch("cliany_site.commands.obscura._download_and_install") as mock_dl:
        cm = MagicMock()
        cm.is_installed.return_value = False
        MockCM.return_value = cm
        mock_dl.return_value = fake_binary

        result = _invoke(runner, ["obscura", "install", "0.1.2", "--json"])
        assert result.exit_code == 0
        data = _json(result)
        assert data["ok"] is True
        assert "path" in data["data"]
        assert data["data"]["already_installed"] is False
        assert data["data"]["version"] == "0.1.2"


def test_install_already_installed(runner, tmp_path):
    fake_binary = tmp_path / "obscura"
    fake_binary.write_text("fake")

    with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
        cm = MagicMock()
        cm.is_installed.return_value = True
        cm.get_binary_path.return_value = fake_binary
        MockCM.return_value = cm

        result = _invoke(runner, ["obscura", "install", "0.1.2", "--json"])
        assert result.exit_code == 0
        data = _json(result)
        assert data["ok"] is True
        assert data["data"]["already_installed"] is True
        assert data["data"]["version"] == "0.1.2"


def test_install_invalid_version_latest(runner):
    result = runner.invoke(cli, ["obscura", "install", "latest", "--json"], catch_exceptions=False)
    assert result.exit_code != 0
    data = _json(result)
    assert data["ok"] is False
    assert data["error"]["code"] == "E_INVALID_PARAM"


def test_use_not_installed(runner):
    from cliany_site.binary.cache import CacheError
    from cliany_site.envelope import ErrorCode

    with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
        cm = MagicMock()
        cm.set_active_version.side_effect = CacheError(
            "版本 9.9.9 未安装", ErrorCode.E_BINARY_NOT_FOUND
        )
        MockCM.return_value = cm

        result = runner.invoke(cli, ["obscura", "use", "9.9.9", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        data = _json(result)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_BINARY_NOT_FOUND"


def test_use_success(runner, tmp_path):
    fake_binary = tmp_path / "0.2.0" / "obscura"
    fake_binary.parent.mkdir(parents=True)
    fake_binary.write_text("fake")

    with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
        cm = MagicMock()
        cm.set_active_version.return_value = None
        cm.get_binary_path.return_value = fake_binary
        MockCM.return_value = cm

        result = _invoke(runner, ["obscura", "use", "0.2.0", "--json"])
        assert result.exit_code == 0
        data = _json(result)
        assert data["ok"] is True
        assert data["data"]["active_version"] == "0.2.0"
        assert "path" in data["data"]


def test_status_with_active_version(runner, tmp_path):
    fake_binary = tmp_path / "obscura"
    fake_binary.write_text("fake")

    with patch("cliany_site.commands.obscura.CacheManager") as MockCM, \
         patch("cliany_site.commands.obscura.ProcessManager") as MockPM:
        cm = MagicMock()
        cm.get_active_version.return_value = "0.1.2"
        cm.list_versions.return_value = ["0.1.2"]
        cm.get_binary_path.return_value = fake_binary
        MockCM.return_value = cm

        pm_inst = MagicMock()
        status = MagicMock()
        status.state = "stopped"
        status.pid = None
        pm_inst.get_status.return_value = status
        MockPM.return_value = pm_inst

        result = _invoke(runner, ["obscura", "status", "--json"])
        assert result.exit_code == 0
        data = _json(result)
        assert data["ok"] is True
        assert data["data"]["active_version"] == "0.1.2"
        assert "0.1.2" in data["data"]["installed_versions"]


def test_status_capabilities_axtree_false(runner):
    with patch("cliany_site.commands.obscura.CacheManager") as MockCM, \
         patch("cliany_site.commands.obscura.ProcessManager") as MockPM:
        cm = MagicMock()
        cm.get_active_version.return_value = None
        cm.list_versions.return_value = []
        MockCM.return_value = cm

        pm_inst = MagicMock()
        status = MagicMock()
        status.state = "stopped"
        status.pid = None
        pm_inst.get_status.return_value = status
        MockPM.return_value = pm_inst

        result = _invoke(runner, ["obscura", "status", "--json"])
        assert result.exit_code == 0
        data = _json(result)
        assert data["ok"] is True
        caps = data["data"]["capabilities"]
        assert caps["supports_axtree"] is False
        assert caps["provider"] == "obscura"
