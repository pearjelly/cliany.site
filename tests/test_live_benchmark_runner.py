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
    assert benchmark._has_extract_result({"data": {"results": [
        {"command": "browser extract", "ok": True, "data": {"content": {"text": "Beta"}}}
    ]}})
    assert not benchmark._has_extract_result({"data": {"results": [
        {"command": "browser click", "ok": True}
    ]}})


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
