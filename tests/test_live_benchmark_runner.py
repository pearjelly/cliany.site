from __future__ import annotations

import asyncio
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


def test_explore_quality_diagnostics_keep_structure_without_page_content():
    error = {
        "code": "E_EMPTY_RESULT",
        "message": "private page text",
        "details": {
            "repair_attempts": 1,
            "data_commands": [{
                "name": "private command name",
                "reason": "extract_quality_failed",
                "action_index": 4,
                "extract_mode": "text",
                "quality": {
                    "status": "empty",
                    "row_count": 1,
                    "field_blank_rows": {"url": [1], "private value\nsecret": [1]},
                    "issues": ["private page text"],
                },
            }],
        },
    }
    summary = benchmark._safe_explore_quality_diagnostics(error)
    assert summary == {
        "repair_attempts": 1,
        "failures": [{
            "reason": "extract_quality_failed",
            "action_index": 4,
            "extract_mode": "text",
            "quality_status": "empty",
            "row_count": 1,
            "blank_fields": ["url"],
        }],
    }
    assert "private" not in json.dumps(summary)


def test_explore_execution_failure_exposes_only_safe_error_shape():
    error = {
        "code": "E_EMPTY_RESULT",
        "details": {
            "repair_attempts": 1,
            "data_commands": [{
                "reason": "extraction_execution_failed",
                "action_index": 3,
                "extract_mode": "list",
                "error": {
                    "code": "E_PARSE_FAILED",
                    "message": "private page text",
                    "selector": "#private-selector",
                },
            }],
        },
    }
    summary = benchmark._safe_explore_quality_diagnostics(error)
    assert summary == {
        "repair_attempts": 1,
        "failures": [{
            "reason": "extraction_execution_failed",
            "action_index": 3,
            "extract_mode": "list",
            "error_code": "E_PARSE_FAILED",
            "selector_present": True,
        }],
    }
    assert "private" not in json.dumps(summary)


def test_unknown_contract_diagnostics_keep_only_enumerated_reason():
    error = {
        "code": "E_UNKNOWN",
        "message": "private model response",
        "details": {"reason": "command_partition_invalid", "phase": "completion", "raw": "private page"},
    }
    summary = benchmark._safe_explore_contract_diagnostics(error)
    assert summary == {"reason": "command_partition_invalid", "phase": "completion"}
    assert "private" not in json.dumps(summary)
    error["details"]["reason"] = "private invented reason"
    assert benchmark._safe_explore_contract_diagnostics(error) is None


def test_replay_quality_diagnostics_keep_modes_without_page_content():
    error = {
        "code": "E_EMPTY_RESULT",
        "message": "private page text",
        "details": {
            "status": "partial",
            "ok": False,
            "extracts": [
                {
                    "extract_mode": "text",
                    "status": "ok",
                    "step_index": 2,
                    "description": "private page text",
                },
                {
                    "extract_mode": "list",
                    "status": "empty",
                    "row_count": 0,
                    "step_index": 3,
                    "issues": ["private page text"],
                },
            ],
        },
    }
    summary = benchmark._safe_replay_quality_diagnostics(error)
    assert summary == {
        "status": "partial",
        "extracts": [
            {"mode": "text", "status": "ok", "step_index": 2},
            {"mode": "list", "status": "empty", "row_count": 0, "step_index": 3},
        ],
    }
    assert "private" not in json.dumps(summary)


def test_progress_timing_excludes_raw_stderr_content():
    stderr = b"\n".join([
        b'{"event":"explore_start","url":"private url","workflow":"private workflow","ts":100}',
        b'{"event":"explore_llm_start","step":0,"ts":101}',
        b'private page text',
        b'{"event":"explore_llm_done","step":0,"actions_count":2,"ts":104.5}',
        b'{"event":"explore_llm_start","step":1,"ts":106}',
    ])
    summary = benchmark._safe_explore_timing(stderr, ended_at=109)
    assert summary == {"llm_wait_seconds": [3.5], "inflight_llm_seconds": 3.0}
    assert "private" not in json.dumps(summary)


def test_progress_timing_summarizes_attempts_without_private_content():
    stderr = b"\n".join([
        b'{"event":"explore_llm_start","step":0,"ts":100}',
        b'{"event":"explore_llm_attempt_start","step":0,"attempt":1,"ts":100}',
        b'{"event":"explore_llm_attempt_done","step":0,"attempt":1,"ts":101.5,"elapsed_ms":1500,"outcome":"retry","backoff_ms":2000,"message":"private"}',
        b'{"event":"explore_llm_attempt_start","step":0,"attempt":2,"ts":103.5}',
        b'{"event":"explore_llm_attempt_done","step":0,"attempt":2,"ts":106,"elapsed_ms":2500,"outcome":"success","backoff_ms":0}',
        b'{"event":"explore_llm_done","step":0,"ts":106}',
    ])
    summary = benchmark._safe_explore_timing(stderr, ended_at=106)
    assert summary["attempt_seconds"] == [1.5, 2.5]
    assert summary["attempt_outcomes"] == ["retry", "success"]
    assert summary["retry_count"] == 1
    assert summary["scheduled_backoff_seconds"] == 2.0


