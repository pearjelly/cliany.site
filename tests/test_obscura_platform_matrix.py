# tests/test_obscura_platform_matrix.py
import sys
import pytest
from unittest.mock import patch

from cliany_site.binary.platforms import (
    PlatformTarget,
    UnsupportedPlatformError,
    normalize_platform,
    get_artifact_filename,
)


class TestPlatformTarget:
    def test_dataclass_fields(self):
        target = PlatformTarget(
            os="darwin",
            arch="arm64",
            target_key="darwin-arm64",
            exe_suffix="",
            archive_ext=".tar.gz",
            is_supported=True
        )
        assert target.os == "darwin"
        assert target.arch == "arm64"
        assert target.target_key == "darwin-arm64"
        assert target.exe_suffix == ""
        assert target.archive_ext == ".tar.gz"
        assert target.is_supported is True


class TestNormalizePlatform:
    def test_darwin_arm64(self):
        target = normalize_platform("darwin", "arm64")
        assert target.os == "darwin"
        assert target.arch == "arm64"
        assert target.target_key == "darwin-arm64"
        assert target.exe_suffix == ""
        assert target.archive_ext == ".tar.gz"
        assert target.is_supported is True

    def test_darwin_x86_64(self):
        target = normalize_platform("darwin", "x86_64")
        assert target.os == "darwin"
        assert target.arch == "x86_64"
        assert target.target_key == "darwin-x86_64"
        assert target.exe_suffix == ""
        assert target.archive_ext == ".tar.gz"
        assert target.is_supported is True

    def test_linux_x86_64(self):
        target = normalize_platform("linux", "x86_64")
        assert target.os == "linux"
        assert target.arch == "x86_64"
        assert target.target_key == "linux-x86_64"
        assert target.exe_suffix == ""
        assert target.archive_ext == ".tar.gz"
        assert target.is_supported is True

    def test_windows_x86_64(self):
        target = normalize_platform("win32", "AMD64")
        assert target.os == "windows"
        assert target.arch == "x86_64"
        assert target.target_key == "windows-x86_64"
        assert target.exe_suffix == ".exe"
        assert target.archive_ext == ".zip"
        assert target.is_supported is True

    def test_linux_arm64_unsupported(self):
        with pytest.raises(UnsupportedPlatformError) as exc:
            normalize_platform("linux", "aarch64")
        assert exc.value.target_key == "linux-arm64"
        assert exc.value.error_code == "E_UNSUPPORTED_PLATFORM"

    def test_linux_aarch64_unsupported(self):
        with pytest.raises(UnsupportedPlatformError) as exc:
            normalize_platform("linux", "aarch64")
        assert exc.value.target_key == "linux-arm64"
        assert exc.value.error_code == "E_UNSUPPORTED_PLATFORM"

    def test_unknown_os_unsupported(self):
        with pytest.raises(UnsupportedPlatformError) as exc:
            normalize_platform("unknown", "x86_64")
        assert "unknown-x86_64" in str(exc.value)

    def test_unknown_arch_unsupported(self):
        with pytest.raises(UnsupportedPlatformError) as exc:
            normalize_platform("linux", "unknown")
        assert "linux-unknown" in str(exc.value)


class TestGetArtifactFilename:
    def test_darwin_arm64_filename(self):
        target = PlatformTarget(
            os="darwin", arch="arm64", target_key="darwin-arm64",
            exe_suffix="", archive_ext=".tar.gz", is_supported=True
        )
        filename = get_artifact_filename(target)
        assert filename == "obscura-aarch64-macos.tar.gz"

    def test_darwin_x86_64_filename(self):
        target = PlatformTarget(
            os="darwin", arch="x86_64", target_key="darwin-x86_64",
            exe_suffix="", archive_ext=".tar.gz", is_supported=True
        )
        filename = get_artifact_filename(target)
        assert filename == "obscura-x86_64-macos.tar.gz"

    def test_linux_x86_64_filename(self):
        target = PlatformTarget(
            os="linux", arch="x86_64", target_key="linux-x86_64",
            exe_suffix="", archive_ext=".tar.gz", is_supported=True
        )
        filename = get_artifact_filename(target)
        assert filename == "obscura-x86_64-linux.tar.gz"

    def test_windows_x86_64_filename(self):
        target = PlatformTarget(
            os="windows", arch="x86_64", target_key="windows-x86_64",
            exe_suffix=".exe", archive_ext=".zip", is_supported=True
        )
        filename = get_artifact_filename(target)
        assert filename == "obscura-x86_64-windows.zip"

    def test_unsupported_target_raises_error(self):
        target = PlatformTarget(
            os="linux", arch="arm64", target_key="linux-arm64",
            exe_suffix="", archive_ext=".tar.gz", is_supported=False
        )
        with pytest.raises(UnsupportedPlatformError) as exc:
            get_artifact_filename(target)
        assert exc.value.target_key == "linux-arm64"