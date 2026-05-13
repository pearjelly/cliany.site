#!/usr/bin/env bash
# Obscura Smoke Tests — Layer 1 (offline/mock)
# 目标：验证 Obscura provider 核心路径，不依赖真实 Obscura 进程
# CI：mandatory（mock 模式，无外部依赖）
# 用法：bash qa/test_obscura_smoke.sh [--dry-run]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PASS=0
FAIL=0
DRY_RUN=false

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
  esac
done

_step() {
  local status="$1" step="$2" detail="${3:-}"
  printf '{"status":"%s","step":"%s","detail":"%s"}\n' "$status" "$step" "$detail"
}
pass() { _step "PASS" "$1" "${2:-}"; PASS=$((PASS+1)); }
fail() { _step "FAIL" "$1" "${2:-}"; FAIL=$((FAIL+1)); }
skip() { _step "SKIP" "$1" "${2:-binary not available}"; }

echo "=== Obscura Smoke Tests (Layer 1 — offline/mock) ==="

if [ "$DRY_RUN" = "true" ]; then
  _step "DRY_RUN" "package_importable"      "would run: python -c 'import cliany_site'"
  _step "DRY_RUN" "providers_importable"    "would run: python -c 'from providers.factory import get_provider'"
  _step "DRY_RUN" "capability_snapshot"     "would construct CapabilitySnapshot and call feature_gate"
  _step "DRY_RUN" "explore_gate_check"      "would invoke CLI explore with obscura mock provider"
  _step "DRY_RUN" "pytest_obscura_mock"     "would run pytest tests/test_obscura_provider.py ..."
  _step "DRY_RUN" "binary_version"          "would check binary if available at ~/.cliany-site/bin/"
  printf '{"summary":{"run":0,"pass":0,"fail":0,"mode":"dry-run"}}\n'
  echo "SMOKE: 0 run (dry-run)"
  exit 0
fi

# ── Check 1: package importable ──────────────────────────────────────────────
if (cd "$REPO_ROOT" && uv run python -c "import cliany_site" 2>/dev/null); then
  pass "package_importable"
else
  fail "package_importable" "cliany_site import failed"
fi

# ── Check 2: providers module importable ─────────────────────────────────────
if (cd "$REPO_ROOT" && uv run python -c "from cliany_site.providers.factory import get_provider" 2>/dev/null); then
  pass "providers_importable"
else
  fail "providers_importable" "providers.factory import failed"
fi

# ── Check 3: CapabilitySnapshot mock construction and feature_gate logic ──────
SNAP_EXIT=0
(cd "$REPO_ROOT" && uv run python - 2>/dev/null) <<'PYEOF' || SNAP_EXIT=$?
from cliany_site.providers.capabilities import CapabilitySnapshot, feature_gate

snap = CapabilitySnapshot(
    provider="obscura", version="0.1.0",
    supports_axtree=False, supports_navigation=True,
    supports_screenshot=True, supports_cookies=True,
    supports_network_events=True, supports_console_events=True,
)
assert feature_gate("explore", snap).allowed is False, "explore should be denied (no axtree)"
assert feature_gate("browser.navigate", snap).allowed is True, "navigate should be allowed"
assert feature_gate("browser.screenshot", snap).allowed is True, "screenshot should be allowed"
PYEOF
if [ $SNAP_EXIT -eq 0 ]; then
  pass "capability_snapshot"
else
  fail "capability_snapshot" "assertion failed exit=$SNAP_EXIT"
fi

# ── Check 4: explore gate returns E_MISSING_CAPABILITY for Obscura ────────────
GATE_EXIT=0
(cd "$REPO_ROOT" && CLIANY_BROWSER_PROVIDER=obscura uv run python - 2>/dev/null) <<'PYEOF' || GATE_EXIT=$?
import json, os
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from cliany_site.providers.capabilities import CapabilitySnapshot
from cliany_site.config import reset_config

reset_config()
snap = CapabilitySnapshot(
    provider="obscura", version="0.1.0",
    supports_axtree=False, supports_navigation=True,
    supports_screenshot=True, supports_cookies=True,
    supports_network_events=True, supports_console_events=True,
)
mock_prov = MagicMock()
mock_prov.get_capability_snapshot.return_value = snap

with patch("cliany_site.providers.factory.get_provider", return_value=mock_prov):
    from cliany_site.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "explore", "https://example.com", "test"], catch_exceptions=False)

data = json.loads(result.output)
assert data.get("error", {}).get("code") == "E_MISSING_CAPABILITY", \
    f"expected E_MISSING_CAPABILITY, got {data}"
PYEOF
if [ $GATE_EXIT -eq 0 ]; then
  pass "explore_gate_e_missing_capability"
else
  fail "explore_gate_e_missing_capability" "exit=$GATE_EXIT"
fi

# ── Check 5: mock-based pytest suite (provider + gate tests) ──────────────────
PYTEST_EXIT=0
PYTEST_OUT=$(cd "$REPO_ROOT" && uv run pytest -q \
  tests/test_obscura_provider.py \
  tests/test_obscura_explore_compat.py \
  tests/test_obscura_browser_commands.py \
  tests/test_obscura_session_recording.py \
  2>&1) || PYTEST_EXIT=$?
PYTEST_SUMMARY=$(echo "$PYTEST_OUT" | tail -1)
if [ $PYTEST_EXIT -eq 0 ]; then
  pass "pytest_obscura_mock" "$PYTEST_SUMMARY"
else
  fail "pytest_obscura_mock" "$PYTEST_SUMMARY"
fi

# ── Check 6: binary version (optional — skipped when binary absent) ───────────
OBSCURA_ROOT="${HOME}/.cliany-site/bin/obscura"
ACTIVE_FILE="${OBSCURA_ROOT}/active"
OBSCURA_BIN=""

if [ -f "$ACTIVE_FILE" ]; then
  ACTIVE_VERSION=$(cat "$ACTIVE_FILE" | tr -d '[:space:]')
  if [ -n "$ACTIVE_VERSION" ]; then
    # 考虑 Windows 环境下的可执行文件名（脚本运行于 bash）
    if [ -f "${OBSCURA_ROOT}/${ACTIVE_VERSION}/obscura.exe" ]; then
      OBSCURA_BIN="${OBSCURA_ROOT}/${ACTIVE_VERSION}/obscura.exe"
    elif [ -f "${OBSCURA_ROOT}/${ACTIVE_VERSION}/obscura" ]; then
      OBSCURA_BIN="${OBSCURA_ROOT}/${ACTIVE_VERSION}/obscura"
    fi
  fi
fi

if [ -n "$OBSCURA_BIN" ] && [ -x "$OBSCURA_BIN" ]; then
  VERSION_OUTPUT=$("$OBSCURA_BIN" --version 2>&1 || true)
  if [ -n "$VERSION_OUTPUT" ]; then
    pass "binary_version" "path: $OBSCURA_BIN"
  else
    fail "binary_version" "empty output from --version at $OBSCURA_BIN"
  fi
else
  skip "binary_version" "active binary not found or not executable (checked active version via $ACTIVE_FILE)"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
printf '{"summary":{"pass":%d,"fail":%d}}\n' "$PASS" "$FAIL"
echo "SMOKE: $PASS pass, $FAIL fail"
[ $FAIL -eq 0 ] && exit 0 || exit 1
