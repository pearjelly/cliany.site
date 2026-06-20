import asyncio
import json
import time
from pathlib import Path

import click

from cliany_site.browser.cdp import cdp_from_context
from cliany_site.commands.browser import browser_group
from cliany_site.config import get_config
from cliany_site.envelope import Envelope, ErrorCode, err, ok


def _print_envelope(result: Envelope, json_mode: bool) -> None:
    if json_mode:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        raw_data = result.get("data")
        data = raw_data if isinstance(raw_data, dict) else {}
        click.echo(f"✓ 截图已保存  {data.get('path', '')}  ({data.get('size_bytes', 0)} bytes)")
    else:
        error_info = result.get("error")
        error_code = error_info.get("code", "ERROR") if error_info else "ERROR"
        error_msg = error_info.get("message", "") if error_info else ""
        click.echo(
            f"✗ {error_code}: {error_msg}",
            err=True,
        )


@browser_group.command("screenshot")
@click.option("--out", default=None, type=click.Path(), help="输出文件路径（默认自动生成）")
@click.option("--full-page", is_flag=True, default=False, help="截取完整页面")
@click.option("--session", default=None, help="会话名称")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def screenshot(
    ctx: click.Context,
    out: str | None,
    full_page: bool,
    session: str | None,
    json_mode: bool | None,
) -> None:
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    cdp = cdp_from_context(ctx)
    result = asyncio.run(_run_screenshot(cdp, out, full_page))
    _print_envelope(result, effective_json)
    if not result.get("ok"):
        ctx.exit(1)


async def _run_screenshot(cdp, out: str | None, full_page: bool) -> Envelope:
    from cliany_site.browser.screenshot import capture_screenshot

    _browser_provider = get_config().browser_provider
    if _browser_provider and _browser_provider.lower() != "chrome":
        from cliany_site.providers.capabilities import feature_gate
        from cliany_site.providers.factory import get_provider
        try:
            _provider_inst = get_provider(_browser_provider)
            _snap = _provider_inst.get_capability_snapshot()
        except Exception as _exc:
            return err(
                command="browser screenshot",
                code=ErrorCode.E_PROVIDER_NOT_FOUND,
                message=f"Browser provider '{_browser_provider}' 初始化失败: {_exc}",
                hint="请检查 CLIANY_BROWSER_PROVIDER 配置",
            )
        _gate = feature_gate("browser.screenshot", _snap)
        if not _gate.allowed:
            return err(
                command="browser screenshot",
                code=ErrorCode.E_MISSING_CAPABILITY,
                message=f"当前 provider '{_browser_provider}' 不支持 screenshot 命令（缺少必要能力）",
                hint=_gate.reason,
            )

    if not await cdp.check_available():
        return err(
            command="browser screenshot",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message="Chrome CDP 不可用，请启动 Chrome 或使用 --cdp-url 指定远程地址",
            source="builtin",
        )

    if out is None:
        snapshots_dir = Path.home() / ".cliany-site" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        out_path = snapshots_dir / f"{int(time.time())}.png"
    else:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        browser_session = await cdp.connect()
        try:
            data = await capture_screenshot(browser_session, format="png", full_page=full_page)
        finally:
            await cdp.disconnect()
    except (OSError, RuntimeError) as exc:
        return err(
            command="browser screenshot",
            code=ErrorCode.E_CDP_UNAVAILABLE,
            message=f"截图失败: {exc}",
            source="builtin",
        )

    out_path.write_bytes(data)
    return ok(
        command="browser screenshot",
        data={"path": str(out_path), "size_bytes": len(data)},
        source="builtin",
    )
