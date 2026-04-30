from __future__ import annotations

import asyncio
import json

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.envelope import Envelope, ErrorCode, err, ok


def _print_envelope(result: Envelope, json_mode: bool) -> None:
    if json_mode:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        data = result.get("data", [])
        count = len(data) if isinstance(data, list) else 0
        click.echo(f"✓ 找到 {count} 个元素")
    else:
        error_info = result.get("error")
        error_code = error_info.get("code", "ERROR") if error_info else "ERROR"
        error_msg = error_info.get("message", "") if error_info else ""
        click.echo(
            f"✗ {error_code}: {error_msg}",
            err=True,
        )


@browser_group.command("find")
@click.option(
    "--by",
    "by_field",
    type=click.Choice(["text", "role", "attr"]),
    default="text",
    help="查找方式：text 文本模糊匹配 / role 角色精确匹配 / attr 属性值匹配",
)
@click.option("--value", required=True, help="查找值")
@click.option("--limit", default=5, show_default=True, help="最大返回数量")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def find(
    ctx: click.Context,
    by_field: str,
    value: str,
    limit: int,
    session: str | None,
    json_mode: bool | None,
) -> None:
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    cdp = cdp_from_context(ctx)
    result = asyncio.run(_run_find(cdp, by_field, value, limit))
    _print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_find(cdp, by_field: str, value: str, limit: int) -> Envelope:
    from cliany_site.browser.axtree import capture_axtree
    from cliany_site.commands.browser._common import fuzzy_find_by_text

    if not await cdp.check_available():
        return err(
            command="browser find",
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
            command="browser find",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"获取页面状态失败: {exc}",
            source="builtin",
        )

    selector_map = tree.get("selector_map", {})

    if by_field == "text":
        results = fuzzy_find_by_text(selector_map, value, limit)
    elif by_field == "role":
        results = [
            {
                "ref": str(ref_id),
                "role": element.get("role", "unknown"),
                "name": element.get("name", ""),
                "score": 1.0,
                "snippet": element.get("name", "")[:80],
            }
            for ref_id, element in selector_map.items()
            if element.get("role", "").lower() == value.lower()
        ][:limit]
    else:
        results = [
            {
                "ref": str(ref_id),
                "role": element.get("role", "unknown"),
                "name": element.get("name", ""),
                "score": 1.0,
                "snippet": element.get("name", "")[:80],
            }
            for ref_id, element in selector_map.items()
            if value in (element.get("attributes") or {}).values()
        ][:limit]

    return ok(
        command="browser find",
        data=results,
        source="builtin",
    )
