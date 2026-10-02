# src/cliany_site/browser/launcher.py
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from cliany_site.config import get_config


class ChromeNotFoundError(Exception):
    """Chrome 二进制文件未找到"""

    pass


def find_chrome_binary() -> Path | None:
    """查找 Chrome 二进制文件路径（macOS/Linux）"""
    # macOS 路径
    mac_paths = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
    ]
    for p in mac_paths:
        if p.exists():
            return p

    # Linux PATH 查找
    linux_names = [
        "google-chrome",
        "google-chrome-stable",
        "chromium-browser",
        "chromium",
    ]
    for name in linux_names:
        path = shutil.which(name)
        if path:
            return Path(path)

    return None


def detect_running_chrome(port: int | None = None) -> str | None:
    """检测指定端口是否有运行中的 Chrome，返回 WebSocket URL"""
    if port is None:
        port = get_config().cdp_port
    try:
        with urllib.request.urlopen(
            f"http://localhost:{port}/json/version", timeout=get_config().cdp_timeout
        ) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                result: str | None = data.get("webSocketDebuggerUrl")
                return result
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        pass
    return None


def _tcp_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=0.2):
            return True
    except OSError:
        return False


def launch_chrome(port: int | None = None, headless: bool = False) -> subprocess.Popen:
    if port is None:
        port = get_config().cdp_port
    binary = find_chrome_binary()
    if not binary:
        raise ChromeNotFoundError("未找到 Chrome 浏览器，请安装 Chrome 或确认 Chrome 可执行文件在 PATH 中")

    user_data_dir = f"/tmp/cliany-site-chrome-{os.getpid()}"

    args = [
        str(binary),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if headless:
        args.append("--headless=new")

    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    started_at = time.monotonic()
    for _ in range(40):
        time.sleep(0.5)
        ws_url = detect_running_chrome(port)
        if ws_url:
            return proc
        exit_code = proc.poll()
        if exit_code is not None:
            raise RuntimeError(f"Chrome 启动后提前退出 (exit={exit_code}, port={port})")

    elapsed = time.monotonic() - started_at
    port_open = _tcp_port_open(port)
    profile_created = Path(user_data_dir).exists()
    exit_code = proc.poll()
    if exit_code is None:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    process_state = "running" if exit_code is None else f"exit={exit_code}"
    raise TimeoutError(
        f"Chrome 启动后 20 秒内 CDP 端口 {port} 未就绪 "
        f"(elapsed={elapsed:.1f}s, process={process_state}, tcp_open={port_open}, "
        f"profile_created={profile_created})"
    )


def ensure_chrome(port: int | None = None, headless: bool = False) -> tuple[str, subprocess.Popen | None]:
    if port is None:
        port = get_config().cdp_port
    ws_url = detect_running_chrome(port)
    if ws_url:
        return (ws_url, None)

    proc = launch_chrome(port, headless=headless)
    ws_url = detect_running_chrome(port)
    if not ws_url:
        proc.terminate()
        raise RuntimeError(f"Chrome 已启动但无法获取 WebSocket URL (port {port})")
    return (ws_url, proc)
