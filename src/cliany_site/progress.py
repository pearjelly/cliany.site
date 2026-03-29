"""进度反馈模块 — 为 explore 和 execute 提供统一的进度回调协议。

提供两种实现：
- RichProgressReporter: 交互式终端下使用 rich Spinner / Progress bar
- NdjsonProgressReporter: --json 模式下输出 NDJSON 事件流到 stderr
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any, Protocol

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

# ── 回调协议 ──────────────────────────────────────────────


class ProgressReporter(Protocol):
    """explore / execute 进度回调协议。"""

    # ── explore 阶段 ──
    def on_explore_start(self, url: str, workflow: str, max_steps: int) -> None: ...
    def on_explore_step_start(self, step: int, max_steps: int) -> None: ...
    def on_explore_llm_start(self, step: int) -> None: ...
    def on_explore_llm_done(self, step: int, actions_count: int) -> None: ...
    def on_explore_step_done(self, step: int, actions_count: int, elapsed_ms: float) -> None: ...
    def on_explore_done(self, total_steps: int, total_actions: int, total_commands: int, elapsed_ms: float) -> None: ...

    # ── execute 阶段 ──
    def on_execute_start(self, total_actions: int, domain: str, command: str) -> None: ...
    def on_execute_step_start(self, index: int, total: int, action_type: str, description: str) -> None: ...
    def on_execute_step_done(
        self, index: int, total: int, success: bool, elapsed_ms: float, error: str | None = None
    ) -> None: ...
    def on_execute_done(self, succeeded: int, failed: int, total: int, elapsed_ms: float) -> None: ...


# ── 空实现 ──────────────────────────────────────────────


class NullProgressReporter:
    """不做任何事的哑进度报告器，用作默认值。"""

    def on_explore_start(self, url: str, workflow: str, max_steps: int) -> None:
        pass

    def on_explore_step_start(self, step: int, max_steps: int) -> None:
        pass

    def on_explore_llm_start(self, step: int) -> None:
        pass

    def on_explore_llm_done(self, step: int, actions_count: int) -> None:
        pass

    def on_explore_step_done(self, step: int, actions_count: int, elapsed_ms: float) -> None:
        pass

    def on_explore_done(self, total_steps: int, total_actions: int, total_commands: int, elapsed_ms: float) -> None:
        pass

    def on_execute_start(self, total_actions: int, domain: str, command: str) -> None:
        pass

    def on_execute_step_start(self, index: int, total: int, action_type: str, description: str) -> None:
        pass

    def on_execute_step_done(
        self, index: int, total: int, success: bool, elapsed_ms: float, error: str | None = None
    ) -> None:
        pass

    def on_execute_done(self, succeeded: int, failed: int, total: int, elapsed_ms: float) -> None:
        pass


# ── Rich 交互式进度 ──────────────────────────────────────


class RichProgressReporter:
    """使用 rich Live display 展示实时进度。

    - explore: Spinner + 步骤信息表
    - execute: 进度条 + 每步状态标记
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console(stderr=True)
        self._live: Live | None = None
        self._explore_start: float = 0.0
        self._execute_start: float = 0.0
        self._explore_steps: list[dict[str, Any]] = []
        self._current_explore_step: int = 0
        self._max_explore_steps: int = 0
        self._explore_phase: str = ""
        self._execute_steps: list[dict[str, Any]] = []
        self._execute_total: int = 0

    # ── explore ──

    def on_explore_start(self, url: str, workflow: str, max_steps: int) -> None:
        self._explore_start = time.monotonic()
        self._max_explore_steps = max_steps
        self._explore_steps = []
        self._console.print(f"[bold cyan]探索[/bold cyan] {url}")
        self._console.print(f"[dim]工作流: {workflow}[/dim]")
        self._live = Live(self._build_explore_display(), console=self._console, refresh_per_second=4)
        self._live.start()

    def on_explore_step_start(self, step: int, max_steps: int) -> None:
        self._current_explore_step = step
        self._explore_phase = "捕获页面"
        self._update_explore_live()

    def on_explore_llm_start(self, step: int) -> None:
        self._explore_phase = "LLM 分析中..."
        self._update_explore_live()

    def on_explore_llm_done(self, step: int, actions_count: int) -> None:
        self._explore_phase = f"执行 {actions_count} 个动作"
        self._update_explore_live()

    def on_explore_step_done(self, step: int, actions_count: int, elapsed_ms: float) -> None:
        self._explore_steps.append(
            {
                "step": step,
                "actions": actions_count,
                "elapsed_ms": elapsed_ms,
            }
        )
        self._explore_phase = ""
        self._update_explore_live()

    def on_explore_done(self, total_steps: int, total_actions: int, total_commands: int, elapsed_ms: float) -> None:
        if self._live:
            self._live.stop()
            self._live = None
        elapsed_s = elapsed_ms / 1000
        self._console.print(
            f"[bold green]探索完成[/bold green]  "
            f"{total_steps} 步 / {total_actions} 动作 / {total_commands} 命令  "
            f"[dim]({elapsed_s:.1f}s)[/dim]"
        )

    def _update_explore_live(self) -> None:
        if self._live:
            self._live.update(self._build_explore_display())

    def _build_explore_display(self) -> Table:
        elapsed = time.monotonic() - self._explore_start
        table = Table(show_header=False, show_edge=False, padding=(0, 1), expand=False)
        table.add_column(style="bold", no_wrap=True)
        table.add_column()

        step_label = f"步骤 {self._current_explore_step + 1}/{self._max_explore_steps}"
        spinner_text = Text(f"  {step_label}", style="cyan")
        if self._explore_phase:
            spinner_text.append(f"  {self._explore_phase}", style="yellow")
        spinner_text.append(f"  [{elapsed:.1f}s]", style="dim")
        table.add_row("", spinner_text)

        for step_info in self._explore_steps:
            done_text = Text(
                f"  步骤 {step_info['step'] + 1}: {step_info['actions']} 动作 ({step_info['elapsed_ms']:.0f}ms)",
                style="green",
            )
            table.add_row("", done_text)

        return table

    # ── execute ──

    def on_execute_start(self, total_actions: int, domain: str, command: str) -> None:
        self._execute_start = time.monotonic()
        self._execute_total = total_actions
        self._execute_steps = []
        self._console.print(f"[bold cyan]执行[/bold cyan] {domain} {command}  [dim]({total_actions} 步)[/dim]")
        self._live = Live(self._build_execute_display(), console=self._console, refresh_per_second=4)
        self._live.start()

    def on_execute_step_start(self, index: int, total: int, action_type: str, description: str) -> None:
        self._execute_steps.append(
            {
                "index": index,
                "action_type": action_type,
                "description": description,
                "status": "running",
                "elapsed_ms": 0.0,
                "error": None,
            }
        )
        self._update_execute_live()

    def on_execute_step_done(
        self, index: int, total: int, success: bool, elapsed_ms: float, error: str | None = None
    ) -> None:
        for step in self._execute_steps:
            if step["index"] == index:
                step["status"] = "success" if success else "failed"
                step["elapsed_ms"] = elapsed_ms
                step["error"] = error
                break
        self._update_execute_live()

    def on_execute_done(self, succeeded: int, failed: int, total: int, elapsed_ms: float) -> None:
        if self._live:
            self._live.stop()
            self._live = None
        elapsed_s = elapsed_ms / 1000
        status = "[bold green]执行完成[/bold green]" if failed == 0 else "[bold yellow]执行完成(部分失败)[/bold yellow]"
        self._console.print(f"{status}  成功 {succeeded} / 失败 {failed} / 总计 {total}  [dim]({elapsed_s:.1f}s)[/dim]")

    def _update_execute_live(self) -> None:
        if self._live:
            self._live.update(self._build_execute_display())

    def _build_execute_display(self) -> Table:
        elapsed = time.monotonic() - self._execute_start
        table = Table(show_header=False, show_edge=False, padding=(0, 1), expand=False)
        table.add_column(width=3, no_wrap=True)
        table.add_column(width=10, no_wrap=True)
        table.add_column()
        table.add_column(width=10, justify="right")

        done_count = sum(1 for s in self._execute_steps if s["status"] != "running")
        header = Text(f"进度 {done_count}/{self._execute_total}  [{elapsed:.1f}s]", style="cyan")
        table.add_row("", "", header, "")

        for step in self._execute_steps:
            if step["status"] == "success":
                marker = Text("[green]OK[/green]")
                style = "green"
            elif step["status"] == "failed":
                marker = Text("[red]ERR[/red]")
                style = "red"
            else:
                marker = Text("[yellow]...[/yellow]")
                style = "yellow"

            desc = step["description"] or step["action_type"]
            timing = f"{step['elapsed_ms']:.0f}ms" if step["elapsed_ms"] > 0 else ""
            table.add_row(
                marker,
                Text(step["action_type"], style="dim"),
                Text(desc, style=style),
                Text(timing, style="dim"),
            )

        return table


