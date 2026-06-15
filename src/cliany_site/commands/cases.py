from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import click

from cliany_site.envelope import ErrorCode, err, ok
from cliany_site.response import print_response

ALLOWED_STATUSES = ("active", "candidate", "degraded", "known-gap", "retired")
PROMOTION_TASKS = ("adapter_package", "metadata_validation", "online_smoke")


def _case_catalog_paths() -> list[Path]:
    command_path = Path(__file__).resolve()
    return [
        command_path.parents[1] / "cases" / "manifest.json",
        command_path.parents[3] / "cases" / "manifest.json",
        Path.cwd() / "cases" / "manifest.json",
    ]


def _load_cases_manifest() -> tuple[list[dict[str, Any]], Path | None, list[Path]]:
    checked_paths = _case_catalog_paths()
    for path in checked_paths:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            msg = f"{path} must contain a JSON array"
            raise ValueError(msg)
        cases = [case for case in payload if isinstance(case, dict)]
        return cases, path, checked_paths
    return [], None, checked_paths


def _offline_commands(case: dict[str, Any]) -> list[str]:
    validation = case.get("validation")
    if not isinstance(validation, dict):
        return []
    commands = validation.get("offline_commands")
    if not isinstance(commands, list):
        return []
    return [str(command) for command in commands]


def _compact_case(case: dict[str, Any], *, detail: bool) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": case.get("id"),
        "title": case.get("title"),
        "category": case.get("category"),
        "status": case.get("status"),
        "target_url": case.get("target_url"),
        "adapter_domain": case.get("adapter_domain"),
        "docs": case.get("docs"),
        "example_output": case.get("example_output"),
        "commands": case.get("commands") if isinstance(case.get("commands"), list) else [],
        "offline_commands": _offline_commands(case),
    }
    if detail:
        for key in ("source_release", "validation", "promotion", "promotion_evidence"):
            if key in case:
                item[key] = case.get(key)
    return item


def _case_ids(cases: list[dict[str, Any]]) -> list[str]:
    return [str(case.get("id")) for case in cases if case.get("id")]


def _promotion_evidence_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    task_status_counts: dict[str, Counter[str]] = {task: Counter() for task in PROMOTION_TASKS}
    pending_tasks: list[dict[str, str]] = []
    task_count = 0

    for case in cases:
        if case.get("status") != "candidate":
            continue
        evidence = case.get("promotion_evidence")
        if not isinstance(evidence, dict):
            continue
        case_id = str(case.get("id") or "")
        for task in PROMOTION_TASKS:
            task_evidence = evidence.get(task)
            if not isinstance(task_evidence, dict):
                continue
            status = str(task_evidence.get("status") or "pending")
            next_action = str(task_evidence.get("next_action") or "")
            status_counts[status] += 1
            task_status_counts[task][status] += 1
            task_count += 1
            if status in {"pending", "blocked"}:
                pending_tasks.append(
                    {
                        "case_id": case_id,
                        "task": task,
                        "status": status,
                        "next_action": next_action,
                    }
                )

    primary = pending_tasks[0] if pending_tasks else {}
    return {
        "candidate_count": sum(1 for case in cases if case.get("status") == "candidate"),
        "task_count": task_count,
        "status_counts": {
            "pending": status_counts.get("pending", 0),
            "blocked": status_counts.get("blocked", 0),
            "complete": status_counts.get("complete", 0),
        },
        "task_status_counts": {
            task: {
                "pending": counts.get("pending", 0),
                "blocked": counts.get("blocked", 0),
                "complete": counts.get("complete", 0),
            }
            for task, counts in task_status_counts.items()
        },
        "pending_count": status_counts.get("pending", 0),
        "blocked_count": status_counts.get("blocked", 0),
        "complete_count": status_counts.get("complete", 0),
        "primary_case_id": primary.get("case_id", ""),
        "primary_task": primary.get("task", ""),
        "primary_next_action": primary.get("next_action", ""),
    }


def _summary(cases: list[dict[str, Any]], *, catalog_total: int) -> dict[str, Any]:
    statuses = Counter(str(case.get("status") or "unknown") for case in cases)
    categories = Counter(str(case.get("category") or "unknown") for case in cases)
    return {
        "total": len(cases),
        "catalog_total": catalog_total,
        "status_counts": {status: statuses.get(status, 0) for status in ALLOWED_STATUSES},
        "category_counts": dict(sorted(categories.items())),
        "active_count": statuses.get("active", 0),
        "candidate_count": statuses.get("candidate", 0),
        "known_gap_count": statuses.get("known-gap", 0),
    }


def _print_single_case_detail(console: Any, case: dict[str, Any]) -> None:
    console.print("\n[bold]案例详情[/bold]")
    for label, key in (
        ("ID", "id"),
        ("Title", "title"),
        ("Status", "status"),
        ("Category", "category"),
        ("Target", "target_url"),
        ("Adapter", "adapter_domain"),
        ("Docs", "docs"),
        ("Example", "example_output"),
    ):
        value = case.get(key)
        if value:
            console.print(f"- {label}: {value}")

    validation = case.get("validation")
    if isinstance(validation, dict):
        console.print("\n[bold]Validation[/bold]")
        for key in ("offline", "online"):
            value = validation.get(key)
            if value:
                console.print(f"- {key}: {value}")

    evidence = case.get("promotion_evidence")
    if isinstance(evidence, dict):
        console.print("\n[bold]Promotion Tasks[/bold]")
        for task in PROMOTION_TASKS:
            task_evidence = evidence.get(task)
            if not isinstance(task_evidence, dict):
                continue
            status = task_evidence.get("status") or "unknown"
            evidence_value = task_evidence.get("evidence") or "Not attached yet."
            next_action = task_evidence.get("next_action") or "No next action declared."
            console.print(f"- {task}: {status}")
            console.print(f"  evidence: {evidence_value}")
            console.print(f"  next: {next_action}")


