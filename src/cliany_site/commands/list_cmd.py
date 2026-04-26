import json

import click

from cliany_site.config import get_config
from cliany_site.envelope import ok
from cliany_site.loader import discover_adapters
from cliany_site.metadata import LegacyMetadataError, load_metadata
from cliany_site.response import print_response, success_response


@click.command("list")
@click.option(
    "--detail", is_flag=True, default=False, help="显示每个 adapter 的命令详情"
)
@click.option(
    "--legacy", is_flag=True, default=False, help="只列出旧版 adapter（需重新生成）"
)
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
def list_cmd(ctx: click.Context, detail: bool, legacy: bool, json_mode: bool | None):
    """列出所有已生成的 CLI adapter"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = (
        json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))
    )

    if legacy:
        _list_legacy(effective_json_mode)
        return

    adapters_raw = discover_adapters()

    adapters_data = []
    for adapter in adapters_raw:
        domain = adapter["domain"]
        metadata = adapter.get("metadata", {})
        entry = {
            "domain": domain,
            "source_url": metadata.get("source_url", ""),
            "workflow": metadata.get("workflow", ""),
            "command_count": adapter["command_count"],
            "generated_at": metadata.get("generated_at", ""),
        }
        if detail:
            entry["commands"] = metadata.get("commands", [])
        adapters_data.append(entry)

    if not adapters_data:
        message = "未发现任何 adapter。使用 'cliany-site explore' 创建一个。"
    else:
        message = f"共 {len(adapters_data)} 个 adapter"

    result = success_response({"adapters": adapters_data, "message": message})

    if not effective_json_mode:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        if not adapters_data:
            console.print(f"[yellow]{message}[/yellow]")
        else:
            table = Table(title="已安装 Adapters")
            table.add_column("Domain", style="cyan")
            table.add_column("命令数", justify="right")
            table.add_column("生成时间")
            table.add_column("工作流描述")
            for a in adapters_data:
                table.add_row(
                    a["domain"],
                    str(a["command_count"]),
                    a["generated_at"][:10] if a["generated_at"] else "-",
                    a["workflow"][:40] if a["workflow"] else "-",
                )
            console.print(table)
        return

    print_response(result, effective_json_mode)


def _list_legacy(json_mode: bool) -> None:
    adapters_dir = get_config().adapters_dir
    legacy_list = []

    if adapters_dir.exists():
        for adapter_dir in sorted(adapters_dir.iterdir()):
            if not adapter_dir.is_dir():
                continue
            metadata_path = adapter_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            domain = adapter_dir.name
            try:
                load_metadata(metadata_path)
            except LegacyMetadataError:
                source_url = "<entry_url>"
                try:
                    raw_md = json.loads(metadata_path.read_text(encoding="utf-8"))
                    source_url = raw_md.get("source_url", "<entry_url>")
                except (json.JSONDecodeError, OSError):
                    pass
                legacy_list.append(
                    {
                        "domain": domain,
                        "path": str(adapter_dir),
                        "suggested_command": f"cliany-site explore {source_url}",
                    }
                )
            except Exception:  # noqa: BLE001
                pass

    result = ok(command="list", data=legacy_list, source="builtin")

    if json_mode:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console

        console = Console()
        if not legacy_list:
            console.print("[green]没有旧版 adapter。[/green]")
        else:
            for item in legacy_list:
                console.print(
                    f"[yellow]{item['domain']}[/yellow]: {item['suggested_command']}"
                )
