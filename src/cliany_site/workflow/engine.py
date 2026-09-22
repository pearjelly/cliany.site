from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from cliany_site.workflow.models import StepDef, WorkflowDef

logger = logging.getLogger(__name__)

# $prev.data.field  /  $steps.step_name.data.field  /  $env.VAR
_VAR_PATTERN = re.compile(r"\$(?:prev|steps\.\w+|env)\.[a-zA-Z0-9_.]+")


# ── 变量插值 ─────────────────────────────────────────────


def resolve_variable(expr: str, context: WorkflowContext) -> Any:
    if not expr.startswith("$"):
        return expr

    parts = expr[1:].split(".")

    if parts[0] == "prev":
        node: Any = context.prev_result
        for key in parts[1:]:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                return None
        return node

    if parts[0] == "steps" and len(parts) >= 3:
        step_name = parts[1]
        node = context.step_results.get(step_name)
        for key in parts[2:]:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                return None
        return node

    if parts[0] == "env" and len(parts) == 2:
        import os

        return os.environ.get(parts[1], "")

    return expr


def interpolate_value(value: str, context: WorkflowContext) -> str:
    if not isinstance(value, str):
        return value

    full_match = _VAR_PATTERN.fullmatch(value)
    if full_match:
        resolved = resolve_variable(value, context)
        return str(resolved) if resolved is not None else ""

    def _replace(m: re.Match) -> str:
        resolved = resolve_variable(m.group(0), context)
        return str(resolved) if resolved is not None else ""

    return _VAR_PATTERN.sub(_replace, value)


def interpolate_params(params: dict[str, str], context: WorkflowContext) -> dict[str, str]:
    return {k: interpolate_value(v, context) for k, v in params.items()}


# ── 条件求值 ─────────────────────────────────────────────

_CONDITION_PATTERN = re.compile(r"^(\$[a-zA-Z0-9_.]+)\s*(==|!=|>=|<=|>|<)\s*(.+)$")


def evaluate_condition(when: str, context: WorkflowContext) -> bool:
    if not when or not when.strip():
        return True

    when = when.strip()
    m = _CONDITION_PATTERN.match(when)
    if not m:
        logger.warning("无法解析条件表达式: %s，默认执行", when)
        return True

    var_expr, operator, raw_expected = m.group(1), m.group(2), m.group(3).strip()

    actual = resolve_variable(var_expr, context)

    expected: Any = raw_expected
    if raw_expected.lower() == "true":
        expected = True
    elif raw_expected.lower() == "false":
        expected = False
    elif raw_expected.lower() == "none" or raw_expected.lower() == "null":
        expected = None
    else:
        try:
            expected = int(raw_expected)
        except ValueError:
            try:
                expected = float(raw_expected)
            except ValueError:
                if (raw_expected.startswith('"') and raw_expected.endswith('"')) or (
                    raw_expected.startswith("'") and raw_expected.endswith("'")
                ):
                    expected = raw_expected[1:-1]

    if operator == "==":
        return bool(actual == expected)
    if operator == "!=":
        return bool(actual != expected)

    try:
        a, b = float(actual), float(expected)
    except (TypeError, ValueError):
        logger.warning("条件比较无法转为数字: %s %s %s，默认执行", actual, operator, expected)
        return True

    if operator == ">":
        return bool(a > b)
    if operator == "<":
        return bool(a < b)
    if operator == ">=":
        return bool(a >= b)
    if operator == "<=":
        return bool(a <= b)

    return True


# ── 执行上下文 ───────────────────────────────────────────


@dataclass
class StepResult:
    name: str
    success: bool
    data: Any = None
    error: str | None = None
    skipped: bool = False
    elapsed_ms: float = 0.0
    attempts: int = 1


@dataclass
class WorkflowContext:
    prev_result: dict[str, Any] = field(default_factory=dict)
    step_results: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    name: str
    success: bool
    steps: list[StepResult] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "success": self.success,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "steps": [
                {
                    "name": s.name,
                    "success": s.success,
                    "skipped": s.skipped,
                    "elapsed_ms": round(s.elapsed_ms, 1),
                    "attempts": s.attempts,
                    "error": s.error,
                    "data": s.data,
                }
                for s in self.steps
            ],
            "summary": {
                "total": len(self.steps),
                "succeeded": sum(1 for s in self.steps if s.success),
                "failed": sum(1 for s in self.steps if not s.success and not s.skipped),
                "skipped": sum(1 for s in self.steps if s.skipped),
            },
        }


