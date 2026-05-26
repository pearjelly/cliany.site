import asyncio
from typing import Any
from urllib.parse import urlparse

import click

from cliany_site.config import get_config
from cliany_site.errors import CDP_UNAVAILABLE
from cliany_site.response import error_response, print_response, success_response


@click.command("login")
@click.argument("url")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def login(ctx: click.Context, url: str, json_mode: bool | None):
    """捕获浏览器 Session 并持久化到本地文件

    URL: 目标网站地址（如 https://github.com）

    使用前请先在 Chrome 中手动登录目标网站。
    """
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    from cliany_site.browser.cdp import cdp_from_context

    cdp_conn = cdp_from_context(ctx)
    result = asyncio.run(_capture_session(url, cdp_conn))
    print_response(result, json_mode=effective_json_mode)


async def _capture_session(url: str, cdp_conn: Any = None) -> Any:
    from cliany_site.browser.cdp import CDPConnection
    from cliany_site.session import save_session

    # Browser provider capability gate：非 Chrome provider 必须支持 login 能力
    _browser_provider = get_config().browser_provider
    if _browser_provider and _browser_provider.lower() != "chrome":
        from cliany_site.envelope import ErrorCode, err
        from cliany_site.providers.capabilities import feature_gate
        from cliany_site.providers.factory import get_provider
        try:
            _provider_inst = get_provider(_browser_provider)
            _snap = _provider_inst.get_capability_snapshot()
        except Exception as _exc:
            return err(
                "login",
                ErrorCode.E_PROVIDER_NOT_FOUND,
                f"Browser provider '{_browser_provider}' 初始化失败: {_exc}",
                hint="请检查 CLIANY_BROWSER_PROVIDER 配置",
            )
        _gate = feature_gate("login", _snap)
        if not _gate.allowed:
            return err(
                "login",
                ErrorCode.E_MISSING_CAPABILITY,
                "Obscura provider 暂不支持 login（需要 navigation/cookies）。请改用 Chrome（unset CLIANY_BROWSER_PROVIDER）或参阅文档。",
                hint="Obscura 当前缺少 navigation/cookies 能力，无法执行 login。",
                details={
                    "suggested_action": "unset CLIANY_BROWSER_PROVIDER",
                    "doc_url": "docs/walkthroughs/obscura-experimental-guide.md",
                    "missing_capability": "supports_navigation",
                },
            )

    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    if not domain:
        return error_response("INVALID_URL", f"无法从 URL 提取 domain: {url}")

    cdp = cdp_conn if cdp_conn is not None else CDPConnection()
    available = await cdp.check_available()
    if not available:
        return error_response(
            CDP_UNAVAILABLE,
            "Chrome 未通过 CDP 运行",
            fix="请使用 --remote-debugging-port=9222 启动 Chrome，或使用 --cdp-url 指定远程地址",
        )

    try:
        browser_session = await cdp.connect()
    except (OSError, RuntimeError) as e:
        return error_response(CDP_UNAVAILABLE, f"连接 Chrome 失败: {e}")

    try:
        try:
            page = await browser_session.get_current_page()
            if page is not None:
                await page.goto(url)
        except (OSError, RuntimeError) as nav_err:
            click.echo(
                f"⚠ 页面导航失败（{nav_err}），请手动在 Chrome 中打开 {url}",
                err=True,
            )

        click.echo("提示：请在 Chrome 中完成登录，然后按 Enter 继续...", err=True)
        click.pause("")

        path, cookies_count = await save_session(domain, browser_session)

        if cookies_count == 0:
            return error_response(
                "NO_COOKIES",
                f"未从 {domain} 获取到任何 Cookie，登录可能未成功",
                fix="请确认已在 Chrome 中完成登录后重试",
            )

        return success_response(
            {
                "domain": domain,
                "session_file": path,
                "cookies_count": cookies_count,
                "message": f"Session 已保存到 {path}（{cookies_count} 个 Cookie）",
            }
        )
    except (OSError, RuntimeError, ValueError) as e:
        return error_response("EXECUTION_FAILED", f"Session 捕获失败: {e}")
    finally:
        await cdp.disconnect()
