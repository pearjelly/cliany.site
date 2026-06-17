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


_CHECK_ACTIONS: dict[str, dict[str, str]] = {
    "cdp": {
        "fail": "启动 Chrome/Chromium，并开放 CDP 调试端口；或使用 --cdp-url 指向可用浏览器。",
        "ok": "Chrome/CDP 可用，可以执行 login、explore 和浏览器 replay。",
    },
    "llm": {
        "warning": (
            "如果要生成新 adapter，请配置 CLIANY_ANTHROPIC_API_KEY 或 "
            "CLIANY_OPENAI_API_KEY；只安装/执行已有 adapter 可暂时忽略。"
        ),
        "ok": "LLM key 已配置，可以执行 explore 生成新 adapter。",
    },
    "llm_provider": {
        "fail": "将 CLIANY_LLM_PROVIDER 设置为 anthropic 或 openai。",
        "ok": "LLM provider 配置有效。",
    },
    "llm_live": {
        "warning": "LLM 上游暂不可用；请稍后重试，或切换 CLIANY_LLM_PROVIDER / CLIANY_OPENAI_BASE_URL。",
        "ok": "LLM provider live preflight 通过，可以发起 explore。",
    },
    "openai_base_url": {
        "fail": "检查 CLIANY_OPENAI_BASE_URL，需是可规范化为 /v1 的 OpenAI-compatible base URL。",
        "ok": "OpenAI-compatible base URL 配置有效。",
    },
    "dirs": {
        "fail": "创建 ~/.cliany-site/adapters 与 ~/.cliany-site/sessions，或检查当前用户的目录权限。",
        "ok": "运行时目录可用。",
    },
    "registry": {
        "warning": "存在命令注册冲突，请检查 details.conflicts 并重命名冲突 adapter 命令。",
        "ok": "命令注册表无冲突。",
    },
    "legacy_adapters": {
        "warning": "运行 cliany-site migrate --json，或重新 explore 生成 schema v3 adapter。",
        "ok": "未发现 legacy adapter。",
    },
    "agent_md": {
        "warning": "运行一次 explore 让 cliany-site 生成/更新 AGENTS.md，或手动补齐 sentinel。",
        "ok": "Agent 契约文档可识别。",
    },
    "healed_pending": {
        "warning": "检查 metadata.healed.json 后运行 cliany-site adapter accept-heal <domain> 接受修复。",
        "ok": "没有待接受的自愈结果。",
    },
    "provider": {
        "warning": "检查 CLIANY_BROWSER_PROVIDER；探索新 workflow 时建议使用默认 Chrome provider。",
        "ok": "浏览器 provider 可加载，能力快照可读取。",
    },
}


def _action_for_check(check: dict[str, Any]) -> str:
    status = str(check.get("status", ""))
    name = str(check.get("name", ""))
    return _CHECK_ACTIONS.get(name, {}).get(status, "无需处理，仅供诊断参考。")


def _severity_for_check(check: dict[str, Any]) -> str:
    status = check.get("status")
    if status == "fail":
        return "must_fix"
    if status == "warning":
        return "should_fix"
    return "info"


