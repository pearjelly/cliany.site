from __future__ import annotations

import asyncio
import re

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.commands.browser._common import print_envelope
from cliany_site.envelope import ErrorCode, err, ok


@browser_group.command("extract")
@click.option("--selector", default=None, help="CSS 选择器（留空则提取全页）")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "markdown", "json"], case_sensitive=False),
    default="text",
    help="输出格式（text/markdown/json）",
)
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def extract(
    ctx: click.Context,
    selector: str | None,
    fmt: str,
    session: str | None,
    json_mode: bool | None,
) -> None:
    """提取当前页面内容（文本/Markdown/JSON）"""
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    cdp = cdp_from_context(ctx)
    result = asyncio.run(_run_extract(cdp, selector, fmt))
    print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_extract(cdp, selector: str | None, fmt: str) -> dict:
    if not await cdp.check_available():
        return err(
            command="browser extract",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message="Chrome CDP 不可用，请启动 Chrome 或使用 --cdp-url 指定远程地址",
            source="builtin",
        )
    try:
        browser_session = await cdp.connect()
        try:
            content = await _do_extract(browser_session, selector, fmt)
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError) as exc:
        return err(
            command="browser extract",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"提取页面内容失败: {exc}",
            source="builtin",
        )

    return ok(
        command="browser extract",
        data={"content": content, "format": fmt, "selector": selector},
        source="builtin",
    )


async def _do_extract(browser_session, selector: str | None, fmt: str) -> str:
    try:
        result = await browser_session.execute_action(
            {"action": "extract_content", "selector": selector, "format": fmt}
        )
        if isinstance(result, dict) and "content" in result:
            return str(result["content"])
        if isinstance(result, str):
            return result
    except Exception:
        pass

    # 回退：获取页面源码并提取文本
    try:
        source = await browser_session.execute_action({"action": "get_page_source"})
        if isinstance(source, dict):
            source = source.get("html", "") or source.get("source", "")
        if isinstance(source, str):
            return _html_to_text(source, fmt)
    except Exception:
        pass

    return ""


def _html_to_text(html: str, fmt: str) -> str:
    cleaned = re.sub(
        r"<(script|style)[^>]*>.*?</\1>",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # 移除所有 HTML 标签
    text = re.sub(r"<[^>]+>", " ", cleaned)
    # 合并多余空白
    return re.sub(r"\s+", " ", text).strip()
