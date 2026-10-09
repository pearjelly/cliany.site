from __future__ import annotations

import json
import subprocess
import time
from contextvars import ContextVar
from typing import Any, cast
from urllib.parse import urlparse

import click
from click.testing import CliRunner

from cliany_site.envelope import Envelope
from cliany_site.extract_quality import evaluate_extract_quality

_workflow_browser: ContextVar[dict[str, Any] | None] = ContextVar("workflow_browser", default=None)


def run_atom(
    command: list[str],
    session: str | None = None,
    heal_on_failure: bool = False,
) -> Envelope:
    from cliany_site.cli import cli  # 延迟导入，避免与 loader.py 的循环导入

    current_ctx = click.get_current_context(silent=True)
    root_obj = current_ctx.find_root().obj if current_ctx is not None else None
    args: list[str] = []
    browser = _workflow_browser.get()
    if browser is not None:
        from cliany_site.browser.launcher import ChromeNotFoundError, ensure_chrome
        from cliany_site.config import get_config
        from cliany_site.envelope import ErrorCode, err

        cfg = get_config()
        requested_url = root_obj.get("cdp_url") if isinstance(root_obj, dict) else None
        requested_url = requested_url or cfg.cdp_url
        parsed = None
        if requested_url:
            parsed = urlparse(requested_url if "://" in requested_url else f"http://{requested_url}")
        local_url = parsed is not None and (
            parsed.scheme == "http"
            and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            and parsed.path in {"", "/"}
            and not parsed.query
        )
        if local_url or (not requested_url and cfg.browser_provider in {"", "chrome"}):
            if "url" not in browser:
                port = (parsed.port or 9222) if parsed is not None else cfg.cdp_port
                headless = bool(root_obj.get("headless", cfg.headless)) if isinstance(root_obj, dict) else cfg.headless
                try:
                    _, proc = ensure_chrome(port, headless=headless)
                except (ChromeNotFoundError, OSError, RuntimeError, TimeoutError) as exc:
                    return err(
                        command=" ".join(command),
                        code=ErrorCode.E_CDP_UNAVAILABLE,
                        message=f"Chrome CDP 不可用: {exc}",
                        source="builtin",
                    )
                browser["url"] = f"http://localhost:{port}"
                browser["proc"] = proc
            if not (isinstance(root_obj, dict) and root_obj.get("cdp_url")):
                args.extend(["--cdp-url", browser["url"]])
    if isinstance(root_obj, dict):
        if root_obj.get("cdp_url"):
            args.extend(["--cdp-url", root_obj["cdp_url"]])
        if root_obj.get("headless"):
            args.append("--headless")
    args.extend(command)
    if session:
        args.extend(["--session", session])
    args.append("--json")
    runner = CliRunner()
    result = runner.invoke(cli, args, catch_exceptions=False)
    try:
        parsed = json.loads(result.stdout)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("ok"), bool):
            raise ValueError("命令 JSON 必须包含布尔 ok 状态")
        if result.exit_code != 0 and parsed["ok"]:
            raise ValueError(f"命令以非零状态退出: {result.exit_code}")
        envelope = cast(Envelope, parsed)
    except ValueError as exc:
        from cliany_site.envelope import ErrorCode, err

        envelope = err(
            command=" ".join(command),
            code=ErrorCode.E_UNKNOWN,
            message=f"{exc}: {result.output[:200]}",
            source="builtin",
        )

    if not envelope.get("ok") and heal_on_failure:
        from cliany_site.healer import Healer

        domain = session or ""
        cmd_name = command[0] if command else ""
        Healer().heal(
            domain=domain,
            command=cmd_name,
            failure_envelope=envelope,
        )

    return envelope


