from __future__ import annotations

from unittest.mock import patch

import pytest

from cliany_site.workflow.engine import (
    StepExecutor,
    StepResult,
    WorkflowContext,
    WorkflowResult,
    evaluate_condition,
    interpolate_params,
    interpolate_value,
    resolve_variable,
    run_workflow,
)
from cliany_site.workflow.models import RetryPolicy, StepDef, WorkflowDef
from cliany_site.workflow.parser import (
    WorkflowParseError,
    load_workflow_file,
    parse_workflow_yaml,
)

# ── models ───────────────────────────────────────────────


class TestRetryPolicy:
    def test_defaults(self) -> None:
        p = RetryPolicy()
        assert p.max_attempts == 1
        assert p.delay == 1.0
        assert p.backoff == 1.0

    def test_custom(self) -> None:
        p = RetryPolicy(max_attempts=3, delay=2.0, backoff=2.0)
        assert p.max_attempts == 3


class TestStepDef:
    def test_minimal(self) -> None:
        s = StepDef(name="s1", adapter="example.com", command="search")
        assert s.params == {}
        assert s.when == ""
        assert s.retry.max_attempts == 1

    def test_full(self) -> None:
        s = StepDef(
            name="s1",
            adapter="example.com",
            command="search",
            params={"q": "test"},
            when="$prev.success == true",
            retry=RetryPolicy(max_attempts=3),
        )
        assert s.params["q"] == "test"
        assert s.when == "$prev.success == true"


class TestWorkflowDef:
    def test_empty_steps(self) -> None:
        w = WorkflowDef(name="test")
        assert w.steps == []

    def test_with_steps(self) -> None:
        s = StepDef(name="s1", adapter="a", command="c")
        w = WorkflowDef(name="w1", steps=[s])
        assert len(w.steps) == 1


# ── parser ───────────────────────────────────────────────


class TestParseWorkflowYaml:
    def test_minimal_valid(self) -> None:
        yaml_text = """
name: test-workflow
steps:
  - name: step1
    adapter: example.com
    command: search
"""
        wf = parse_workflow_yaml(yaml_text)
        assert wf.name == "test-workflow"
        assert len(wf.steps) == 1
        assert wf.steps[0].adapter == "example.com"

    def test_full_workflow(self) -> None:
        yaml_text = """
name: full-test
description: A full workflow
steps:
  - name: search
    adapter: github.com
    command: search
    params:
      query: cliany-site
  - name: star
    adapter: github.com
    command: star
    params:
      repo: "$prev.data.repo_name"
    when: "$prev.success == true"
    retry:
      max_attempts: 3
      delay: 2.0
      backoff: 1.5
"""
        wf = parse_workflow_yaml(yaml_text)
        assert wf.name == "full-test"
        assert wf.description == "A full workflow"
        assert len(wf.steps) == 2
        assert wf.steps[1].when == "$prev.success == true"
        assert wf.steps[1].retry.max_attempts == 3
        assert wf.steps[1].retry.delay == 2.0
        assert wf.steps[1].retry.backoff == 1.5
        assert wf.steps[1].params["repo"] == "$prev.data.repo_name"

    def test_missing_name(self) -> None:
        with pytest.raises(WorkflowParseError, match="缺少必填字段.*name"):
            parse_workflow_yaml("steps:\n  - name: s\n    adapter: a\n    command: c\n")

    def test_missing_steps(self) -> None:
        with pytest.raises(WorkflowParseError, match="缺少必填字段.*steps"):
            parse_workflow_yaml("name: test\n")

    def test_empty_steps(self) -> None:
        with pytest.raises(WorkflowParseError, match="非空列表"):
            parse_workflow_yaml("name: test\nsteps: []\n")

    def test_step_missing_adapter(self) -> None:
        with pytest.raises(WorkflowParseError, match="步骤 0.*adapter"):
            parse_workflow_yaml("name: t\nsteps:\n  - name: s\n    command: c\n")

    def test_step_not_dict(self) -> None:
        with pytest.raises(WorkflowParseError, match="步骤 0.*字典"):
            parse_workflow_yaml("name: t\nsteps:\n  - just_a_string\n")

    def test_invalid_yaml(self) -> None:
        with pytest.raises(WorkflowParseError, match="YAML 解析失败"):
            parse_workflow_yaml(":\n  invalid: {{{\n")

    def test_top_level_not_dict(self) -> None:
        with pytest.raises(WorkflowParseError, match="顶层.*字典"):
            parse_workflow_yaml("- item1\n- item2\n")

    def test_retry_not_dict(self) -> None:
        with pytest.raises(WorkflowParseError, match="retry.*字典"):
            parse_workflow_yaml("name: t\nsteps:\n  - name: s\n    adapter: a\n    command: c\n    retry: 3\n")

    def test_params_not_dict(self) -> None:
        with pytest.raises(WorkflowParseError, match="params.*字典"):
            parse_workflow_yaml("name: t\nsteps:\n  - name: s\n    adapter: a\n    command: c\n    params: bad\n")


