import asyncio
from urllib.parse import urlparse

import click

from cliany_site.response import success_response, error_response, print_response
from cliany_site.errors import CDP_UNAVAILABLE


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
    effective_json_mode = (
        json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))
    )

    result = asyncio.run(_capture_session(url))
    print_response(result, json_mode=effective_json_mode)


async def _capture_session(url: str) -> dict:
    from cliany_site.browser.cdp import CDPConnection
    from cliany_site.session import save_session

    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    if not domain:
        return error_response("INVALID_URL", f"无法从 URL 提取 domain: {url}")

    cdp = CDPConnection()
    available = await cdp.check_available()
    if not available:
        return error_response(
            CDP_UNAVAILABLE,
            "Chrome 未通过 CDP 运行",
            fix="请使用 --remote-debugging-port=9222 启动 Chrome",
        )

    try:
        browser_session = await cdp.connect()
    except Exception as e:
        return error_response(CDP_UNAVAILABLE, f"连接 Chrome 失败: {e}")

    try:
        try:
            page = await browser_session.get_current_page()
            if page is not None:
                await page.goto(url)
        except Exception as nav_err:
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
    except Exception as e:
        return error_response("EXECUTION_FAILED", f"Session 捕获失败: {e}")
    finally:
        await cdp.disconnect()
