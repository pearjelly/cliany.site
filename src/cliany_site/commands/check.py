import asyncio
import json
import logging

import click

from cliany_site.config import get_config
from cliany_site.response import error_response, print_response, success_response

logger = logging.getLogger(__name__)


@click.command("check")
@click.argument("domain")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.option("--fix", "auto_fix", is_flag=True, default=False, help="自动修复 selector 差异")
@click.pass_context
def check_cmd(ctx: click.Context, domain: str, json_mode: bool | None, auto_fix: bool):
    """检查适配器健康状态，对比 AXTree 快照与当前页面"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    from cliany_site.browser.cdp import cdp_from_context

    cdp_conn = cdp_from_context(ctx)
    result = asyncio.run(_run_check(domain, auto_fix, cdp_conn=cdp_conn))
    print_response(result, json_mode=effective_json_mode, exit_on_error=True)


async def _run_check(domain: str, auto_fix: bool, cdp_conn: object = None) -> dict:
    from cliany_site.snapshot import list_snapshots, load_snapshot

    cfg = get_config()
    safe_domain = domain.replace("/", "_").replace(":", "_").strip() or "unknown-domain"
    adapter_dir = cfg.adapters_dir / safe_domain

    if not adapter_dir.exists():
        return error_response(
            code="ADAPTER_NOT_FOUND",
            message=f"未找到适配器: {domain}",
            fix=f"请先运行 cliany-site explore <url> <workflow> 生成 {domain} 的适配器",
        )

    metadata_path = adapter_dir / "metadata.json"
    if not metadata_path.exists():
        return error_response(
            code="METADATA_MISSING",
            message=f"适配器元数据缺失: {domain}",
            fix="请重新 explore 生成适配器",
        )

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return error_response(
            code="METADATA_INVALID",
            message=f"元数据读取失败: {exc}",
            fix="请重新 explore 生成适配器",
        )

    commands = metadata.get("commands", [])
    if not isinstance(commands, list):
        commands = []

    snapshots = list_snapshots(domain)
    if not snapshots:
        return success_response(
            {
                "domain": domain,
                "status": "no_snapshots",
                "message": "未找到 AXTree 快照，无法执行健康检查",
                "commands": [_cmd_name(c) for c in commands],
                "suggestion": "请重新 explore 以生成快照",
            }
        )

    command_results: list[dict] = []
    overall_healthy = True

    for cmd in commands:
        cmd_name = _cmd_name(cmd)
        snapshot_data = load_snapshot(domain, cmd_name)
        if not snapshot_data:
            command_results.append(
                {
                    "command": cmd_name,
                    "status": "no_snapshot",
                    "healthy": True,
                }
            )
            continue

        snapshot_elements = snapshot_data.get("elements", [])
        if not snapshot_elements:
            command_results.append(
                {
                    "command": cmd_name,
                    "status": "empty_snapshot",
                    "healthy": True,
                }
            )
            continue

        try:
            current_elements = await _get_current_elements(snapshot_data.get("page_url", ""), cdp_conn=cdp_conn)
        except (OSError, RuntimeError, TimeoutError) as exc:
            command_results.append(
                {
                    "command": cmd_name,
                    "status": "check_failed",
                    "healthy": False,
                    "error": str(exc),
                }
            )
            overall_healthy = False
            continue

        from cliany_site.healthcheck import compare_elements

        check_result = compare_elements(snapshot_elements, current_elements, domain, cmd_name)

        cmd_report: dict = {
            "command": cmd_name,
            "status": "healthy" if check_result.healthy else "degraded",
            "healthy": check_result.healthy,
            "snapshot_count": check_result.snapshot_count,
            "current_count": check_result.current_count,
            "matched": check_result.matched,
            "missing": check_result.missing,
            "changed": check_result.changed,
            "diff_ratio": round(check_result.diff_ratio, 4),
        }

        if not check_result.healthy:
            overall_healthy = False

        if check_result.fixes and auto_fix:
            cmd_report["fixes_applied"] = len(check_result.fixes)
            cmd_report["fixes"] = check_result.fixes
            _apply_fixes_to_metadata(metadata, cmd_name, check_result.fixes)
        elif check_result.fixes:
            cmd_report["fixes_available"] = len(check_result.fixes)
            cmd_report["suggestion"] = "使用 --fix 自动修复，或重新 explore"

        command_results.append(cmd_report)

    if auto_fix and any(r.get("fixes_applied", 0) > 0 for r in command_results):
        try:
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("保存修复后的元数据失败: %s", exc)

    return success_response(
        {
            "domain": domain,
            "healthy": overall_healthy,
            "commands": command_results,
        }
    )


def _cmd_name(cmd: dict | str) -> str:
    if isinstance(cmd, dict):
        return str(cmd.get("name", "default"))
    return str(cmd)


async def _get_current_elements(page_url: str, cdp_conn: object = None) -> list[dict]:
    from cliany_site.browser.axtree import capture_axtree, extract_interactive_elements
    from cliany_site.browser.cdp import CDPConnection

    cdp = cdp_conn if isinstance(cdp_conn, CDPConnection) else CDPConnection()
    if not await cdp.check_available():
        raise RuntimeError("Chrome CDP 不可用，请启动 Chrome 或使用 --cdp-url 指定远程地址")

    browser_session = await cdp.connect()
    try:
        if page_url:
            try:
                current_url = await browser_session.get_current_page_url()
                if current_url != page_url:
                    await browser_session.navigate_to(page_url, new_tab=False)
                    import asyncio as _asyncio

                    await _asyncio.sleep(1.5)
            except (RuntimeError, OSError, AttributeError):
                pass

        tree = await capture_axtree(browser_session)
        return extract_interactive_elements(tree)
    finally:
        await cdp.disconnect()


def _apply_fixes_to_metadata(metadata: dict, cmd_name: str, fixes: list[dict]) -> None:
    from cliany_site.healthcheck import apply_selector_fixes

    commands = metadata.get("commands", [])
    for cmd in commands:
        if not isinstance(cmd, dict):
            continue
        if cmd.get("name") != cmd_name:
            continue
        actions = cmd.get("actions", [])
        if isinstance(actions, list):
            apply_selector_fixes(actions, fixes)
