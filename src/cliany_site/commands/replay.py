import json
import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cliany_site.explorer.models import StepRecord
from cliany_site.explorer.recording import RecordingManager


def _display_step(console: Console, step: StepRecord, step_num: int, total: int) -> None:
    action_type = step.action_data.get("type", "unknown")
    description = step.action_data.get("description", "") or str(step.action_data)
    status_text = "[bold red]⚠ 已回退[/bold red]" if step.rolled_back else "[bold green]正常[/bold green]"

    lines = Text()
    lines.append(f"动作类型: ", style="dim")
    lines.append(f"{action_type}\n", style="cyan")
    lines.append(f"描述: ", style="dim")
    lines.append(f"{description}\n", style="white")
    lines.append(f"状态: ", style="dim")
    lines.append_text(Text.from_markup(status_text))
    lines.append("\n")
    lines.append(f"时间: ", style="dim")
    lines.append(f"{step.timestamp}\n", style="dim")

    if step.screenshot_path:
        lines.append(f"截图: ", style="dim")
        lines.append(f"{step.screenshot_path}\n", style="blue")

    if step.axtree_snapshot_path:
        try:
            import json as _json
            from pathlib import Path

            axtree_raw = Path(step.axtree_snapshot_path).read_text(encoding="utf-8")
            axtree_preview = axtree_raw[:500]
            lines.append(f"AXTree 摘要:\n", style="dim")
            lines.append(f"{axtree_preview}\n", style="dim")
        except OSError:
            lines.append(f"AXTree: {step.axtree_snapshot_path}\n", style="dim")

    console.print(
        Panel(
            lines,
            title=f"[bold]步骤 {step_num}/{total}[/bold]",
            border_style="blue" if not step.rolled_back else "yellow",
        )
    )


@click.command("replay")
@click.argument("domain")
@click.option("--session", "session_id", default=None, help="指定具体录像会话 ID")
@click.option("--step", "step_mode", is_flag=True, default=False, help="手动翻页模式（按 Enter 继续，q 退出）")
@click.pass_context
def replay(ctx: click.Context, domain: str, session_id: str | None, step_mode: bool) -> None:
    """回放指定域名的探索录像（Rich 终端展示）"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    if root_obj.get("json_mode", False):
        raise click.UsageError("replay 命令不支持 --json 模式")

    console = Console()
    mgr = RecordingManager()

    if session_id:
        try:
            manifest = mgr.load_recording(domain, session_id)
        except (FileNotFoundError, OSError) as exc:
            console.print(f"[bold red]错误:[/bold red] 找不到录像会话 [cyan]{session_id}[/cyan]（{domain}）")
            console.print(f"[dim]{exc}[/dim]")
            raise SystemExit(1) from exc
    else:
        recordings = mgr.list_recordings(domain)
        if not recordings:
            console.print(f"[bold yellow]提示:[/bold yellow] 域名 [cyan]{domain}[/cyan] 暂无录像")
            console.print("[dim]使用 'cliany-site explore <url> <workflow> --record' 创建录像[/dim]")
            raise SystemExit(1)

        if len(recordings) == 1:
            manifest = recordings[0]
        else:
            console.print(f"[bold]找到 {len(recordings)} 个录像（{domain}）:[/bold]")
            for idx, rec in enumerate(recordings, 1):
                completed_mark = "✓" if rec.completed else "✗"
                console.print(
                    f"  [cyan]{idx}.[/cyan] {rec.session_id}  "
                    f"[dim]{rec.started_at[:19]}  {completed_mark}  {len(rec.steps)} 步[/dim]"
                )
            console.print("[dim]输入编号选择（q 退出）:[/dim] ", end="")
            choice = input().strip()
            if choice.lower() == "q":
                raise SystemExit(0)
            try:
                chosen_idx = int(choice) - 1
                if chosen_idx < 0 or chosen_idx >= len(recordings):
                    raise ValueError
                manifest = recordings[chosen_idx]
            except (ValueError, IndexError):
                console.print(f"[red]无效选择: {choice}[/red]")
                raise SystemExit(1)

    steps = manifest.steps
    total = len(steps)
    if total == 0:
        console.print(f"[yellow]录像 {manifest.session_id} 没有步骤记录[/yellow]")
        raise SystemExit(0)

    console.print(
        f"[bold cyan]回放录像[/bold cyan] [cyan]{domain}[/cyan]  "
        f"会话: [dim]{manifest.session_id}[/dim]  "
        f"共 [bold]{total}[/bold] 步"
    )
    console.print(f"[dim]工作流: {manifest.workflow}[/dim]")

    for i, step in enumerate(steps):
        _display_step(console, step, step_num=i + 1, total=total)

        if i < total - 1:
            if step_mode:
                console.print("[dim]按 Enter 继续，输入 q 退出:[/dim] ", end="")
                user_input = input().strip()
                if user_input.lower() == "q":
                    console.print("[yellow]已退出回放[/yellow]")
                    break
            else:
                time.sleep(2)

    console.print("[bold green]回放完成[/bold green]")
