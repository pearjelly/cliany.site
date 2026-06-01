# 自动生成 — DO NOT EDIT
# pyright: reportMissingImports=false
# 来源 URL: http://test.local/
# 工作流: 搜索站内内容

import json
import click
from cliany_site.codegen.runtime_helpers import execute_steps_via_atoms, diagnose_if_enabled
from cliany_site.envelope import ok, err, ErrorCode
from cliany_site.action_runtime import substitute_parameters

DOMAIN = 'test.local'
SOURCE_URL = 'http://test.local/'


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


@cli.command("search")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
@click.option('--query', 'query', required=True, default='cliany-site', help='搜索关键词')
def search(ctx: click.Context, json_mode: bool | None, query):
    """搜索站内内容"""
    action_steps = []
    action_steps = json.loads('[{"type": "click", "ref": "1", "url": "", "value": "", "description": "点击打开搜索框", "target_name": "打开搜索", "target_role": "button", "target_attributes": {"id": "search-open", "class": "benchmark-search-open"}}, {"type": "type", "ref": "2", "url": "", "value": "{{query}}", "description": "输入搜索关键词", "target_name": "搜索关键词", "target_role": "textbox", "target_attributes": {"id": "search-input", "class": "benchmark-search-input"}}, {"type": "submit", "ref": "2", "url": "", "value": "", "description": "提交搜索表单", "target_name": "搜索关键词", "target_role": "textbox", "target_attributes": {"id": "search-input", "class": "benchmark-search-input"}}]')
    # - [0] click: 1 | 点击打开搜索框
    # - [1] type: 2 <- cliany-site | 输入搜索关键词
    # - [2] submit: 提交当前表单 | 提交搜索表单
    action_steps = substitute_parameters(action_steps, {'query': query})
    action_steps.extend(action_steps)
    results = execute_steps_via_atoms(action_steps, SOURCE_URL, DOMAIN)
    failed = next((r for r in results if not r.get("ok")), None)
    if _resolve_json_mode(json_mode):
        click.echo(json.dumps({
            "ok": failed is None,
            "data": {"results": results, "command": "search", "args": {'query': query}},
            "error": (failed or {}).get("error"),
            "meta": {"source": "adapter"},
        }, ensure_ascii=False))
    elif failed is None:
        click.echo("✓ search 完成")
    else:
        diagnose_if_enabled(ctx, failed or {})
        err_msg = (failed.get("error") or {}).get("message", "")
        click.echo(f"✗ {err_msg}", err=True)
        ctx.exit(1)



if __name__ == "__main__":
    cli()