class TestLoadWorkflowFile:
    def test_file_not_found(self, tmp_path) -> None:
        with pytest.raises(WorkflowParseError, match="不存在"):
            load_workflow_file(tmp_path / "missing.yaml")

    def test_wrong_extension(self, tmp_path) -> None:
        f = tmp_path / "workflow.txt"
        f.write_text("name: t\nsteps:\n  - name: s\n    adapter: a\n    command: c\n")
        with pytest.raises(WorkflowParseError, match=".yaml.*\\.yml"):
            load_workflow_file(f)

    def test_valid_yaml_file(self, tmp_path) -> None:
        f = tmp_path / "wf.yaml"
        f.write_text("name: from-file\nsteps:\n  - name: s\n    adapter: a\n    command: c\n")
        wf = load_workflow_file(f)
        assert wf.name == "from-file"

    def test_valid_yml_file(self, tmp_path) -> None:
        f = tmp_path / "wf.yml"
        f.write_text("name: yml-test\nsteps:\n  - name: s\n    adapter: a\n    command: c\n")
        wf = load_workflow_file(f)
        assert wf.name == "yml-test"


# ── resolve_variable ─────────────────────────────────────


class TestResolveVariable:
    def test_non_variable(self) -> None:
        ctx = WorkflowContext()
        assert resolve_variable("plain-text", ctx) == "plain-text"

    def test_prev_data_field(self) -> None:
        ctx = WorkflowContext(prev_result={"success": True, "data": {"repo": "cliany"}})
        assert resolve_variable("$prev.data.repo", ctx) == "cliany"
        assert resolve_variable("$prev.success", ctx) is True

    def test_prev_nested(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"items": {"first": "hello"}}})
        assert resolve_variable("$prev.data.items.first", ctx) == "hello"

    def test_prev_missing_key(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {}})
        assert resolve_variable("$prev.data.missing", ctx) is None

    def test_steps_reference(self) -> None:
        ctx = WorkflowContext(step_results={"login": {"success": True, "data": {"token": "abc"}}})
        assert resolve_variable("$steps.login.data.token", ctx) == "abc"
        assert resolve_variable("$steps.login.success", ctx) is True

    def test_steps_missing_step(self) -> None:
        ctx = WorkflowContext()
        assert resolve_variable("$steps.missing.data", ctx) is None

    def test_env_variable(self) -> None:
        ctx = WorkflowContext()
        with patch.dict("os.environ", {"TEST_VAR": "hello"}):
            assert resolve_variable("$env.TEST_VAR", ctx) == "hello"

    def test_env_missing(self) -> None:
        ctx = WorkflowContext()
        with patch.dict("os.environ", {}, clear=True):
            assert resolve_variable("$env.MISSING_VAR", ctx) == ""

    def test_unknown_prefix(self) -> None:
        ctx = WorkflowContext()
        assert resolve_variable("$unknown.field", ctx) == "$unknown.field"


# ── interpolate ──────────────────────────────────────────


