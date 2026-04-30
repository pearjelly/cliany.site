import asyncio
import json
import time

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.envelope import Envelope, ErrorCode, err, ok


def _print_envelope(result: Envelope, json_mode: bool) -> None:
    if json_mode:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        data = result.get("data", {})
        click.echo(f"✓ 等待完成  elapsed={data.get('elapsed_ms', 0)}ms")
    else:
        error_info = result.get("error")
        error_code = error_info.get("code", "ERROR") if error_info else "ERROR"
        error_msg = error_info.get("message", "") if error_info else ""
        click.echo(
            f"✗ {error_code}: {error_msg}",
            err=True,
        )


@browser_group.command("wait")
@click.option("--selector", default=None, help="等待该 CSS selector 可见")
@click.option("--state", "wait_state", default="networkidle", help="等待加载状态（无 selector 时生效）")
@click.option("--timeout", default=30, type=int, show_default=True, help="超时秒数")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def wait(
    ctx: click.Context,
    selector: str | None,
    wait_state: str,
    timeout: int,
    session: str | None,
    json_mode: bool | None,
) -> None:
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    cdp = cdp_from_context(ctx)
    result = asyncio.run(_run_wait(cdp, selector, wait_state, timeout))
    _print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_wait(cdp, selector: str | None, wait_state: str, timeout: int) -> Envelope:
    if not await cdp.check_available():
        return err(
            command="browser wait",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message="Chrome CDP 不可用，请启动 Chrome 或使用 --cdp-url 指定远程地址",
            source="builtin",
        )
    start = time.monotonic()
    try:
        browser_session = await cdp.connect()
        try:
            page = await browser_session.get_current_page()
            if selector:
                await page.wait_for_selector(selector, timeout=timeout * 1000)
            else:
                await page.wait_for_load_state(wait_state, timeout=timeout * 1000)
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError, TimeoutError) as exc:
        return err(
            command="browser wait",
            code=ErrorCode.E_TIMEOUT,
            message=f"等待超时或失败: {exc}",
            source="builtin",
        )
    elapsed_ms = int((time.monotonic() - start) * 1000)
    return ok(
        command="browser wait",
        data={"waited": True, "selector": selector, "elapsed_ms": elapsed_ms},
        source="builtin",
    )
