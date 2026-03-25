import importlib.util
import json
import sys
import warnings
from pathlib import Path
from typing import Any

import click


ADAPTERS_DIR = Path.home() / ".cliany-site" / "adapters"


def discover_adapters() -> list[dict[str, Any]]:
    """扫描 ~/.cliany-site/adapters/ 目录，返回所有已安装的 adapter 信息"""
    adapters = []
    if not ADAPTERS_DIR.exists():
        return adapters

    for adapter_dir in sorted(ADAPTERS_DIR.iterdir()):
        if not adapter_dir.is_dir():
            continue
        commands_py = adapter_dir / "commands.py"
        if not commands_py.exists():
            continue

        domain = adapter_dir.name
        metadata = {}
        metadata_path = adapter_dir / "metadata.json"
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        commands_list = metadata.get("commands", [])
        command_count = len(commands_list) if isinstance(commands_list, list) else 0

        adapters.append(
            {
                "domain": domain,
                "commands_path": str(commands_py),
                "command_count": command_count,
                "metadata": metadata,
            }
        )

    return adapters


def load_adapter(domain: str) -> click.Group | None:
    """动态导入指定 domain 的 commands.py，返回其 Click 命令组，失败返回 None"""
    adapter_dir = ADAPTERS_DIR / domain
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
    except Exception as exc:
        warnings.warn(f"加载 adapter '{domain}' 失败: {exc}", stacklevel=2)
        return None


def register_adapters(main_cli: click.Group) -> None:
    """将所有已安装 adapter 的命令组注册到主 CLI"""
    for adapter_info in discover_adapters():
        domain = adapter_info["domain"]
        try:
            group = load_adapter(domain)
            if group is not None:
                # 将 adapter 的命令组以 domain 为名注册为子命令
                # 设置 name 确保使用 domain 作为命令名（而非 adapter 内部的 group 名）
                group.name = domain
                main_cli.add_command(group, name=domain)
        except Exception as exc:
            warnings.warn(f"注册 adapter '{domain}' 失败: {exc}", stacklevel=2)
