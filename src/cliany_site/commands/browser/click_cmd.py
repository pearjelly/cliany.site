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
        data = result.get("data", {})
        click.echo(f"✓ 已点击  ref={data.get('ref', '')}  name={data.get('name', '')}")
    else:
        error_info = result.get("error")
        error_code = error_info.get("code", "ERROR") if error_info else "ERROR"
        error_msg = error_info.get("message", "") if error_info else ""
        click.echo(
            f"✗ {error_code}: {error_msg}",
            err=True,
        )


@browser_group.command("click")
@click.option("--ref", "ref", default=None, help="元素 ref ID")
@click.option("--text", "text", default=None, help="元素文本（模糊匹配）")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def click_cmd(
    ctx: click.Context,
    ref: str | None,
    text: str | None,
    session: str | None,
    json_mode: bool | None,
) -> None:
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    if ref is None and text is None:
        click.echo("✗ 必须提供 --ref 或 --text", err=True)
        ctx.exit(1)
        return
    cdp = cdp_from_context(ctx)
    result = asyncio.run(_run_click(cdp, ref, text))
    _print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_click(cdp, ref: str | None, text: str | None) -> Envelope:
    from cliany_site.browser.axtree import capture_axtree
    from cliany_site.commands.browser._common import fuzzy_find_by_text, resolve_ref

    if not await cdp.check_available():
        return err(
            command="browser click",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message="Chrome CDP 不可用，请启动 Chrome 或使用 --cdp-url 指定远程地址",
            source="builtin",
        )
    found_ref: str | None = None
    element: dict | None = None
    try:
        browser_session = await cdp.connect()
        try:
            tree = await capture_axtree(browser_session)
            selector_map = tree.get("selector_map", {})

            if ref is not None:
                element = resolve_ref(selector_map, ref)
                found_ref = ref
            elif text is not None:
                results = fuzzy_find_by_text(selector_map, text, limit=1)
                if results:
                    found_ref = results[0]["ref"]
                    element = resolve_ref(selector_map, found_ref)

            if element is None:
                return err(
                    command="browser click",
                    code=ErrorCode.E_SELECTOR_NOT_FOUND,
                    message=f"未找到元素: ref={ref!r} text={text!r}",
                    hint="尝试 'cliany-site browser find' 或 '--heal'",
                    source="builtin",
                )

            assert found_ref is not None
            await browser_session.execute_action(
                {"action": "click_element", "index": int(found_ref)}
            )
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError) as exc:
        return err(
            command="browser click",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"操作失败: {exc}",
            source="builtin",
        )

    return ok(
        command="browser click",
        data={
            "ref": str(found_ref),
            "name": element.get("name", ""),
            "role": element.get("role", "unknown"),
            "status": "clicked",
        },
        source="builtin",
    )
