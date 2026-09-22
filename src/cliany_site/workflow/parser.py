from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from cliany_site.workflow.engine import _parse_condition
from cliany_site.workflow.models import RetryPolicy, StepDef, WorkflowDef

logger = logging.getLogger(__name__)

_REQUIRED_WORKFLOW_KEYS = {"name", "steps"}
_REQUIRED_STEP_KEYS = {"name", "adapter", "command"}


class WorkflowParseError(Exception):
    pass


def _parse_retry(raw: Any) -> RetryPolicy:
    if raw is None:
        return RetryPolicy()
    if not isinstance(raw, dict):
        raise WorkflowParseError(f"retry 必须是字典，实际类型: {type(raw).__name__}")
    return RetryPolicy(
        max_attempts=int(raw.get("max_attempts", 1)),
        delay=float(raw.get("delay", 1.0)),
        backoff=float(raw.get("backoff", 1.0)),
    )


def _parse_step(raw: Any, index: int) -> StepDef:
    if not isinstance(raw, dict):
        raise WorkflowParseError(f"步骤 {index} 必须是字典，实际类型: {type(raw).__name__}")

    missing = _REQUIRED_STEP_KEYS - raw.keys()
    if missing:
        raise WorkflowParseError(f"步骤 {index} 缺少必填字段: {', '.join(sorted(missing))}")

    params_raw = raw.get("params", {})
    if not isinstance(params_raw, dict):
        raise WorkflowParseError(f"步骤 {index} 的 params 必须是字典")

    params: dict[str, str] = {str(k): str(v) for k, v in params_raw.items()}
    when = str(raw.get("when", ""))
    try:
        _parse_condition(when)
    except ValueError as exc:
        raise WorkflowParseError(f"步骤 {index} 的 when 无效: {exc}") from exc

    return StepDef(
        name=str(raw["name"]),
        adapter=str(raw["adapter"]),
        command=str(raw["command"]),
        params=params,
        when=when,
        retry=_parse_retry(raw.get("retry")),
    )


def parse_workflow_yaml(text: str) -> WorkflowDef:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise WorkflowParseError(f"YAML 解析失败: {exc}") from exc

    if not isinstance(data, dict):
        raise WorkflowParseError("工作流文件顶层必须是字典")

    missing = _REQUIRED_WORKFLOW_KEYS - data.keys()
    if missing:
        raise WorkflowParseError(f"工作流缺少必填字段: {', '.join(sorted(missing))}")

    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list) or len(raw_steps) == 0:
        raise WorkflowParseError("steps 必须是非空列表")

    steps = [_parse_step(s, i) for i, s in enumerate(raw_steps)]

    return WorkflowDef(
        name=str(data["name"]),
        steps=steps,
        description=str(data.get("description", "")),
    )


def load_workflow_file(path: str | Path) -> WorkflowDef:
    p = Path(path)
    if not p.exists():
        raise WorkflowParseError(f"工作流文件不存在: {p}")
    if p.suffix.lower() not in (".yaml", ".yml"):
        raise WorkflowParseError(f"工作流文件必须是 .yaml 或 .yml 格式: {p}")
    text = p.read_text(encoding="utf-8")
    return parse_workflow_yaml(text)
