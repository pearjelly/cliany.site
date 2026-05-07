"""T23: 验证生成的 adapter 代码包含 diagnose_if_enabled 调用。"""
from __future__ import annotations

import tempfile
import pathlib
from unittest import mock

import pytest

from cliany_site.codegen.generator import AdapterGenerator
from cliany_site.explorer.models import CommandSuggestion, ExploreResult


def _make_result() -> ExploreResult:
    return ExploreResult(
        commands=[CommandSuggestion(name="search", description="搜索", args=[], action_steps=[])],
    )


def test_template_calls_diagnose(tmp_path):
    """生成代码应包含 diagnose_if_enabled 调用。"""
    gen = AdapterGenerator()
    result = _make_result()
    
    code = gen.generate(result, "https://test.com")
    assert "diagnose_if_enabled" in code, "生成代码应包含 diagnose_if_enabled 调用"


def test_generated_code_has_no_llm_import(tmp_path):
    """生成代码不应直接 import cliany_site.llm 或 cliany_site.explorer。"""
    gen = AdapterGenerator()
    result = _make_result()
    
    code = gen.generate(result, "https://test.com")
    assert "from cliany_site.llm" not in code, "生成代码不应直接调用 LLM"
    assert "from cliany_site.explorer" not in code, "生成代码不应 import explorer"


def test_diagnose_import_in_generated_header(tmp_path):
    """生成代码头部的 runtime_helpers 导入应包含 diagnose_if_enabled。"""
    gen = AdapterGenerator()
    result = _make_result()
    
    code = gen.generate(result, "https://test.com")
    assert "diagnose_if_enabled" in code
    # 确认从 runtime_helpers 导入
    assert "runtime_helpers" in code or "from cliany_site.codegen.runtime_helpers import" in code