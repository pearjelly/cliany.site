import copy
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_REQUIRED_TOP = ["platform", "timestamp", "provider", "scenarios", "comparison"]
_REQUIRED_SCENARIO = ["name", "duration_ms", "success"]
_REQUIRED_COMPARISON = ["chrome_baseline_ms", "obscura_ms", "delta_pct"]

_DEGRADATION_THRESHOLD_PCT = 200.0


def validate_benchmark_schema(data: dict) -> list[str]:
    errors = []
    for field in _REQUIRED_TOP:
        if field not in data:
            errors.append(f"missing top-level field: {field}")

    scenarios = data.get("scenarios")
    if scenarios is not None:
        if not isinstance(scenarios, list):
            errors.append("scenarios must be a list")
        elif len(scenarios) == 0:
            errors.append("scenarios must not be empty")
        else:
            for i, s in enumerate(scenarios):
                for f in _REQUIRED_SCENARIO:
                    if f not in s:
                        errors.append(f"scenarios[{i}] missing field: {f}")

    comparison = data.get("comparison")
    if comparison is not None:
        if not isinstance(comparison, dict):
            errors.append("comparison must be a dict")
        else:
            for f in _REQUIRED_COMPARISON:
                if f not in comparison:
                    errors.append(f"comparison missing field: {f}")

    return errors


def check_threshold(data: dict, threshold_pct: float = _DEGRADATION_THRESHOLD_PCT) -> tuple[bool, str]:
    comparison = data.get("comparison", {})
    delta_pct = comparison.get("delta_pct")
    if delta_pct is None:
        return False, "comparison.delta_pct missing"
    if delta_pct > threshold_pct:
        return False, f"regression: delta_pct={delta_pct:.1f}% > threshold {threshold_pct:.1f}%"
    return True, f"ok: delta_pct={delta_pct:.1f}%"


def parse_benchmark_json(text: str) -> dict:
    data = json.loads(text)
    errors = validate_benchmark_schema(data)
    if errors:
        raise ValueError(f"benchmark schema errors: {errors}")
    return data


def load_benchmark_file(path: Path) -> dict:
    return parse_benchmark_json(path.read_text())


def build_platform_label() -> str:
    p = sys.platform
    m = platform.machine()
    os_name = {"darwin": "darwin", "linux": "linux", "win32": "windows"}.get(p, p)
    arch = "arm64" if m in ("arm64", "aarch64") else "x86_64" if m in ("x86_64", "AMD64") else m
    return f"{os_name}-{arch}"


VALID_BENCHMARK = {
    "platform": "darwin-arm64",
    "timestamp": "2026-01-01T00:00:00Z",
    "provider": "obscura",
    "scenarios": [
        {"name": "chrome_provider_init", "duration_ms": 50.0, "success": True},
        {"name": "obscura_provider_init", "duration_ms": 45.0, "success": True},
    ],
    "comparison": {
        "chrome_baseline_ms": 50.0,
        "obscura_ms": 45.0,
        "delta_pct": -10.0,
    },
}

DEGRADED_BENCHMARK = {
    **VALID_BENCHMARK,
    "comparison": {
        "chrome_baseline_ms": 100.0,
        "obscura_ms": 350.0,
        "delta_pct": 250.0,
    },
}


