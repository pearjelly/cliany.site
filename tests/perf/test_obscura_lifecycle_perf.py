"""Obscura 平台检测生命周期性能微基准测试。

仅测纯函数（无 I/O、无网络请求、无 ChromeDriver 依赖）。

手动运行基准（采集数据）:
    pytest tests/perf/ -m perf --benchmark-only -v

冒烟检查（不采集时序）:
    pytest tests/perf/ -m perf --benchmark-disable -v
"""
from __future__ import annotations

import platform
import sys

import pytest

from cliany_site.binary.platforms import UnsupportedPlatformError, normalize_platform

# 宽松阈值基线（首次实测 mean × 1.5）
# normalize_platform 为纯内存计算，通常 <0.1ms；5ms 作为极宽松上限
_PLATFORM_BASELINE_MS = 5.0


def _safe_p95_ms(benchmark) -> float | None:
    try:
        stats = benchmark.stats
        if stats is None:
            return None
        mean = getattr(stats, "mean", None)
        if mean is None:
            return None
        percentiles = getattr(stats, "percentiles", None)
        p95_s = percentiles.get("p95", mean) if percentiles is not None else mean
        return p95_s * 1000
    except (AttributeError, TypeError, KeyError):
        return None  # --benchmark-disable 模式下 stats 不可用，跳过


@pytest.mark.perf
def test_normalize_platform_darwin_arm64(benchmark):
    result = benchmark(normalize_platform, "darwin", "arm64")

    assert result.os == "darwin"
    assert result.arch == "arm64"
    assert result.target_key == "darwin-arm64"
    assert result.is_supported is True
    assert result.exe_suffix == ""
    assert result.archive_ext == ".tar.gz"


@pytest.mark.perf
def test_normalize_platform_linux_x86_64(benchmark):
    result = benchmark(normalize_platform, "linux", "x86_64")

    assert result.target_key == "linux-x86_64"
    assert result.is_supported is True


@pytest.mark.perf
def test_normalize_platform_darwin_x86_64(benchmark):
    result = benchmark(normalize_platform, "darwin", "x86_64")

    assert result.target_key == "darwin-x86_64"
    assert result.is_supported is True


@pytest.mark.perf
def test_normalize_platform_windows_amd64(benchmark):
    result = benchmark(normalize_platform, "win32", "AMD64")

    assert result.target_key == "windows-x86_64"
    assert result.exe_suffix == ".exe"
    assert result.archive_ext == ".zip"


@pytest.mark.perf
def test_normalize_platform_unsupported_raises(benchmark):
    with pytest.raises(UnsupportedPlatformError):
        benchmark(normalize_platform, "freebsd", "x86_64")


@pytest.mark.perf
def test_normalize_platform_current_host_p95(benchmark):
    current_platform = sys.platform
    current_machine = platform.machine()

    try:
        normalize_platform(current_platform, current_machine)
    except UnsupportedPlatformError:
        pytest.skip(f"当前平台 {current_platform}-{current_machine} 不受支持")

    result = benchmark(normalize_platform, current_platform, current_machine)

    assert result is not None
    assert result.is_supported is True

    p95_ms = _safe_p95_ms(benchmark)
    if p95_ms is not None:
        threshold = _PLATFORM_BASELINE_MS * 1.2
        assert p95_ms < threshold, (
            f"平台检测 P95={p95_ms:.3f}ms 超过阈值 {threshold:.1f}ms（基线 {_PLATFORM_BASELINE_MS:.0f}ms × 1.2）"
        )