# ── 步骤执行器协议 ───────────────────────────────────────


class StepExecutor:
    def execute_step(self, adapter: str, command: str, params: dict[str, str]) -> dict[str, Any]:
        raise NotImplementedError


class ClickAdapterExecutor(StepExecutor):
    def __init__(self, cli_group: Any = None) -> None:
        self._cli = cli_group

    def execute_step(self, adapter: str, command: str, params: dict[str, str]) -> dict[str, Any]:
        from click.testing import CliRunner

        if self._cli is None:
            from cliany_site.cli import cli

            self._cli = cli

        args = [adapter, command, "--json"]
        for key, val in params.items():
            args.extend([f"--{key}", val])

        runner = CliRunner()
        result = runner.invoke(self._cli, args, catch_exceptions=False)

        import json as _json

        try:
            parsed: dict[str, Any] = _json.loads(result.output)
            if not isinstance(parsed, dict):
                return {
                    "success": False,
                    "data": None,
                    "error": {"code": "STEP_FAILED", "message": "命令 JSON 必须是结果对象"},
                }
            if result.exit_code != 0 and parsed.get("ok", parsed.get("success")) is True:
                return {
                    "success": False,
                    "data": parsed.get("data"),
                    "error": {"code": "STEP_FAILED", "message": f"命令以非零状态退出: {result.exit_code}"},
                }
            return parsed
        except (ValueError, _json.JSONDecodeError):
            if result.exit_code == 0:
                return {"success": True, "data": {"raw_output": result.output}, "error": None}
            return {
                "success": False,
                "data": None,
                "error": {"code": "STEP_FAILED", "message": result.output.strip()},
            }


# ── 工作流引擎 ───────────────────────────────────────────


def _run_step_with_retry(
    step: StepDef,
    context: WorkflowContext,
    executor: StepExecutor,
) -> StepResult:
    params = interpolate_params(step.params, context)
    policy = step.retry

    last_error: str | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = executor.execute_step(step.adapter, step.command, params)
            success = result.get("ok", result.get("success")) is True
            if success or attempt >= policy.max_attempts:
                return StepResult(
                    name=step.name,
                    success=bool(success),
                    data=result.get("data"),
                    error=_extract_error_message(result) if not success else None,
                    attempts=attempt,
                )
            last_error = _extract_error_message(result)
        except Exception as exc:
            last_error = str(exc)
            if attempt >= policy.max_attempts:
                return StepResult(
                    name=step.name,
                    success=False,
                    error=last_error,
                    attempts=attempt,
                )

        delay = policy.delay * (policy.backoff ** (attempt - 1))
        logger.info(
            "步骤 '%s' 第 %d 次尝试失败，%.1f 秒后重试...",
            step.name,
            attempt,
            delay,
        )
        time.sleep(delay)

    return StepResult(name=step.name, success=False, error=last_error, attempts=policy.max_attempts)


def _extract_error_message(result: dict[str, Any]) -> str:
    err = result.get("error")
    if isinstance(err, dict):
        return str(err.get("message", str(err)))
    if isinstance(err, str):
        return err
    return "未知错误"


def run_workflow(
    workflow: WorkflowDef,
    executor: StepExecutor | None = None,
) -> WorkflowResult:
    if executor is None:
        executor = ClickAdapterExecutor()

    context = WorkflowContext()
    results: list[StepResult] = []
    overall_start = time.monotonic()
    all_ok = True

    for i, step in enumerate(workflow.steps):
        logger.info("执行步骤 %d/%d: %s", i + 1, len(workflow.steps), step.name)

        if not evaluate_condition(step.when, context):
            logger.info("步骤 '%s' 条件不满足，跳过", step.name)
            results.append(StepResult(name=step.name, success=True, skipped=True))
            continue

        step_start = time.monotonic()
        step_result = _run_step_with_retry(step, context, executor)
        step_result.elapsed_ms = (time.monotonic() - step_start) * 1000

        results.append(step_result)

        result_dict: dict[str, Any] = {
            "success": step_result.success,
            "data": step_result.data,
            "error": step_result.error,
        }
        context.prev_result = result_dict
        context.step_results[step.name] = result_dict

        if not step_result.success:
            all_ok = False
            logger.warning("步骤 '%s' 执行失败: %s", step.name, step_result.error)
            break

    elapsed_ms = (time.monotonic() - overall_start) * 1000

    return WorkflowResult(
        name=workflow.name,
        success=all_ok,
        steps=results,
        elapsed_ms=elapsed_ms,
    )
