import socket
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cliany_site.browser import launcher


def test_tcp_port_probe_reports_listening_state():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        assert launcher._tcp_port_open(port) is True
    assert launcher._tcp_port_open(port) is False


def test_chrome_launch_reports_early_exit(monkeypatch):
    process = MagicMock()
    process.poll.return_value = 127
    monkeypatch.setattr(launcher, "find_chrome_binary", lambda: Path("/chrome"))
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(launcher, "detect_running_chrome", lambda port: None)
    monkeypatch.setattr(launcher.time, "sleep", lambda seconds: None)

    with pytest.raises(RuntimeError, match=r"提前退出 \(exit=127, port=48792\)"):
        launcher.launch_chrome(48792, headless=True)

    assert process.poll.call_count == 1
    process.terminate.assert_not_called()


def test_chrome_launch_waits_twenty_seconds_and_cleans_up(monkeypatch):
    process = MagicMock()
    process.poll.return_value = None
    waits = []
    monkeypatch.setattr(launcher, "find_chrome_binary", lambda: Path("/chrome"))
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(launcher, "detect_running_chrome", lambda port: None)
    monkeypatch.setattr(launcher, "_tcp_port_open", lambda port: False)
    monkeypatch.setattr(launcher.time, "sleep", waits.append)

    with pytest.raises(TimeoutError, match=r"20 秒内 CDP 端口 48793 未就绪 .*tcp_open=False"):
        launcher.launch_chrome(48793, headless=True)

    assert waits == [0.5] * 40
    process.terminate.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=5)


def test_chrome_launch_reports_bound_port_without_exposing_browser_output(monkeypatch):
    process = MagicMock()
    process.poll.return_value = None
    monkeypatch.setattr(launcher, "find_chrome_binary", lambda: Path("/chrome"))
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(launcher, "detect_running_chrome", lambda port: None)
    monkeypatch.setattr(launcher, "_tcp_port_open", lambda port: True)
    monkeypatch.setattr(launcher.time, "sleep", lambda seconds: None)

    with pytest.raises(TimeoutError, match=r"tcp_open=True") as exc_info:
        launcher.launch_chrome(48794, headless=True)

    assert "elapsed=" in str(exc_info.value)
    assert "profile_created=" in str(exc_info.value)
    assert "--user-data-dir" not in str(exc_info.value)


def test_chrome_launch_reports_exit_at_timeout_boundary(monkeypatch):
    process = MagicMock()
    process.poll.side_effect = [None] * 40 + [127]
    monkeypatch.setattr(launcher, "find_chrome_binary", lambda: Path("/chrome"))
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(launcher, "detect_running_chrome", lambda port: None)
    monkeypatch.setattr(launcher, "_tcp_port_open", lambda port: False)
    monkeypatch.setattr(launcher.time, "sleep", lambda seconds: None)

    with pytest.raises(TimeoutError, match=r"process=exit=127"):
        launcher.launch_chrome(48796, headless=True)

    process.terminate.assert_not_called()


def test_chrome_launch_accepts_slow_start_before_wait_limit(monkeypatch):
    process = MagicMock()
    process.poll.return_value = None
    probes = iter([None] * 35 + ["ws://browser"])
    monkeypatch.setattr(launcher, "find_chrome_binary", lambda: Path("/chrome"))
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(launcher, "detect_running_chrome", lambda port: next(probes))
    monkeypatch.setattr(launcher.time, "sleep", lambda seconds: None)

    assert launcher.launch_chrome(48795, headless=True) is process
    assert process.poll.call_count == 35
    process.terminate.assert_not_called()
