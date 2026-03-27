import json
from pathlib import Path

import click

from cliany_site.report import list_reports
from cliany_site.response import error_response, print_response, success_response


@click.group("report")
@click.pass_context
def report_group(ctx: click.Context):
    """管理执行报告（list / show）"""
    ctx.ensure_object(dict)


@report_group.command("list")
@click.option("--domain", default=None, help="按域名过滤报告")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def report_list(ctx: click.Context, domain: str | None, json_mode: bool | None):
    """列出执行报告"""
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = (
        json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))
    )
    reports = list_reports(domain=domain)
    result = success_response({"reports": reports})
    print_response(result, json_mode=effective_json, exit_on_error=False)


@report_group.command("show")
@click.argument("report_id")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def report_show(ctx: click.Context, report_id: str, json_mode: bool | None):
    """显示指定报告详情（report_id 为报告文件路径或文件名）"""
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = (
        json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))
    )

    from cliany_site.report import REPORTS_DIR

    candidate = Path(report_id)
    if not candidate.is_absolute():
        candidate = REPORTS_DIR / report_id

    if not candidate.exists():
        result = error_response(
            "REPORT_NOT_FOUND",
            f"报告文件不存在: {report_id}",
            fix="使用 'cliany-site report list' 查看可用报告路径",
        )
        print_response(result, json_mode=effective_json, exit_on_error=True)
        return

    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        result = success_response(data)
    except Exception as exc:
        result = error_response(
            "REPORT_READ_ERROR",
            f"读取报告失败: {exc}",
            fix="报告文件可能已损坏",
        )

    print_response(result, json_mode=effective_json, exit_on_error=True)
