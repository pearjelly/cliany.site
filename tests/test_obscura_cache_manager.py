import io
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from cliany_site.binary.cache import CacheError, CacheManager, _detect_archive_prefix, _strip_prefix
from cliany_site.binary.platforms import PlatformTarget
from cliany_site.binary.releases import ArtifactSpec
from cliany_site.envelope import ErrorCode


EXE_NAME = "obscura.exe" if sys.platform == "win32" else "obscura"


def _make_platform(archive_ext: str = ".tar.gz", exe_suffix: str = "") -> PlatformTarget:
    return PlatformTarget(
        os="darwin",
        arch="arm64",
        target_key="darwin-arm64",
        exe_suffix=exe_suffix,
        archive_ext=archive_ext,
        is_supported=True,
    )


def _make_artifact(version: str = "0.1.0", filename: str = "obscura-aarch64-macos.tar.gz") -> ArtifactSpec:
    return ArtifactSpec(
        version=version,
        platform=_make_platform(),
        download_url=f"https://example.com/{filename}",
        filename=filename,
    )


def _make_tar_gz(binary_name: str = None, content: bytes = b"fake binary") -> bytes:
    if binary_name is None:
        binary_name = EXE_NAME
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info = tarfile.TarInfo(name=binary_name)
        info.size = len(content)
        tf.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def _make_tar_gz_with_prefix(binary_name: str = None, prefix: str = "obscura-0.1.0") -> bytes:
    if binary_name is None:
        binary_name = EXE_NAME
    content = b"fake binary with prefix"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        dir_info = tarfile.TarInfo(name=prefix)
        dir_info.type = tarfile.DIRTYPE
        tf.addfile(dir_info)
        info = tarfile.TarInfo(name=f"{prefix}/{binary_name}")
        info.size = len(content)
        tf.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def _make_zip(binary_name: str = None, content: bytes = b"fake binary zip") -> bytes:
    if binary_name is None:
        binary_name = EXE_NAME
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        zf.writestr(binary_name, content)
    return buf.getvalue()


