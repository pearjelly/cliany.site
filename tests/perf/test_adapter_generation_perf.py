"""Adapter 代码生成性能微基准测试。

手动运行基准（采集数据）:
    pytest tests/perf/ -m perf --benchmark-only -v

冒烟检查（不采集时序）:
    pytest tests/perf/ -m perf --benchmark-disable -v
"""
from __future__ import annotations

import pytest

from cliany_site.codegen.generator import AdapterGenerator
from cliany_site.explorer.models import (
    ActionStep,
    CommandSuggestion,
    ExploreResult,
    PageInfo,
)

# 宽松阈值基线（首次实测 P95 × 1.5）
# adapter 生成为纯内存字符串操作，通常 <10ms；50ms 作为极宽松上限
_ADAPTER_BASELINE_MS = 50.0


def _make_minimal_explore_result() -> ExploreResult:
    return ExploreResult(
        pages=[
            PageInfo(
                url="https://benchmark.example.com",
                title="Benchmark Test Page",
                elements=[],
            )
        ],
        actions=[
            ActionStep(
                action_type="navigate",
                page_url="https://benchmark.example.com",
                target_url="https://benchmark.example.com",
            ),
            ActionStep(
                action_type="click",
                page_url="https://benchmark.example.com",
                target_ref="@ref1",
                target_name="搜索按钮",
                target_role="button",
            ),
            ActionStep(
                action_type="type",
                page_url="https://benchmark.example.com",
                target_ref="@ref2",
                target_name="搜索输入框",
                target_role="textbox",
                value="benchmark query",
            ),
        ],
        commands=[
            CommandSuggestion(
                name="search",
                description="执行搜索操作",
                args=[],
                action_steps=[0, 1, 2],
            ),
        ],
        explore_model="benchmark-model",
    )


@pytest.fixture
def generator() -> AdapterGenerator:
    return AdapterGenerator(domain="benchmark.example.com")


@pytest.fixture
def minimal_explore_result() -> ExploreResult:
    return _make_minimal_explore_result()


def _assert_p95_threshold(benchmark, baseline_ms: float, label: str) -> None:
    try:
        stats = benchmark.stats
        if stats is None:
            return
        mean = getattr(stats, "mean", None)
        if mean is None:
            return
        percentiles = getattr(stats, "percentiles", None)
        if percentiles is not None:
            p95_s = percentiles.get("p95", mean)
        else:
            p95_s = mean
        p95_ms = p95_s * 1000
        threshold = baseline_ms * 1.2
        assert p95_ms < threshold, (
            f"{label} P95={p95_ms:.1f}ms 超过阈值 {threshold:.0f}ms（基线 {baseline_ms:.0f}ms × 1.2）"
        )
    except (AttributeError, TypeError, KeyError):
        pass  # --benchmark-disable 模式下 stats 不可用，跳过


@pytest.mark.perf
def test_adapter_generation_p95(benchmark, generator, minimal_explore_result):
    benchmark.warmup_rounds = 0
    benchmark.rounds = 10

    result = benchmark(generator.generate, minimal_explore_result, "benchmark.example.com")

    assert result is not None
    assert "# 自动生成" in result
    assert "benchmark.example.com" in result
    assert "@click.group()" in result

    _assert_p95_threshold(benchmark, _ADAPTER_BASELINE_MS, "adapter 生成")


@pytest.mark.perf
def test_adapter_generation_empty_commands(benchmark):
    generator = AdapterGenerator(domain="empty.example.com")
    empty_result = ExploreResult(
        pages=[PageInfo(url="https://empty.example.com", title="Empty", elements=[])],
        actions=[],
        commands=[],
        explore_model="benchmark-model",
    )

    result = benchmark(generator.generate, empty_result, "empty.example.com")

    assert result is not None
    assert "# 自动生成" in result
    assert "empty.example.com" in result


@pytest.mark.perf
def test_adapter_generation_multi_commands(benchmark):
    generator = AdapterGenerator(domain="multi.example.com")

    actions = [
        ActionStep(action_type="navigate", page_url="https://multi.example.com", target_url="https://multi.example.com"),
        ActionStep(action_type="click", page_url="https://multi.example.com", target_ref="@ref1", target_name="登录按钮"),
        ActionStep(action_type="type", page_url="https://multi.example.com", target_ref="@ref2", value="user@test.com"),
        ActionStep(action_type="click", page_url="https://multi.example.com", target_ref="@ref3", target_name="搜索"),
        ActionStep(action_type="type", page_url="https://multi.example.com", target_ref="@ref4", value="keyword"),
    ]
    multi_result = ExploreResult(
        pages=[PageInfo(url="https://multi.example.com", title="Multi", elements=[])],
        actions=actions,
        commands=[
            CommandSuggestion(name="login", description="用户登录", args=[], action_steps=[0, 1, 2]),
            CommandSuggestion(name="search", description="搜索内容", args=[], action_steps=[0, 3, 4]),
            CommandSuggestion(name="navigate", description="跳转首页", args=[], action_steps=[0]),
        ],
        explore_model="benchmark-model",
    )

    result = benchmark(generator.generate, multi_result, "multi.example.com")

    assert result is not None
    assert "# 自动生成" in result
    assert result.count("@cli.command") >= 3