def execute_steps_via_atoms(
    action_steps: list[dict[str, Any]],
    source_url: str,
    domain: str,
    *,
    sandbox: bool = False,
) -> list[Envelope]:
    if sandbox:
        from cliany_site.envelope import ErrorCode
        from cliany_site.envelope import err as _err
        from cliany_site.sandbox import SandboxPolicy, validate_action_steps

        policy = SandboxPolicy.from_domain(domain)
        source_violations = (
            validate_action_steps([{"type": "navigate", "url": source_url}], policy)
            if source_url
            else []
        )
        violations = source_violations or validate_action_steps(action_steps, policy)
        if violations:
            first = violations[0]
            return [
                _err(
                    command=f"adapter {domain}",
                    code=ErrorCode.E_SANDBOX_VIOLATION,
                    message=f"沙箱阻止执行: 第 {first['index']} 步 {first['action'] or 'unknown'}",
                    hint=first.get("error") or "关闭 --sandbox 或重新 explore 以调整动作路径",
                    details={"domain": domain, **first},
                    source="adapter",
                )
            ]

    results: list[Envelope] = []
    browser: dict[str, Any] = {}
    token = _workflow_browser.set(browser)
    try:
        if source_url:
            nav_result = run_atom(["browser", "navigate", source_url], session=_navigation_session(domain))
            results.append(nav_result)
            if not nav_result.get("ok"):
                return results

        for step in action_steps:
            result = _execute_single_step(step, domain)
            results.append(result)
            if not result.get("ok"):
                break

        return results
    finally:
        _workflow_browser.reset(token)
        proc = browser.get("proc")
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


# New adapters import this capability name so older runtimes cannot silently ignore targets.
execute_semantic_steps_via_atoms = execute_steps_via_atoms


def _execute_single_step(step: dict[str, Any], domain: str) -> Envelope:
    from cliany_site.envelope import ErrorCode
    from cliany_site.envelope import err as _err

    action_type = (step.get("type") or "").lower()

    if action_type == "navigate":
        url = step.get("url") or step.get("value") or ""
        if not url:
            return _err(
                command="browser navigate",
                code=ErrorCode.E_INVALID_PARAM,
                message="navigate 步骤缺少目标 url",
                source="builtin",
            )
        return run_atom(["browser", "navigate", url], session=_navigation_session(domain))

    if action_type == "click":
        args: list[str] = ["browser", "click"]
        ref = step.get("ref")
        name = step.get("target_name")
        if name:
            args.extend(["--text", str(name)])
            if step.get("target_role"):
                args.extend(["--role", str(step["target_role"])])
        elif ref:
            args.extend(["--ref", str(ref)])
        return run_atom(args, session=domain)

    if action_type == "type":
        args = ["browser", "type"]
        ref = step.get("ref")
        name = step.get("target_name")
        value = str(step.get("value") or "")
        if name:
            args.extend(["--text", str(name)])
            if step.get("target_role"):
                args.extend(["--role", str(step["target_role"])])
        elif ref:
            args.extend(["--ref", str(ref)])
        args.extend(["--value", value])
        args.append("--clear")
        return run_atom(args, session=domain)

    if action_type == "select":
        args = ["browser", "select"]
        ref = step.get("ref")
        name = step.get("target_name")
        value = str(step.get("value") or "")
        if name:
            args.extend(["--text", str(name)])
            if step.get("target_role"):
                args.extend(["--role", str(step["target_role"])])
        elif ref:
            args.extend(["--ref", str(ref)])
        args.extend(["--value", value])
        return run_atom(args, session=domain)

    if action_type == "submit":
        args = ["browser", "submit"]
        ref = step.get("ref")
        name = step.get("target_name")
        if name:
            args.extend(["--text", str(name)])
            if step.get("target_role"):
                args.extend(["--role", str(step["target_role"])])
        elif ref:
            args.extend(["--ref", str(ref)])
        return run_atom(args, session=domain)

    if action_type == "extract":
        args = ["browser", "extract"]
        raw_selector = step.get("selector")
        selector = raw_selector.strip() if isinstance(raw_selector, str) else ""
        if not selector:
            return _err(
                command="browser extract",
                code=ErrorCode.E_PARSE_FAILED,
                message="extract 动作缺少 selector",
                details={"selector": None, "extract_mode": step.get("extract_mode") or "text"},
                source="builtin",
            )
        args.extend(["--selector", selector])
        if step.get("extract_target"):
            args.extend(["--target-json", json.dumps(step["extract_target"], ensure_ascii=False)])
        mode = step.get("extract_mode")
        if mode:
            args.extend(["--mode", str(mode)])
        fields = step.get("fields")
        if isinstance(fields, dict) and fields:
            args.extend(["--fields-json", json.dumps(fields, ensure_ascii=False)])
        result = run_atom(args, session=domain)
        if mode in ("list", "table"):
            for delay in (0.5, 1.0):
                data = result.get("data")
                quality = data.get("quality") if isinstance(data, dict) else None
                if not (result.get("ok") and isinstance(quality, dict) and quality.get("status") == "empty"):
                    break
                time.sleep(delay)
                result = run_atom(args, session=domain)
        return result

    return _err(
        command=f"browser {action_type}",
        code=ErrorCode.E_UNKNOWN,
        message=f"未知操作类型: {action_type!r}",
        source="builtin",
    )


