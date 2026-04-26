from __future__ import annotations

import asyncio

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.commands.browser._common import print_envelope
from cliany_site.envelope import ErrorCode, err, ok


@browser_group.command("eval")
@click.option("--expr", required=True, help="要执行的 JavaScript 表达式")
@click.option("--allow-eval", is_flag=True, default=False, help="启用 eval（默认禁用）")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def eval_cmd(
    ctx: click.Context,
    expr: str,
    allow_eval: bool,
    session: str | None,
    json_mode: bool | None,
) -> None:
    """在当前页面执行 JavaScript 表达式（需显式传 --allow-eval）"""
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))

    if not allow_eval:
        result = err(
            command="browser eval",
            code=ErrorCode.E_EVAL_DISABLED,
            message="eval 默认禁用，请传 --allow-eval 以启用",
            source="builtin",
        )
        print_envelope(result, effective_json)
        ctx.exit(1)
        return

    cdp = cdp_from_context(ctx)
    result = asyncio.run(_run_eval(cdp, expr))
    print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_eval(cdp, expr: str) -> dict:
    if not await cdp.check_available():
        return err(
            command="browser eval",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message="Chrome CDP 不可用，请启动 Chrome 或使用 --cdp-url 指定远程地址",
            source="builtin",
        )
    try:
        browser_session = await cdp.connect()
        try:
            eval_result = await browser_session.execute_action(
                {"action": "execute_script", "script": expr}
            )
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError) as exc:
        return err(
            command="browser eval",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"执行脚本失败: {exc}",
            source="builtin",
        )

    return ok(
        command="browser eval",
        data={"result": eval_result, "expr": expr},
        source="builtin",
    )
