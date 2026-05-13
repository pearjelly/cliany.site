import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cliany_site.binary.process import (
    CleanupResult,
    ProcessError,
    ProcessHandle,
    ProcessManager,
    ProcessStatus,
)
from cliany_site.envelope import ErrorCode


class TestFindFreePort:
    def test_find_free_port_available(self, tmp_path):
        manager = ProcessManager(pid_file=tmp_path / "obscura.pid")
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.bind.return_value = None

        with patch("socket.socket", return_value=mock_sock):
            port = manager.find_free_port(start=9300, max_tries=5)

        assert port == 9300

    def test_find_free_port_all_taken(self, tmp_path):
        manager = ProcessManager(pid_file=tmp_path / "obscura.pid")
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)
        mock_sock.bind.side_effect = OSError("端口占用")

        with patch("socket.socket", return_value=mock_sock):
            with pytest.raises(ProcessError) as exc_info:
                manager.find_free_port(start=9300, max_tries=3)

        assert exc_info.value.error_code == ErrorCode.E_PORT_CONFLICT


class TestGetStatus:
    def test_get_status_no_process(self, tmp_path):
        pid_file = tmp_path / "obscura.pid"
        manager = ProcessManager(pid_file=pid_file)
        status = manager.get_status()

        assert status.state == "stopped"
        assert status.pid is None
        assert status.stale is False

    def test_get_status_stale(self, tmp_path):
        pid_file = tmp_path / "obscura.pid"
        pid_file.write_text("99999", encoding="utf-8")
        manager = ProcessManager(pid_file=pid_file)

        with patch("os.kill", side_effect=ProcessLookupError):
            status = manager.get_status()

        assert status.state == "stale"
        assert status.pid == 99999
        assert status.stale is True


class TestCleanupStale:
    def test_cleanup_stale_removes_pid_file(self, tmp_path):
        pid_file = tmp_path / "obscura.pid"
        pid_file.write_text("99999", encoding="utf-8")
        manager = ProcessManager(pid_file=pid_file)

        with patch("os.kill", side_effect=ProcessLookupError):
            result = manager.cleanup_stale()

        assert not pid_file.exists()
        assert isinstance(result, CleanupResult)
        assert 99999 in result.removed_pids
        assert pid_file in result.removed_pid_files

    def test_cleanup_stale_no_pid_file(self, tmp_path):
        manager = ProcessManager(pid_file=tmp_path / "obscura.pid")
        result = manager.cleanup_stale()

        assert result.removed_pids == []
        assert result.removed_pid_files == []
        assert result.warnings == []

    def test_cleanup_stale_live_process_not_removed(self, tmp_path):
        pid_file = tmp_path / "obscura.pid"
        current_pid = os.getpid()
        pid_file.write_text(str(current_pid), encoding="utf-8")
        manager = ProcessManager(pid_file=pid_file)

        result = manager.cleanup_stale()

        assert pid_file.exists()
        assert result.removed_pids == []


class TestReadyProbe:
    def test_ready_probe_success(self, tmp_path):
        pid_file = tmp_path / "obscura.pid"
        current_pid = os.getpid()
        pid_file.write_text(str(current_pid), encoding="utf-8")
        manager = ProcessManager(pid_file=pid_file)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = manager.is_running(port=9300)

        assert result is True

    def test_ready_probe_timeout(self, tmp_path):
        pid_file = tmp_path / "obscura.pid"
        current_pid = os.getpid()
        pid_file.write_text(str(current_pid), encoding="utf-8")
        manager = ProcessManager(pid_file=pid_file)

        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            result = manager.is_running(port=9300)

        assert result is False
