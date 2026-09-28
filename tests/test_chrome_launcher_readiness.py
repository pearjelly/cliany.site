from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cliany_site.browser import launcher


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
    monkeypatch.setattr(launcher.time, "sleep", waits.append)

    with pytest.raises(TimeoutError, match=r"20 秒内 CDP 端口 48793 未就绪"):
        launcher.launch_chrome(48793, headless=True)

    assert waits == [0.5] * 40
    process.terminate.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=5)
