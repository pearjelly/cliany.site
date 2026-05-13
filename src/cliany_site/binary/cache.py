from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import List, Optional

from cliany_site.binary.releases import ArtifactSpec
from cliany_site.envelope import ErrorCode
from cliany_site.errors import ClanySiteError

logger = logging.getLogger(__name__)


class CacheError(ClanySiteError):
    def __init__(self, message: str, error_code: str = ErrorCode.E_BINARY_NOT_FOUND):
        self.error_code = error_code
        super().__init__(message)


def _exe_name() -> str:
    return "obscura.exe" if sys.platform == "win32" else "obscura"


def _version_dir(cache_root: Path, version: str) -> Path:
    return cache_root / version


def _ready_file(cache_root: Path, version: str) -> Path:
    return _version_dir(cache_root, version) / ".ready"


def _active_file(cache_root: Path) -> Path:
    return cache_root / "active"


def _find_binary(version_dir: Path, exe_name: str) -> Optional[Path]:
    for p in version_dir.rglob(exe_name):
        if p.is_file():
            return p
    return None


def _fix_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | 0o111)


def _remove_quarantine(path: Path) -> Optional[str]:
    """仅在 macOS 上运行 xattr -dr；失败返回 warning 字符串，不抛异常。"""
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            ["xattr", "-dr", "com.apple.quarantine", str(path)],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            return (
                f"quarantine 移除失败 (code={result.returncode}): "
                f"{result.stderr.decode(errors='replace').strip()}"
            )
    except Exception as exc:  # noqa: BLE001
        return f"quarantine 移除异常: {exc}"
    return None


def _detect_archive_prefix(names: List[str]) -> str:
    """返回归档内公共顶层目录前缀（含尾部 /）；若根层有直接文件则返回空字符串。"""
    if not names:
        return ""
    first_segments: set[str] = set()
    for name in names:
        parts = name.replace("\\", "/").split("/", 1)
        if len(parts) == 2 and parts[1]:
            first_segments.add(parts[0])
        else:
            return ""
    if len(first_segments) == 1:
        return first_segments.pop() + "/"
    return ""


def _strip_prefix(name: str, prefix: str) -> str:
    if not prefix:
        return name
    normalized = name.replace("\\", "/")
    if normalized.startswith(prefix):
        return normalized[len(prefix):]
    return name


