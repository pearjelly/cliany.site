from __future__ import annotations

import asyncio
import importlib

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.commands.browser._common import fuzzy_find_by_text, print_envelope, resolve_ref
from cliany_site.envelope import Envelope, ErrorCode, err, ok


@browser_group.command("submit")
@click.option("--ref", "ref", default=None, help="要聚焦的输入元素 ref ID")
@click.option("--text", "text", default=None, help="要聚焦的输入元素文本（模糊匹配）")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def submit_cmd(
    ctx: click.Context,
    ref: str | None,
    text: str | None,
    session: str | None,
    json_mode: bool | None,
) -> None:
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    cdp = cdp_from_context(ctx)
    result = asyncio.run(_run_submit(cdp, ref, text))
    print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_submit(cdp, ref: str | None, text: str | None) -> Envelope:
    from cliany_site.browser.axtree import capture_axtree

    if not await cdp.check_available():
        return err(
            command="browser submit",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message="Chrome CDP 不可用，请启动 Chrome 或使用 --cdp-url 指定远程地址",
            source="builtin",
        )

    found_ref: str | None = None
    element: dict | None = None
    try:
        browser_session = await cdp.connect()
        try:
            events_module = importlib.import_module("browser_use.browser.events")
            if ref is not None or text is not None:
                tree = await capture_axtree(browser_session)
                selector_map = tree.get("selector_map", {})
                if ref is not None:
                    element = resolve_ref(selector_map, ref)
                    found_ref = ref
                else:
                    results = fuzzy_find_by_text(selector_map, text or "", limit=1)
                    if results:
                        found_ref = results[0]["ref"]
                        element = resolve_ref(selector_map, found_ref)

                if element is None or found_ref is None:
                    return err(
                        command="browser submit",
                        code=ErrorCode.E_SELECTOR_NOT_FOUND,
                        message=f"未找到元素: ref={ref!r} text={text!r}",
                        hint="尝试 'cliany-site browser find' 或 '--heal'",
                        source="builtin",
                    )

                node = await browser_session.get_element_by_index(int(found_ref))
                if node is None:
                    return err(
                        command="browser submit",
                        code=ErrorCode.E_SELECTOR_NOT_FOUND,
                        message=f"未找到可提交元素: ref={found_ref!r}",
                        hint="页面结构可能已变化，建议重新 explore",
                        source="builtin",
                    )

                focus_event = browser_session.event_bus.dispatch(events_module.ClickElementEvent(node=node))
                await focus_event
                await focus_event.event_result(raise_if_any=True, raise_if_none=False)

            event = browser_session.event_bus.dispatch(events_module.SendKeysEvent(keys="Enter"))
            await event
            await event.event_result(raise_if_any=True, raise_if_none=False)
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError, ValueError) as exc:
        return err(
            command="browser submit",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"操作失败: {exc}",
            source="builtin",
        )

    return ok(
        command="browser submit",
        data={
            "ref": str(found_ref or ""),
            "name": element.get("name", "") if element else "",
            "role": element.get("role", "unknown") if element else "unknown",
            "submitted": True,
            "status": "submitted",
        },
        source="builtin",
    )