def test_progress_timing_keeps_inflight_attempt_without_content():
    stderr = b"\n".join([
        b'{"event":"explore_llm_start","step":0,"ts":100}',
        b'{"event":"explore_llm_attempt_start","step":0,"attempt":1,"ts":101,"prompt":"private"}',
    ])
    summary = benchmark._safe_explore_timing(stderr, ended_at=109)
    assert summary["inflight_attempt_seconds"] == 8.0
    assert summary["inflight_llm_seconds"] == 9.0
    assert summary["retry_count"] == 0
    assert "private" not in json.dumps(summary)


def test_progress_timing_drops_unrecognized_attempt_outcome():
    stderr = b"\n".join([
        b'{"event":"explore_llm_attempt_start","step":0,"attempt":1,"ts":100}',
        b'{"event":"explore_llm_attempt_done","step":0,"attempt":1,"ts":101,'
        b'"elapsed_ms":1000,"outcome":"private response"}',
    ])
    summary = benchmark._safe_explore_timing(stderr, ended_at=101)
    assert summary["attempt_outcomes"] == ["unknown"]
    assert "private" not in json.dumps(summary)
    assert "private" not in json.dumps(summary)


def test_provider_context_uses_doctor_checks_without_leaking_endpoint():
    payload = {"data": {"checks": [
        {"name": "llm_provider", "details": {"provider": "openai"}},
        {"name": "openai_base_url", "details": {"base_url": "https://private.example/v1?key=secret"}},
    ]}}
    context = benchmark._safe_provider_context(payload)
    assert context == {"provider": "openai", "endpoint_type": "custom"}
    assert "private" not in json.dumps(context)
    assert "secret" not in json.dumps(context)

    payload["data"]["checks"][1]["details"]["base_url"] = None
    assert benchmark._safe_provider_context(payload) == {"provider": "openai", "endpoint_type": "default"}
    payload["data"]["checks"][0]["details"]["provider"] = "anthropic"
    assert benchmark._safe_provider_context(payload) == {"provider": "anthropic", "endpoint_type": "not_reported"}
    payload["data"]["checks"][0]["details"]["provider"] = "private-provider"
    assert benchmark._safe_provider_context(payload) == {"provider": "unknown", "endpoint_type": "unknown"}
    assert benchmark._safe_provider_context({}) == {"provider": "unknown", "endpoint_type": "unknown"}


@pytest.mark.asyncio
async def test_timeout_keeps_only_safe_inflight_timing(tmp_home, monkeypatch):
    class HangingProcess:
        def __init__(self):
            self.stopped = asyncio.Event()

        async def communicate(self):
            await self.stopped.wait()
            return b"private stdout", (
                f'{{"event":"explore_llm_start","step":0,"ts":{benchmark.time.time() - 1}}}\n'
                "private page text"
            ).encode()

        def kill(self):
            self.stopped.set()

    process = HangingProcess()

    async def launch(*_args, **_kwargs):
        return process

    monkeypatch.setattr(benchmark.asyncio, "create_subprocess_exec", launch)
    result, _ = await benchmark._run_cli(tmp_home, ["explore"], timeout=0.01)
    assert result["error"]["code"] == "BENCHMARK_TIMEOUT"
    assert result["benchmark_timing"]["llm_wait_seconds"] == []
    assert 1 <= result["benchmark_timing"]["inflight_llm_seconds"] < 2
    assert "private" not in json.dumps(result)


@pytest.mark.asyncio
async def test_failed_cli_report_drops_raw_quality_details(tmp_home, monkeypatch):
    class FailedProcess:
        returncode = 1

        async def communicate(self):
            return json.dumps({
                "ok": False,
                "error": {
                    "code": "E_EMPTY_RESULT",
                    "message": "private page text",
                    "details": {
                        "repair_attempts": 1,
                        "data_commands": [{
                            "reason": "extract_quality_failed",
                            "action_index": 2,
                            "extract_mode": "text",
                            "quality": {"status": "empty", "issues": ["private page text"]},
                        }],
                    },
                },
            }).encode(), b"private stderr"

    async def launch(*_args, **_kwargs):
        return FailedProcess()

    monkeypatch.setattr(benchmark.asyncio, "create_subprocess_exec", launch)
    result, _ = await benchmark._run_cli(tmp_home, ["explore"], timeout=1)
    assert result["error"] == {
        "code": "E_EMPTY_RESULT",
        "quality_diagnostics": {
            "repair_attempts": 1,
            "failures": [{
                "reason": "extract_quality_failed",
                "action_index": 2,
                "extract_mode": "text",
                "quality_status": "empty",
            }],
        },
    }
    assert "private" not in json.dumps(result)


