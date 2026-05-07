from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import click

from cliany_site.atomic_io import atomic_write_json
from cliany_site.config import get_config
from cliany_site.envelope import ok
from cliany_site.response import print_response


def _compute_signature(commands_py_path: Path) -> str:
    return hashlib.sha256(commands_py_path.read_bytes()).hexdigest()


def _run_migrate() -> dict:
    adapters_dir = get_config().adapters_dir
    migrated: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []

    if not adapters_dir.exists():
        return {"migrated": migrated, "skipped": skipped, "warnings": warnings}

    for adapter_dir in sorted(adapters_dir.iterdir()):
        if not adapter_dir.is_dir():
            continue

        metadata_path = adapter_dir / "metadata.json"
        commands_py_path = adapter_dir / "commands.py"
        domain = adapter_dir.name

        if not metadata_path.exists():
            continue

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            warnings.append(f"{domain}: metadata.json 解析失败 — {exc}")
            continue

        schema_version = metadata.get("schema_version")

        if schema_version == 3:
            if commands_py_path.exists() and "signature" in metadata:
                current_sig = _compute_signature(commands_py_path)
                if current_sig != metadata["signature"]:
                    warnings.append(
                        f"{domain}: commands.py 已修改（signature drift），建议重新探索以更新"
                    )
            skipped.append(domain)
            continue

        shutil.copy2(metadata_path, metadata_path.parent / "metadata.json.bak")

        new_metadata = dict(metadata)
        new_metadata["schema_version"] = 3

        axtree = new_metadata.get("axtree")
        if not isinstance(axtree, dict):
            axtree = {}
        axtree.setdefault("compounds", {})
        axtree.setdefault(
            "pruning_meta",
            {"original_count": 0, "pruned_count": 0, "pruning_ratio": 0.0},
        )
        new_metadata["axtree"] = axtree

        new_metadata.setdefault("capability", "browser")
        new_metadata.setdefault("api_endpoints", [])

        if commands_py_path.exists():
            new_metadata["signature"] = _compute_signature(commands_py_path)

        atomic_write_json(metadata_path, new_metadata)
        migrated.append(domain)

    return {"migrated": migrated, "skipped": skipped, "warnings": warnings}


@click.command("migrate")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
def migrate_cmd(ctx: click.Context, json_mode: bool | None):
    """将旧版 adapter 迁移到 v3 schema"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = (
        json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))
    )

    data = _run_migrate()
    result = ok(command="migrate", data=data, source="builtin")

    if not effective_json_mode:
        from rich.console import Console

        console = Console()
        console.print(
            f"[green]迁移完成[/green]: "
            f"{len(data['migrated'])} 个已迁移，"
            f"{len(data['skipped'])} 个已跳过"
        )
        for w in data["warnings"]:
            console.print(f"[yellow]⚠ {w}[/yellow]")
        return

    print_response(result, effective_json_mode)
