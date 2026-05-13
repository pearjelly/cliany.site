import json
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
QA_DIR = REPO_ROOT / "qa"
DOCS_DIR = REPO_ROOT / "docs" / "walkthroughs"


class TestQAScriptsExist:
    def test_smoke_script_exists(self):
        assert (QA_DIR / "test_obscura_smoke.sh").exists()

    def test_compat_script_exists(self):
        assert (QA_DIR / "test_obscura_compat.sh").exists()

    def test_benchmark_script_exists(self):
        assert (QA_DIR / "test_obscura_benchmark.sh").exists()

    def test_smoke_supports_dry_run_flag(self):
        content = (QA_DIR / "test_obscura_smoke.sh").read_text()
        assert "--dry-run" in content

    def test_benchmark_outputs_json(self):
        content = (QA_DIR / "test_obscura_benchmark.sh").read_text()
        assert "json" in content.lower()

    def test_benchmark_not_in_run_all(self):
        run_all = (QA_DIR / "run_all.sh").read_text()
        assert "test_obscura_benchmark" not in run_all


class TestStrategyDocExists:
    def test_strategy_doc_exists(self):
        assert (DOCS_DIR / "obscura-test-strategy.md").exists()

    def test_strategy_doc_covers_three_layers(self):
        content = (DOCS_DIR / "obscura-test-strategy.md").read_text()
        assert "smoke" in content.lower()
        assert "compat" in content.lower()
        assert "benchmark" in content.lower()


VALID_BENCHMARK_RESULT = {
    "platform": "darwin-arm64",
    "timestamp": "2026-01-01T00:00:00Z",
    "provider": "obscura",
    "scenarios": [
        {"name": "chrome_provider_init", "duration_ms": 100.0, "success": True},
        {"name": "obscura_provider_init", "duration_ms": 90.0, "success": True},
    ],
    "comparison": {
        "chrome_baseline_ms": 100.0,
        "obscura_ms": 90.0,
        "delta_pct": -10.0,
    },
}


def _validate_benchmark_schema(data: dict) -> list[str]:
    errors = []
    required_top = ["platform", "timestamp", "provider", "scenarios", "comparison"]
    for field in required_top:
        if field not in data:
            errors.append(f"missing top-level field: {field}")

    scenarios = data.get("scenarios")
    if scenarios is not None:
        if not isinstance(scenarios, list) or len(scenarios) == 0:
            errors.append("scenarios must be a non-empty list")
        else:
            for i, s in enumerate(scenarios):
                for f in ["name", "duration_ms", "success"]:
                    if f not in s:
                        errors.append(f"scenarios[{i}] missing field: {f}")

    comparison = data.get("comparison")
    if comparison is not None:
        if not isinstance(comparison, dict):
            errors.append("comparison must be a dict")
        else:
            for f in ["chrome_baseline_ms", "obscura_ms", "delta_pct"]:
                if f not in comparison:
                    errors.append(f"comparison missing field: {f}")

    return errors


class TestBenchmarkSchemaValidator:
    def test_valid_schema_passes(self):
        errors = _validate_benchmark_schema(VALID_BENCHMARK_RESULT)
        assert errors == []

    def test_missing_timestamp_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK_RESULT.items() if k != "timestamp"}
        errors = _validate_benchmark_schema(data)
        assert any("timestamp" in e for e in errors)

    def test_missing_platform_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK_RESULT.items() if k != "platform"}
        errors = _validate_benchmark_schema(data)
        assert any("platform" in e for e in errors)

    def test_missing_provider_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK_RESULT.items() if k != "provider"}
        errors = _validate_benchmark_schema(data)
        assert any("provider" in e for e in errors)

    def test_missing_scenarios_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK_RESULT.items() if k != "scenarios"}
        errors = _validate_benchmark_schema(data)
        assert any("scenarios" in e for e in errors)

    def test_missing_comparison_fails(self):
        data = {k: v for k, v in VALID_BENCHMARK_RESULT.items() if k != "comparison"}
        errors = _validate_benchmark_schema(data)
        assert any("comparison" in e for e in errors)

    def test_missing_comparison_delta_pct_fails(self):
        import copy
        data = copy.deepcopy(VALID_BENCHMARK_RESULT)
        del data["comparison"]["delta_pct"]
        errors = _validate_benchmark_schema(data)
        assert any("delta_pct" in e for e in errors)

    def test_missing_chrome_baseline_fails(self):
        import copy
        data = copy.deepcopy(VALID_BENCHMARK_RESULT)
        del data["comparison"]["chrome_baseline_ms"]
        errors = _validate_benchmark_schema(data)
        assert any("chrome_baseline_ms" in e for e in errors)

    def test_missing_obscura_ms_fails(self):
        import copy
        data = copy.deepcopy(VALID_BENCHMARK_RESULT)
        del data["comparison"]["obscura_ms"]
        errors = _validate_benchmark_schema(data)
        assert any("obscura_ms" in e for e in errors)

    def test_empty_scenarios_fails(self):
        import copy
        data = copy.deepcopy(VALID_BENCHMARK_RESULT)
        data["scenarios"] = []
        errors = _validate_benchmark_schema(data)
        assert any("scenarios" in e for e in errors)

    def test_scenario_missing_name_fails(self):
        import copy
        data = copy.deepcopy(VALID_BENCHMARK_RESULT)
        data["scenarios"][0] = {"duration_ms": 50.0, "success": True}
        errors = _validate_benchmark_schema(data)
        assert any("name" in e for e in errors)

    def test_json_serializable(self):
        serialized = json.dumps(VALID_BENCHMARK_RESULT)
        roundtripped = json.loads(serialized)
        assert roundtripped == VALID_BENCHMARK_RESULT
