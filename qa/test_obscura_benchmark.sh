#!/usr/bin/env bash
# Obscura Benchmark — Layer 3 (Chrome vs Obscura baseline)
# 输出 JSON 格式：{platform, timestamp, provider, scenarios, comparison}
# 退化检测：delta_pct > threshold（默认 200%）时返回失败
# CI：不加入常规 CI（仅 release/手动门禁）
# 用法：bash qa/test_obscura_benchmark.sh [--output=<file>] [--threshold=<pct>]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_FILE=""
THRESHOLD=200

for arg in "$@"; do
  case $arg in
    --output=*) OUTPUT_FILE="${arg#--output=}" ;;
    --threshold=*) THRESHOLD="${arg#--threshold=}" ;;
  esac
done

echo "=== Obscura Benchmark (Layer 3 — Chrome vs Obscura) ==="

TMPPY=$(mktemp /tmp/obscura_bench_XXXXXX.py)
trap 'rm -f "$TMPPY"' EXIT

cat > "$TMPPY" << 'PYEOF'
import sys
import json
import time
import platform as _platform
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

threshold_pct = float(sys.argv[1]) if len(sys.argv) > 1 else 200.0

_p = sys.platform
_m = _platform.machine()
_os = {"darwin": "darwin", "linux": "linux", "win32": "windows"}.get(_p, _p)
_arch = "arm64" if _m in ("arm64", "aarch64") else "x86_64" if _m in ("x86_64", "AMD64") else _m
platform_label = f"{_os}-{_arch}"

N = 10


def _measure(fn):
    times = []
    for _ in range(N):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return round(sum(times) / len(times), 3)


def _chrome_init():
    with patch("cliany_site.browser.cdp.CDPConnection"):
        from cliany_site.providers.chrome import ChromeProvider
        ChromeProvider()


def _chrome_snap():
    with patch("cliany_site.browser.cdp.CDPConnection"):
        from cliany_site.providers.chrome import ChromeProvider
        ChromeProvider().get_capability_snapshot()


def _make_cm():
    cm = MagicMock()
    cm.list_versions.return_value = ["0.1.0"]
    cm.get_binary_path.return_value = "/tmp/fake_obscura"
    cm.get_active_version.return_value = "0.1.0"
    cm._get_active_version.return_value = "0.1.0"
    return cm


def _obscura_init():
    from cliany_site.binary.platforms import PlatformTarget
    pt = PlatformTarget(
        os="darwin", arch="arm64", target_key="darwin-arm64",
        exe_suffix="", archive_ext=".tar.gz", is_supported=True,
    )
    with patch("cliany_site.providers.obscura.CacheManager", return_value=_make_cm()), \
         patch("cliany_site.providers.obscura.normalize_platform", return_value=pt):
        from cliany_site.providers.obscura import ObscuraProvider
        ObscuraProvider(source="managed")


def _obscura_snap():
    from cliany_site.binary.platforms import PlatformTarget
    pt = PlatformTarget(
        os="darwin", arch="arm64", target_key="darwin-arm64",
        exe_suffix="", archive_ext=".tar.gz", is_supported=True,
    )
    with patch("cliany_site.providers.obscura.CacheManager", return_value=_make_cm()), \
         patch("cliany_site.providers.obscura.normalize_platform", return_value=pt):
        from cliany_site.providers.obscura import ObscuraProvider
        ObscuraProvider(source="managed").get_capability_snapshot()


chrome_init_ms = _measure(_chrome_init)
chrome_snap_ms = _measure(_chrome_snap)
obscura_init_ms = _measure(_obscura_init)
obscura_snap_ms = _measure(_obscura_snap)

chrome_avg = round((chrome_init_ms + chrome_snap_ms) / 2, 3)
obscura_avg = round((obscura_init_ms + obscura_snap_ms) / 2, 3)
delta_pct = round(((obscura_avg - chrome_avg) / chrome_avg * 100) if chrome_avg > 0 else 0.0, 1)

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

result = {
    "platform": platform_label,
    "timestamp": timestamp,
    "provider": "obscura",
    "scenarios": [
        {"name": "chrome_provider_init", "duration_ms": chrome_init_ms, "success": True},
        {"name": "chrome_capability_snapshot", "duration_ms": chrome_snap_ms, "success": True},
        {"name": "obscura_provider_init", "duration_ms": obscura_init_ms, "success": True},
        {"name": "obscura_capability_snapshot", "duration_ms": obscura_snap_ms, "success": True},
    ],
    "comparison": {
        "chrome_baseline_ms": chrome_avg,
        "obscura_ms": obscura_avg,
        "delta_pct": delta_pct,
    },
}

print(json.dumps(result, indent=2))

if delta_pct > threshold_pct:
    print(
        json.dumps({"threshold_check": "FAIL", "delta_pct": delta_pct, "threshold": threshold_pct}),
        file=sys.stderr,
    )
    sys.exit(2)
else:
    print(
        json.dumps({"threshold_check": "PASS", "delta_pct": delta_pct, "threshold": threshold_pct}),
        file=sys.stderr,
    )
PYEOF

BENCH_EXIT=0
BENCH_OUT=$(cd "$REPO_ROOT" && uv run python "$TMPPY" "$THRESHOLD" 2>/tmp/obscura_bench_stderr.txt) || BENCH_EXIT=$?
THRESHOLD_LINE=$(cat /tmp/obscura_bench_stderr.txt 2>/dev/null || echo "")
rm -f /tmp/obscura_bench_stderr.txt

echo ""
echo "=== Benchmark JSON Result ==="
echo "$BENCH_OUT"
[ -n "$THRESHOLD_LINE" ] && echo "$THRESHOLD_LINE"

if [ -n "$OUTPUT_FILE" ]; then
  echo "$BENCH_OUT" > "$OUTPUT_FILE"
  echo "Benchmark saved to: $OUTPUT_FILE"
fi

if [ $BENCH_EXIT -eq 2 ]; then
  echo "BENCHMARK: FAIL — regression detected (delta_pct > ${THRESHOLD}%)"
  exit 1
elif [ $BENCH_EXIT -ne 0 ]; then
  echo "BENCHMARK: ERROR (exit=$BENCH_EXIT)"
  exit 1
else
  echo "BENCHMARK: PASS"
  exit 0
fi
