import contextlib
import datetime
import importlib.util
import json
import logging
import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

import click
import portalocker

from cliany_site.codegen.generator import METADATA_SCHEMA_VERSION
from cliany_site.config import get_config
from cliany_site.errors import LOCK_TIMEOUT
from cliany_site.metadata import LegacyMetadataError, MetadataParseError, load_metadata

logger = logging.getLogger(__name__)


def discover_adapters(include_legacy: bool = False) -> list[dict[str, Any]]:
    """扫描 ~/.cliany-site/adapters/ 目录，返回已安装的 adapter 信息。

    默认只返回可加载的 v2 adapter（exclude legacy）；传 include_legacy=True 则包含旧版。
    """
    adapters_dir = get_config().adapters_dir
    adapters: list[dict[str, Any]] = []
    if not adapters_dir.exists():
        return adapters

    for adapter_dir in sorted(adapters_dir.iterdir()):
        if not adapter_dir.is_dir():
            continue
        commands_py = adapter_dir / "commands.py"
        if not commands_py.exists():
            continue

        domain = adapter_dir.name
        metadata = {}
        metadata_path = adapter_dir / "metadata.json"
        if metadata_path.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        schema_version = metadata.get("schema_version", "")
        needs_migration = schema_version != METADATA_SCHEMA_VERSION

        if needs_migration and not include_legacy:
            continue

        commands_list = metadata.get("commands", [])
        command_count = len(commands_list) if isinstance(commands_list, list) else 0

        adapters.append(
            {
                "domain": domain,
                "commands_path": str(commands_py),
                "command_count": command_count,
                "metadata": metadata,
                "needs_migration": needs_migration,
            }
        )

    return adapters


def load_adapter(domain: str) -> click.Group | None:
    """动态导入指定 domain 的 commands.py，返回其 Click 命令组，失败返回 None"""
    adapter_dir = get_config().adapters_dir / domain
    commands_py = adapter_dir / "commands.py"

    if not commands_py.exists():
        return None

    module_name = f"cliany_site_adapters.{domain.replace('.', '_').replace('-', '_')}"

    try:
        # Force fresh load by removing stale cached module
        sys.modules.pop(module_name, None)
        spec = importlib.util.spec_from_file_location(module_name, commands_py)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

        cli_group = getattr(module, "cli", None)
        if not isinstance(cli_group, click.Group):
            return None
        return cli_group
    except (ImportError, SyntaxError, OSError, json.JSONDecodeError) as exc:
        logger.warning("加载 adapter '%s' 失败: %s", domain, exc)
        return None


def register_adapters(main_cli: click.Group) -> dict:
    """将所有已安装 adapter 的命令组注册到主 CLI，返回含 legacy_adapters 的结果字典"""
    legacy_adapters: list[str] = []

    for adapter_info in discover_adapters(include_legacy=True):
        domain = adapter_info["domain"]
        metadata_path = get_config().adapters_dir / domain / "metadata.json"

        try:
            load_metadata(metadata_path)
        except LegacyMetadataError:
            logger.warning("跳过旧版 adapter '%s'（需重新生成）", domain)
            legacy_adapters.append(domain)
            continue
        except MetadataParseError as exc:
            logger.warning("跳过无效 metadata '%s': %s", domain, exc)
            continue
        except (ImportError, SyntaxError, AttributeError, RuntimeError) as exc:
            logger.warning("注册 adapter '%s' 时出错: %s", domain, exc, exc_info=True)
            continue

        try:
            group = load_adapter(domain)
            if group is not None:
                group.name = domain
                main_cli.add_command(group, name=domain)
                logger.debug("已注册 adapter: %s", domain)
        except (ImportError, SyntaxError, OSError) as exc:
            logger.warning("注册 adapter '%s' 失败: %s", domain, exc)

    if legacy_adapters:
        n = len(legacy_adapters)
        print(
            f"⚠ legacy adapters: {n} 个（运行 cliany-site list --legacy 查看详情）",
            file=sys.stderr,
        )

    return {"legacy_adapters": legacy_adapters}


