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
        "warning": "运行一次 explore 让 cliany-site 生成/更新 AGENT.md，或手动补齐 sentinel。",
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

_CAPABILITY_CHOICES = (
    "manage_adapters",
    "run_browser_workflows",
    "generate_adapters",
)


_CHECK_LABELS = {
    "cdp": "Chrome 浏览器连接",
    "llm": "LLM API 密钥",
    "llm_provider": "LLM 服务商配置",
    "llm_live": "LLM 服务连通性",
    "openai_base_url": "OpenAI 兼容接口地址",
    "dirs": "运行时目录",
    "registry": "命令注册表",
    "legacy_adapters": "旧版 adapter",
    "agent_md": "项目说明文件",
    "healed_pending": "待确认的自愈结果",
    "provider": "浏览器 provider",
}


def _check_label(name: str) -> str:
    return _CHECK_LABELS.get(name, name)


def _human_action_for_check(check: dict[str, Any]) -> str:
    """Translate the few upstream-facing diagnostics that users act on most."""
    name = str(check.get("name") or "")
    if name != "llm_live":
        return str(check.get("action") or _action_for_check(check))

    details = check.get("details")
    if not isinstance(details, dict):
        return str(check.get("action") or _action_for_check(check))

    provider = str(details.get("provider") or "LLM")
    provider_label = "OpenAI 兼容服务" if provider == "openai" else "Anthropic 服务"
    status_code = details.get("status_code")
    message = str(details.get("message") or "")
    if isinstance(status_code, int):
        return (
            f"{provider_label} 暂时不可用（HTTP {status_code}）。请稍后重试；"
            "若持续失败，请检查服务地址和账户状态。"
        )
    if "connection" in message.lower():
        config_name = "CLIANY_OPENAI_BASE_URL" if provider == "openai" else "CLIANY_LLM_PROVIDER"
        return f"无法连接 {provider_label}。请检查网络和 {config_name} 后重试。"
    return str(check.get("action") or _action_for_check(check))


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

    capabilities: dict[str, dict[str, Any]] = {
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


def _llm_live_preflight_summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    for check in checks:
        if check.get("name") != "llm_live":
            continue
        status = str(check.get("status") or "unknown")
        summary: dict[str, Any] = {
            "checked": True,
            "ready": status == "ok",
            "status": status,
            "blocks_explore": status != "ok",
            "action": check.get("action") or _action_for_check(check),
        }
        details = check.get("details")
        if isinstance(details, dict):
            for key in (
                "provider",
                "error_code",
                "message",
                "retryable",
                "status_code",
                "phase",
                "skipped",
                "reason",
            ):
                if key in details:
                    summary[key] = details[key]
        return summary
    return {
        "checked": False,
        "ready": None,
        "status": "not_run",
        "blocks_explore": False,
        "action": (
            "Run `cliany-site doctor --llm-live --require-capability generate_adapters --json` "
            "before long explore or candidate adapter promotion."
        ),
    }


def _demo_adapter_quickstart() -> dict[str, Any]:
    from cliany_site.commands.cases import _load_cases_manifest

    try:
        catalog_cases, _source_path, _checked_paths = _load_cases_manifest()
    except (OSError, ValueError, json.JSONDecodeError):
        catalog_cases = []

    for case in catalog_cases:
        if case.get("status") != "active":
            continue

        commands = case.get("commands")
        if not isinstance(commands, list):
            continue
        command_strings = [str(command) for command in commands]
        if any(command.startswith("cliany-site login ") for command in command_strings):
            continue

        install_command = next(
            (command for command in command_strings if command.startswith("cliany-site market install ")),
            "",
        )
        adapter_domain = str(case.get("adapter_domain") or "")
        read_only_command = next(
            (
                command
                for command in command_strings
                if command.startswith(f"cliany-site {adapter_domain} ")
            ),
            "",
        )
        if (
            not install_command.startswith("cliany-site market install https://")
            or " --sha256 " not in install_command
            or not adapter_domain
            or not read_only_command
        ):
            continue

        verify_command = f"cliany-site verify {adapter_domain} --json"
        strict_verify_command = f"cliany-site verify {adapter_domain} --strict --json"
        adapter_present = (get_config().adapters_dir / adapter_domain).exists()
        recommended_commands = [strict_verify_command, read_only_command]
        if not adapter_present:
            recommended_commands.insert(0, install_command)
        return {
            "label": "已发布 active demo adapter 快速路径",
            "case_id": case.get("id"),
            "case_status": "active",
            "commands": [install_command, verify_command, read_only_command],
            "recommended_commands": recommended_commands,
            "install_command": install_command,
            "verify_command": verify_command,
            "strict_verify_command": strict_verify_command,
            "read_only_command": read_only_command,
            "adapter_present": adapter_present,
            "docs": case.get("docs"),
            "source_release": case.get("source_release"),
            "available": True,
            "deprecated": False,
        }

    return {
        "label": "历史 demo adapter 路径（当前不可用）",
        "commands": [],
        "docs": "docs/quickstart-10min.md",
        "available": False,
        "deprecated": True,
        "reason": "当前没有可安装的 demo adapter release asset。",
        "replacement": "case_catalog_quickstart",
    }


def _case_catalog_quickstart() -> dict[str, Any]:
    return {
        "label": "先查看维护中的公开案例",
        "commands": ["cliany-site cases", "cliany-site cases --json"],
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
    summary["ready_for_existing_adapters"] = not summary["must_fix"]
    summary["ready_for_explore"] = not summary["must_fix"] and not any(
        item["name"] in {"llm", "llm_live"} for item in summary["should_fix"]
    )
    summary["capabilities"] = _build_capabilities(checks)
    summary["llm_live_preflight"] = _llm_live_preflight_summary(checks)
    demo_adapter_quickstart = _demo_adapter_quickstart()
    summary["demo_adapter_quickstart"] = demo_adapter_quickstart
    summary["ready_for_demo_adapters"] = bool(demo_adapter_quickstart["available"]) and bool(
        summary["ready_for_existing_adapters"]
    )
    summary["case_catalog_quickstart"] = _case_catalog_quickstart()
    if summary["must_fix"]:
        summary["recommended_next_step"] = "先处理必须修复项，然后重新运行 cliany-site doctor。"
    elif summary["ready_for_demo_adapters"]:
        if demo_adapter_quickstart["adapter_present"]:
            summary["recommended_next_step"] = (
                "已检测到 active demo 安装目标；按 demo_adapter_quickstart.recommended_commands "
                "先运行严格 verify，再执行只读案例命令。"
            )
        else:
            summary["recommended_next_step"] = (
                "按 demo_adapter_quickstart.recommended_commands 依次安装已发布 active adapter、"
                "运行严格 verify，再执行只读案例命令。"
            )
    elif summary["ready_for_explore"]:
        summary["recommended_next_step"] = (
            "先运行 cliany-site cases 查看维护中的案例；准备好后可使用 explore 生成自己的命令。"
        )
    else:
        summary["recommended_next_step"] = (
            "先运行 cliany-site cases 查看维护中的案例；需要生成新 adapter 时再配置 LLM key。"
        )
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


def _required_capability_error_code(
    checks: list[dict[str, Any]],
    blockers: list[str],
) -> str:
    checks_by_name = {str(check.get("name")): check for check in checks}
    for blocker in blockers:
        details = checks_by_name.get(blocker, {}).get("details")
        if isinstance(details, dict):
            code = details.get("error_code")
            if isinstance(code, str) and code.startswith("E_"):
                return code
    if "cdp" in blockers:
        return ErrorCode.E_CDP_UNAVAILABLE
    return ErrorCode.E_MISSING_CAPABILITY


def _require_capability(result: Envelope, capability_name: str | None) -> Envelope:
    if capability_name is None or not result.get("ok"):
        return result

    data = result.get("data")
    if not isinstance(data, dict):
        return result
    summary = data.get("summary")
    if not isinstance(summary, dict):
        return result
    capabilities = summary.get("capabilities")
    if not isinstance(capabilities, dict):
        return result
    capability = capabilities.get(capability_name)
    if not isinstance(capability, dict) or capability.get("ready") is True:
        return result

    blockers = capability.get("blockers")
    blocker_names = [str(blocker) for blocker in blockers] if isinstance(blockers, list) else []
    checks = data.get("checks")
    check_items = [check for check in checks if isinstance(check, dict)] if isinstance(checks, list) else []
    return err(
        "doctor",
        _required_capability_error_code(check_items, blocker_names),
        f"请求的能力尚未就绪: {capability_name}",
        hint=str(capability.get("next_step") or "先处理 doctor blockers 后重试。"),
        details={
            **data,
            "required_capability": capability_name,
            "required_capability_blockers": blocker_names,
        },
        source="builtin",
    )


def _print_doctor_human(result: Envelope) -> None:
    payload = _doctor_payload(result)
    summary_value = payload.get("summary")
    summary: dict[str, Any] = summary_value if isinstance(summary_value, dict) else {}
    capabilities_value = summary.get("capabilities")
    capabilities: dict[str, Any] = (
        capabilities_value if isinstance(capabilities_value, dict) else {}
    )
    checks_value = payload.get("checks")
    checks: list[Any] = checks_value if isinstance(checks_value, list) else []
    checks_by_name = {
        str(check.get("name")): check
        for check in checks
        if isinstance(check, dict) and check.get("name")
    }
    required_capability = payload.get("required_capability")
    required_capability = str(required_capability) if required_capability else None
    required_blockers = payload.get("required_capability_blockers")
    required_blockers = (
        [str(blocker) for blocker in required_blockers]
        if isinstance(required_blockers, list)
        else []
    )

    click.secho("cliany-site doctor", bold=True)
    if required_capability:
        requested = capabilities.get(required_capability)
        label = requested.get("label") if isinstance(requested, dict) else required_capability
        click.echo(f"目标: {label}")
        click.secho("状态: 尚未就绪", fg="yellow")
    elif result.get("ok"):
        click.secho("状态: 环境检查完成", fg="green")
    else:
        click.secho("状态: 有阻塞项需要处理", fg="red")

    if not summary:
        click.echo("未生成诊断摘要，请使用 --json 查看原始检查结果。")
        return

    ready_capabilities: list[str] = []
    unavailable_capabilities: list[str] = []
    blockers: list[str] = []
    for name, capability in capabilities.items():
        if not isinstance(capability, dict):
            continue
        label = str(capability.get("label") or name)
        if capability.get("ready"):
            ready_capabilities.append(label)
            continue
        unavailable_capabilities.append(label)
        capability_blockers = capability.get("blockers")
        if isinstance(capability_blockers, list):
            blockers.extend(str(blocker) for blocker in capability_blockers)

    if required_capability:
        blockers = required_blockers

    if ready_capabilities:
        click.echo("\n现在可以：")
        for label in ready_capabilities:
            click.echo(f"- ✓ {label}")

    if unavailable_capabilities:
        click.echo("\n暂时不能：")
        for label in unavailable_capabilities:
            click.echo(f"- · {label}")

    unique_blockers = list(dict.fromkeys(blockers))
    if unique_blockers:
        click.secho("\n需要先处理：", fg="yellow", bold=True)
        for name in unique_blockers:
            check = checks_by_name.get(name)
            if check is None:
                continue
            click.echo(f"- {_check_label(name)}：{_human_action_for_check(check)}")

    nonblocking_items: list[dict[str, Any]] = []
    for item in summary.get("should_fix", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if name and name not in unique_blockers:
            nonblocking_items.append(item)
    if nonblocking_items:
        click.echo("\n可选提示（不影响上述能力）：")
        for item in nonblocking_items:
            name = str(item.get("name") or "unknown")
            check = checks_by_name.get(name, item)
            click.echo(f"- {_check_label(name)}：{_human_action_for_check(check)}")

    click.echo("\n建议下一步：")
    if required_capability:
        command = "cliany-site doctor --llm-live --require-capability " + required_capability
        click.echo(f"- 处理完成后重新检查：{command}")
    elif summary.get("ready_for_existing_adapters"):
        demo_quickstart = summary.get("demo_adapter_quickstart")
        demo_quickstart = demo_quickstart if isinstance(demo_quickstart, dict) else {}
        demo_commands = demo_quickstart.get("recommended_commands")
        if demo_quickstart.get("adapter_present") and isinstance(demo_commands, list) and demo_commands:
            click.echo(f"- 先校验已安装案例：{demo_commands[0]}")
            if len(demo_commands) > 1:
                click.echo(f"- 校验通过后可执行：{demo_commands[1]}")
        elif isinstance(demo_commands, list) and len(demo_commands) >= 3:
            click.echo(f"- 安装已发布案例：{demo_commands[0]}")
            click.echo(f"- 安装完成后严格校验：{demo_commands[1]}")
            click.echo(f"- 校验通过后可执行：{demo_commands[2]}")
        else:
            click.echo("- 查看可直接运行的公开案例：cliany-site cases")
        if summary.get("ready_for_explore"):
            live_preflight = summary.get("llm_live_preflight")
            if isinstance(live_preflight, dict) and live_preflight.get("checked") is False:
                click.echo(
                    "- 创建自己的站点命令前先做实时预检："
                    "cliany-site doctor --llm-live --require-capability generate_adapters"
                )
            else:
                click.echo('- 创建自己的站点命令：cliany-site explore <url> "要完成的任务"')
    else:
        click.echo("- 先完成“需要先处理”中的项目，然后重新运行：cliany-site doctor")


@click.command("doctor")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出模式")
@click.option("--llm-live", is_flag=True, default=False, help="实际调用一次 LLM provider，检查上游是否可用")
@click.option(
    "--require-capability",
    type=click.Choice(_CAPABILITY_CHOICES),
    default=None,
    help="要求指定能力就绪；未就绪时返回非零退出码",
)
@click.pass_context
def doctor(
    ctx: click.Context,
    json_mode: bool | None,
    llm_live: bool,
    require_capability: str | None,
):
    """检查运行环境（CDP / LLM API key / 目录）"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))
    if require_capability == "generate_adapters" and not llm_live:
        raise click.UsageError(
            "--require-capability generate_adapters 需要同时指定 --llm-live",
            ctx=ctx,
        )

    from cliany_site.browser.cdp import cdp_from_context

    cdp_conn = cdp_from_context(ctx)
    result = asyncio.run(_run_checks(cdp_conn, llm_live=llm_live))
    result = _require_capability(result, require_capability)
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

    cwd = Path.cwd()
    managed_agent_md_path = cwd / "AGENT.md"
    plural_agent_md_path = cwd / "AGENTS.md"
    agent_md_path: Path | None = None
    agent_md_details: dict[str, Any]

    if managed_agent_md_path.exists():
        agent_md_path = managed_agent_md_path
        content = agent_md_path.read_text(encoding="utf-8")
        if _SENTINEL_RE.search(content):
            agent_md_status = "ok"
            agent_md_message = None
        else:
            agent_md_status = "no_sentinel"
            agent_md_message = "AGENT.md 存在但缺少 sentinel，建议运行 cliany-site explore"
        agent_md_details = {
            "status": agent_md_status,
            "path": agent_md_path.name,
            "message": agent_md_message,
        }
    elif plural_agent_md_path.exists():
        agent_md_path = plural_agent_md_path
        content = agent_md_path.read_text(encoding="utf-8")
        if _SENTINEL_RE.search(content):
            agent_md_status = "ok"
            agent_md_message = None
        else:
            agent_md_status = "manual"
            agent_md_message = "发现人工 AGENTS.md；explore 成功后会生成/更新 AGENT.md"
        agent_md_details = {
            "status": agent_md_status,
            "path": agent_md_path.name,
            "managed_path": managed_agent_md_path.name,
            "message": agent_md_message,
        }
    else:
        agent_md_status = "missing"
        agent_md_message = "未找到 AGENT.md / AGENTS.md，建议运行 cliany-site explore"
        agent_md_details = {
            "status": agent_md_status,
            "path": managed_agent_md_path.name,
            "message": agent_md_message,
        }
    checks.append({
        "name": "agent_md",
        "status": "warning" if agent_md_status in {"missing", "no_sentinel"} else "ok",
        "duration_ms": 0,
        "details": agent_md_details,
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
    data: dict[str, Any] = {"checks": checks, "summary": summary}
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
