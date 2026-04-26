from __future__ import annotations

import json
from typing import Any

from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.envelope import Envelope


def run_atom(command: list[str], session: str | None = None) -> Envelope:
    """
    in-process 调用 cliany-site atom 子命令（零网络，零 LLM）。
    command: 命令路径，如 ["browser", "navigate", "https://example.com"]
    返回 Envelope dict；失败时返回 err envelope。
    """
    args = list(command)
    if session:
        args.extend(["--session", session])
    args.append("--json")
    runner = CliRunner()
    result = runner.invoke(cli, args, catch_exceptions=False)
    try:
        return json.loads(result.output)
    except (json.JSONDecodeError, ValueError):
        from cliany_site.envelope import ErrorCode, err

        return err(
            command=" ".join(command),
            code=ErrorCode.E_UNKNOWN,
            message=result.output[:200],
            source="builtin",
        )


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

    if action_type == "extract":
        args = ["browser", "extract"]
        selector = step.get("selector")
        if selector:
            args.extend(["--selector", str(selector)])
        mode = step.get("extract_mode")
        if mode:
            args.extend(["--mode", str(mode)])
        return run_atom(args, session=domain)

    return _err(
        command=f"browser {action_type}",
        code=ErrorCode.E_UNKNOWN,
        message=f"未知操作类型: {action_type!r}",
        source="builtin",
    )


__all__ = ["run_atom", "execute_steps_via_atoms", "_execute_single_step"]
