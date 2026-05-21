"""
跨平台文件锁行为验证测试。
确认 portalocker 在 macOS/Linux/Windows 上行为一致。
"""
# pyright: reportMissingImports=false
from __future__ import annotations

from pathlib import Path

import portalocker
import pytest


class TestPortalockerBasic:
    """portalocker 基本行为验证 - 平台独立"""

    def test_exclusive_lock_and_release(self, tmp_path: Path) -> None:
        """排他锁获取与释放正常工作。"""
        lock_file = tmp_path / "test.lock"
        with portalocker.Lock(str(lock_file), mode="a", timeout=5):
            assert lock_file.exists()

    def test_lock_file_created(self, tmp_path: Path) -> None:
        """确认锁文件会被创建。"""
        lock_file = tmp_path / "created.lock"
        assert not lock_file.exists()
        with portalocker.Lock(str(lock_file), mode="a", timeout=5):
            assert lock_file.exists()

    def test_non_blocking_second_lock_raises(self, tmp_path: Path) -> None:
        """已加锁文件再次尝试 non-blocking 锁时抛出异常。"""
        lock_file = tmp_path / "double.lock"
        with portalocker.Lock(str(lock_file), mode="a", timeout=5):
            with open(str(lock_file), "a") as handle:
                with pytest.raises((portalocker.LockException, portalocker.AlreadyLocked)):
                    portalocker.lock(handle, portalocker.LOCK_EX | portalocker.LOCK_NB)


class TestCrossPlatformNormalize:
    """normalize_platform 跨平台别名验证。"""

    def test_linux_aarch64(self) -> None:
        from cliany_site.binary.platforms import normalize_platform

        result = normalize_platform("linux", "aarch64")
        assert result.target_key == "linux-aarch64"

    def test_darwin_arm64(self) -> None:
        from cliany_site.binary.platforms import normalize_platform

        result = normalize_platform("darwin", "arm64")
        assert result.target_key == "darwin-arm64"

    def test_darwin_universal(self) -> None:
        from cliany_site.binary.platforms import normalize_platform

        result = normalize_platform("darwin", "universal2")
        assert result.target_key in ("darwin-arm64", "darwin-x86_64")

    def test_windows_amd64(self) -> None:
        from cliany_site.binary.platforms import normalize_platform

        result = normalize_platform("win32", "AMD64")
        assert result.target_key == "windows-x86_64"

    def test_unknown_platform_raises_with_hint(self) -> None:
        from cliany_site.binary.platforms import UnsupportedPlatformError, normalize_platform

        with pytest.raises(UnsupportedPlatformError) as exc_info:
            normalize_platform("plan9", "pdp11")
        err = exc_info.value
        assert hasattr(err, "hint")
        assert err.hint
