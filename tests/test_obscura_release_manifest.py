import pytest
from pathlib import Path
from unittest.mock import patch

from cliany_site.binary.releases import (
    ArtifactSpec,
    resolve_release,
    ReleaseNotFoundError,
    DownloadError,
)
from cliany_site.binary.platforms import PlatformTarget


class TestResolveRelease:
    def test_resolve_release_darwin_arm64(self):
        platform = PlatformTarget(
            os="darwin",
            arch="arm64",
            target_key="darwin-arm64",
            exe_suffix="",
            archive_ext=".tar.gz",
            is_supported=True,
        )
        result = resolve_release("0.1.2", platform)
        expected_url = "https://github.com/h4ckf0r0day/obscura/releases/download/v0.1.2/obscura-aarch64-macos.tar.gz"
        expected_filename = "obscura-aarch64-macos.tar.gz"
        assert result.version == "0.1.2"
        assert result.platform == platform
        assert result.download_url == expected_url
        assert result.filename == expected_filename

    def test_resolve_release_linux_x86_64(self):
        platform = PlatformTarget(
            os="linux",
            arch="x86_64",
            target_key="linux-x86_64",
            exe_suffix="",
            archive_ext=".tar.gz",
            is_supported=True,
        )
        result = resolve_release("0.1.2", platform)
        expected_url = "https://github.com/h4ckf0r0day/obscura/releases/download/v0.1.2/obscura-x86_64-linux.tar.gz"
        expected_filename = "obscura-x86_64-linux.tar.gz"
        assert result.version == "0.1.2"
        assert result.platform == platform
        assert result.download_url == expected_url
        assert result.filename == expected_filename

    def test_resolve_release_windows_x86_64(self):
        platform = PlatformTarget(
            os="windows",
            arch="x86_64",
            target_key="windows-x86_64",
            exe_suffix=".exe",
            archive_ext=".zip",
            is_supported=True,
        )
        result = resolve_release("0.1.2", platform)
        expected_url = "https://github.com/h4ckf0r0day/obscura/releases/download/v0.1.2/obscura-x86_64-windows.zip"
        expected_filename = "obscura-x86_64-windows.zip"
        assert result.version == "0.1.2"
        assert result.platform == platform
        assert result.download_url == expected_url
        assert result.filename == expected_filename
        assert result.download_url.endswith(".zip")

    def test_resolve_release_offline_miss(self, tmp_path):
        platform = PlatformTarget(
            os="linux",
            arch="x86_64",
            target_key="linux-x86_64",
            exe_suffix="",
            archive_ext=".tar.gz",
            is_supported=True,
        )
        cache_root = tmp_path / "cache"
        with pytest.raises(DownloadError) as exc_info:
            resolve_release("0.1.2", platform, offline=True, cache_root=cache_root)
        assert exc_info.value.error_code == "E_DOWNLOAD_FAILED"
        assert "缓存中不存在版本 0.1.2 的 artifact" in str(exc_info.value)

    def test_resolve_release_no_latest_default(self):
        platform = PlatformTarget(
            os="linux",
            arch="x86_64",
            target_key="linux-x86_64",
            exe_suffix="",
            archive_ext=".tar.gz",
            is_supported=True,
        )
        with pytest.raises(ReleaseNotFoundError):
            resolve_release("latest", platform)

        with pytest.raises(ReleaseNotFoundError):
            resolve_release(None, platform)  # type: ignore

    def test_resolve_release_offline_hit(self, tmp_path):
        platform = PlatformTarget(
            os="linux",
            arch="x86_64",
            target_key="linux-x86_64",
            exe_suffix="",
            archive_ext=".tar.gz",
            is_supported=True,
        )
        cache_root = tmp_path / "cache"
        version_dir = cache_root / "0.1.2"
        version_dir.mkdir(parents=True)
        cached_file = version_dir / "obscura-x86_64-linux.tar.gz"
        cached_file.write_text("fake content")

        result = resolve_release("0.1.2", platform, offline=True, cache_root=cache_root)
        assert result.version == "0.1.2"
        assert result.platform == platform
        assert result.download_url.startswith("file://")
        assert result.download_url.endswith("obscura-x86_64-linux.tar.gz")
        assert result.filename == "obscura-x86_64-linux.tar.gz"