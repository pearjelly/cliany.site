import asyncio
import json

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.envelope import ErrorCode, err, ok


def _print_envelope(result: dict, json_mode: bool) -> None:
    if json_mode:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        data = result.get("data", {})
        click.echo(f"✓ 页面状态  url={data.get('url', '')}  title={data.get('title', '')}")
    else:
        error = result.get("error", {})
        click.echo(
            f"✗ {error.get('code', 'ERROR')}: {error.get('message', '')}",
            err=True,
        )


@browser_group.command("state")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def state(ctx: click.Context, session: str | None, json_mode: bool | None) -> None:
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    cdp = cdp_from_context(ctx)
    result = asyncio.run(_run_state(cdp))
    _print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_state(cdp) -> dict:
    from cliany_site.browser.axtree import capture_axtree, extract_interactive_elements

    if not await cdp.check_available():
        return err(
            command="browser state",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message="Chrome CDP 不可用，请启动 Chrome 或使用 --cdp-url 指定远程地址",
            source="builtin",
        )
    try:
        browser_session = await cdp.connect()
        try:
            tree = await capture_axtree(browser_session)
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError) as exc:
        return err(
            command="browser state",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"获取页面状态失败: {exc}",
            source="builtin",
        )

    elements = extract_interactive_elements(tree)
    truncated = len(tree.get("element_tree", "")) > 20_000
    return ok(
        command="browser state",
        data={
            "url": tree.get("url", ""),
            "title": tree.get("title", ""),
            "elements": elements,
            "truncated": truncated,
        },
        source="builtin",
    )