def _navigation_session(domain: str) -> str | None:
    from cliany_site.session import _session_path

    return domain if _session_path(domain).is_file() else None


def summarize_extract_quality(
    results: list[Envelope],
    action_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    extracts: list[dict[str, Any]] = []
    result_index = 1 if results and results[0].get("command") == "browser navigate" else 0

    for step_index, step in enumerate(action_steps):
        if result_index >= len(results):
            break
        result = results[result_index]
        result_index += 1
        if (step.get("type") or "").lower() != "extract":
            continue

        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        content = data.get("content") if isinstance(data, dict) else None
        fields = step.get("fields") if isinstance(step.get("fields"), dict) else None
        extract_mode = str(step.get("extract_mode") or "text")
        quality = evaluate_extract_quality(extract_mode, content, fields).to_dict()
        source_quality = data.get("quality") if isinstance(data, dict) else None
        if (
            extract_mode == "list"
            and isinstance(source_quality, dict)
            and isinstance(source_quality.get("row_limit"), int)
            and isinstance(source_quality.get("limit_reached"), bool)
        ):
            quality["row_limit"] = source_quality["row_limit"]
            quality["limit_reached"] = source_quality["limit_reached"]
        quality["extract_mode"] = extract_mode
        quality["step_index"] = step_index
        if step.get("description"):
            quality["description"] = str(step.get("description"))
        extracts.append(quality)

    if not extracts:
        return {"status": "not_applicable", "ok": True, "extracts": []}
    if all(item.get("ok") for item in extracts):
        status = "ok"
    elif any(
        item.get("status") == "partial"
        or item.get("field_blank_rows")
        or (item.get("status") == "empty" and item.get("extract_mode") not in {"list", "table"})
        for item in extracts
    ):
        status = "partial"
    elif any(item.get("status") == "empty" for item in extracts):
        status = "empty"
    else:
        status = "partial"
    return {
        "status": status,
        "ok": status == "ok",
        "extracts": extracts,
    }


def diagnose_if_enabled(ctx, failure_context: dict) -> dict:
    """失败时若 --diagnose flag 开启，调用 diagnostic.run_diagnose 返回诊断结果。

    若 diagnose 未启用或 LLM 不可用，直接返回空 dict。
    """
    import click as _click
    try:
        root_obj = _click.get_current_context().find_root().obj or {}
    except RuntimeError:
        root_obj = {}

    if not root_obj.get("diagnose", False):
        return {}

    try:
        from cliany_site.diagnostic import collect_diagnostic_context, run_diagnose
        context = collect_diagnostic_context(
            failure=failure_context,
            recording={},
            network=[],
            console=[],
            axtree_snapshot={},
        )
        return run_diagnose(context, llm_call_fn=None)  # llm_call_fn=None 时若 CLIANY_DIAGNOSE_LLM=0 则跳过
    except Exception:
        return {}


__all__ = [
    "run_atom",
    "execute_steps_via_atoms",
    "execute_semantic_steps_via_atoms",
    "_execute_single_step",
    "summarize_extract_quality",
    "diagnose_if_enabled",
]
