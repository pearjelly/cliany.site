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
        data = result.get("data")
        url_text = data.get("url", "") if isinstance(data, dict) else ""
        click.echo(f"✓ 已导航至 {url_text}")
    else:
        error_info = result.get("error")
        if isinstance(error_info, dict):
            error_code = error_info.get("code", "ERROR")
            error_msg = error_info.get("message", "")
        else:
            error_code = "ERROR"
            error_msg = ""
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
    if session:
        result = asyncio.run(_run_navigate(cdp, url, wait_state, timeout, session))
    else:
        result = asyncio.run(_run_navigate(cdp, url, wait_state, timeout))
    _print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_navigate(cdp, url: str, wait_state: str, timeout: int, session: str | None = None) -> Envelope:
    _browser_provider = get_config().browser_provider
    can_capture_axtree = True
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
        can_capture_axtree = _snap.supports_axtree
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
            if session:
                from cliany_site.session import load_session_data

                saved = load_session_data(session)
                if not saved:
                    return err(
                        "browser navigate",
                        ErrorCode.E_SESSION_EXPIRED,
                        "Session 不存在或无法读取，请重新登录",
                    )
                if saved.get("expires_hint") == "expired":
                    return err("browser navigate", ErrorCode.E_SESSION_EXPIRED, "Session 已失效，请重新登录")
                await browser_session._cdp_set_cookies(saved.get("cookies", []))
            await browser_session.navigate_to(url)
            if wait_state in ("networkidle", "domcontentloaded"):
                page = await browser_session.get_current_page()
                await page.wait_for_load_state(wait_state, timeout=timeout * 1000)
            if can_capture_axtree:
                from cliany_site.browser.axtree import capture_axtree
                from cliany_site.commands.browser._common import site_challenge_error

                challenge = site_challenge_error("browser navigate", await capture_axtree(browser_session))
                if challenge is not None:
                    return challenge
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError, TimeoutError) as exc:
        if isinstance(exc, TimeoutError) or (
            isinstance(exc, RuntimeError) and str(exc).startswith("Page.navigate() timed out after ")
        ):
            return err(
                command="browser navigate",
                code=ErrorCode.E_PAGE_NOT_READY,
                message="页面就绪超时",
                hint="请确认目标站点在当前网络可访问后重试；若站点返回验证页，不要绕过其限制。",
                details={"error": str(exc)},
                source="builtin",
            )
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


navigate_atom = navigate
