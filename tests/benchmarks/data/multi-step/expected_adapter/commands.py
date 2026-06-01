# 自动生成 — DO NOT EDIT
# pyright: reportMissingImports=false
# 来源 URL: http://test.local/dashboard
# 工作流: 创建新工单

import json
import click
from cliany_site.codegen.runtime_helpers import execute_steps_via_atoms, diagnose_if_enabled
from cliany_site.envelope import ok, err, ErrorCode
from cliany_site.action_runtime import substitute_parameters

DOMAIN = 'test.local'
SOURCE_URL = 'http://test.local/dashboard'


@click.group()
def cli():
    """test.local 的自动生成 CLI 命令"""
    pass


def _resolve_json_mode(local_json_mode):
    if local_json_mode is not None:
        return bool(local_json_mode)
    ctx = click.get_current_context(silent=True)
    if ctx is None:
        return False
    root_ctx = ctx.find_root()
    obj = getattr(root_ctx, "obj", None)
    if not isinstance(obj, dict):
        return False
    return bool(obj.get("json_mode", False))


@cli.command("create-ticket")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
@click.option('--title', 'title', required=True, default='登录失败', help='工单标题')
@click.option('--priority', 'priority', required=True, default='高', help='工单优先级')
def create_ticket(ctx: click.Context, json_mode: bool | None, title, priority):
    """创建新工单"""
    action_steps = []
    action_steps = json.loads('[{"type": "navigate", "ref": "", "url": "http://test.local/tickets/new", "value": "", "description": "进入新建工单页面", "target_name": "", "target_role": "", "target_attributes": {}}, {"type": "type", "ref": "5", "url": "", "value": "{{title}}", "description": "输入工单标题", "target_name": "标题", "target_role": "textbox", "target_attributes": {"id": "ticket-title", "class": "benchmark-ticket-title"}}, {"type": "select", "ref": "6", "url": "", "value": "{{priority}}", "description": "选择优先级", "target_name": "优先级", "target_role": "combobox", "target_attributes": {"id": "ticket-priority", "class": "benchmark-ticket-priority"}}, {"type": "click", "ref": "7", "url": "", "value": "", "description": "保存工单", "target_name": "保存", "target_role": "button", "target_attributes": {"id": "ticket-save", "class": "benchmark-ticket-save"}}]')
    # - [0] navigate: http://test.local/tickets/new | 进入新建工单页面
    # - [1] type: 5 <- 登录失败 | 输入工单标题
    # - [2] select: 6 => 高 | 选择优先级
    # - [3] click: 7 | 保存工单
    action_steps = substitute_parameters(action_steps, {'title': title, 'priority': priority})
    action_steps.extend(action_steps)
    results = execute_steps_via_atoms(action_steps, SOURCE_URL, DOMAIN)
    failed = next((r for r in results if not r.get("ok")), None)
    if _resolve_json_mode(json_mode):
        click.echo(json.dumps({
            "ok": failed is None,
            "data": {"results": results, "command": "create-ticket", "args": {'title': title, 'priority': priority}},
            "error": (failed or {}).get("error"),
            "meta": {"source": "adapter"},
        }, ensure_ascii=False))
    elif failed is None:
        click.echo("✓ create-ticket 完成")
    else:
        diagnose_if_enabled(ctx, failed or {})
        err_msg = (failed.get("error") or {}).get("message", "")
        click.echo(f"✗ {err_msg}", err=True)
        ctx.exit(1)



if __name__ == "__main__":
    cli()
