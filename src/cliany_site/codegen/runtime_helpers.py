from __future__ import annotations

import json
from typing import Any, cast

from click.testing import CliRunner

from cliany_site.envelope import Envelope
from cliany_site.extract_quality import evaluate_extract_quality


def run_atom(
    command: list[str],
    session: str | None = None,
    heal_on_failure: bool = False,
) -> Envelope:
    from cliany_site.cli import cli  # 延迟导入，避免与 loader.py 的循环导入

    args = list(command)
    if session:
        args.extend(["--session", session])
    args.append("--json")
    runner = CliRunner()
    result = runner.invoke(cli, args, catch_exceptions=False)
    try:
        envelope = cast(Envelope, json.loads(result.output))
    except (json.JSONDecodeError, ValueError):
        from cliany_site.envelope import ErrorCode, err

        envelope = err(
            command=" ".join(command),
            code=ErrorCode.E_UNKNOWN,
            message=result.output[:200],
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
) -> list[Envelope]:
    results: list[Envelope] = []

    if source_url:
        nav_result = run_atom(["browser", "navigate", source_url], session=domain)
        results.append(nav_result)
        if not nav_result.get("ok"):
            return results

    for step in action_steps:
        result = _execute_single_step(step, domain)
        results.append(result)
        if not result.get("ok"):
            break

    return results


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
        return run_atom(["browser", "navigate", url], session=domain)

    if action_type == "click":
        args: list[str] = ["browser", "click"]
        ref = step.get("ref")
        name = step.get("target_name")
        if ref:
            args.extend(["--ref", str(ref)])
        elif name:
            args.extend(["--text", str(name)])
        return run_atom(args, session=domain)

    if action_type == "type":
        args = ["browser", "type"]
        ref = step.get("ref")
        name = step.get("target_name")
        value = str(step.get("value") or "")
        if ref:
            args.extend(["--ref", str(ref)])
        elif name:
            args.extend(["--text", str(name)])
        args.extend(["--value", value])
        return run_atom(args, session=domain)

    if action_type == "select":
        args = ["browser", "select"]
        ref = step.get("ref")
        name = step.get("target_name")
        value = str(step.get("value") or "")
        if ref:
            args.extend(["--ref", str(ref)])
        elif name:
            args.extend(["--text", str(name)])
        args.extend(["--value", value])
        return run_atom(args, session=domain)

    if action_type == "submit":
        args = ["browser", "submit"]
        ref = step.get("ref")
        name = step.get("target_name")
        if ref:
            args.extend(["--ref", str(ref)])
        elif name:
            args.extend(["--text", str(name)])
        return run_atom(args, session=domain)

    if action_type == "extract":
        args = ["browser", "extract"]
        selector = step.get("selector")
        if selector:
            args.extend(["--selector", str(selector)])
        mode = step.get("extract_mode")
        if mode:
            args.extend(["--mode", str(mode)])
        fields = step.get("fields")
        if isinstance(fields, dict) and fields:
            args.extend(["--fields-json", json.dumps(fields, ensure_ascii=False)])
        return run_atom(args, session=domain)

    return _err(
        command=f"browser {action_type}",
        code=ErrorCode.E_UNKNOWN,
        message=f"未知操作类型: {action_type!r}",
        source="builtin",
    )


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
        quality = evaluate_extract_quality(str(step.get("extract_mode") or "text"), content, fields).to_dict()
        quality["step_index"] = step_index
        if step.get("description"):
            quality["description"] = str(step.get("description"))
        extracts.append(quality)

    if not extracts:
        return {"status": "not_applicable", "ok": True, "extracts": []}
    if all(item.get("ok") for item in extracts):
        status = "ok"
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
    "_execute_single_step",
    "summarize_extract_quality",
    "diagnose_if_enabled",
]