class TestInterpolateValue:
    def test_plain_string(self) -> None:
        ctx = WorkflowContext()
        assert interpolate_value("hello world", ctx) == "hello world"

    def test_full_variable(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"name": "test"}})
        assert interpolate_value("$prev.data.name", ctx) == "test"

    def test_embedded_variable(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"id": "42"}})
        assert interpolate_value("item-$prev.data.id-done", ctx) == "item-42-done"

    def test_none_value_becomes_empty(self) -> None:
        ctx = WorkflowContext(prev_result={})
        assert interpolate_value("$prev.missing", ctx) == ""

    def test_multiple_variables(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"a": "X", "b": "Y"}})
        result = interpolate_value("$prev.data.a-$prev.data.b", ctx)
        assert result == "X-Y"


class TestInterpolateParams:
    def test_replaces_all(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"q": "hello", "page": "1"}})
        params = {"query": "$prev.data.q", "page": "$prev.data.page", "static": "val"}
        result = interpolate_params(params, ctx)
        assert result == {"query": "hello", "page": "1", "static": "val"}


# ── evaluate_condition ───────────────────────────────────


class TestEvaluateCondition:
    def test_empty_always_true(self) -> None:
        ctx = WorkflowContext()
        assert evaluate_condition("", ctx) is True
        assert evaluate_condition("   ", ctx) is True

    def test_eq_true(self) -> None:
        ctx = WorkflowContext(prev_result={"success": True})
        assert evaluate_condition("$prev.success == true", ctx) is True

    def test_eq_false(self) -> None:
        ctx = WorkflowContext(prev_result={"success": False})
        assert evaluate_condition("$prev.success == true", ctx) is False

    def test_ne(self) -> None:
        ctx = WorkflowContext(prev_result={"success": True})
        assert evaluate_condition("$prev.success != false", ctx) is True

    def test_numeric_gt(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"count": 10}})
        assert evaluate_condition("$prev.data.count > 5", ctx) is True
        assert evaluate_condition("$prev.data.count > 20", ctx) is False

    def test_numeric_lt(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"count": 3}})
        assert evaluate_condition("$prev.data.count < 5", ctx) is True

    def test_numeric_gte(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"count": 5}})
        assert evaluate_condition("$prev.data.count >= 5", ctx) is True

    def test_numeric_lte(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"count": 5}})
        assert evaluate_condition("$prev.data.count <= 5", ctx) is True

    def test_string_eq(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"status": "ok"}})
        assert evaluate_condition('$prev.data.status == "ok"', ctx) is True
        assert evaluate_condition("$prev.data.status == 'ok'", ctx) is True

    def test_none_comparison(self) -> None:
        ctx = WorkflowContext(prev_result={"data": None})
        assert evaluate_condition("$prev.data == none", ctx) is True

    def test_int_comparison(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"val": 42}})
        assert evaluate_condition("$prev.data.val == 42", ctx) is True

    def test_unparseable_raises(self) -> None:
        ctx = WorkflowContext()
        with pytest.raises(ValueError):
            evaluate_condition("this is not a condition", ctx)

    def test_non_numeric_comparison_raises(self) -> None:
        ctx = WorkflowContext(prev_result={"data": {"name": "abc"}})
        with pytest.raises(ValueError):
            evaluate_condition("$prev.data.name > 5", ctx)


# ── StepResult / WorkflowResult ──────────────────────────


class TestStepResult:
    def test_defaults(self) -> None:
        sr = StepResult(name="test", success=True)
        assert sr.skipped is False
        assert sr.elapsed_ms == 0.0
        assert sr.attempts == 1


class TestWorkflowResult:
    def test_to_dict(self) -> None:
        wr = WorkflowResult(
            name="wf",
            success=True,
            steps=[
                StepResult(name="s1", success=True, elapsed_ms=100.0),
                StepResult(name="s2", success=True, skipped=True),
            ],
            elapsed_ms=200.0,
        )
        d = wr.to_dict()
        assert d["name"] == "wf"
        assert d["success"] is True
        assert d["summary"]["total"] == 2
        assert d["summary"]["succeeded"] == 2
        assert d["summary"]["skipped"] == 1

    def test_to_dict_with_failure(self) -> None:
        wr = WorkflowResult(
            name="wf",
            success=False,
            steps=[
                StepResult(name="s1", success=True),
                StepResult(name="s2", success=False, error="boom"),
            ],
        )
        d = wr.to_dict()
        assert d["summary"]["failed"] == 1
        assert d["steps"][1]["error"] == "boom"


