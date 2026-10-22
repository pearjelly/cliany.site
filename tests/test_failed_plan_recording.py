import asyncio
import json
import stat
from types import SimpleNamespace

import pytest

from cliany_site.errors import ExploreContractError
from cliany_site.explorer.engine import WorkflowExplorer
from cliany_site.explorer.recording import RecordingManager
from tests.test_engine_recording import _make_config, _prepare_explore_mocks


def prepare(mocker, tmp_home):
    manager = RecordingManager(base_dir=tmp_home / "recordings")
    mocks = _prepare_explore_mocks(mocker, parse_results=[{
        "actions": [{"type": "extract", "selector": "#unobserved li", "extract_mode": "list"}], "done": False,
    }])
    tree = mocks["capture_axtree"].return_value
    tree["extract_candidates"] = [{"role": "list", "selectors": ["#observed"]}]
    mocker.patch("cliany_site.explorer.engine.get_config", return_value=_make_config(1))
    mocker.patch("cliany_site.explorer.recording.RecordingManager", return_value=manager)
    return manager, mocks


@pytest.mark.parametrize("record", [True, False])
async def test_rejected_plan_is_private_failure_not_executed_step(mocker, tmp_home, record):
    manager, mocks = prepare(mocker, tmp_home)
    with pytest.raises(ExploreContractError) as error:
        await WorkflowExplorer().explore("https://example.com/start", "Controlled", record=record)
    assert error.value.reason == "extract_selector_ungrounded"
    mocks["execute"].assert_not_awaited()
    assert mocks["capture_axtree"].await_count == mocks["invoke"].await_count == 1
    if not record:
        assert not manager.base_dir.exists()
        return
    manifests = manager.list_recordings("example.com")
    assert len(manifests) == 1 and manifests[0].completed is False and manifests[0].steps == []
    path = manager.base_dir / "example.com" / manifests[0].session_id / "failure.json"
    payload = json.loads(path.read_text())
    assert payload["reason"] == error.value.reason and payload["phase"] == "planning"
    assert payload["dispatch_status"] == "not_started" and payload["execution_receipt"] is False
    assert payload["llm_response_raw"] == "response-0"
    assert payload["planning_axtree"]["url"] == "https://example.com/start"
    assert "screenshot" not in payload["planning_axtree"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


async def test_failure_write_error_does_not_replace_original_refusal(mocker, tmp_home):
    manager, _mocks = prepare(mocker, tmp_home)
    mocker.patch.object(manager, "save_failure", side_effect=OSError("private-storage-error"), create=True)
    with pytest.raises(ExploreContractError) as error:
        await WorkflowExplorer().explore("https://example.com/start", "Controlled", record=True)
    assert error.value.reason == "extract_selector_ungrounded"
    assert manager.list_recordings("example.com")[0].completed is False


async def test_cancelled_model_is_still_cancelled_and_recording_incomplete(mocker, tmp_home):
    manager, mocks = prepare(mocker, tmp_home)
    mocks["invoke"].side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await WorkflowExplorer().explore("https://example.com/start", "Controlled", record=True)
    assert mocks["capture_axtree"].await_count == 1
    mocks["execute"].assert_not_awaited()
    manifests = manager.list_recordings("example.com")
    assert len(manifests) == 1 and manifests[0].completed is False
    payload = json.loads(next(manager.base_dir.glob("*/*/failure.json")).read_text())
    assert payload["reason"] == "exploration_cancelled" and payload["llm_response_raw"] is None


def test_failure_record_never_replaces_existing_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIANY_CAPTURE_NETWORK", "0")
    monkeypatch.setenv("CLIANY_CAPTURE_CONSOLE", "0")
    manager = RecordingManager(base_dir=tmp_path)
    manifest = manager.start_recording("example.com", "https://example.com", "Controlled", "session")
    manager.save_failure(manifest, {"reason": "first"})
    with pytest.raises(FileExistsError):
        manager.save_failure(manifest, {"reason": "second"})
    assert json.loads((tmp_path / "example.com/session/failure.json").read_text()) == {"reason": "first"}


async def test_exhausted_repair_retains_first_rejected_turn_without_relabeling(mocker, tmp_home):
    manager, mocks = prepare(mocker, tmp_home)
    plan = {"actions": [{"type": "extract", "selector": "#unobserved li", "extract_mode": "list"}], "done": False}
    mocker.patch("cliany_site.explorer.engine.get_config", return_value=_make_config(2))
    mocker.patch("cliany_site.explorer.engine._parse_llm_response", side_effect=[plan, plan])
    mocks["invoke"].side_effect = [
        SimpleNamespace(content="first-rejected"), SimpleNamespace(content="second-rejected"),
    ]
    with pytest.raises(ExploreContractError):
        await WorkflowExplorer().explore("https://example.com/start", "Controlled", record=True)
    payload = json.loads(next(manager.base_dir.glob("*/*/failure.json")).read_text())
    assert payload["llm_response_raw"] == "second-rejected"
    assert len(payload["preceding_turns"]) == 1
    first = payload["preceding_turns"][0]
    assert first["llm_response_raw"] == "first-rejected" and first["dispatch_status"] == "not_started"
    assert first["actions_before_count"] == payload["actions_before_count"] == 0
    assert mocks["capture_axtree"].await_count == mocks["invoke"].await_count == 2
    mocks["execute"].assert_not_awaited()


async def test_dispatched_failure_keeps_planning_observation_and_original_cause(mocker, tmp_home):
    manager, mocks = prepare(mocker, tmp_home)
    plan = {"actions": [{"type": "click", "ref": "1"}], "done": False}
    mocker.patch("cliany_site.explorer.engine._parse_llm_response", return_value=plan)
    original = RuntimeError("private-execution-text")
    mocks["execute"].side_effect = original
    with pytest.raises(ExploreContractError) as error:
        await WorkflowExplorer().explore("https://example.com/start", "Controlled", record=True)
    assert error.value.__cause__ is original and error.value.reason == "action_execution_failed"
    payload = json.loads(next(manager.base_dir.glob("*/*/failure.json")).read_text())
    assert payload["phase"] == "execution" and payload["dispatch_status"] == "started"
    assert payload["execution_receipt"] is False
    assert "private-execution-text" not in json.dumps(payload)
    assert mocks["capture_axtree"].await_count == 1


async def test_success_keeps_existing_step_recording_without_failure_sidecar(mocker, tmp_home):
    from tests.test_engine_recording import _one_step_done_result
    manager, mocks = prepare(mocker, tmp_home)
    mocker.patch("cliany_site.explorer.engine._parse_llm_response", side_effect=_one_step_done_result())
    await WorkflowExplorer().explore("https://example.com/start", "Controlled", record=True)
    manifests = manager.list_recordings("example.com")
    assert len(manifests) == 1 and manifests[0].completed is True and len(manifests[0].steps) == 1
    assert not list(manager.base_dir.glob("*/*/failure.json"))
    assert mocks["capture_axtree"].await_count == 2
