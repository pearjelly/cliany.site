# src/cliany_site/commands/doctor.py
import asyncio
import os
import time
from pathlib import Path
from typing import Any

import click

from cliany_site.agent_md import _SENTINEL_RE
from cliany_site.config import get_config
from cliany_site.envelope import ErrorCode, err, ok
from cliany_site.metadata import LegacyMetadataError, load_metadata
from cliany_site.registry import Registry
from cliany_site.response import print_response

try:
    from cliany_site.explorer.engine import _load_dotenv

    _load_dotenv()
except ImportError:
    pass


@click.command("doctor")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.pass_context
def doctor(ctx: click.Context, json_mode: bool | None):
    """检查运行环境（CDP / LLM API key / 目录）"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    from cliany_site.browser.cdp import cdp_from_context

    cdp_conn = cdp_from_context(ctx)
    result = asyncio.run(_run_checks(cdp_conn))
    print_response(result, json_mode=effective_json_mode, exit_on_error=True)


async def _run_checks(cdp_conn: Any = None) -> dict:
    from cliany_site.browser.cdp import CDPConnection
    from cliany_site.explorer.engine import _load_dotenv, _normalize_openai_base_url

    _load_dotenv()

    checks: list[dict[str, Any]] = []

    try:
        cdp = cdp_conn if cdp_conn is not None else CDPConnection()
        cdp_available = await cdp.check_available()
        checks.append({
            "name": "cdp",
            "status": "ok" if cdp_available else "fail",
            "duration_ms": 0,
            "details": None
        })
    except (OSError, RuntimeError, TimeoutError):
        checks.append({
            "name": "cdp",
            "status": "fail",
            "duration_ms": 0,
            "details": None
        })

    has_llm = bool(
        os.environ.get("CLIANY_ANTHROPIC_API_KEY")
        or os.environ.get("CLIANY_OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    checks.append({
        "name": "llm",
        "status": "ok" if has_llm else "fail",
        "duration_ms": 0,
        "details": None
    })

    provider = os.environ.get("CLIANY_LLM_PROVIDER", "anthropic").lower()
    checks.append({
        "name": "llm_provider",
        "status": "ok" if provider in {"anthropic", "openai"} else "fail",
        "duration_ms": 0,
        "details": {"provider": provider}
    })

    if provider == "openai":
        base_url = os.environ.get("CLIANY_OPENAI_BASE_URL")
        try:
            normalized_base_url = _normalize_openai_base_url(base_url)
            checks.append({
                "name": "openai_base_url",
                "status": "ok" if (normalized_base_url or not base_url) else "fail",
                "duration_ms": 0,
                "details": {"base_url": base_url}
            })
        except (ValueError, TypeError):
            checks.append({
                "name": "openai_base_url",
                "status": "fail",
                "duration_ms": 0,
                "details": {"base_url": base_url}
            })

    cfg = get_config()
    adapters_dir = cfg.adapters_dir
    checks.append({
        "name": "dirs",
        "status": "ok" if adapters_dir.exists() else "fail",
        "duration_ms": 0,
        "details": {"adapters_dir": str(adapters_dir), "sessions_dir": str(cfg.sessions_dir)}
    })

    t0 = time.monotonic()
    registry = Registry()
    registry.collect([], [], [])
    registry_ms = int((time.monotonic() - t0) * 1000)
    conflicts = registry.conflicts
    checks.append({
        "name": "registry",
        "status": "warning" if conflicts else "ok",
        "duration_ms": registry_ms,
        "details": {"conflict_count": len(conflicts), "conflicts": conflicts}
    })

    legacy_count = 0
    if adapters_dir.exists():
        for d in adapters_dir.iterdir():
            if d.is_dir():
                meta_path = d / "metadata.json"
                if meta_path.exists():
                    try:
                        load_metadata(meta_path)
                    except LegacyMetadataError:
                        legacy_count += 1
    checks.append({
        "name": "legacy_adapters",
        "status": "warning" if legacy_count > 0 else "ok",
        "duration_ms": 0,
        "details": {"count": legacy_count}
    })

    agent_md_path = Path.cwd() / "AGENT.md"
    if not agent_md_path.exists():
        agent_md_status = "missing"
    else:
        content = agent_md_path.read_text()
        agent_md_status = "ok" if _SENTINEL_RE.search(content) else "no_sentinel"
    checks.append({
        "name": "agent_md",
        "status": "warning" if agent_md_status != "ok" else "ok",
        "duration_ms": 0,
        "details": {"status": agent_md_status}
    })

    healed_count = 0
    if adapters_dir.exists():
        healed_count = sum(
            1 for d in adapters_dir.iterdir()
            if d.is_dir() and (d / "metadata.healed.json").exists()
        )
    checks.append({
        "name": "healed_pending",
        "status": "warning" if healed_count > 0 else "ok",
        "duration_ms": 0,
        "details": {"count": healed_count, "hint": "cliany-site adapter accept-heal <domain>"}
    })

    failed = [c["name"] for c in checks if c["status"] == "fail"]
    if failed:
        return err("doctor", ErrorCode.E_UNKNOWN, f"检查失败: {', '.join(failed)}",
                   details={"checks": checks}, source="builtin")
    return ok("doctor", {"checks": checks}, source="builtin")