def _build_capabilities(checks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    statuses = {str(check.get("name")): str(check.get("status")) for check in checks}

    def blocked_by(required_ok: tuple[str, ...], required_not_warning: tuple[str, ...] = ()) -> list[str]:
        blockers: list[str] = []
        for name in required_ok:
            if name not in statuses:
                continue
            if statuses.get(name) != "ok":
                blockers.append(name)
        for name in required_not_warning:
            if name not in statuses:
                continue
            if statuses.get(name) in {"fail", "warning"}:
                blockers.append(name)
        return blockers

    capabilities = {
        "manage_adapters": {
            "label": "安装、查看和校验已有 adapter",
            "blockers": blocked_by(("dirs",)),
            "next_step": "可以运行 cliany-site market install、list 或 verify。",
        },
        "run_browser_workflows": {
            "label": "执行需要浏览器的已有 adapter 命令",
            "blockers": blocked_by(("cdp", "dirs")),
            "next_step": "可以执行已安装 adapter 的只读命令；失败时先看命令返回的 error.code。",
        },
        "generate_adapters": {
            "label": "使用 explore 生成新 adapter",
            "blockers": blocked_by(("cdp", "dirs", "llm_provider", "openai_base_url"), ("llm", "llm_live")),
            "next_step": "可以运行 cliany-site explore 生成自己的站点命令。",
        },
    }
    for capability in capabilities.values():
        capability["ready"] = not capability["blockers"]
        if capability["blockers"]:
            capability["next_step"] = "先处理 blockers 中列出的 doctor check，然后重新运行 cliany-site doctor。"
    return capabilities


def _demo_adapter_quickstart() -> dict[str, Any]:
    return {
        "label": "先跑一个真实只读 demo adapter",
        "commands": [
            "cliany-site market install ./issues.apache.org.cliany-adapter-v0.14.0.tar.gz",
            "cliany-site list --json",
            "cliany-site verify issues.apache.org --json",
            "cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json",
        ],
        "docs": "docs/quickstart-10min.md",
    }


def _enrich_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "must_fix": [],
        "should_fix": [],
        "info": [],
        "counts": {"must_fix": 0, "should_fix": 0, "info": 0},
    }
    for check in checks:
        severity = _severity_for_check(check)
        action = _action_for_check(check)
        check["severity"] = severity
        check["action"] = action
        item = {"name": check["name"], "status": check["status"], "action": action}
        summary[severity].append(item)
        summary["counts"][severity] += 1
    summary["ready_for_demo_adapters"] = not summary["must_fix"]
    summary["ready_for_explore"] = not summary["must_fix"] and not any(
        item["name"] in {"llm", "llm_live"} for item in summary["should_fix"]
    )
    summary["capabilities"] = _build_capabilities(checks)
    summary["demo_adapter_quickstart"] = _demo_adapter_quickstart()
    if summary["must_fix"]:
        summary["recommended_next_step"] = "先处理必须修复项，然后重新运行 cliany-site doctor。"
    elif summary["ready_for_explore"]:
        summary["recommended_next_step"] = "可以运行真实 demo adapter，或使用 explore 生成自己的命令。"
    else:
        summary["recommended_next_step"] = "先运行真实 demo adapter；需要生成新 adapter 时再配置 LLM key。"
    return summary


def _doctor_payload(result: Envelope) -> dict[str, Any]:
    if result.get("ok"):
        data = result.get("data")
        return data if isinstance(data, dict) else {}
    error = result.get("error")
    if isinstance(error, dict):
        details = error.get("details")
        return details if isinstance(details, dict) else {}
    return {}


def _print_doctor_human(result: Envelope) -> None:
    payload = _doctor_payload(result)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    ok_result = bool(result.get("ok"))

    click.secho("cliany-site doctor", bold=True)
    if ok_result:
        click.secho("状态: 可继续", fg="green")
    else:
        message = ""
        error = result.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or "")
        click.secho(f"状态: 需要修复 {message}".strip(), fg="red")

    if summary:
        demo_ready = "yes" if summary.get("ready_for_demo_adapters") else "no"
        explore_ready = "yes" if summary.get("ready_for_explore") else "no"
        click.echo(f"Demo adapter ready: {demo_ready}")
        click.echo(f"Explore ready: {explore_ready}")
        recommended_next_step = summary.get("recommended_next_step")
        if recommended_next_step:
            click.echo(f"下一步: {recommended_next_step}")
        demo_quickstart = summary.get("demo_adapter_quickstart")
        demo_quickstart = demo_quickstart if isinstance(demo_quickstart, dict) else {}
        demo_commands = demo_quickstart.get("commands")
        if summary.get("ready_for_demo_adapters") and isinstance(demo_commands, list) and demo_commands:
            click.echo("\nDemo adapter 快速路径:")
            for command in demo_commands:
                click.echo(f"- {command}")

        capabilities = summary.get("capabilities") if isinstance(summary.get("capabilities"), dict) else {}
        if capabilities:
            click.echo("\n可用能力:")
            for name, capability in capabilities.items():
                if not isinstance(capability, dict):
                    continue
                status = "yes" if capability.get("ready") else "no"
                label = capability.get("label") or name
                blockers = capability.get("blockers")
                suffix = ""
                if isinstance(blockers, list) and blockers:
                    suffix = f" (blocked by: {', '.join(str(item) for item in blockers)})"
                click.echo(f"- {name}: {status} - {label}{suffix}")

        labels = (
            ("must_fix", "必须修复"),
            ("should_fix", "建议处理"),
            ("info", "诊断信息"),
        )
        for key, label in labels:
            items = summary.get(key)
            if not items:
                continue
            click.echo(f"\n{label}:")
            for item in items:
                name = item.get("name", "unknown")
                action = item.get("action", "无需处理，仅供诊断参考。")
                click.echo(f"- {name}: {action}")
    else:
        click.echo("未生成诊断摘要，请使用 --json 查看原始检查结果。")


