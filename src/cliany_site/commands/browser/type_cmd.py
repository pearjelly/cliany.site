from __future__ import annotations

import asyncio
import importlib
import json

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.envelope import Envelope, ErrorCode, err, ok


def _print_envelope(result: Envelope, json_mode: bool) -> None:
    if json_mode:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        raw_data = result.get("data")
        data = raw_data if isinstance(raw_data, dict) else {}
        click.echo(f"✓ 已输入  ref={data.get('ref', '')}  value={data.get('value', '')}")
    else:
        error_info = result.get("error")
        error_code = error_info.get("code", "ERROR") if error_info else "ERROR"
        error_msg = error_info.get("message", "") if error_info else ""
        click.echo(
            f"✗ {error_code}: {error_msg}",
            err=True,
        )


@browser_group.command("type")
@click.option("--ref", "ref", default=None, help="元素 ref ID")
@click.option("--text", "text", default=None, help="元素文本（模糊匹配）")
@click.option("--value", required=True, help="要输入的内容")
@click.option("--submit", is_flag=True, default=False, help="输入后发送 Enter")
@click.option("--clear", is_flag=True, default=False, help="输入前清空字段")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def type_cmd(
    ctx: click.Context,
    ref: str | None,
    text: str | None,
    value: str,
    submit: bool,
    clear: bool,
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
    result = asyncio.run(_run_type(cdp, ref, text, value, submit, clear))
    _print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_type(
    cdp,
    ref: str | None,
    text: str | None,
    value: str,
    submit: bool,
    clear: bool,
) -> Envelope:
    from cliany_site.browser.axtree import capture_axtree
    from cliany_site.commands.browser._common import fuzzy_find_by_text, resolve_ref

    if not await cdp.check_available():
        return err(
            command="browser type",
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
                    command="browser type",
                    code=ErrorCode.E_SELECTOR_NOT_FOUND,
                    message=f"未找到元素: ref={ref!r} text={text!r}",
                    hint="尝试 'cliany-site browser find' 或 '--heal'",
                    source="builtin",
                )

            assert found_ref is not None
            node = await browser_session.get_element_by_index(int(found_ref))
            if node is None:
                return err(
                    command="browser type",
                    code=ErrorCode.E_SELECTOR_NOT_FOUND,
                    message=f"未找到可输入元素: ref={found_ref!r}",
                    hint="页面结构可能已变化，请重新运行 browser find",
                    source="builtin",
                )
            events_module = importlib.import_module("browser_use.browser.events")
            # browser-use treats empty TypeTextEvent text as a request to clear.
            action = (
                events_module.TypeTextEvent(node=node, text=value, clear=clear)
                if value or clear else events_module.ClickElementEvent(node=node)
            )
            event = browser_session.event_bus.dispatch(action)
            await event
            await event.event_result(raise_if_any=True, raise_if_none=False)
            if submit:
                submit_event = browser_session.event_bus.dispatch(
                    events_module.SendKeysEvent(keys="Enter")
                )
                await submit_event
                await submit_event.event_result(raise_if_any=True, raise_if_none=False)
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError, ValueError) as exc:
        return err(
            command="browser type",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"操作失败: {exc}",
            source="builtin",
        )

    return ok(
        command="browser type",
        data={
            "ref": str(found_ref),
            "name": element.get("name", ""),
            "role": element.get("role", "unknown"),
            "value": value,
            "submitted": submit,
            "cleared": clear,
            "status": "typed",
        },
        source="builtin",
    )
