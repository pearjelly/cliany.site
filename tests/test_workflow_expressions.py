import pytest

from cliany_site.workflow.engine import (
    StepExecutor, WorkflowContext, evaluate_condition, interpolate_value, resolve_variable, run_workflow,
)
from cliany_site.workflow.models import StepDef, WorkflowDef
from cliany_site.workflow.batch import run_batch
from cliany_site.workflow.parser import WorkflowParseError, parse_workflow_yaml


@pytest.mark.parametrize("expr", ["$prev.data.results[0].name", "$steps.search.data.results[0].name"])
def test_indexed_result_reference(expr):
    result = {"data": {"results": [{"name": "actual"}]}}
    context = WorkflowContext(prev_result=result, step_results={"search": result})
    assert resolve_variable(expr, context) == "actual"
    assert interpolate_value(f"item-{expr}-done", context) == "item-actual-done"


def test_nested_arrays_and_indexed_condition():
    context = WorkflowContext(prev_result={"data": [[{"count": 3}]]})
    assert resolve_variable("$prev.data[0][0].count", context) == 3
    assert evaluate_condition("$prev.data[0][0].count >= 3", context) is True
    assert evaluate_condition("$prev.data[0][0].count > 3", context) is False
    assert resolve_variable("$prev.data[7]", context) is None


@pytest.mark.parametrize("when", [
    "not a condition", "$prev.data.count > 3", "$prev.data.missing != true",
    "$prev.success == true or false", "$prev.data.results[-1] == 1",
])
def test_invalid_conditions_raise_instead_of_running(when):
    context = WorkflowContext(prev_result={"success": True, "data": {"count": "abc"}})
    with pytest.raises(ValueError):
        evaluate_condition(when, context)


class RecordingExecutor(StepExecutor):
    def __init__(self):
        self.calls = []

    def execute_step(self, adapter, command, params):
        self.calls.append(params)
        return {"ok": True, "data": {"results": [{"name": "actual"}]}}


def test_syntax_error_is_rejected_before_any_step():
    executor = RecordingExecutor()
    result = run_workflow(WorkflowDef("test", steps=[
        StepDef("first", "example.com", "read"),
        StepDef("invalid", "example.com", "read", when="typo"),
    ]), executor)
    assert result.success is False
    assert executor.calls == []
    assert result.steps[0].name == "invalid"
    assert result.steps[0].attempts == 0


def test_missing_runtime_condition_stops_before_dispatch():
    executor = RecordingExecutor()
    result = run_workflow(WorkflowDef("test", steps=[
        StepDef("first", "example.com", "read"),
        StepDef("guarded", "example.com", "read", when="$prev.data.missing != true"),
    ]), executor)
    assert result.success is False
    assert len(executor.calls) == 1
    assert result.steps[-1].attempts == 0


def test_workflow_passes_indexed_result_to_next_step():
    executor = RecordingExecutor()
    result = run_workflow(WorkflowDef("test", steps=[
        StepDef("search", "example.com", "read"),
        StepDef("next", "example.com", "read", params={"name": "$prev.data.results[0].name"}),
    ]), executor)
    assert result.success is True
    assert executor.calls == [{}, {"name": "actual"}]


@pytest.mark.parametrize("expr", ["$prev.data.results[-1].name", "$prev.data.results[abc]", "$prev.data.results["])
def test_malformed_index_fails_without_dispatch(expr):
    executor = RecordingExecutor()
    step = StepDef("read", "example.com", "read", params={"name": expr})
    workflow = run_workflow(WorkflowDef("test", steps=[step]), executor)
    batch = run_batch(step, [{}], executor)
    assert workflow.success is False
    assert workflow.steps[0].attempts == 0
    assert batch.failed == 1
    assert executor.calls == []


def test_explicit_null_and_unquoted_status_remain_supported():
    context = WorkflowContext(prev_result={"data": {"status": "in-progress", "value": None}})
    assert evaluate_condition("$prev.data.value == null", context) is True
    assert evaluate_condition("$prev.data.status == in-progress", context) is True
    assert interpolate_value("[$prev.data.status]", context) == "[in-progress]"


def test_indexed_environment_condition_rejected_before_first_step():
    executor = RecordingExecutor()
    result = run_workflow(WorkflowDef("test", steps=[
        StepDef("first", "example.com", "read"),
        StepDef("invalid", "example.com", "read", when="$env.MISSING[0] != true"),
    ]), executor)
    assert result.success is False
    assert executor.calls == []


def test_yaml_validation_rejects_invalid_when():
    with pytest.raises(WorkflowParseError, match="when"):
        parse_workflow_yaml("""
name: test
steps:
  - name: first
    adapter: example.com
    command: read
    when: typo
""")
