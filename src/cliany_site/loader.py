import contextlib
import importlib.util
import json
import logging
import sys
from typing import Any

import click

from cliany_site.codegen.generator import METADATA_SCHEMA_VERSION
from cliany_site.config import get_config
from cliany_site.metadata import LegacyMetadataError, MetadataParseError, load_metadata

logger = logging.getLogger(__name__)


def discover_adapters() -> list[dict[str, Any]]:
    """扫描 ~/.cliany-site/adapters/ 目录，返回所有已安装的 adapter 信息"""
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

        commands_list = metadata.get("commands", [])
        command_count = len(commands_list) if isinstance(commands_list, list) else 0

        schema_version = metadata.get("schema_version", "")
        needs_migration = schema_version != METADATA_SCHEMA_VERSION

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

    for adapter_info in discover_adapters():
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
        except Exception as exc:  # noqa: BLE001
            logger.warning("注册 adapter '%s' 时出错: %s", domain, exc)
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
