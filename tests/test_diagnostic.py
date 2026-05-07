from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

import pytest

from cliany_site.diagnostic import (
    collect_diagnostic_context,
    format_diagnostic_prompt,
    run_diagnose,
)


FAILURE_ENVELOPE = {
    "ok": False,
    "command": "search",
    "error": {"code": "E_SELECTOR_NOT_FOUND", "message": "element not found"},
}


def test_run_diagnose_returns_structure():
    mock_fn = MagicMock(
        return_value='{"root_cause": "selector expired", "suggested_fixes": ["re-explore"], "confidence": 0.9}'
    )
    ctx = collect_diagnostic_context(FAILURE_ENVELOPE, {}, [], [], {})
    result = run_diagnose(ctx, llm_call_fn=mock_fn)
    assert result["root_cause"] == "selector expired"
    assert result["suggested_fixes"] == ["re-explore"]
    assert result["confidence"] == pytest.approx(0.9)


def test_disabled_skips_llm(monkeypatch):
    monkeypatch.setenv("CLIANY_DIAGNOSE_LLM", "0")
    mock_fn = MagicMock()
    ctx = collect_diagnostic_context(FAILURE_ENVELOPE, {}, [], [], {})
    result = run_diagnose(ctx, llm_call_fn=mock_fn)
    assert mock_fn.call_count == 0
    assert result["root_cause"] == "diagnosis disabled"


def test_max_tokens_enforced():
    captured = {}

    def fake_llm(prompt: str, max_tokens: int):
        captured["max_tokens"] = max_tokens
        return '{"root_cause": "test", "suggested_fixes": [], "confidence": 0.5}'

    ctx = collect_diagnostic_context(FAILURE_ENVELOPE, {}, [], [], {})
    run_diagnose(ctx, llm_call_fn=fake_llm, max_tokens=300)
    assert captured["max_tokens"] == 300


def test_collect_context_truncates_network():
    network = [{"url": f"http://example.com/{i}"} for i in range(100)]
    ctx = collect_diagnostic_context(FAILURE_ENVELOPE, {}, network, [], {})
    assert len(ctx["network_requests"]) == 50


def test_format_prompt_contains_failure():
    ctx = collect_diagnostic_context(FAILURE_ENVELOPE, {}, [], [], {})
    prompt = format_diagnostic_prompt(ctx)
    assert "search" in prompt
    assert "E_SELECTOR_NOT_FOUND" in prompt
    assert "element not found" in prompt


def test_null_llm_fn_returns_disabled():
    ctx = collect_diagnostic_context(FAILURE_ENVELOPE, {}, [], [], {})
    result = run_diagnose(ctx, llm_call_fn=None)
    assert result["root_cause"] == "diagnosis disabled"
    assert result["suggested_fixes"] == []
    assert result["confidence"] == 0.0


def test_collect_context_truncates_console():
    console = [{"message": f"log {i}"} for i in range(80)]
    ctx = collect_diagnostic_context(FAILURE_ENVELOPE, {}, [], console, {})
    assert len(ctx["console_entries"]) == 50


def test_collect_context_truncates_axtree():
    big_tree = {"nodes": ["x" * 100 for _ in range(100)]}
    ctx = collect_diagnostic_context(FAILURE_ENVELOPE, {}, [], [], big_tree)
    assert len(ctx["axtree_snapshot"]) <= 2000


def test_run_diagnose_dict_response():
    mock_fn = MagicMock(
        return_value={"root_cause": "dict response", "suggested_fixes": ["fix-a"], "confidence": 0.7}
    )
    ctx = collect_diagnostic_context(FAILURE_ENVELOPE, {}, [], [], {})
    result = run_diagnose(ctx, llm_call_fn=mock_fn)
    assert result["root_cause"] == "dict response"
    assert result["confidence"] == pytest.approx(0.7)