@pytest.mark.asyncio
async def test_failed_replay_report_drops_raw_quality_details(tmp_home, monkeypatch):
    class FailedProcess:
        returncode = 1

        async def communicate(self):
            return json.dumps({
                "ok": False,
                "error": {
                    "code": "E_EMPTY_RESULT",
                    "message": "private page text",
                    "details": {
                        "status": "empty",
                        "extracts": [{
                            "extract_mode": "list",
                            "status": "empty",
                            "row_count": 0,
                            "step_index": 2,
                            "issues": ["private page text"],
                        }],
                    },
                },
            }).encode(), b"private stderr"

    async def launch(*_args, **_kwargs):
        return FailedProcess()

    monkeypatch.setattr(benchmark.asyncio, "create_subprocess_exec", launch)
    result, _ = await benchmark._run_cli(tmp_home, ["search-packages"], timeout=1)
    assert result["error"] == {
        "code": "E_EMPTY_RESULT",
        "quality_diagnostics": {
            "status": "empty",
            "extracts": [{"mode": "list", "status": "empty", "row_count": 0, "step_index": 2}],
        },
    }
    assert "private" not in json.dumps(result)


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


@pytest.mark.parametrize("rows", [
    ["Gamma toolkit", "Alpha toolkit"],
    ["Gamma toolkit", "Gamma toolkit"],
    [{"name": "Gamma toolkit"}, {"name": "Alpha toolkit"}],
    [{"name": "Gamma toolkit"}, {"name": "Gamma toolkit"}],
])
def test_benchmark_rejects_additional_and_duplicate_rows(rows):
    positive = _case("filter-catalog")["replays"][0]
    assert not benchmark._matches_expected_extracts([{"text": "1 matches"}, rows], positive)


@pytest.mark.parametrize("contents", [
    ["0 matches", [], ["Alpha toolkit"]],
    [{"summary": "0 matches", "rows": [], "other_rows": [{"name": "Alpha toolkit"}]}],
    ["1 matches", [{"name": "Gamma toolkit"}], []],
    ["1 matches", "Gamma toolkit", [{"name": "Alpha toolkit"}]],
    ["1 matches", "Gamma toolkit"],
])
def test_benchmark_rejects_missing_or_contradictory_row_collections(contents):
    replays = _case("filter-catalog")["replays"]
    expected = replays[1] if "0 matches" in json.dumps(contents) else replays[0]
    assert not benchmark._matches_expected_extracts(contents, expected)


@pytest.mark.parametrize("contents", [
    ["1 matches", ["Gamma toolkit"]],
    [{"text": "1 matches"}, [{"name": "Gamma toolkit", "code": "gamma"}]],
    [{"summary": "1 matches", "packages": [{"label": "Gamma toolkit"}]}],
    [[{"summary": "1 matches", "name": "Gamma toolkit"}]],
    [{"summary": "0 matches", "packages": []}],
])
def test_benchmark_accepts_exact_row_collections_with_flexible_field_names(contents):
    replays = _case("filter-catalog")["replays"]
    expected = replays[1] if "0 matches" in json.dumps(contents) else replays[0]
    assert benchmark._matches_expected_extracts(contents, expected)


def test_benchmark_checks_row_order_and_each_row():
    expected = {"expected_summary": "2 matches", "expected_rows": ["Alpha toolkit", "Gamma toolkit"]}
    assert benchmark._matches_expected_extracts(["2 matches", ["Alpha toolkit", "Gamma toolkit"]], expected)
    assert not benchmark._matches_expected_extracts(["2 matches", ["Gamma toolkit", "Alpha toolkit"]], expected)
    assert not benchmark._matches_expected_extracts(
        ["2 matches", [{"names": ["Alpha toolkit", "Gamma toolkit"]}, {"name": "Other toolkit"}]], expected
    )


@pytest.mark.parametrize("contents", [
    ["1 matches", "0 matches", ["Gamma toolkit"]],
    [{"summary": "1 matches", "stale_summary": "0 matches", "rows": ["Gamma toolkit"]}],
])
def test_benchmark_rejects_conflicting_summary_values(contents):
    positive = _case("filter-catalog")["replays"][0]
    assert not benchmark._matches_expected_extracts(contents, positive)


@pytest.mark.parametrize("case_id,correct,wrong", [
    ("form-result", "Grace:Red", "Ada:Blue"),
    ("semantic-reorder", "Beta", "Alpha"),
])
def test_benchmark_rejects_conflicting_scalar_extracts(case_id, correct, wrong):
    replay = _case(case_id)["replays"][0]
    assert not benchmark._matches_expected_extracts([{"text": correct}, {"text": wrong}], replay)


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


def test_failed_benchmark_start_reports_oracle_without_private_error(tmp_home, monkeypatch):
    report = tmp_home / "failed-report.json"
    monkeypatch.delenv("CLIANY_QA_OFFLINE", raising=False)
    monkeypatch.delenv("CLIANY_QA_FAKE_LLM_RESPONSES", raising=False)

    def fail(coroutine):
        coroutine.close()
        raise RuntimeError("private browser diagnostic")

    monkeypatch.setattr(benchmark.asyncio, "run", fail)
    assert benchmark.main(["--allow-live-llm", "--report", str(report)]) == 1
    payload = json.loads(report.read_text())
    assert payload["output_oracle"] == "per-row-v2"
    assert payload["error"] == "RuntimeError"
    assert payload["trials"] == []
    assert "private" not in json.dumps(payload)


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
