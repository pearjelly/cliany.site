# src/cliany_site/commands/doctor.py
import asyncio
import importlib.metadata as importlib_metadata
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import click

from cliany_site.agent_md import _SENTINEL_RE
from cliany_site.config import get_config
from cliany_site.envelope import Envelope, ErrorCode, err, ok
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


async def _run_checks(cdp_conn: Any = None) -> Envelope:
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
        "status": "ok" if has_llm else "warning",
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

    provider_name = cfg.browser_provider or "chrome"
    try:
        from cliany_site.providers.factory import get_provider
        _prov = get_provider(provider_name)
        snap = _prov.get_capability_snapshot()
        provider_caps = {
            "provider": snap.provider,
            "version": snap.version,
            "supports_axtree": snap.supports_axtree,
            "supports_navigation": snap.supports_navigation,
            "supports_screenshot": snap.supports_screenshot,
            "supports_cookies": snap.supports_cookies,
            "supports_network_events": snap.supports_network_events,
            "supports_console_events": snap.supports_console_events,
        }
        checks.append({
            "name": "provider",
            "status": "ok",
            "duration_ms": 0,
            "details": {"provider_name": provider_name, "provider_capabilities": provider_caps},
        })
    except Exception as exc:
        checks.append({
            "name": "provider",
            "status": "warning",
            "duration_ms": 0,
            "details": {"provider_name": provider_name, "provider_capabilities": None, "error": str(exc)},
        })

    failed = [c["name"] for c in checks if c["status"] == "fail"]
    if failed:
        return err("doctor", ErrorCode.E_UNKNOWN, f"检查失败: {', '.join(failed)}",
                   details={"checks": checks}, source="builtin")

    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    try:
        cliany_ver = importlib_metadata.version("cliany-site")
    except importlib_metadata.PackageNotFoundError:
        cliany_ver = "unknown"
    versions_details: dict[str, str] = {"python": python_ver, "cliany_site": cliany_ver}
    for pkg in ("click", "anthropic", "openai"):
        try:
            versions_details[pkg] = importlib_metadata.version(pkg)
        except importlib_metadata.PackageNotFoundError:
            versions_details[pkg] = "not installed"
    checks.append({"name": "versions", "status": "ok", "duration_ms": 0, "details": versions_details})

    adapter_count = 0
    command_count = 0
    if adapters_dir.exists():
        for d in adapters_dir.iterdir():
            if d.is_dir():
                meta_path = d / "metadata.json"
                if meta_path.exists():
                    adapter_count += 1
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        command_count += len(meta.get("commands", {}))
                    except (json.JSONDecodeError, OSError):
                        pass
    checks.append({"name": "adapter_stats", "status": "ok", "duration_ms": 0, "details": {"adapter_count": adapter_count, "command_count": command_count}})

    # 新增字段
    data = {"checks": checks}
    data["schema_version"] = 3
    
    # manifest_status
    manifest_path = Path.home() / ".cliany-site" / "cli-manifest.json"
    if not manifest_path.exists():
        data["manifest_status"] = "missing"
    else:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                json.load(f)
            data["manifest_status"] = "ok"
        except (json.JSONDecodeError, OSError):
            data["manifest_status"] = "corrupt"
    
    # legacy_adapter_count
    legacy_count = 0
    if adapters_dir.exists():
        for d in adapters_dir.iterdir():
            if d.is_dir():
                meta_path = d / "metadata.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        if meta.get("schema_version") != 3:
                            legacy_count += 1
                    except (json.JSONDecodeError, OSError):
                        pass  # 忽略损坏的 metadata
    data["legacy_adapter_count"] = legacy_count
    
    data["capability_router"] = "enabled"
    data["network_capture"] = os.environ.get("CLIANY_CAPTURE_NETWORK", "1") != "0"
    data["console_capture"] = os.environ.get("CLIANY_CAPTURE_CONSOLE", "1") != "0"
    data["diagnose_llm"] = os.environ.get("CLIANY_DIAGNOSE_LLM", "1") != "0"
    
    return ok("doctor", data, source="builtin")
