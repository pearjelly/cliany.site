"""适配器市场 — 打包/发布/安装/版本管理

分发格式：tarball (.tar.gz) 内含 manifest.json + commands.py + metadata.json + 可选快照。
manifest.json 记录版本、依赖、签名哈希、兼容性信息。
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
import logging
import os
import shutil
import tarfile
import tempfile
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from cliany_site.config import get_config

logger = logging.getLogger(__name__)

MANIFEST_VERSION = "1"
PACK_EXTENSION = ".cliany-adapter.tar.gz"
MAX_REMOTE_PACKAGE_SIZE = 64 * 1024 * 1024
_REMOTE_READ_CHUNK_SIZE = 64 * 1024


def _display_source(source: str) -> str:
    """Return a source suitable for user-facing errors without URL secrets."""
    try:
        parsed = urlsplit(source)
    except ValueError:
        return source.split("?", 1)[0].split("#", 1)[0]
    if not parsed.scheme:
        return source
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _validate_remote_sha256(expected_sha256: str | None) -> str:
    if expected_sha256 is None:
        msg = "远程安装包必须提供 --sha256（64 位十六进制 SHA-256）"
        raise ValueError(msg)
    if len(expected_sha256) != 64 or any(char not in "0123456789abcdefABCDEF" for char in expected_sha256):
        msg = "--sha256 必须是 64 位十六进制 SHA-256"
        raise ValueError(msg)
    return expected_sha256.lower()


class _HTTPSOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Any:
        try:
            parsed = urlsplit(newurl)
            is_https = parsed.scheme.lower() == "https" and bool(parsed.hostname)
        except ValueError:
            is_https = False
        if not is_https:
            error_source = _display_source(newurl)
            msg = f"禁止 HTTPS 降级重定向: {error_source}"
            raise ValueError(msg)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _response_content_length(response: Any) -> int | None:
    headers = getattr(response, "headers", None)
    content_length = headers.get("Content-Length") if headers is not None else None
    if content_length is None:
        getheader = getattr(response, "getheader", None)
        if getheader is not None:
            content_length = getheader("Content-Length")
    if content_length is None:
        return None
    try:
        length = int(content_length)
    except (TypeError, ValueError) as exc:
        msg = "远程响应 Content-Length 无效"
        raise ValueError(msg) from exc
    if length < 0:
        msg = "远程响应 Content-Length 无效"
        raise ValueError(msg)
    return length


@contextlib.contextmanager
def resolve_adapter_source(
    source: str | Path,
    *,
    expected_sha256: str | None = None,
) -> Iterator[Path]:
    """Resolve a local package or download and verify one direct HTTPS package."""
    source_text = str(source)
    parsed = urlsplit(source_text)
    is_windows_drive_path = len(parsed.scheme) == 1 and len(source_text) > 1 and source_text[1] == ":"
    if not parsed.scheme or is_windows_drive_path:
        yield Path(source_text)
        return

    if parsed.scheme.lower() != "https" or not parsed.hostname:
        msg = f"安装包来源必须是本地路径或 HTTPS URL: {_display_source(source_text)}"
        raise ValueError(msg)
    expected_digest = _validate_remote_sha256(expected_sha256)
    display_source = _display_source(source_text)
    temp_path: Path | None = None

    try:
        try:
            opener = urllib.request.build_opener(_HTTPSOnlyRedirectHandler())
            with opener.open(source_text) as response:
                content_length = _response_content_length(response)
                if content_length is not None and content_length > MAX_REMOTE_PACKAGE_SIZE:
                    msg = "远程安装包超过 64 MiB 限制"
                    raise ValueError(msg)

                fd, temp_name = tempfile.mkstemp(
                    prefix="cliany-site-",
                    suffix=PACK_EXTENSION,
                )
                temp_path = Path(temp_name)
                try:
                    digest = hashlib.sha256()
                    total_size = 0
                    with os.fdopen(fd, "wb") as output:
                        fd = -1
                        while True:
                            chunk = response.read(_REMOTE_READ_CHUNK_SIZE)
                            if not chunk:
                                break
                            total_size += len(chunk)
                            if total_size > MAX_REMOTE_PACKAGE_SIZE:
                                msg = "远程安装包超过 64 MiB 限制"
                                raise ValueError(msg)
                            output.write(chunk)
                            digest.update(chunk)
                finally:
                    if fd != -1:
                        os.close(fd)

                actual_digest = digest.hexdigest()
                if actual_digest != expected_digest:
                    msg = (
                        "远程安装包 SHA-256 校验失败 "
                        f"(期望 {expected_digest}，实际 {actual_digest})"
                    )
                    raise ValueError(msg)
        except ValueError:
            raise
        except Exception as exc:
            msg = f"远程安装包下载失败: {display_source}"
            raise ValueError(msg) from exc

        assert temp_path is not None
        try:
            yield temp_path
        except Exception as exc:
            temp_text = str(temp_path)
            if temp_text in str(exc):
                exc.args = tuple(
                    value.replace(temp_text, display_source) if isinstance(value, str) else value
                    for value in exc.args
                )
            raise
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@dataclass(frozen=True)
class AdapterManifest:
    manifest_version: str = MANIFEST_VERSION
    domain: str = ""
    version: str = "0.1.0"
    description: str = ""
    source_url: str = ""
    author: str = ""
    created_at: str = ""
    cliany_site_min_version: str = "0.2.0"
    files: list[str] = field(default_factory=list)
    file_hashes: dict[str, str] = field(default_factory=dict)
    checksum: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "domain": self.domain,
            "version": self.version,
            "description": self.description,
            "source_url": self.source_url,
            "author": self.author,
            "created_at": self.created_at,
            "cliany_site_min_version": self.cliany_site_min_version,
            "files": self.files,
            "file_hashes": self.file_hashes,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: object) -> AdapterManifest:
        if not isinstance(data, dict):
            msg = "manifest.json 根节点必须是对象"
            raise ValueError(msg)

        files = data.get("files", [])
        if not isinstance(files, list) or not all(isinstance(filename, str) for filename in files):
            msg = "manifest.json 的 files 必须是字符串列表"
            raise ValueError(msg)

        file_hashes = data.get("file_hashes", {})
        if not isinstance(file_hashes, dict) or not all(
            isinstance(filename, str) and isinstance(file_hash, str)
            for filename, file_hash in file_hashes.items()
        ):
            msg = "manifest.json 的 file_hashes 必须是字符串映射"
            raise ValueError(msg)

        return cls(
            manifest_version=str(data.get("manifest_version", MANIFEST_VERSION)),
            domain=str(data.get("domain", "")),
            version=str(data.get("version", "0.1.0")),
            description=str(data.get("description", "")),
            source_url=str(data.get("source_url", "")),
            author=str(data.get("author", "")),
            created_at=str(data.get("created_at", "")),
            cliany_site_min_version=str(data.get("cliany_site_min_version", "0.2.0")),
            files=list(files),
            file_hashes=dict(file_hashes),
            checksum=str(data.get("checksum", "")),
        )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def pack_adapter(domain: str, version: str = "0.1.0", author: str = "") -> Path:
    """将指定域名的 adapter 打包为 .tar.gz 分发包，返回打包文件路径"""
    cfg = get_config()
    adapter_dir = cfg.adapters_dir / domain

    commands_py = adapter_dir / "commands.py"
    if not commands_py.exists():
        msg = f"adapter 不存在: {adapter_dir}"
        raise FileNotFoundError(msg)

    pack_files: list[Path] = [
        f for f in sorted(adapter_dir.iterdir()) if f.is_file() and not f.name.startswith(".") and f.suffix != ".tmp"
    ]

    metadata: dict[str, Any] = {}
    metadata_path = adapter_dir / "metadata.json"
    if metadata_path.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    file_hashes: dict[str, str] = {f.name: _sha256_file(f) for f in pack_files}

    manifest = AdapterManifest(
        domain=domain,
        version=version,
        description=str(metadata.get("workflow", "")),
        source_url=str(metadata.get("source_url", "")),
        author=author,
        created_at=datetime.now(UTC).isoformat(),
        files=[f.name for f in pack_files],
        file_hashes=file_hashes,
    )

    output_dir = cfg.home_dir / "packages"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_domain = domain.replace("/", "_").replace(":", "_")
    safe_version = version.replace("/", "_")
    pack_name = f"{safe_domain}-{safe_version}{PACK_EXTENSION}"
    pack_path = output_dir / pack_name

    with tarfile.open(pack_path, "w:gz") as tar:
        manifest_bytes = json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")
        manifest_info = tarfile.TarInfo(name="manifest.json")
        manifest_info.size = len(manifest_bytes)
        tar.addfile(manifest_info, BytesIO(manifest_bytes))

        for f in pack_files:
            tar.add(str(f), arcname=f.name)

    pack_checksum = _sha256_file(pack_path)
    logger.info("适配器已打包: %s (checksum: %s)", pack_path, pack_checksum[:16])

    return pack_path


def install_adapter(
    pack_path: str | Path,
    *,
    force: bool = False,
) -> AdapterManifest:
    """从 .tar.gz 分发包安装 adapter，返回安装后的 manifest"""
    with _validated_adapter_package(pack_path) as (manifest, tmp_path, _package_sha256):
        adapter_dir, would_replace = _adapter_install_target(manifest, force=force)

        if would_replace:
            _create_backup(manifest.domain)
            shutil.rmtree(adapter_dir)
        adapter_dir.mkdir(parents=True, exist_ok=True)

        for filename in manifest.files:
            shutil.copy2(str(tmp_path / filename), str(adapter_dir / filename))

        manifest_dest = adapter_dir / "manifest.json"
        manifest_dest.write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    logger.info(
        "adapter 已安装: domain=%s version=%s",
        manifest.domain,
        manifest.version,
    )
    return manifest


@contextlib.contextmanager
def _validated_adapter_package(
    pack_path: str | Path,
) -> Iterator[tuple[AdapterManifest, Path, str]]:
    archive_path = Path(pack_path)
    if not archive_path.exists():
        msg = f"安装包不存在: {archive_path}"
        raise FileNotFoundError(msg)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.startswith("/") or ".." in member.name:
                        msg = f"安装包包含不安全路径: {member.name}"
                        raise ValueError(msg)

                try:
                    manifest_file = tar.extractfile("manifest.json")
                    if manifest_file is None:
                        msg = "安装包缺少 manifest.json"
                        raise ValueError(msg)
                    with manifest_file:
                        manifest_data = json.loads(manifest_file.read().decode("utf-8"))
                except KeyError:
                    msg = "安装包缺少 manifest.json"
                    raise ValueError(msg) from None

                manifest = AdapterManifest.from_dict(manifest_data)
                if not manifest.domain:
                    msg = "manifest.json 缺少 domain 字段"
                    raise ValueError(msg)
                _validate_manifest_domain(manifest.domain)

                tar.extractall(tmp_path, filter="data")  # noqa: S202
                _validate_extracted_adapter_package(manifest, tmp_path)
                package_sha256 = _sha256_file(archive_path)
        except (tarfile.TarError, EOFError, gzip.BadGzipFile) as exc:
            msg = f"安装包无法读取: {archive_path}"
            raise ValueError(msg) from exc

        yield manifest, tmp_path, package_sha256


def _validate_manifest_domain(domain: str) -> None:
    """Keep manifest domains as single safe adapter directory names."""
    windows_path = PureWindowsPath(domain)
    if (
        domain in {".", ".."}
        or Path(domain).is_absolute()
        or bool(windows_path.drive or windows_path.root)
        or "/" in domain
        or "\\" in domain
        or ":" in domain
    ):
        msg = f"manifest.json 的 domain 包含不安全路径: {domain}"
        raise ValueError(msg)


def _adapter_install_target(
    manifest: AdapterManifest,
    *,
    force: bool,
) -> tuple[Path, bool]:
    cfg = get_config()
    adapter_dir = cfg.adapters_dir / manifest.domain
    would_replace = adapter_dir.exists()
    if would_replace and not force:
        existing_version = _get_installed_version(manifest.domain)
        version_detail = f" (版本 {existing_version})" if existing_version else ""
        msg = (
            f"adapter '{manifest.domain}' 已安装{version_detail}。"
            "使用 --force 覆盖安装，或先卸载。"
        )
        raise FileExistsError(msg)
    return adapter_dir, would_replace


def inspect_adapter_package(
    pack_path: str | Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """校验 adapter 分发包并报告安装计划，不写入运行时状态。"""
    with _validated_adapter_package(pack_path) as (manifest, _tmp_path, package_sha256):
        _adapter_dir, would_replace = _adapter_install_target(manifest, force=force)
        return {
            "dry_run": True,
            "package_sha256": package_sha256,
            "domain": manifest.domain,
            "version": manifest.version,
            "files": sorted(manifest.files),
            "would_replace": would_replace,
            "would_create_backup": would_replace and force,
        }


def _validate_extracted_adapter_package(manifest: AdapterManifest, tmp_path: Path) -> None:
    required_files = {"commands.py", "metadata.json"}
    manifest_files = set(manifest.files)
    hash_files = set(manifest.file_hashes)

    missing_required = sorted(required_files - manifest_files)
    if missing_required:
        msg = f"manifest.json 缺少必要文件声明: {', '.join(missing_required)}"
        raise ValueError(msg)

    missing_hashes = sorted(manifest_files - hash_files)
    if missing_hashes:
        msg = f"manifest.json 缺少文件哈希: {', '.join(missing_hashes)}"
        raise ValueError(msg)

    unknown_hashes = sorted(hash_files - manifest_files)
    if unknown_hashes:
        msg = f"manifest.json 包含未声明文件哈希: {', '.join(unknown_hashes)}"
        raise ValueError(msg)

    extracted_files = {item.name for item in tmp_path.iterdir() if item.is_file() and item.name != "manifest.json"}
    undeclared_files = sorted(extracted_files - manifest_files)
    if undeclared_files:
        msg = f"安装包包含未声明文件: {', '.join(undeclared_files)}"
        raise ValueError(msg)

    for filename in manifest.files:
        if Path(filename).name != filename:
            msg = f"manifest.json 包含不安全文件名: {filename}"
            raise ValueError(msg)

        file_path = tmp_path / filename
        if not file_path.is_file():
            msg = f"安装包缺少声明文件: {filename}"
            raise ValueError(msg)

        expected_hash = manifest.file_hashes[filename]
        actual_hash = _sha256_file(file_path)
        if actual_hash != expected_hash:
            msg = f"文件校验失败: {filename} (期望 {expected_hash[:16]}..., 实际 {actual_hash[:16]}...)"
            raise ValueError(msg)


def uninstall_adapter(domain: str) -> bool:
    cfg = get_config()
    adapter_dir = cfg.adapters_dir / domain
    if not adapter_dir.exists():
        return False

    shutil.rmtree(adapter_dir)
    logger.info("adapter 已卸载: %s", domain)
    return True


def _get_installed_version(domain: str) -> str | None:
    cfg = get_config()

    manifest_path = cfg.adapters_dir / domain / "manifest.json"
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return str(data.get("version", ""))
        except (json.JSONDecodeError, OSError):
            pass

    metadata_path = cfg.adapters_dir / domain / "metadata.json"
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            return str(data.get("version", ""))
        except (json.JSONDecodeError, OSError):
            pass

    return None


def _create_backup(domain: str) -> Path:
    cfg = get_config()
    adapter_dir = cfg.adapters_dir / domain
    backup_base = cfg.home_dir / "backups" / domain
    backup_base.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    version = _get_installed_version(domain) or "unknown"
    backup_dir = backup_base / f"{version}-{timestamp}"
    shutil.copytree(str(adapter_dir), str(backup_dir))
    logger.info("已创建备份: %s", backup_dir)
    return backup_dir


def list_backups(domain: str) -> list[dict[str, Any]]:
    cfg = get_config()
    backup_base = cfg.home_dir / "backups" / domain
    if not backup_base.exists():
        return []

    backups: list[dict[str, Any]] = []
    for backup_dir in sorted(backup_base.iterdir(), reverse=True):
        if not backup_dir.is_dir():
            continue
        name = backup_dir.name
        parts = name.split("-", 1)
        version = parts[0] if parts else "unknown"
        timestamp = parts[1] if len(parts) > 1 else ""

        backups.append(
            {
                "version": version,
                "timestamp": timestamp,
                "path": str(backup_dir),
            }
        )
    return backups


def rollback_adapter(domain: str, backup_index: int = 0) -> bool:
    backups = list_backups(domain)
    if not backups:
        logger.warning("没有可用的备份: %s", domain)
        return False

    if backup_index < 0 or backup_index >= len(backups):
        logger.warning("备份索引越界: %d (共 %d 个备份)", backup_index, len(backups))
        return False

    backup_info = backups[backup_index]
    backup_dir = Path(backup_info["path"])
    if not backup_dir.exists():
        logger.warning("备份目录不存在: %s", backup_dir)
        return False

    cfg = get_config()
    adapter_dir = cfg.adapters_dir / domain

    if adapter_dir.exists():
        _create_backup(domain)
        shutil.rmtree(adapter_dir)

    shutil.copytree(str(backup_dir), str(adapter_dir))
    logger.info(
        "adapter 已回滚: domain=%s → version=%s",
        domain,
        backup_info["version"],
    )
    return True


def get_adapter_info(domain: str) -> dict[str, Any] | None:
    cfg = get_config()
    adapter_dir = cfg.adapters_dir / domain

    if not adapter_dir.exists():
        return None

    info: dict[str, Any] = {
        "domain": domain,
        "installed": True,
        "path": str(adapter_dir),
    }

    manifest_path = adapter_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            info["manifest"] = manifest_data
            info["version"] = manifest_data.get("version", "")
        except (json.JSONDecodeError, OSError):
            pass

    metadata_path = adapter_dir / "metadata.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            info["metadata"] = metadata
            if "version" not in info:
                info["version"] = metadata.get("version", "")
        except (json.JSONDecodeError, OSError):
            pass

    info["backups"] = list_backups(domain)

    return info
