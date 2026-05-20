from __future__ import annotations

import os
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import portalocker

from cliany_site.envelope import ErrorCode
from cliany_site.errors import ClanySiteError


class ProcessError(ClanySiteError):
    def __init__(self, message: str, error_code: str = ErrorCode.E_UNKNOWN):
        self.error_code = error_code
        super().__init__(message)


@dataclass
class ProcessHandle:
    pid: int
    port: int
    binary_path: Path


@dataclass
class ProcessStatus:
    state: str  # "running" | "stopped" | "stale"
    pid: Optional[int]
    port: Optional[int]
    pid_file: Path
    stale: bool


@dataclass
class CleanupResult:
    removed_pids: list = field(default_factory=list)
    removed_pid_files: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class ProcessManager:
    def __init__(self, pid_file: Optional[Path] = None):
        self.pid_file = pid_file or Path.home() / ".cliany-site" / "run" / "obscura.pid"

    def _write_pid_file(self, pid: int) -> None:
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.pid_file.with_suffix(self.pid_file.suffix + ".lock")
        with lock_file.open("a+", encoding="utf-8") as fd:
            portalocker.lock(fd, portalocker.LOCK_EX)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.pid_file.parent,
                prefix=f"{self.pid_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp.write(str(pid))
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = Path(tmp.name)
            os.replace(tmp_path, self.pid_file)

    def _read_pid_file(self) -> Optional[int]:
        if not self.pid_file.exists():
            return None
        try:
            text = self.pid_file.read_text(encoding="utf-8").strip()
            if not text:
                return None
            return int(text)
        except (ValueError, OSError):
            return None

    @staticmethod
    def _close_process_pipes(proc: subprocess.Popen) -> None:
        for pipe in (proc.stdout, proc.stderr):
            if pipe is not None:
                pipe.close()

    def _terminate_after_start_timeout(self, proc: subprocess.Popen) -> None:
        proc.terminate()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
        finally:
            self._close_process_pipes(proc)

    def find_free_port(self, start: int = 9222, max_tries: int = 10) -> int:
        """扫描并返回第一个可用端口。

        Raises:
            ProcessError(E_PORT_CONFLICT): 尝试范围内所有端口均被占用
        """
        for port in range(start, start + max_tries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", port))
                    return port
            except OSError:
                continue
        raise ProcessError(
            f"无法找到可用端口（已尝试 {start}–{start + max_tries - 1}）",
            ErrorCode.E_PORT_CONFLICT,
        )

    def _is_port_available(self, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return True
        except OSError:
            return False

    def _probe_endpoint(self, port: int, timeout: float = 1.0) -> bool:
        url = f"http://localhost:{port}/json/version"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:  # noqa: BLE001
            return False

    def _wait_ready(self, port: int, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        delay = 0.1
        while time.monotonic() < deadline:
            if self._probe_endpoint(port):
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(delay, remaining))
            delay = min(delay * 1.5, 1.0)
        return False

    def start(
        self,
        binary_path: Path,
        port: Optional[int] = None,
        *,
        timeout: float = 30.0,
    ) -> ProcessHandle:
        """启动 obscura serve，等待 ready probe 通过后返回 ProcessHandle。

        Raises:
            ProcessError(E_PORT_CONFLICT): 指定端口已被占用
            ProcessError(E_TIMEOUT): 进程启动后 ready probe 超时
        """
        if port is not None:
            if not self._is_port_available(port):
                raise ProcessError(f"端口 {port} 已被占用", ErrorCode.E_PORT_CONFLICT)
            selected_port = port
        else:
            selected_port = self.find_free_port()

        proc = subprocess.Popen(
            [str(binary_path), "serve", "--port", str(selected_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if not self._wait_ready(selected_port, timeout):
            self._terminate_after_start_timeout(proc)
            raise ProcessError(
                f"Obscura 启动超时（端口 {selected_port}，{timeout}s 内未就绪）",
                ErrorCode.E_TIMEOUT,
            )

        self._write_pid_file(proc.pid)

        return ProcessHandle(pid=proc.pid, port=selected_port, binary_path=binary_path)

    def stop(self, handle: ProcessHandle) -> None:
        pid = self._read_pid_file()
        if pid is None:
            return

        try:
            os.kill(pid, signal.SIGTERM)
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except ProcessLookupError:
                    break
            else:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        except ProcessLookupError:
            pass

        if self.pid_file.exists():
            self.pid_file.unlink(missing_ok=True)

    def is_running(self, port: int) -> bool:
        if not self.pid_file.exists():
            return False
        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            pass
        return self._probe_endpoint(port)

    def get_status(self) -> ProcessStatus:
        if not self.pid_file.exists():
            return ProcessStatus(
                state="stopped",
                pid=None,
                port=None,
                pid_file=self.pid_file,
                stale=False,
            )

        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            return ProcessStatus(
                state="stopped",
                pid=None,
                port=None,
                pid_file=self.pid_file,
                stale=False,
            )

        try:
            os.kill(pid, 0)
            return ProcessStatus(
                state="running",
                pid=pid,
                port=None,
                pid_file=self.pid_file,
                stale=False,
            )
        except ProcessLookupError:
            return ProcessStatus(
                state="stale",
                pid=pid,
                port=None,
                pid_file=self.pid_file,
                stale=True,
            )
        except PermissionError:
            return ProcessStatus(
                state="running",
                pid=pid,
                port=None,
                pid_file=self.pid_file,
                stale=False,
            )

    def cleanup_stale(self) -> CleanupResult:
        result = CleanupResult()

        if not self.pid_file.exists():
            return result

        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError) as exc:
            result.warnings.append(f"读取 PID 文件失败: {exc}")
            return result

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            try:
                self.pid_file.unlink()
                result.removed_pids.append(pid)
                result.removed_pid_files.append(self.pid_file)
            except OSError as exc:
                result.warnings.append(f"删除 PID 文件失败: {exc}")
        except PermissionError:
            pass

        return result
