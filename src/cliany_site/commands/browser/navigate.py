import asyncio
import json

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.config import get_config
from cliany_site.envelope import Envelope, ErrorCode, err, ok


def _print_envelope(result: Envelope, json_mode: bool) -> None:
    if json_mode:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        data = result.get("data", {})
        click.echo(f"✓ 已导航至 {data.get('url', '')}")
    else:
        error_info = result.get("error")
        error_code = error_info.get("code", "ERROR") if error_info else "ERROR"
        error_msg = error_info.get("message", "") if error_info else ""
        click.echo(
            f"✗ {error_code}: {error_msg}",
            err=True,
        )


@browser_group.command("navigate")
@click.argument("url")
@click.option(
    "--wait",
    "wait_state",
    default="load",
    type=click.Choice(["load", "networkidle", "domcontentloaded"]),
    help="等待页面加载状态",
)
@click.option("--timeout", default=30, type=int, show_default=True, help="超时秒数")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def navigate(
    ctx: click.Context,
    url: str,
    wait_state: str,
    timeout: int,
    session: str | None,
    json_mode: bool | None,
) -> None:
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    cdp = cdp_from_context(ctx)
    result = asyncio.run(_run_navigate(cdp, url, wait_state, timeout))
    _print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_navigate(cdp, url: str, wait_state: str, timeout: int) -> Envelope:
    _browser_provider = get_config().browser_provider
    if _browser_provider and _browser_provider.lower() != "chrome":
        from cliany_site.providers.capabilities import feature_gate
        from cliany_site.providers.factory import get_provider
        try:
            _provider_inst = get_provider(_browser_provider)
            _snap = _provider_inst.get_capability_snapshot()
        except Exception as _exc:
            return err(
                command="browser navigate",
                code=ErrorCode.E_PROVIDER_NOT_FOUND,
                message=f"Browser provider '{_browser_provider}' 初始化失败: {_exc}",
                hint="请检查 CLIANY_BROWSER_PROVIDER 配置",
            )
        _gate = feature_gate("browser.navigate", _snap)
        if not _gate.allowed:
            return err(
                command="browser navigate",
                code=ErrorCode.E_MISSING_CAPABILITY,
                message=f"当前 provider '{_browser_provider}' 不支持 navigate 命令（缺少必要能力）",
                hint=_gate.reason,
            )

    if not await cdp.check_available():
        return err(
            command="browser navigate",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message="Chrome CDP 不可用，请启动 Chrome 或使用 --cdp-url 指定远程地址",
            source="builtin",
        )
    try:
        browser_session = await cdp.connect()
        try:
            await browser_session.navigate_to(url)
            if wait_state in ("networkidle", "domcontentloaded"):
                page = await browser_session.get_current_page()
                await page.wait_for_load_state(wait_state, timeout=timeout * 1000)
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError) as exc:
        return err(
            command="browser navigate",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"导航失败: {exc}",
            source="builtin",
        )
    return ok(
        command="browser navigate",
        data={"url": url, "status": "navigated"},
        source="builtin",
    )
