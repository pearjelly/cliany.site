import json

import click
import pytest

from cliany_site.envelope import err, ok
from cliany_site.workflow.batch import run_batch
from cliany_site.workflow.engine import ClickAdapterExecutor, StepExecutor, run_workflow
from cliany_site.workflow.models import RetryPolicy, StepDef, WorkflowDef


def _executor(responses, *, exit_code=0):
    calls = []

    @click.group()
    def cli():
        pass

    @cli.group("example.com")
    def adapter():
        pass

    @adapter.command("read")
    @click.option("--value", default="Ada")
    @click.option("--json", "json_mode", is_flag=True)
    @click.pass_context
    def read(ctx, value, json_mode):
        calls.append(value)
        click.echo(json.dumps(responses[min(len(calls) - 1, len(responses) - 1)]))
        ctx.exit(exit_code)

    return ClickAdapterExecutor(cli), calls


def test_workflow_consumes_real_click_envelope_and_preserves_data(tmp_home):
    executor, calls = _executor([ok("read", {"name": "Ada"})])
    result = run_workflow(WorkflowDef("test", steps=[
        StepDef("first", "example.com", "read"),
        StepDef("second", "example.com", "read", params={"value": "$prev.data.name"}, when="$prev.success == true"),
    ]), executor)
    assert result.success is True
    assert calls == ["Ada", "Ada"]
    assert result.to_dict()["steps"][0]["data"] == {"name": "Ada"}


def test_batch_consumes_real_click_envelope_and_preserves_data(tmp_home):
    executor, calls = _executor([ok("read", ["Ada"])])
    result = run_batch(StepDef("read", "example.com", "read"), [{"value": "Ada"}], executor)
    assert (result.succeeded, result.failed) == (1, 0)
    assert calls == ["Ada"]
    assert result.to_dict()["results"][0]["data"] == ["Ada"]


def test_error_envelope_retries_then_stops_before_next_step(tmp_home):
    executor, calls = _executor([err("read", "E_EMPTY_RESULT", "No rows")])
    result = run_workflow(WorkflowDef("test", steps=[
        StepDef("first", "example.com", "read", retry=RetryPolicy(2, 0)),
        StepDef("never", "example.com", "read"),
    ]), executor)
    assert result.success is False
    assert len(calls) == 2
    assert len(result.steps) == 1
    assert result.steps[0].error == "No rows"
    assert result.steps[0].attempts == 2


def test_retry_succeeds_on_new_envelope(tmp_home):
    executor, calls = _executor([err("read", "E_TIMEOUT", "Retry"), ok("read", {"name": "Ada"})])
    result = run_workflow(WorkflowDef("test", steps=[
        StepDef("first", "example.com", "read", retry=RetryPolicy(3, 0)),
    ]), executor)
    assert result.success is True
    assert len(calls) == 2
    assert result.steps[0].attempts == 2


@pytest.mark.parametrize("payload", [{"ok": True}, {"success": True}, [], True, 1])
def test_nonzero_click_exit_never_succeeds(tmp_home, payload):
    executor, _ = _executor([payload], exit_code=1)
    result = run_batch(StepDef("read", "example.com", "read"), [{}], executor)
    assert result.failed == 1


@pytest.mark.parametrize("payload,success", [
    ({"ok": True}, True), ({"success": True}, True),
    ({"ok": False, "success": True}, False),
    ({"ok": "false"}, False), ({"success": "false"}, False),
    ({"ok": 1}, False), ({"success": 1}, False), ({}, False),
])
def test_custom_executor_status_is_boolean_and_ok_takes_precedence(tmp_home, payload, success):
    class Executor(StepExecutor):
        def execute_step(self, adapter, command, params):
            return payload

    step = StepDef("read", "example.com", "read")
    workflow = run_workflow(WorkflowDef("test", steps=[step]), Executor())
    batch = run_batch(step, [{}, {}], Executor(), concurrency=2)
    assert workflow.success is success
    assert batch.succeeded == (2 if success else 0)
