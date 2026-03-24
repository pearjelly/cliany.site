import click
from cliany_site.loader import discover_adapters
from cliany_site.response import print_response, success_response


@click.command("list")
@click.option(
    "--detail", is_flag=True, default=False, help="显示每个 adapter 的命令详情"
)
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出")
def list_cmd(detail, json_mode):
    """列出所有已生成的 CLI adapter"""
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

    if not json_mode:
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

    print_response(result, json_mode)
