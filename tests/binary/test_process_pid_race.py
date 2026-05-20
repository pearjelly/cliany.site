# pyright: reportMissingImports=false

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cliany_site.binary.process import ProcessHandle, ProcessManager


class FakePipe:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_pid_file_written_atomically(tmp_path):
    pid_file = tmp_path / "run" / "obscura.pid"
    manager = ProcessManager(pid_file=pid_file)
    proc = Mock(pid=4321)

    with patch("subprocess.Popen", return_value=proc) as popen, \
         patch.object(manager, "_is_port_available", return_value=True), \
         patch.object(manager, "_wait_ready", return_value=True):
        handle = manager.start(Path("/fake/obscura"), port=9333, timeout=0.01)

    assert handle.pid == 4321
    assert pid_file.exists()
    assert pid_file.read_text(encoding="utf-8") == "4321"
    assert list(tmp_path.rglob("*.tmp")) == []
    popen.assert_called_once()


def test_stop_handles_stale_pid(tmp_path):
    pid_file = tmp_path / "obscura.pid"
    pid_file.write_text("999999", encoding="utf-8")
    manager = ProcessManager(pid_file=pid_file)
    handle = ProcessHandle(pid=1234, port=9333, binary_path=Path("/fake/obscura"))

    with patch("os.kill", side_effect=ProcessLookupError):
        manager.stop(handle)

    assert not pid_file.exists()


def test_stop_cleans_pid_file(tmp_path):
    pid_file = tmp_path / "obscura.pid"
    pid_file.write_text("1234", encoding="utf-8")
    manager = ProcessManager(pid_file=pid_file)
    handle = ProcessHandle(pid=1234, port=9333, binary_path=Path("/fake/obscura"))

    with patch("os.kill", side_effect=[None, ProcessLookupError]) as kill:
        manager.stop(handle)

    assert not pid_file.exists()
    kill.assert_any_call(1234, 15)


def test_subprocess_pipes_closed_on_timeout(tmp_path):
    pid_file = tmp_path / "obscura.pid"
    manager = ProcessManager(pid_file=pid_file)
    stdout = FakePipe()
    stderr = FakePipe()
    proc = Mock(pid=4321, stdout=stdout, stderr=stderr)
    proc.communicate.return_value = (b"", b"")

    with patch("subprocess.Popen", return_value=proc) as popen, \
         patch.object(manager, "_is_port_available", return_value=True), \
         patch.object(manager, "_wait_ready", return_value=False):
        with pytest.raises(Exception):
            manager.start(Path("/fake/obscura"), port=9333, timeout=0.01)

    kwargs = popen.call_args.kwargs
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.PIPE
    proc.terminate.assert_called_once()
    proc.communicate.assert_called_once_with(timeout=5)
    assert stdout.closed is True
    assert stderr.closed is True