# ── NDJSON 流式事件 ──────────────────────────────────────


class NdjsonProgressReporter:
    """--json 模式下输出 NDJSON 事件流到 stderr。

    每行一个 JSON 对象：
    {"event": "explore_step_start", "step": 1, "max_steps": 10, "ts": 1234567890.123}
    """

    def __init__(self, file: Any = None) -> None:
        self._file = file or sys.stderr
        self._start: float = 0.0

    def _emit(self, event: str, **data: Any) -> None:
        payload: dict[str, Any] = {"event": event, "ts": time.time()}
        payload.update(data)
        try:
            line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            print(line, file=self._file, flush=True)
        except (TypeError, ValueError, OSError):
            pass

    # ── explore ──

    def on_explore_start(self, url: str, workflow: str, max_steps: int) -> None:
        self._start = time.monotonic()
        self._emit("explore_start", url=url, workflow=workflow, max_steps=max_steps)

    def on_explore_step_start(self, step: int, max_steps: int) -> None:
        self._emit("explore_step_start", step=step, max_steps=max_steps)

    def on_explore_llm_start(self, step: int) -> None:
        self._emit("explore_llm_start", step=step)

    def on_explore_llm_done(self, step: int, actions_count: int) -> None:
        self._emit("explore_llm_done", step=step, actions_count=actions_count)

    def on_explore_step_done(self, step: int, actions_count: int, elapsed_ms: float) -> None:
        self._emit("explore_step_done", step=step, actions_count=actions_count, elapsed_ms=round(elapsed_ms, 1))

    def on_explore_done(self, total_steps: int, total_actions: int, total_commands: int, elapsed_ms: float) -> None:
        self._emit(
            "explore_done",
            total_steps=total_steps,
            total_actions=total_actions,
            total_commands=total_commands,
            elapsed_ms=round(elapsed_ms, 1),
        )

    # ── execute ──

    def on_execute_start(self, total_actions: int, domain: str, command: str) -> None:
        self._start = time.monotonic()
        self._emit("execute_start", total_actions=total_actions, domain=domain, command=command)

    def on_execute_step_start(self, index: int, total: int, action_type: str, description: str) -> None:
        self._emit("execute_step_start", index=index, total=total, action_type=action_type, description=description)

    def on_execute_step_done(
        self, index: int, total: int, success: bool, elapsed_ms: float, error: str | None = None
    ) -> None:
        data: dict[str, Any] = {
            "index": index,
            "total": total,
            "success": success,
            "elapsed_ms": round(elapsed_ms, 1),
        }
        if error:
            data["error"] = error
        self._emit("execute_step_done", **data)

    def on_execute_done(self, succeeded: int, failed: int, total: int, elapsed_ms: float) -> None:
        self._emit("execute_done", succeeded=succeeded, failed=failed, total=total, elapsed_ms=round(elapsed_ms, 1))