class CacheManager:
    """管理 Obscura 二进制的本地缓存。

    缓存结构：
      cache_root/
        <version>/
          obscura  (或 obscura.exe)
          .ready   (安装成功哨兵)
        active     (当前 active 版本文本文件)
    """

    def __init__(self, cache_root: Optional[Path] = None):
        if cache_root is None:
            cache_root = Path.home() / ".cliany-site" / "bin" / "obscura"
        self.cache_root = cache_root

    def install(self, artifact_spec: ArtifactSpec, archive_bytes: bytes) -> Path:
        """安装 artifact 到缓存。原子写临时归档 → 解压 → chmod+x → quarantine 清理 → .ready 哨兵 → 原子 rename。

        Raises:
            CacheError: 解压失败或归档中找不到 obscura 二进制
        """
        version = artifact_spec.version
        ver_dir = _version_dir(self.cache_root, version)
        tmp_dir = Path(str(ver_dir) + ".tmp")

        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        tmp_archive = tmp_dir / ".archive.tmp"
        try:
            tmp_archive.write_bytes(archive_bytes)
            self._extract_archive(tmp_archive, artifact_spec.filename, tmp_dir)
        finally:
            if tmp_archive.exists():
                tmp_archive.unlink()

        exe_name = _exe_name()
        binary_path = _find_binary(tmp_dir, exe_name)
        if binary_path is None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise CacheError(
                f"解压后未找到二进制 '{exe_name}'（版本 {version}）",
                ErrorCode.E_BINARY_NOT_FOUND,
            )

        _fix_executable(binary_path)
        warn = _remove_quarantine(binary_path)
        if warn:
            logger.warning(warn)
        (tmp_dir / ".ready").write_text("ok", encoding="utf-8")

        if ver_dir.exists():
            shutil.rmtree(ver_dir)
        tmp_dir.rename(ver_dir)

        binary_path = _find_binary(ver_dir, exe_name)
        if binary_path is None:
            raise CacheError(
                f"重命名后找不到二进制 '{exe_name}'（版本 {version}）",
                ErrorCode.E_BINARY_NOT_FOUND,
            )

        return binary_path

    def is_installed(self, version: str) -> bool:
        return _ready_file(self.cache_root, version).exists()

    def get_binary_path(self, version: str) -> Path:
        """Raises:
            CacheError(E_BINARY_NOT_FOUND): 版本未安装或二进制文件缺失
        """
        if not self.is_installed(version):
            raise CacheError(f"版本 {version} 未安装", ErrorCode.E_BINARY_NOT_FOUND)
        binary_path = _find_binary(_version_dir(self.cache_root, version), _exe_name())
        if binary_path is None:
            raise CacheError(
                f"版本 {version} 已安装但找不到二进制 '{_exe_name()}'",
                ErrorCode.E_BINARY_NOT_FOUND,
            )
        return binary_path

    def list_versions(self) -> List[str]:
        if not self.cache_root.exists():
            return []
        return sorted(
            entry.name
            for entry in self.cache_root.iterdir()
            if entry.is_dir() and (entry / ".ready").exists()
        )

    def remove_version(self, version: str) -> None:
        """Raises:
            CacheError: 版本未安装，或该版本为当前 active 版本
        """
        if not self.is_installed(version):
            raise CacheError(f"版本 {version} 未安装，无法删除", ErrorCode.E_BINARY_NOT_FOUND)
        active = self._get_active_version()
        if active is not None and active == version:
            raise CacheError(
                f"不允许删除当前 active 版本 {version}",
                ErrorCode.E_BINARY_NOT_FOUND,
            )
        shutil.rmtree(_version_dir(self.cache_root, version))

    def check_integrity(self, version: str) -> bool:
        if not self.is_installed(version):
            return False
        binary_path = _find_binary(_version_dir(self.cache_root, version), _exe_name())
        if binary_path is None:
            return False
        return bool(binary_path.stat().st_mode & 0o100)

    def get_active_version(self) -> Optional[str]:
        """返回当前 active 版本号，若未设置则返回 None。"""
        active_f = _active_file(self.cache_root)
        if not active_f.exists():
            return None
        content = active_f.read_text(encoding="utf-8").strip()
        return content if content else None

    def set_active_version(self, version: str) -> None:
        """切换 active 版本。

        Raises:
            CacheError(E_BINARY_NOT_FOUND): 版本未安装
        """
        if not self.is_installed(version):
            raise CacheError(f"版本 {version} 未安装", ErrorCode.E_BINARY_NOT_FOUND)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        _active_file(self.cache_root).write_text(version, encoding="utf-8")

    def _get_active_version(self) -> Optional[str]:
        return self.get_active_version()

    def _extract_archive(self, archive_path: Path, filename: str, dest_dir: Path) -> None:
        """Raises:
            CacheError: 不支持的格式或解压失败
        """
        try:
            if filename.endswith(".tar.gz") or filename.endswith(".tgz"):
                self._extract_tar_gz(archive_path, dest_dir)
            elif filename.endswith(".zip"):
                self._extract_zip(archive_path, dest_dir)
            else:
                raise CacheError(f"不支持的归档格式: {filename}", ErrorCode.E_DOWNLOAD_FAILED)
        except CacheError:
            raise
        except Exception as exc:
            raise CacheError(f"解压失败: {exc}", ErrorCode.E_DOWNLOAD_FAILED) from exc

    @staticmethod
    def _extract_tar_gz(archive_path: Path, dest_dir: Path) -> None:
        with tarfile.open(archive_path, "r:gz") as tf:
            members = tf.getmembers()
            prefix = _detect_archive_prefix([m.name for m in members])
            for member in members:
                stripped = _strip_prefix(member.name, prefix)
                if not stripped:
                    continue
                if member.isreg():
                    tf.extract(member, path=dest_dir, set_attrs=False, filter="data")
                    extracted = dest_dir / member.name
                    target = dest_dir / stripped
                    if extracted != target:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        extracted.rename(target)
                elif member.isdir():
                    (dest_dir / stripped).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _extract_zip(archive_path: Path, dest_dir: Path) -> None:
        with zipfile.ZipFile(archive_path, "r") as zf:
            names = zf.namelist()
            prefix = _detect_archive_prefix(names)
            for name in names:
                stripped = _strip_prefix(name, prefix)
                if not stripped:
                    continue
                if name.endswith("/"):
                    (dest_dir / stripped).mkdir(parents=True, exist_ok=True)
                    continue
                target = dest_dir / stripped
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))