# ── MockExecutor for engine tests ────────────────────────


class MockExecutor(StepExecutor):
    def __init__(self, results: list[dict]) -> None:
        self._results = list(results)
        self._call_log: list[tuple[str, str, dict]] = []

    def execute_step(self, adapter: str, command: str, params: dict[str, str]) -> dict:
        self._call_log.append((adapter, command, params))
        if self._results:
            return self._results.pop(0)
        return {"success": False, "data": None, "error": "no more results"}


# ── run_workflow ─────────────────────────────────────────


class TestRunWorkflow:
    def test_single_step_success(self) -> None:
        wf = WorkflowDef(
            name="simple",
            steps=[StepDef(name="s1", adapter="a.com", command="go")],
        )
        executor = MockExecutor([{"success": True, "data": {"key": "val"}, "error": None}])
        result = run_workflow(wf, executor=executor)
        assert result.success is True
        assert len(result.steps) == 1
        assert result.steps[0].success is True

    def test_step_failure_stops_workflow(self) -> None:
        wf = WorkflowDef(
            name="fail-test",
            steps=[
                StepDef(name="s1", adapter="a.com", command="fail"),
                StepDef(name="s2", adapter="a.com", command="skip"),
            ],
        )
        executor = MockExecutor(
            [
                {"success": False, "data": None, "error": {"code": "ERR", "message": "boom"}},
                {"success": True, "data": {}, "error": None},
            ]
        )
        result = run_workflow(wf, executor=executor)
        assert result.success is False
        assert len(result.steps) == 1
        assert result.steps[0].error == "boom"
        assert len(executor._call_log) == 1

    def test_data_passing_prev(self) -> None:
        wf = WorkflowDef(
            name="data-pass",
            steps=[
                StepDef(name="fetch", adapter="a.com", command="get"),
                StepDef(
                    name="use",
                    adapter="a.com",
                    command="put",
                    params={"id": "$prev.data.item_id"},
                ),
            ],
        )
        executor = MockExecutor(
            [
                {"success": True, "data": {"item_id": "42"}, "error": None},
                {"success": True, "data": {"done": True}, "error": None},
            ]
        )
        result = run_workflow(wf, executor=executor)
        assert result.success is True
        assert executor._call_log[1][2] == {"id": "42"}

    def test_data_passing_steps_by_name(self) -> None:
        wf = WorkflowDef(
            name="named-ref",
            steps=[
                StepDef(name="login", adapter="a.com", command="auth"),
                StepDef(
                    name="action",
                    adapter="a.com",
                    command="do",
                    params={"token": "$steps.login.data.token"},
                ),
            ],
        )
        executor = MockExecutor(
            [
                {"success": True, "data": {"token": "secret"}, "error": None},
                {"success": True, "data": {}, "error": None},
            ]
        )
        result = run_workflow(wf, executor=executor)
        assert result.success is True
        assert executor._call_log[1][2] == {"token": "secret"}

    def test_condition_skip(self) -> None:
        wf = WorkflowDef(
            name="cond-skip",
            steps=[
                StepDef(name="check", adapter="a.com", command="c"),
                StepDef(
                    name="act",
                    adapter="a.com",
                    command="do",
                    when="$prev.success == false",
                ),
            ],
        )
        executor = MockExecutor(
            [
                {"success": True, "data": {}, "error": None},
            ]
        )
        result = run_workflow(wf, executor=executor)
        assert result.success is True
        assert len(result.steps) == 2
        assert result.steps[1].skipped is True
        assert len(executor._call_log) == 1

    def test_condition_execute(self) -> None:
        wf = WorkflowDef(
            name="cond-exec",
            steps=[
                StepDef(name="check", adapter="a.com", command="c"),
                StepDef(
                    name="act",
                    adapter="a.com",
                    command="do",
                    when="$prev.success == true",
                ),
            ],
        )
        executor = MockExecutor(
            [
                {"success": True, "data": {}, "error": None},
                {"success": True, "data": {}, "error": None},
            ]
        )
        result = run_workflow(wf, executor=executor)
        assert result.success is True
        assert not result.steps[1].skipped
        assert len(executor._call_log) == 2

    def test_retry_on_failure(self) -> None:
        wf = WorkflowDef(
            name="retry-test",
            steps=[
                StepDef(
                    name="flaky",
                    adapter="a.com",
                    command="go",
                    retry=RetryPolicy(max_attempts=3, delay=0.01),
                ),
            ],
        )
        executor = MockExecutor(
            [
                {"success": False, "data": None, "error": "fail1"},
                {"success": False, "data": None, "error": "fail2"},
                {"success": True, "data": {"ok": True}, "error": None},
            ]
        )
        result = run_workflow(wf, executor=executor)
        assert result.success is True
        assert result.steps[0].attempts == 3

    def test_retry_all_fail(self) -> None:
        wf = WorkflowDef(
            name="all-fail",
            steps=[
                StepDef(
                    name="bad",
                    adapter="a.com",
                    command="go",
                    retry=RetryPolicy(max_attempts=2, delay=0.01),
                ),
            ],
        )
        executor = MockExecutor(
            [
                {"success": False, "data": None, "error": "e1"},
                {"success": False, "data": None, "error": "e2"},
            ]
        )
        result = run_workflow(wf, executor=executor)
        assert result.success is False
        assert result.steps[0].attempts == 2

    def test_retry_exception(self) -> None:
        class FailExecutor(StepExecutor):
            def __init__(self) -> None:
                self.calls = 0

            def execute_step(self, adapter: str, command: str, params: dict[str, str]) -> dict:
                self.calls += 1
                if self.calls < 3:
                    raise RuntimeError("connection lost")
                return {"success": True, "data": {}, "error": None}

        wf = WorkflowDef(
            name="exc-retry",
            steps=[
                StepDef(
                    name="recover",
                    adapter="a.com",
                    command="go",
                    retry=RetryPolicy(max_attempts=3, delay=0.01),
                ),
            ],
        )
        executor = FailExecutor()
        result = run_workflow(wf, executor=executor)
        assert result.success is True
        assert result.steps[0].attempts == 3

    def test_workflow_elapsed_ms(self) -> None:
        wf = WorkflowDef(
            name="timed",
            steps=[StepDef(name="s1", adapter="a.com", command="go")],
        )
        executor = MockExecutor([{"success": True, "data": {}, "error": None}])
        result = run_workflow(wf, executor=executor)
        assert result.elapsed_ms >= 0


# ── CLI commands ─────────────────────────────────────────


class TestWorkflowCLI:
    def test_validate_valid_file(self, tmp_path) -> None:
        from click.testing import CliRunner

        from cliany_site.cli import cli

        f = tmp_path / "wf.yaml"
        f.write_text("name: cli-test\nsteps:\n  - name: s\n    adapter: a\n    command: c\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["workflow", "validate", str(f), "--json"])
        assert result.exit_code == 0
        assert '"valid": true' in result.output

    def test_validate_invalid_file(self, tmp_path) -> None:
        from click.testing import CliRunner

        from cliany_site.cli import cli

        f = tmp_path / "bad.yaml"
        f.write_text("name: t\nsteps: []\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["workflow", "validate", str(f), "--json"])
        assert result.exit_code == 1
        assert "WORKFLOW_PARSE_ERROR" in result.output

    def test_dry_run(self, tmp_path) -> None:
        from click.testing import CliRunner

        from cliany_site.cli import cli

        f = tmp_path / "wf.yaml"
        f.write_text("name: dry-test\nsteps:\n  - name: s1\n    adapter: a.com\n    command: do\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["workflow", "run", str(f), "--dry-run", "--json"])
        assert result.exit_code == 0
        assert "dry-run" in result.output
