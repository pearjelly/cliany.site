import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.binary.cache import CacheError
from cliany_site.cli import cli
from cliany_site.envelope import ErrorCode


@pytest.fixture()
def runner():
    return CliRunner()


def _invoke(runner, args):
    return runner.invoke(cli, args, catch_exceptions=False)


def _json(result):
    return json.loads(result.output)


def _make_cm(installed_versions=None, active_version=None):
    cm = MagicMock()
    cm.list_versions.return_value = installed_versions or []
    cm.get_active_version.return_value = active_version
    cm.remove_version.return_value = None
    cm.set_active_version.return_value = None
    return cm


def _make_pm(state="stopped", pid=None, stale=False):
    pm_inst = MagicMock()
    status = MagicMock()
    status.state = state
    status.pid = pid
    status.stale = stale
    pm_inst.get_status.return_value = status
    return pm_inst


class TestClean:
    def test_clean_specific_version_success(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
            cm = _make_cm(installed_versions=["0.1.0", "0.2.0"], active_version="0.2.0")
            MockCM.return_value = cm

            result = _invoke(runner, ["obscura", "clean", "--version", "0.1.0", "--json"])
            assert result.exit_code == 0
            data = _json(result)
            assert data["ok"] is True
            assert "0.1.0" in data["data"]["removed"]
            cm.remove_version.assert_called_once_with("0.1.0")

    def test_clean_nonexistent_version_fails(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
            cm = _make_cm()
            cm.remove_version.side_effect = CacheError(
                "版本 9.9.9 未安装，无法删除", ErrorCode.E_BINARY_NOT_FOUND
            )
            MockCM.return_value = cm

            result = _invoke(runner, ["obscura", "clean", "--version", "9.9.9", "--json"])
            assert result.exit_code != 0
            data = _json(result)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_BINARY_NOT_FOUND"

    def test_clean_all_skips_active_version(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
            cm = _make_cm(installed_versions=["0.1.0", "0.2.0", "0.3.0"], active_version="0.2.0")
            MockCM.return_value = cm

            result = _invoke(runner, ["obscura", "clean", "--all", "--json"])
            assert result.exit_code == 0
            data = _json(result)
            assert data["ok"] is True
            assert "0.2.0" in data["data"]["skipped"]
            removed = data["data"]["removed"]
            assert "0.1.0" in removed
            assert "0.3.0" in removed
            assert "0.2.0" not in removed

    def test_clean_all_no_versions(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
            cm = _make_cm(installed_versions=[], active_version=None)
            MockCM.return_value = cm

            result = _invoke(runner, ["obscura", "clean", "--all", "--json"])
            assert result.exit_code == 0
            data = _json(result)
            assert data["ok"] is True
            assert data["data"]["removed"] == []

    def test_clean_no_args_fails(self, runner):
        result = _invoke(runner, ["obscura", "clean", "--json"])
        assert result.exit_code != 0
        data = _json(result)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_INVALID_PARAM"

    def test_clean_version_and_all_together_fails(self, runner):
        result = _invoke(runner, ["obscura", "clean", "--version", "0.1.0", "--all", "--json"])
        assert result.exit_code != 0
        data = _json(result)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_INVALID_PARAM"


class TestRollback:
    def test_rollback_success(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
            cm = _make_cm(installed_versions=["0.1.0", "0.2.0"], active_version="0.2.0")
            MockCM.return_value = cm

            result = _invoke(runner, ["obscura", "rollback", "--json"])
            assert result.exit_code == 0
            data = _json(result)
            assert data["ok"] is True
            assert data["data"]["active_version"] == "0.1.0"
            assert data["data"]["previous_version"] == "0.2.0"
            cm.set_active_version.assert_called_once_with("0.1.0")

    def test_rollback_single_version_fails(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
            cm = _make_cm(installed_versions=["0.1.0"], active_version="0.1.0")
            MockCM.return_value = cm

            result = _invoke(runner, ["obscura", "rollback", "--json"])
            assert result.exit_code != 0
            data = _json(result)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_BINARY_NOT_FOUND"

    def test_rollback_no_installed_versions_fails(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
            cm = _make_cm(installed_versions=[], active_version=None)
            MockCM.return_value = cm

            result = _invoke(runner, ["obscura", "rollback", "--json"])
            assert result.exit_code != 0
            data = _json(result)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_BINARY_NOT_FOUND"

    def test_rollback_already_oldest_fails(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM:
            cm = _make_cm(installed_versions=["0.1.0", "0.2.0"], active_version="0.1.0")
            MockCM.return_value = cm

            result = _invoke(runner, ["obscura", "rollback", "--json"])
            assert result.exit_code != 0
            data = _json(result)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_BINARY_NOT_FOUND"


class TestUpgrade:
    def test_upgrade_success(self, runner, tmp_path):
        fake_binary = tmp_path / "0.3.0" / "obscura"
        fake_binary.parent.mkdir(parents=True)
        fake_binary.write_text("fake")

        with patch("cliany_site.commands.obscura.CacheManager") as MockCM, \
             patch("cliany_site.commands.obscura._download_and_install") as mock_dl, \
             patch("cliany_site.commands.obscura.normalize_platform"):
            cm = _make_cm()
            MockCM.return_value = cm
            mock_dl.return_value = fake_binary

            result = _invoke(runner, ["obscura", "upgrade", "0.3.0", "--json"])
            assert result.exit_code == 0
            data = _json(result)
            assert data["ok"] is True
            assert data["data"]["version"] == "0.3.0"
            assert data["data"]["active_version"] == "0.3.0"
            assert "path" in data["data"]
            mock_dl.assert_called_once()
            cm.set_active_version.assert_called_once_with("0.3.0")

    def test_upgrade_invalid_version_format(self, runner):
        result = _invoke(runner, ["obscura", "upgrade", "latest", "--json"])
        assert result.exit_code != 0
        data = _json(result)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_INVALID_PARAM"

    def test_upgrade_download_failure(self, runner):
        from cliany_site.binary.cache import CacheError

        with patch("cliany_site.commands.obscura.CacheManager") as MockCM, \
             patch("cliany_site.commands.obscura._download_and_install") as mock_dl, \
             patch("cliany_site.commands.obscura.normalize_platform"):
            cm = _make_cm()
            MockCM.return_value = cm
            exc = CacheError("下载失败", ErrorCode.E_DOWNLOAD_FAILED)
            mock_dl.side_effect = exc

            result = _invoke(runner, ["obscura", "upgrade", "0.3.0", "--json"])
            assert result.exit_code != 0
            data = _json(result)
            assert data["ok"] is False


class TestDoctor:
    def test_doctor_output_fields(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM, \
             patch("cliany_site.commands.obscura.ProcessManager") as MockPM:
            cm = _make_cm(installed_versions=["0.1.0", "0.2.0"], active_version="0.2.0")
            MockCM.return_value = cm
            MockPM.return_value = _make_pm(state="stopped", pid=None, stale=False)

            result = _invoke(runner, ["obscura", "doctor", "--json"])
            assert result.exit_code == 0
            data = _json(result)
            assert data["ok"] is True
            d = data["data"]

            assert "cache" in d
            assert "installed_versions" in d["cache"]
            assert "active_version" in d["cache"]
            assert d["cache"]["installed_versions"] == ["0.1.0", "0.2.0"]
            assert d["cache"]["active_version"] == "0.2.0"

            assert "stale_pid" in d
            assert d["stale_pid"] is False

            assert "platform" in d
            assert "target_key" in d["platform"]

            assert "capabilities" in d
            caps = d["capabilities"]
            assert caps["provider"] == "obscura"
            assert "supports_axtree" in caps

            assert "process" in d
            assert "state" in d["process"]
            assert "pid" in d["process"]

    def test_doctor_stale_pid_true(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM, \
             patch("cliany_site.commands.obscura.ProcessManager") as MockPM:
            cm = _make_cm()
            MockCM.return_value = cm
            MockPM.return_value = _make_pm(state="stale", pid=12345, stale=True)

            result = _invoke(runner, ["obscura", "doctor", "--json"])
            assert result.exit_code == 0
            data = _json(result)
            assert data["ok"] is True
            assert data["data"]["stale_pid"] is True
            assert data["data"]["process"]["state"] == "stale"
            assert data["data"]["process"]["pid"] == 12345

    def test_doctor_empty_cache(self, runner):
        with patch("cliany_site.commands.obscura.CacheManager") as MockCM, \
             patch("cliany_site.commands.obscura.ProcessManager") as MockPM:
            cm = _make_cm(installed_versions=[], active_version=None)
            MockCM.return_value = cm
            MockPM.return_value = _make_pm()

            result = _invoke(runner, ["obscura", "doctor", "--json"])
            assert result.exit_code == 0
            data = _json(result)
            assert data["ok"] is True
            assert data["data"]["cache"]["installed_versions"] == []
            assert data["data"]["cache"]["active_version"] is None
