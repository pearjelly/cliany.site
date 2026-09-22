import logging

import click

from cliany_site.response import error_response, print_response, success_response
from cliany_site.workflow.parser import WorkflowParseError, load_workflow_file

logger = logging.getLogger(__name__)


@click.group("workflow")
def workflow_group() -> None:
    """工作流编排命令"""


@workflow_group.command("run")
@click.argument("file", type=click.Path(exists=True))
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.option("--dry-run", is_flag=True, default=False, help="仅解析验证，不实际执行")
@click.pass_context
def workflow_run(ctx: click.Context, file: str, json_mode: bool | None, dry_run: bool) -> None:
    """执行 YAML 工作流文件"""
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    try:
        workflow = load_workflow_file(file)
    except WorkflowParseError as exc:
        print_response(
            error_response("WORKFLOW_PARSE_ERROR", str(exc)),
            json_mode=effective_json,
        )
        return

    if dry_run:
        step_summaries = [{"name": s.name, "adapter": s.adapter, "command": s.command} for s in workflow.steps]
        print_response(
            success_response(
                {
                    "workflow": workflow.name,
                    "mode": "dry-run",
                    "steps": step_summaries,
                    "step_count": len(workflow.steps),
                }
            ),
            json_mode=effective_json,
        )
        return

    from cliany_site.workflow.engine import run_workflow

    result = run_workflow(workflow)

    if result.success:
        print_response(
            success_response(result.to_dict()),
            json_mode=effective_json,
        )
    else:
        err_msg = ""
        for sr in result.steps:
            if not sr.success and not sr.skipped and sr.error:
                err_msg = f"步骤 '{sr.name}' 失败: {sr.error}"
                break
        print_response(
            error_response(
                "WORKFLOW_FAILED", err_msg or "工作流执行失败",
                fix="检查各步骤配置和 adapter 状态", details=result.to_dict(),
            ),
            json_mode=effective_json,
        )


@workflow_group.command("validate")
@click.argument("file", type=click.Path(exists=True))
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def workflow_validate(ctx: click.Context, file: str, json_mode: bool | None) -> None:
    """验证 YAML 工作流文件格式"""
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    try:
        workflow = load_workflow_file(file)
    except WorkflowParseError as exc:
        print_response(
            error_response("WORKFLOW_PARSE_ERROR", str(exc)),
            json_mode=effective_json,
        )
        return

    print_response(
        success_response(
            {
                "workflow": workflow.name,
                "valid": True,
                "step_count": len(workflow.steps),
                "steps": [
                    {
                        "name": s.name,
                        "adapter": s.adapter,
                        "command": s.command,
                        "has_when": bool(s.when),
                        "has_retry": s.retry.max_attempts > 1,
                    }
                    for s in workflow.steps
                ],
            }
        ),
        json_mode=effective_json,
    )


@workflow_group.command("batch")
@click.argument("adapter")
@click.argument("command")
@click.argument("data_file", type=click.Path(exists=True))
@click.option("--concurrency", "-c", type=int, default=1, help="并发数（默认 1）")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def workflow_batch(
    ctx: click.Context,
    adapter: str,
    command: str,
    data_file: str,
    concurrency: int,
    json_mode: bool | None,
) -> None:
    """批量执行：从 CSV/JSON 读取参数列表"""
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    from cliany_site.workflow.batch import BatchDataError, load_batch_data, run_batch
    from cliany_site.workflow.engine import ClickAdapterExecutor
    from cliany_site.workflow.models import StepDef

    try:
        data = load_batch_data(data_file)
    except BatchDataError as exc:
        print_response(
            error_response("BATCH_DATA_ERROR", str(exc)),
            json_mode=effective_json,
        )
        return

    step = StepDef(name="batch", adapter=adapter, command=command)
    executor = ClickAdapterExecutor()
    result = run_batch(step, data, executor, concurrency=concurrency)

    if result.failed == 0:
        print_response(
            success_response(result.to_dict()),
            json_mode=effective_json,
        )
    else:
        print_response(
            error_response(
                "BATCH_PARTIAL_FAILURE",
                f"批量执行完成：成功 {result.succeeded} / 失败 {result.failed} / 总计 {result.total}",
                fix="检查失败项的错误信息",
                details=result.to_dict(),
            ),
            json_mode=effective_json,
        )