@click.command("doctor")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.option("--llm-live", is_flag=True, default=False, help="实际调用一次 LLM provider，检查上游是否可用")
@click.pass_context
def doctor(ctx: click.Context, json_mode: bool | None, llm_live: bool):
    """检查运行环境（CDP / LLM API key / 目录）"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))

    from cliany_site.browser.cdp import cdp_from_context

    cdp_conn = cdp_from_context(ctx)
    result = asyncio.run(_run_checks(cdp_conn, llm_live=llm_live))
    if effective_json_mode:
        print_response(result, json_mode=True, exit_on_error=True)
        return
    _print_doctor_human(result)
    if not result.get("ok", False):
        raise SystemExit(1)


async def _run_llm_live_check(has_llm: bool, provider: str) -> dict[str, Any]:
    if not has_llm:
        return {
            "name": "llm_live",
            "status": "warning",
            "duration_ms": 0,
            "details": {
                "provider": provider,
                "skipped": True,
                "reason": "missing_llm_key",
            },
        }

    from cliany_site.errors import LlmUnavailableError
    from cliany_site.explorer.engine import _get_llm, _invoke_llm_with_retry

    t0 = time.monotonic()
    try:
        llm = _get_llm()
        await _invoke_llm_with_retry(
            llm,
            "Reply with OK only.",
            max_attempts=1,
            base_delay=0,
            backoff_factor=1,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {
            "name": "llm_live",
            "status": "ok",
            "duration_ms": duration_ms,
            "details": {
                "provider": provider,
                "retryable": False,
                "phase": "llm_preflight",
            },
        }
    except LlmUnavailableError as exc:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {
            "name": "llm_live",
            "status": "warning",
            "duration_ms": duration_ms,
            "details": {
                "provider": provider,
                "error_code": ErrorCode.E_LLM_UNAVAILABLE,
                "message": str(exc),
                "retryable": exc.retryable,
                "status_code": exc.status_code,
                "phase": "llm_preflight",
            },
        }
    except Exception as exc:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return {
            "name": "llm_live",
            "status": "warning",
            "duration_ms": duration_ms,
            "details": {
                "provider": provider,
                "error_code": ErrorCode.E_UNKNOWN,
                "message": str(exc),
                "retryable": False,
                "phase": "llm_preflight",
            },
        }


async def _run_checks(cdp_conn: Any = None, *, llm_live: bool = False) -> Envelope:
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

    if llm_live:
        checks.append(await _run_llm_live_check(has_llm, provider))

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

    agent_md_path: Path | None = None
    for candidate in ("AGENT.md", "AGENTS.md"):
        path = Path.cwd() / candidate
        if path.exists():
            agent_md_path = path
            break

    if agent_md_path is None:
        agent_md_status = "missing"
        agent_md_message = "未找到 AGENT.md / AGENTS.md，建议运行 cliany-site explore"
    else:
        content = agent_md_path.read_text(encoding="utf-8")
        if _SENTINEL_RE.search(content):
            agent_md_status = "ok"
            agent_md_message = None
        else:
            agent_md_status = "no_sentinel"
            agent_md_message = "文件存在但缺少 sentinel，建议运行 cliany-site explore"
    checks.append({
        "name": "agent_md",
        "status": "warning" if agent_md_status != "ok" else "ok",
        "duration_ms": 0,
        "details": {
            "status": agent_md_status,
            "path": agent_md_path.name if agent_md_path is not None else "AGENT.md",
            "message": agent_md_message,
        }
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

    summary = _enrich_checks(checks)
    failed = [c["name"] for c in checks if c["status"] == "fail"]
    if failed:
        return err("doctor", ErrorCode.E_UNKNOWN, f"检查失败: {', '.join(failed)}",
                   details={"checks": checks, "summary": summary}, source="builtin")

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
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                        command_count += len(meta.get("commands", {}))
                    except (json.JSONDecodeError, OSError):
                        pass
    checks.append({
        "name": "adapter_stats",
        "status": "ok",
        "duration_ms": 0,
        "details": {"adapter_count": adapter_count, "command_count": command_count},
    })
    summary = _enrich_checks(checks)

    # 新增字段
    data = {"checks": checks, "summary": summary}
    data["schema_version"] = 3

    # manifest_status
    manifest_path = Path.home() / ".cliany-site" / "cli-manifest.json"
    if not manifest_path.exists():
        data["manifest_status"] = "missing"
    else:
        try:
            json.loads(manifest_path.read_text(encoding="utf-8"))
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
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
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
