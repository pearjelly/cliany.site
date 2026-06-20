from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any, cast


def collect_diagnostic_context(
    failure: dict,
    recording: dict,
    network: list,
    console: list,
    axtree_snapshot: dict,
) -> dict:
    axtree_str = json.dumps(axtree_snapshot, ensure_ascii=False) if axtree_snapshot else ""
    return {
        "failure": failure,
        "recording": recording,
        "network_requests": network[:50],
        "console_entries": console[:50],
        "axtree_snapshot": axtree_str[:2000],
    }


def format_diagnostic_prompt(context: dict) -> str:
    failure = context.get("failure") or {}
    err_obj = failure.get("error") or {}
    code = err_obj.get("code", "unknown") if isinstance(err_obj, dict) else "unknown"
    message = err_obj.get("message", "") if isinstance(err_obj, dict) else str(err_obj)
    command = failure.get("command", "")

    network = context.get("network_requests") or []
    console = context.get("console_entries") or []
    axtree = context.get("axtree_snapshot") or ""

    network_str = json.dumps(network[:10], ensure_ascii=False) if network else "（无）"
    console_str = json.dumps(console[:10], ensure_ascii=False) if console else "（无）"

    return (
        "你是一个网页自动化诊断专家。以下命令执行失败，请分析根本原因并给出修复建议。\n\n"
        f"命令: {command}\n"
        f"错误码: {code}\n"
        f"错误信息: {message}\n\n"
        f"网络请求（前10条）:\n{network_str}\n\n"
        f"控制台日志（前10条）:\n{console_str}\n\n"
        f"AXTree 快照（前2000字符）:\n{axtree or '（未提供）'}\n\n"
        "请以 JSON 格式返回诊断结果，包含以下字段：\n"
        '- root_cause: str，根本原因描述\n'
        '- suggested_fixes: list[str]，修复建议列表\n'
        '- confidence: float，置信度（0.0-1.0）\n\n'
        '只返回 JSON，不要其他内容。示例：\n'
        '{"root_cause": "选择器过期", "suggested_fixes": ["重新探索页面"], "confidence": 0.85}'
    )


def run_diagnose(
    context: dict,
    llm_call_fn: Callable[[str, int], Any] | None,
    max_tokens: int = 500,
) -> dict:
    disabled = os.environ.get("CLIANY_DIAGNOSE_LLM", "1") == "0"

    if disabled or llm_call_fn is None:
        return {
            "root_cause": "diagnosis disabled",
            "suggested_fixes": [],
            "confidence": 0.0,
            "raw_context": context,
        }

    prompt = format_diagnostic_prompt(context)
    raw = llm_call_fn(prompt, max_tokens)

    parsed = _parse_llm_response(raw)
    if parsed is None:
        return {
            "root_cause": "LLM 响应解析失败",
            "suggested_fixes": [],
            "confidence": 0.0,
            "raw_context": context,
        }

    return {
        "root_cause": str(parsed.get("root_cause", "")),
        "suggested_fixes": list(parsed.get("suggested_fixes", [])),
        "confidence": float(parsed.get("confidence", 0.0)),
    }


def _parse_llm_response(raw: Any) -> dict | None:
    import re

    if isinstance(raw, dict):
        return raw

    text = raw.content if hasattr(raw, "content") else str(raw)

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

    try:
        return cast(dict[Any, Any], json.loads(text))
    except (json.JSONDecodeError, ValueError):
        return None


__all__ = ["collect_diagnostic_context", "format_diagnostic_prompt", "run_diagnose"]
