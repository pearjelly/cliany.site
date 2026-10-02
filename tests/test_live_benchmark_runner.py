from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "embodied" / "run_live_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_live_benchmark", SCRIPT)
assert SPEC and SPEC.loader
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def _case(case_id: str) -> dict:
    spec = json.loads((ROOT / "tests" / "embodied" / "explore_benchmark_cases.json").read_text())
    return next(case for case in spec["tasks"] if case["id"] == case_id)


def test_command_selection_requires_actions_and_replay_args():
    case = _case("form-result")
    metadata = {
        "commands": [
            {
                "name": "apply-and-read",
                "args": [{"name": "name"}, {"name": "color"}],
                "actions": [{"action_type": name} for name in case["required_actions"]],
            }
        ]
    }
    assert benchmark._select_command(metadata, case) == "apply-and-read"
    assert benchmark._command_summaries(metadata) == [{
        "name": "apply-and-read",
        "args": ["name", "color"],
        "actions": case["required_actions"],
    }]
    metadata["commands"][0]["actions"] = [{"action_type": "extract"}, {"action_type": "click"}]
    with pytest.raises(ValueError, match="expected one command"):
        benchmark._select_command(metadata, case)


def test_extract_evidence_must_be_successful_result():
    assert benchmark._extract_contents({"data": {"results": [
        {"command": "browser extract", "ok": True, "data": {"content": {"text": "Beta"}}}
    ]}}) == [{"text": "Beta"}]
    assert benchmark._extract_contents({"data": {"results": [
        {"command": "browser click", "ok": True}
    ]}}) == []


def test_benchmark_requires_returned_count_and_rows_not_just_correct_page():
    positive = _case("filter-catalog")["replays"][0]
    zero = _case("filter-catalog")["replays"][1]
    assert benchmark._matches_expected_extracts(
        [{"text": "1 matches"}, [{"name": "Gamma toolkit"}]], positive
    )
    assert not benchmark._matches_expected_extracts(
        [{"text": ""}, [{"name": "Gamma toolkit"}]], positive
    )
    assert benchmark._matches_expected_extracts([{"text": "0 matches"}, []], zero)
    assert not benchmark._matches_expected_extracts([{"text": ""}, []], zero)
    assert not benchmark._matches_expected_extracts([{"text": "0 matches"}], zero)


def test_benchmark_requires_returned_form_and_semantic_values():
    form = _case("form-result")["replays"][0]
    semantic = _case("semantic-reorder")["replays"][0]
    assert benchmark._matches_expected_extracts([{"text": "Grace:Red"}], form)
    assert not benchmark._matches_expected_extracts([{"text": "Ada:Blue"}], form)
    assert benchmark._matches_expected_extracts([{"text": "Beta"}], semantic)
    assert not benchmark._matches_expected_extracts([{"text": "Alpha"}], semantic)


def test_summary_counts_failures_by_task():
    trials = [
        {"case_id": "form-result", "ok": True},
        {"case_id": "form-result", "ok": False},
        {"case_id": "filter-catalog", "ok": False},
    ]
    assert benchmark._summarize_trials(trials, ["form-result", "filter-catalog"]) == {
        "form-result": {"successful": 1, "total": 2},
        "filter-catalog": {"successful": 0, "total": 1},
    }


def test_live_runner_requires_explicit_opt_in_and_rejects_offline(tmp_home, monkeypatch):
    report = tmp_home / "report.json"
    with pytest.raises(SystemExit, match="2"):
        benchmark.main(["--report", str(report)])
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    with pytest.raises(SystemExit, match="2"):
        benchmark.main(["--allow-live-llm", "--report", str(report)])
    assert not report.exists()


def test_benchmark_cli_uses_isolated_runtime_home(tmp_home):
    runtime_home = tmp_home / "runtime"
    process = subprocess.run(
        [sys.executable, str(benchmark.CLI_ENTRY), "--runtime-home", str(runtime_home), "--", "list", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["ok"] is True
    assert (runtime_home / "adapters").is_dir()
