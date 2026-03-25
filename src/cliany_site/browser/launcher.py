# src/cliany_site/browser/launcher.py
from pathlib import Path
import shutil
import subprocess
import time
import os
import urllib.error
import urllib.request
import json
from typing import Optional


class ChromeNotFoundError(Exception):
    """Chrome 二进制文件未找到"""

    pass


def find_chrome_binary() -> Optional[Path]:
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


def detect_running_chrome(port: int = 9222) -> Optional[str]:
    """检测指定端口是否有运行中的 Chrome，返回 WebSocket URL"""
    try:
        with urllib.request.urlopen(
            f"http://localhost:{port}/json/version", timeout=2
        ) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data.get("webSocketDebuggerUrl")
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        pass
    return None


def launch_chrome(port: int = 9222, headless: bool = False) -> subprocess.Popen:
    binary = find_chrome_binary()
    if not binary:
        raise ChromeNotFoundError(
            "未找到 Chrome 浏览器，请安装 Chrome 或确认 Chrome 可执行文件在 PATH 中"
        )

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

    for _ in range(20):
        time.sleep(0.5)
        ws_url = detect_running_chrome(port)
        if ws_url:
            return proc

    proc.terminate()
    raise TimeoutError(f"Chrome 启动后 10 秒内 CDP 端口 {port} 未就绪")


def ensure_chrome(port: int = 9222) -> tuple[str, Optional[subprocess.Popen]]:
    ws_url = detect_running_chrome(port)
    if ws_url:
        return (ws_url, None)

    proc = launch_chrome(port)
    ws_url = detect_running_chrome(port)
    if not ws_url:
        proc.terminate()
        raise RuntimeError(f"Chrome 已启动但无法获取 WebSocket URL (port {port})")
    return (ws_url, proc)
