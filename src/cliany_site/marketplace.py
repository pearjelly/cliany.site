"""适配器市场 — 打包/发布/安装/版本管理

分发格式：tarball (.tar.gz) 内含 manifest.json + commands.py + metadata.json + 可选快照。
manifest.json 记录版本、依赖、签名哈希、兼容性信息。
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from cliany_site.config import get_config

logger = logging.getLogger(__name__)

MANIFEST_VERSION = "1"
PACK_EXTENSION = ".cliany-adapter.tar.gz"


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
    def from_dict(cls, data: dict[str, Any]) -> AdapterManifest:
        return cls(
            manifest_version=str(data.get("manifest_version", MANIFEST_VERSION)),
            domain=str(data.get("domain", "")),
            version=str(data.get("version", "0.1.0")),
            description=str(data.get("description", "")),
            source_url=str(data.get("source_url", "")),
            author=str(data.get("author", "")),
            created_at=str(data.get("created_at", "")),
            cliany_site_min_version=str(data.get("cliany_site_min_version", "0.2.0")),
            files=list(data.get("files", [])),
            file_hashes=dict(data.get("file_hashes", {})),
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
    pack_path = Path(pack_path)
    if not pack_path.exists():
        msg = f"安装包不存在: {pack_path}"
        raise FileNotFoundError(msg)

    with tarfile.open(pack_path, "r:gz") as tar:
        # SECURITY: 阻止 tarball 路径穿越攻击
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in member.name:
                msg = f"安装包包含不安全路径: {member.name}"
                raise ValueError(msg)

        try:
            manifest_file = tar.extractfile("manifest.json")
            if manifest_file is None:
                msg = "安装包缺少 manifest.json"
                raise ValueError(msg)
            manifest_data = json.loads(manifest_file.read().decode("utf-8"))
        except KeyError:
            msg = "安装包缺少 manifest.json"
            raise ValueError(msg) from None

        manifest = AdapterManifest.from_dict(manifest_data)
        if not manifest.domain:
            msg = "manifest.json 缺少 domain 字段"
            raise ValueError(msg)

        cfg = get_config()
        adapter_dir = cfg.adapters_dir / manifest.domain

        if adapter_dir.exists() and not force:
            existing_version = _get_installed_version(manifest.domain)
            if existing_version:
                msg = f"adapter '{manifest.domain}' 已安装 (版本 {existing_version})。使用 --force 覆盖安装，或先卸载。"
                raise FileExistsError(msg)

        backup_path: Path | None = None
        if adapter_dir.exists():
            backup_path = _create_backup(manifest.domain)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            tar.extractall(tmp_path, filter="data")  # noqa: S202

            for filename, expected_hash in manifest.file_hashes.items():
                file_path = tmp_path / filename
                if file_path.exists():
                    actual_hash = _sha256_file(file_path)
                    if actual_hash != expected_hash:
                        msg = f"文件校验失败: {filename} (期望 {expected_hash[:16]}..., 实际 {actual_hash[:16]}...)"
                        raise ValueError(msg)

            if adapter_dir.exists():
                shutil.rmtree(adapter_dir)
            adapter_dir.mkdir(parents=True, exist_ok=True)

            for item in tmp_path.iterdir():
                if item.is_file() and item.name != "manifest.json":
                    shutil.copy2(str(item), str(adapter_dir / item.name))

            manifest_dest = adapter_dir / "manifest.json"
            manifest_dest.write_text(
                json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        if backup_path and backup_path.exists():
            logger.debug("安装成功，保留备份: %s", backup_path)

        logger.info(
            "adapter 已安装: domain=%s version=%s",
            manifest.domain,
            manifest.version,
        )
        return manifest


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