class LazyAdapterRegistry:
    def __init__(self, adapters_dir: Path):
        self._adapters_dir = adapters_dir
        self._discovered: dict[str, dict] | None = None
        self._cache: dict[str, click.Group] = {}
        self._lock = threading.RLock()

    def discover(self) -> dict[str, dict]:
        with self._lock:
            if self._discovered is not None:
                return self._discovered
            self._discovered = {}
            if not self._adapters_dir.exists():
                return self._discovered
            for adapter_dir in self._adapters_dir.iterdir():
                if not adapter_dir.is_dir():
                    continue
                metadata_path = adapter_dir / "metadata.json"
                if not metadata_path.exists():
                    continue
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                if metadata.get("schema_version") != METADATA_SCHEMA_VERSION:
                    continue
                self._discovered[adapter_dir.name] = metadata
            return self._discovered

    def domains(self) -> list[str]:
        return list(self.discover().keys())

    def get(self, domain: str, cmd_name: str) -> click.Command | None:
        with self._lock:
            if domain not in self._cache:
                adapter_dir = self._adapters_dir / domain
                commands_py = adapter_dir / "commands.py"
                if not commands_py.exists():
                    return None
                module_name = f"cliany_site_adapters.{domain.replace('.', '_').replace('-', '_')}"
                try:
                    sys.modules.pop(module_name, None)
                    spec = importlib.util.spec_from_file_location(module_name, commands_py)
                    if spec is None or spec.loader is None:
                        return None
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    cli_group = getattr(module, "cli", None)
                    if not isinstance(cli_group, click.Group):
                        return None
                    self._cache[domain] = cli_group
                except (ImportError, SyntaxError, OSError, json.JSONDecodeError) as exc:
                    logger.warning("加载 adapter '%s' 失败: %s", domain, exc)
                    return None
            cli_group = self._cache.get(domain)
            if cli_group is None:
                return None
            return cli_group.commands.get(cmd_name)


def manifest_path() -> Path:
    return Path.home() / ".cliany-site" / "cli-manifest.json"


def build_manifest(registry: LazyAdapterRegistry) -> dict:
    adapters = {}
    for domain, meta in registry.discover().items():
        metadata_path = registry._adapters_dir / domain / "metadata.json"
        last_modified = ""
        if metadata_path.exists():
            try:
                mtime_ns = metadata_path.stat().st_mtime_ns
                last_modified = datetime.datetime.fromtimestamp(
                    mtime_ns / 1e9, tz=datetime.timezone.utc
                ).isoformat()
            except OSError:
                pass
        adapters[domain] = {
            "schema_version": METADATA_SCHEMA_VERSION,
            "signature": meta.get("signature", ""),
            "command_count": len(meta.get("commands", [])),
            "last_modified": last_modified,
        }
    return {
        "schema_version": METADATA_SCHEMA_VERSION,
        "generated_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "adapters": adapters,
    }


def validate_manifest(manifest: dict, registry: LazyAdapterRegistry) -> bool:
    if manifest.get("schema_version") != METADATA_SCHEMA_VERSION:
        return False
    manifest_domains = set(manifest.get("adapters", {}).keys())
    registry_domains = set(registry.domains())
    return manifest_domains == registry_domains


def load_or_rebuild(registry: LazyAdapterRegistry) -> dict:
    manifest_file = manifest_path()
    lock_file = manifest_file.with_suffix(".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with portalocker.Lock(str(lock_file), timeout=10, mode="a"):
            try:
                if manifest_file.exists():
                    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                    if validate_manifest(manifest, registry):
                        return manifest
            except (json.JSONDecodeError, OSError, KeyError) as exc:
                logger.warning("加载 manifest 失败: %s", exc)

            manifest = build_manifest(registry)

            try:
                manifest_file.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp = tempfile.mkstemp(dir=str(manifest_file.parent), suffix=".tmp")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(manifest, f, ensure_ascii=False, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp, str(manifest_file))
                except (OSError, TypeError, ValueError):
                    if os.path.exists(tmp):
                        os.unlink(tmp)
                    raise
            except OSError as exc:
                logger.warning("写入 manifest 失败: %s", exc)
            return manifest
    except portalocker.LockException as _lock_exc:
        from cliany_site.errors import AdapterLoadError
        _exc = AdapterLoadError(f"获取 manifest 锁超时，请稍后重试: {_lock_exc}")
        _exc.error_code = LOCK_TIMEOUT
        raise _exc from _lock_exc