def _print_human_cases(data: dict[str, Any], *, detail: bool) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    cases = data["cases"]
    summary = data["summary"]
    source = data.get("source_path") or "unknown"
    console.print("[bold]cliany-site cases[/bold]")
    case_counts = (
        f"active {summary['active_count']} / "
        f"candidate {summary['candidate_count']} / "
        f"known-gap {summary['known_gap_count']}"
    )
    console.print(f"共 {summary['total']} 个案例（{case_counts}）")
    console.print(f"索引: {source}")

    if not cases:
        console.print("[yellow]没有匹配的案例。[/yellow]")
        return

    if detail and len(cases) == 1:
        _print_single_case_detail(console, cases[0])

    table = Table(title="案例库")
    table.add_column("ID", style="cyan")
    table.add_column("Status")
    table.add_column("Category")
    table.add_column("Adapter")
    table.add_column("First command")
    for case in cases:
        commands = case.get("commands") if isinstance(case.get("commands"), list) else []
        table.add_row(
            str(case.get("id") or ""),
            str(case.get("status") or ""),
            str(case.get("category") or ""),
            str(case.get("adapter_domain") or "-"),
            str(commands[0]) if commands else "-",
        )
    console.print(table)

    console.print("\n[bold]快速命令[/bold]")
    for case in cases:
        commands = case.get("commands") if isinstance(case.get("commands"), list) else []
        if not commands:
            continue
        console.print(f"- {case.get('id')}:")
        command_lines = commands if detail else commands[:1]
        for command in command_lines:
            console.print(f"  {command}")

    promotion = data.get("promotion_evidence_summary")
    if isinstance(promotion, dict) and promotion.get("primary_next_action"):
        console.print("\n[bold]Candidate 下一步[/bold]")
        console.print(
            f"- {promotion.get('primary_case_id')}/{promotion.get('primary_task')}: "
            f"{promotion.get('primary_next_action')}"
        )

    if detail:
        console.print("\n[bold]离线验证命令[/bold]")
        for case in cases:
            offline_commands = case.get("offline_commands")
            if not isinstance(offline_commands, list) or not offline_commands:
                continue
            console.print(f"- {case.get('id')}:")
            for command in offline_commands:
                console.print(f"  {command}")


@click.command("cases")
@click.option("--case-id", default=None, help="只显示指定案例 ID，并自动展开详情")
@click.option("--status", type=click.Choice(ALLOWED_STATUSES), default=None, help="只显示指定状态的案例")
@click.option("--detail", is_flag=True, default=False, help="显示 promotion 和 validation 详情")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
def cases_cmd(
    ctx: click.Context,
    case_id: str | None,
    status: str | None,
    detail: bool,
    json_mode: bool | None,
) -> None:
    """列出内置真实案例和候选工作流"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    try:
        catalog_cases, source_path, checked_paths = _load_cases_manifest()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = err(
            "cases",
            ErrorCode.E_UNKNOWN,
            f"案例索引读取失败: {exc}",
            hint="请确认 cases/manifest.json 存在且是合法 JSON。",
            details={"checked_paths": [str(path) for path in _case_catalog_paths()]},
        )
        print_response(result, effective_json_mode)
        return

    if source_path is None:
        result = err(
            "cases",
            ErrorCode.E_UNKNOWN,
            "未找到案例索引 cases/manifest.json",
            hint="源码仓库请确认 cases/manifest.json 存在；安装包请重新安装包含案例资源的版本。",
            details={"checked_paths": [str(path) for path in checked_paths]},
        )
        print_response(result, effective_json_mode)
        return

    filtered_cases = [case for case in catalog_cases if status is None or case.get("status") == status]
    if case_id:
        exact_matches = [case for case in filtered_cases if case.get("id") == case_id]
        if not exact_matches:
            result = err(
                "cases",
                ErrorCode.E_INVALID_PARAM,
                f"未找到案例: {case_id}",
                hint="运行 cliany-site cases --json 查看可用案例，或检查 --status 筛选条件。",
                details={
                    "case_id": case_id,
                    "status_filter": status,
                    "available_case_ids": _case_ids(filtered_cases),
                },
            )
            print_response(result, effective_json_mode)
            return
        filtered_cases = exact_matches

    include_detail = detail or bool(case_id)
    data = {
        "source_path": str(source_path),
        "case_id": case_id,
        "status_filter": status,
        "summary": _summary(filtered_cases, catalog_total=len(catalog_cases)),
        "promotion_evidence_summary": _promotion_evidence_summary(filtered_cases),
        "cases": [_compact_case(case, detail=include_detail) for case in filtered_cases],
    }
    result = ok(command="cases", data=data, source="builtin")

    if effective_json_mode:
        print_response(result, effective_json_mode)
        return
    _print_human_cases(data, detail=include_detail)
