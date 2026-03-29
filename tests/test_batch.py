from __future__ import annotations

import json

import pytest

from cliany_site.workflow.batch import (
    BatchDataError,
    BatchItemResult,
    BatchResult,
    load_batch_data,
    run_batch,
)
from cliany_site.workflow.engine import StepExecutor
from cliany_site.workflow.models import StepDef

# ── load_batch_data ──────────────────────────────────────


class TestLoadBatchDataCSV:
    def test_valid_csv(self, tmp_path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("name,age\nalice,30\nbob,25\n")
        rows = load_batch_data(f)
        assert len(rows) == 2
        assert rows[0] == {"name": "alice", "age": "30"}
        assert rows[1] == {"name": "bob", "age": "25"}

    def test_empty_csv(self, tmp_path) -> None:
        f = tmp_path / "empty.csv"
        f.write_text("name,age\n")
        with pytest.raises(BatchDataError, match="无数据行"):
            load_batch_data(f)

    def test_csv_with_special_chars(self, tmp_path) -> None:
        f = tmp_path / "special.csv"
        f.write_text('name,desc\n"alice","hello, world"\n')
        rows = load_batch_data(f)
        assert rows[0]["desc"] == "hello, world"


class TestLoadBatchDataJSON:
    def test_valid_json(self, tmp_path) -> None:
        f = tmp_path / "data.json"
        f.write_text('[{"name": "alice"}, {"name": "bob"}]')
        rows = load_batch_data(f)
        assert len(rows) == 2
        assert rows[0] == {"name": "alice"}

    def test_empty_json_array(self, tmp_path) -> None:
        f = tmp_path / "empty.json"
        f.write_text("[]")
        with pytest.raises(BatchDataError, match="数组为空"):
            load_batch_data(f)

    def test_json_not_array(self, tmp_path) -> None:
        f = tmp_path / "obj.json"
        f.write_text('{"key": "val"}')
        with pytest.raises(BatchDataError, match="顶层.*数组"):
            load_batch_data(f)

    def test_json_item_not_object(self, tmp_path) -> None:
        f = tmp_path / "bad.json"
        f.write_text('["string_item"]')
        with pytest.raises(BatchDataError, match="第 0 项.*对象"):
            load_batch_data(f)

    def test_invalid_json(self, tmp_path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("{invalid")
        with pytest.raises(BatchDataError, match="JSON 读取失败"):
            load_batch_data(f)

    def test_json_values_converted_to_str(self, tmp_path) -> None:
        f = tmp_path / "nums.json"
        f.write_text('[{"count": 42, "active": true}]')
        rows = load_batch_data(f)
        assert rows[0] == {"count": "42", "active": "True"}


class TestLoadBatchDataErrors:
    def test_file_not_found(self, tmp_path) -> None:
        with pytest.raises(BatchDataError, match="不存在"):
            load_batch_data(tmp_path / "missing.csv")

    def test_unsupported_format(self, tmp_path) -> None:
        f = tmp_path / "data.xml"
        f.write_text("<data/>")
        with pytest.raises(BatchDataError, match="不支持"):
            load_batch_data(f)


# ── BatchResult ──────────────────────────────────────────


class TestBatchResult:
    def test_to_dict(self) -> None:
        r = BatchResult(
            total=2,
            succeeded=1,
            failed=1,
            results=[
                BatchItemResult(index=0, params={"q": "a"}, success=True, elapsed_ms=100.0),
                BatchItemResult(index=1, params={"q": "b"}, success=False, error="boom", elapsed_ms=50.0),
            ],
            elapsed_ms=200.0,
        )
        d = r.to_dict()
        assert d["total"] == 2
        assert d["succeeded"] == 1
        assert d["failed"] == 1
        assert len(d["results"]) == 2
        assert d["results"][1]["error"] == "boom"


# ── MockExecutor ─────────────────────────────────────────


class MockBatchExecutor(StepExecutor):
    def __init__(self, results: list[dict] | None = None) -> None:
        self._results = list(results) if results else []
        self.call_log: list[tuple[str, str, dict]] = []

    def execute_step(self, adapter: str, command: str, params: dict[str, str]) -> dict:
        self.call_log.append((adapter, command, dict(params)))
        if self._results:
            return self._results.pop(0)
        return {"success": True, "data": {"echo": params}, "error": None}


# ── run_batch ────────────────────────────────────────────


class TestRunBatch:
    def test_sequential_all_success(self) -> None:
        step = StepDef(name="b", adapter="a.com", command="go")
        data = [{"q": "hello"}, {"q": "world"}]
        executor = MockBatchExecutor()
        result = run_batch(step, data, executor, concurrency=1)
        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert len(executor.call_log) == 2

    def test_sequential_with_failure(self) -> None:
        step = StepDef(name="b", adapter="a.com", command="go")
        data = [{"q": "ok"}, {"q": "fail"}]
        executor = MockBatchExecutor(
            [
                {"success": True, "data": {}, "error": None},
                {"success": False, "data": None, "error": {"code": "ERR", "message": "broken"}},
            ]
        )
        result = run_batch(step, data, executor, concurrency=1)
        assert result.succeeded == 1
        assert result.failed == 1
        assert result.results[1].error == "broken"

    def test_concurrent_execution(self) -> None:
        step = StepDef(name="b", adapter="a.com", command="go")
        data = [{"i": str(i)} for i in range(5)]
        executor = MockBatchExecutor()
        result = run_batch(step, data, executor, concurrency=3)
        assert result.total == 5
        assert result.succeeded == 5
        assert [r.index for r in result.results] == [0, 1, 2, 3, 4]

    def test_params_merged_with_row(self) -> None:
        step = StepDef(name="b", adapter="a.com", command="go", params={"static": "val"})
        data = [{"dynamic": "row_val"}]
        executor = MockBatchExecutor()
        result = run_batch(step, data, executor, concurrency=1)
        assert result.succeeded == 1
        assert executor.call_log[0][2] == {"static": "val", "dynamic": "row_val"}

    def test_row_overrides_step_params(self) -> None:
        step = StepDef(name="b", adapter="a.com", command="go", params={"key": "default"})
        data = [{"key": "overridden"}]
        executor = MockBatchExecutor()
        run_batch(step, data, executor, concurrency=1)
        assert executor.call_log[0][2]["key"] == "overridden"

    def test_exception_in_executor(self) -> None:
        class FailingExecutor(StepExecutor):
            def execute_step(self, adapter: str, command: str, params: dict[str, str]) -> dict:
                raise RuntimeError("connection lost")

        step = StepDef(name="b", adapter="a.com", command="go")
        data = [{"q": "a"}]
        result = run_batch(step, data, FailingExecutor(), concurrency=1)
        assert result.failed == 1
        assert "connection lost" in (result.results[0].error or "")

    def test_elapsed_ms_populated(self) -> None:
        step = StepDef(name="b", adapter="a.com", command="go")
        data = [{"q": "a"}]
        executor = MockBatchExecutor()
        result = run_batch(step, data, executor, concurrency=1)
        assert result.elapsed_ms >= 0
        assert result.results[0].elapsed_ms >= 0


# ── CLI batch command ────────────────────────────────────


class TestBatchCLI:
    def test_batch_csv(self, tmp_path) -> None:
        from unittest.mock import patch

        from click.testing import CliRunner

        from cliany_site.cli import cli

        csv_file = tmp_path / "data.csv"
        csv_file.write_text("query\nhello\nworld\n")

        with patch("cliany_site.workflow.batch._execute_one_item") as mock_exec:
            mock_exec.side_effect = [
                BatchItemResult(index=0, params={"query": "hello"}, success=True, elapsed_ms=10.0),
                BatchItemResult(index=1, params={"query": "world"}, success=True, elapsed_ms=10.0),
            ]
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["workflow", "batch", "test.com", "search", str(csv_file), "--json"],
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True

    def test_batch_invalid_data_file(self, tmp_path) -> None:
        from click.testing import CliRunner

        from cliany_site.cli import cli

        f = tmp_path / "bad.xml"
        f.write_text("<data/>")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["workflow", "batch", "test.com", "cmd", str(f), "--json"],
        )
        assert result.exit_code == 1
        assert "BATCH_DATA_ERROR" in result.output