class TestSchemaValidation:
    def test_valid_schema_passes(self):
        assert validate_benchmark_schema(VALID_BENCHMARK) == []

    def test_missing_platform_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK.items() if k != "platform"}
        errors = validate_benchmark_schema(data)
        assert any("platform" in e for e in errors)

    def test_missing_timestamp_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK.items() if k != "timestamp"}
        errors = validate_benchmark_schema(data)
        assert any("timestamp" in e for e in errors)

    def test_missing_provider_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK.items() if k != "provider"}
        errors = validate_benchmark_schema(data)
        assert any("provider" in e for e in errors)

    def test_missing_scenarios_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK.items() if k != "scenarios"}
        errors = validate_benchmark_schema(data)
        assert any("scenarios" in e for e in errors)

    def test_missing_comparison_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK.items() if k != "comparison"}
        errors = validate_benchmark_schema(data)
        assert any("comparison" in e for e in errors)

    def test_empty_scenarios_fails(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        data["scenarios"] = []
        errors = validate_benchmark_schema(data)
        assert any("scenarios" in e for e in errors)

    def test_scenario_missing_name_fails(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        data["scenarios"][0] = {"duration_ms": 50, "success": True}
        errors = validate_benchmark_schema(data)
        assert any("name" in e for e in errors)

    def test_scenario_missing_duration_ms_fails(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        data["scenarios"][0] = {"name": "x", "success": True}
        errors = validate_benchmark_schema(data)
        assert any("duration_ms" in e for e in errors)

    def test_scenario_missing_success_fails(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        data["scenarios"][0] = {"name": "x", "duration_ms": 50}
        errors = validate_benchmark_schema(data)
        assert any("success" in e for e in errors)

    def test_comparison_missing_delta_pct_fails(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        del data["comparison"]["delta_pct"]
        errors = validate_benchmark_schema(data)
        assert any("delta_pct" in e for e in errors)

    def test_comparison_missing_chrome_baseline_fails(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        del data["comparison"]["chrome_baseline_ms"]
        errors = validate_benchmark_schema(data)
        assert any("chrome_baseline_ms" in e for e in errors)

    def test_comparison_missing_obscura_ms_fails(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        del data["comparison"]["obscura_ms"]
        errors = validate_benchmark_schema(data)
        assert any("obscura_ms" in e for e in errors)

    def test_all_missing_fields_reported(self):
        errors = validate_benchmark_schema({})
        assert len(errors) == len(_REQUIRED_TOP)


class TestThresholdChecker:
    def test_negative_delta_passes(self):
        passed, reason = check_threshold(VALID_BENCHMARK)
        assert passed is True

    def test_zero_delta_passes(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        data["comparison"]["delta_pct"] = 0.0
        passed, _ = check_threshold(data)
        assert passed is True

    def test_below_threshold_passes(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        data["comparison"]["delta_pct"] = 199.9
        passed, _ = check_threshold(data)
        assert passed is True

    def test_at_threshold_passes(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        data["comparison"]["delta_pct"] = 200.0
        passed, _ = check_threshold(data)
        assert passed is True

    def test_above_threshold_fails(self):
        passed, reason = check_threshold(DEGRADED_BENCHMARK)
        assert passed is False

    def test_degraded_reason_mentions_regression(self):
        _, reason = check_threshold(DEGRADED_BENCHMARK)
        assert "regression" in reason or "delta_pct" in reason

    def test_custom_threshold_lower_fails(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        data["comparison"]["delta_pct"] = 50.0
        passed, _ = check_threshold(data, threshold_pct=30.0)
        assert passed is False

    def test_custom_threshold_higher_passes(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        data["comparison"]["delta_pct"] = 50.0
        passed, _ = check_threshold(data, threshold_pct=100.0)
        assert passed is True

    def test_missing_delta_pct_fails(self):
        data = copy.deepcopy(VALID_BENCHMARK)
        del data["comparison"]["delta_pct"]
        passed, reason = check_threshold(data)
        assert passed is False
        assert "delta_pct" in reason


class TestParseLoad:
    def test_parse_valid_json(self):
        data = parse_benchmark_json(json.dumps(VALID_BENCHMARK))
        assert data["provider"] == "obscura"

    def test_parse_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_benchmark_json("{invalid json}")

    def test_parse_invalid_schema_raises_value_error(self):
        bad = {k: v for k, v in VALID_BENCHMARK.items() if k != "platform"}
        with pytest.raises(ValueError, match="platform"):
            parse_benchmark_json(json.dumps(bad))

    def test_load_file(self, tmp_path):
        path = tmp_path / "bench.json"
        path.write_text(json.dumps(VALID_BENCHMARK))
        data = load_benchmark_file(path)
        assert data["platform"] == "darwin-arm64"

    def test_load_file_bad_schema_raises(self, tmp_path):
        bad = {k: v for k, v in VALID_BENCHMARK.items() if k != "scenarios"}
        path = tmp_path / "bad_bench.json"
        path.write_text(json.dumps(bad))
        with pytest.raises(ValueError):
            load_benchmark_file(path)

    def test_roundtrip_json(self):
        text = json.dumps(VALID_BENCHMARK)
        data = parse_benchmark_json(text)
        assert json.loads(json.dumps(data)) == VALID_BENCHMARK


class TestPlatformLabel:
    def test_returns_string(self):
        label = build_platform_label()
        assert isinstance(label, str)

    def test_has_dash_separator(self):
        label = build_platform_label()
        assert "-" in label

    def test_known_os_prefix(self):
        label = build_platform_label()
        os_part = label.split("-")[0]
        assert os_part in ("darwin", "linux", "windows", sys.platform)
