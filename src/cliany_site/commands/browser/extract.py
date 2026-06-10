from __future__ import annotations

import asyncio
import json
import re

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.commands.browser._common import print_envelope
from cliany_site.envelope import Envelope, ErrorCode, err, ok
from cliany_site.extract import build_extract_js
from cliany_site.extract_quality import evaluate_extract_quality


@browser_group.command("extract")
@click.option("--selector", default=None, help="CSS 选择器（留空则提取全页）")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "markdown", "json"], case_sensitive=False),
    default="text",
    help="输出格式（text/markdown/json）",
)
@click.option(
    "--mode",
    type=click.Choice(["text", "list", "table", "attribute"], case_sensitive=False),
    default=None,
    help="结构化提取模式（text/list/table/attribute），生成 adapter 使用",
)
@click.option("--fields-json", default=None, help="结构化字段映射 JSON，仅用于 list/table/attribute")
@click.option("--strict-quality", is_flag=True, default=False, help="结构化提取质量为空时返回 E_EMPTY_RESULT")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def extract(
    ctx: click.Context,
    selector: str | None,
    fmt: str,
    mode: str | None,
    fields_json: str | None,
    strict_quality: bool,
    session: str | None,
    json_mode: bool | None,
) -> None:
    """提取当前页面内容（文本/Markdown/JSON）"""
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    cdp = cdp_from_context(ctx)
    fields = _parse_fields_json(fields_json)
    if isinstance(fields, dict) and fields.get("ok") is False:
        print_envelope(fields, effective_json)
        ctx.exit(1)
    result = asyncio.run(_run_extract(cdp, selector, fmt, mode, fields, strict_quality=strict_quality))
    print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


def _parse_fields_json(fields_json: str | None) -> dict | None | Envelope:
    if not fields_json:
        return None
    try:
        data = json.loads(fields_json)
    except json.JSONDecodeError as exc:
        return err(
            command="browser extract",
            code=ErrorCode.E_INVALID_PARAM,
            message=f"--fields-json 不是合法 JSON: {exc.msg}",
            source="builtin",
        )
    if not isinstance(data, dict):
        return err(
            command="browser extract",
            code=ErrorCode.E_INVALID_PARAM,
            message="--fields-json 必须是对象",
            source="builtin",
        )
    return data


async def _run_extract(
    cdp,
    selector: str | None,
    fmt: str,
    mode: str | None = None,
    fields: dict | None = None,
    strict_quality: bool = False,
) -> Envelope:
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
            if mode:
                content = await _do_structured_extract(browser_session, selector, mode, fields)
            else:
                content = await _do_extract(browser_session, selector, fmt)
        finally:
            await cdp.disconnect()
        if isinstance(content, dict) and not content.get("ok", True):
            return content
    except (OSError, RuntimeError) as exc:
        return err(
            command="browser extract",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"提取页面内容失败: {exc}",
            source="builtin",
        )

    payload = {
        "content": content,
        "format": fmt,
        "selector": selector,
        "mode": mode,
        "fields": fields or {},
    }
    if mode:
        quality = evaluate_extract_quality(mode, content, fields).to_dict()
        payload["quality"] = quality
        if strict_quality and quality.get("status") == "empty":
            return err(
                command="browser extract",
                code=ErrorCode.E_EMPTY_RESULT,
                message="结构化提取结果为空",
                details={"quality": quality, "selector": selector, "mode": mode},
                source="builtin",
            )

    return ok(command="browser extract", data=payload, source="builtin")


async def _do_structured_extract(
    browser_session,
    selector: str | None,
    mode: str,
    fields: dict | None,
) -> object | Envelope:
    if not selector:
        return err(
            command="browser extract",
            code=ErrorCode.E_INVALID_PARAM,
            message="结构化提取需要 --selector",
            source="builtin",
        )
    try:
        js_expr = build_extract_js(selector, mode, fields)
        page = await browser_session.get_current_page()
        if page is None:
            return err(
                command="browser extract",
                code=ErrorCode.E_PARSE_FAILED,
                message="无法获取当前页面",
                details={"selector": selector, "mode": mode},
            )
        return await page.evaluate(js_expr)
    except (OSError, RuntimeError, ValueError) as exc:
        return err(
            command="browser extract",
            code=ErrorCode.E_PARSE_FAILED,
            message=str(exc)[:200],
            details={"selector": selector, "mode": mode},
        )


async def _do_extract(browser_session, selector: str | None, fmt: str) -> str | Envelope:
    try:
        result = await browser_session.execute_action(
            {"action": "extract_content", "selector": selector, "format": fmt}
        )
        if isinstance(result, dict) and "content" in result:
            return str(result["content"])
        if isinstance(result, str):
            return result
    except Exception as exc:
        return err(
            command="browser extract",
            code=ErrorCode.E_PARSE_FAILED,
            message=str(exc)[:200],
            details={"selector": selector, "mode": fmt},
        )

    # 回退：获取页面源码并提取文本
    try:
        source = await browser_session.execute_action({"action": "get_page_source"})
        if isinstance(source, dict):
            source = source.get("html", "") or source.get("source", "")
        if isinstance(source, str):
            return _html_to_text(source, fmt)
    except Exception as exc:
        return err(
            command="browser extract",
            code=ErrorCode.E_PARSE_FAILED,
            message=str(exc)[:200],
            details={"selector": selector, "mode": fmt},
        )

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


extract_atom = extract