class TestCacheManagerInstall:
    def test_install_tar_gz(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        artifact = _make_artifact(version="1.0.0", filename="obscura-aarch64-macos.tar.gz")
        archive = _make_tar_gz()

        binary_path = mgr.install(artifact, archive)

        assert binary_path.exists()
        assert binary_path.name == EXE_NAME
        assert mgr.is_installed("1.0.0")
        assert not (tmp_path / "1.0.0" / ".archive.tmp").exists()

    def test_install_zip(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        artifact = ArtifactSpec(
            version="2.0.0",
            platform=_make_platform(archive_ext=".zip"),
            download_url="https://example.com/obscura-x86_64-windows.zip",
            filename="obscura-x86_64-windows.zip",
        )
        archive = _make_zip()

        binary_path = mgr.install(artifact, archive)

        assert binary_path.exists()
        assert mgr.is_installed("2.0.0")
        assert not (tmp_path / "2.0.0" / ".archive.tmp").exists()

    def test_install_idempotent(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        artifact = _make_artifact(version="1.0.0")
        archive = _make_tar_gz()

        path1 = mgr.install(artifact, archive)
        path2 = mgr.install(artifact, archive)

        assert path1 == path2
        assert mgr.is_installed("1.0.0")
        assert not (tmp_path / "1.0.0" / ".archive.tmp").exists()
        assert list((tmp_path / "1.0.0").glob("*.tmp")) == []

    def test_install_tar_gz_with_prefix_directory(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        artifact = _make_artifact(version="1.1.0")
        archive = _make_tar_gz_with_prefix()

        binary_path = mgr.install(artifact, archive)

        assert binary_path.exists()
        assert binary_path.name == EXE_NAME

    def test_install_sets_executable_bit(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        artifact = _make_artifact(version="1.0.0")
        archive = _make_tar_gz()

        binary_path = mgr.install(artifact, archive)

        assert binary_path.stat().st_mode & 0o100

    def test_install_missing_binary_raises(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        artifact = _make_artifact(version="1.0.0")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            info = tarfile.TarInfo(name="some_other_file.txt")
            data = b"not a binary"
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        archive = buf.getvalue()

        with pytest.raises(CacheError) as exc_info:
            mgr.install(artifact, archive)
        assert exc_info.value.error_code == ErrorCode.E_BINARY_NOT_FOUND


class TestCacheManagerQuery:
    def test_get_binary_path_not_found(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)

        with pytest.raises(CacheError) as exc_info:
            mgr.get_binary_path("9.9.9")
        assert exc_info.value.error_code == ErrorCode.E_BINARY_NOT_FOUND

    def test_get_binary_path_returns_correct_path(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        artifact = _make_artifact(version="1.0.0")
        mgr.install(artifact, _make_tar_gz())

        path = mgr.get_binary_path("1.0.0")

        assert path.exists()
        assert path.name == EXE_NAME

    def test_list_versions_empty(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        assert mgr.list_versions() == []

    def test_list_versions(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        for v in ["1.0.0", "1.1.0", "2.0.0"]:
            mgr.install(_make_artifact(version=v), _make_tar_gz())

        versions = mgr.list_versions()

        assert versions == ["1.0.0", "1.1.0", "2.0.0"]

    def test_list_versions_excludes_incomplete(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        mgr.install(_make_artifact(version="1.0.0"), _make_tar_gz())
        incomplete_dir = tmp_path / "0.9.9"
        incomplete_dir.mkdir()

        versions = mgr.list_versions()

        assert versions == ["1.0.0"]
        assert "0.9.9" not in versions


class TestCacheManagerRemove:
    def test_remove_version(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        mgr.install(_make_artifact(version="1.0.0"), _make_tar_gz())
        assert mgr.is_installed("1.0.0")

        mgr.remove_version("1.0.0")

        assert not mgr.is_installed("1.0.0")

    def test_remove_version_not_installed_raises(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)

        with pytest.raises(CacheError):
            mgr.remove_version("9.9.9")

    def test_remove_active_version_raises(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        mgr.install(_make_artifact(version="1.0.0"), _make_tar_gz())
        (tmp_path / "active").write_text("1.0.0", encoding="utf-8")

        with pytest.raises(CacheError) as exc_info:
            mgr.remove_version("1.0.0")
        assert "active" in str(exc_info.value).lower()

    def test_remove_non_active_version_allowed(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        for v in ["1.0.0", "1.1.0"]:
            mgr.install(_make_artifact(version=v), _make_tar_gz())
        (tmp_path / "active").write_text("1.1.0", encoding="utf-8")

        mgr.remove_version("1.0.0")

        assert not mgr.is_installed("1.0.0")
        assert mgr.is_installed("1.1.0")


class TestCacheManagerIntegrity:
    def test_check_integrity_installed(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        mgr.install(_make_artifact(version="1.0.0"), _make_tar_gz())

        assert mgr.check_integrity("1.0.0") is True

    def test_check_integrity_not_installed(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)

        assert mgr.check_integrity("9.9.9") is False

    def test_check_integrity_missing_binary(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        mgr.install(_make_artifact(version="1.0.0"), _make_tar_gz())
        binary = tmp_path / "1.0.0" / EXE_NAME
        binary.unlink()

        assert mgr.check_integrity("1.0.0") is False

    def test_check_integrity_non_executable(self, tmp_path):
        mgr = CacheManager(cache_root=tmp_path)
        mgr.install(_make_artifact(version="1.0.0"), _make_tar_gz())
        binary = tmp_path / "1.0.0" / EXE_NAME
        binary.chmod(0o644)

        assert mgr.check_integrity("1.0.0") is False


class TestDetectArchivePrefix:
    def test_no_names(self):
        assert _detect_archive_prefix([]) == ""

    def test_single_prefix(self):
        names = ["mydir/obscura", "mydir/README"]
        assert _detect_archive_prefix(names) == "mydir/"

    def test_no_common_prefix_root_file(self):
        names = ["obscura", "README"]
        assert _detect_archive_prefix(names) == ""

    def test_multiple_top_dirs(self):
        names = ["dir1/a", "dir2/b"]
        assert _detect_archive_prefix(names) == ""

    def test_strip_prefix(self):
        assert _strip_prefix("mydir/obscura", "mydir/") == "obscura"
        assert _strip_prefix("obscura", "") == "obscura"
