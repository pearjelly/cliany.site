from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class BinaryVersion:
    version: str
    platform: str
    path: Path
    is_ready: bool
    installed_at: datetime | None = None


@dataclass
class BinaryState:
    cache_dir: Path
    active_version: str | None
    installed_versions: list
    auto_upgrade_enabled: bool = False


@dataclass
class BinaryConfig:
    pinned_version: str | None = None
    auto_upgrade: bool = False
    min_version: str = "0.1.2"


def _exe_name() -> str:
    return "obscura.exe" if sys.platform == "win32" else "obscura"


def _version_dir(cache_dir: Path, version: str) -> Path:
    return cache_dir / version


def _active_file(cache_dir: Path) -> Path:
    return cache_dir / "active"


def _ready_file(cache_dir: Path, version: str) -> Path:
    return _version_dir(cache_dir, version) / ".ready"


def install_version(state: BinaryState, version: str, platform: str) -> BinaryState:
    ver_dir = _version_dir(state.cache_dir, version)
    ver_dir.mkdir(parents=True, exist_ok=True)
    exe = ver_dir / _exe_name()
    exe.touch()
    ready = _ready_file(state.cache_dir, version)
    ready.touch()

    bv = BinaryVersion(
        version=version,
        platform=platform,
        path=exe,
        is_ready=True,
        installed_at=datetime.now(UTC),
    )

    existing = [v for v in state.installed_versions if v.version != version]
    return BinaryState(
        cache_dir=state.cache_dir,
        active_version=state.active_version,
        installed_versions=existing + [bv],
        auto_upgrade_enabled=state.auto_upgrade_enabled,
    )


def use_version(state: BinaryState, version: str) -> BinaryState:
    versions = {v.version for v in state.installed_versions}
    if version not in versions:
        raise ValueError(f"版本 {version} 未安装")
    _active_file(state.cache_dir).parent.mkdir(parents=True, exist_ok=True)
    _active_file(state.cache_dir).write_text(version, encoding="utf-8")
    return BinaryState(
        cache_dir=state.cache_dir,
        active_version=version,
        installed_versions=state.installed_versions,
        auto_upgrade_enabled=state.auto_upgrade_enabled,
    )


def rollback_version(state: BinaryState) -> BinaryState:
    sorted_versions = sorted(
        state.installed_versions,
        key=lambda v: v.installed_at or datetime.min.replace(tzinfo=UTC),
    )
    if len(sorted_versions) < 2:
        raise ValueError("没有可回滚的历史版本")
    active_idx = next(
        (i for i, v in enumerate(sorted_versions) if v.version == state.active_version),
        len(sorted_versions) - 1,
    )
    target_idx = active_idx - 1
    if target_idx < 0:
        raise ValueError("已是最旧版本，无法回滚")
    target = sorted_versions[target_idx]
    return use_version(state, target.version)


def get_active_version(cache_dir: Path) -> str | None:
    active = _active_file(cache_dir)
    if not active.exists():
        return None
    content = active.read_text(encoding="utf-8").strip()
    return content if content else None


def validate_pinned_version(config: BinaryConfig) -> None:
    if config.auto_upgrade and config.pinned_version is not None:
        raise ValueError("auto_upgrade=True 时不允许同时设置 pinned_version")
    if config.pinned_version == "":
        raise ValueError("pinned_version 不能为空字符串，请设为 None 或有效版本号")
