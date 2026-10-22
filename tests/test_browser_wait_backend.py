import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from cliany_site.browser import waiting
from cliany_site.cli import cli
from cliany_site.commands.browser import wait as wait_module


@pytest.fixture(autouse=True)
def isolated_home(tmp_home):
    return tmp_home


def backend(mocker, events=()):
    callbacks = []

    async def refresh(**_kwargs):
        for event in events:
            callbacks[0]({"frameId": "main", **event}, session_id="session")

    domain = SimpleNamespace(
        enable=AsyncMock(), setLifecycleEventsEnabled=AsyncMock(side_effect=refresh),
        getFrameTree=AsyncMock(return_value={"frameTree": {"frame": {"id": "main", "loaderId": "current"}}}),
    )
    client = SimpleNamespace(send=SimpleNamespace(Page=domain, Target=SimpleNamespace(
        attachToTarget=AsyncMock(return_value={"sessionId": "session"}),
    )), register=SimpleNamespace(Page=SimpleNamespace(lifecycleEvent=MagicMock(side_effect=callbacks.append))))
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=client)
    manager.__aexit__ = AsyncMock(return_value=None)
    mocker.patch.object(waiting, "CDPClient", return_value=manager)
    client.manager = manager
    page = SimpleNamespace(get_target_info=AsyncMock(return_value={"targetId": "focused"}), evaluate=AsyncMock())
    session = SimpleNamespace(cdp_client=SimpleNamespace(url="ws://owned.test", additional_headers=None),
                              get_current_page=AsyncMock(return_value=page),
                              get_or_create_cdp_session=AsyncMock(return_value=client))
    return session, page, client, domain


@pytest.mark.parametrize(("state", "event"), [
    ("networkidle", "networkIdle"), ("load", "load"), ("load", "networkIdle"),
    ("domcontentloaded", "DOMContentLoaded"), ("domcontentloaded", "load"),
])
async def test_current_loader_uses_owned_monitor_without_backend_handler_changes(mocker, state, event):
    session, page, client, domain = backend(mocker, [{"loaderId": "current", "name": event}])
    await waiting.wait_for_current_page(session, state=state, timeout=1)
    session.get_or_create_cdp_session.assert_not_awaited()
    client.send.Target.attachToTarget.assert_awaited_once_with(params={"targetId": "focused", "flatten": True})
    domain.setLifecycleEventsEnabled.assert_awaited_once_with(params={"enabled": True}, session_id="session")
    client.manager.__aexit__.assert_awaited_once()
    page.evaluate.assert_not_awaited()


@pytest.mark.parametrize("events", [[], [{"loaderId": "old", "name": "networkIdle"}],
    [{"frameId": "child", "loaderId": "current", "name": "networkIdle"}],
    [{"loaderId": "current", "name": "load"}]])
async def test_idle_does_not_accept_missing_stale_child_or_weaker_state(mocker, events):
    session, _page, client, _domain = backend(mocker, events)
    with pytest.raises(TimeoutError):
        await waiting.wait_for_current_page(session, timeout=0.05)
    client.manager.__aexit__.assert_awaited_once()


async def test_current_page_missing_fails_closed(mocker):
    session, _page, _client, domain = backend(mocker)
    session.get_current_page.return_value = None
    with pytest.raises(RuntimeError, match="Page wait unavailable"):
        await waiting.wait_for_current_page(session)
    domain.setLifecycleEventsEnabled.assert_not_awaited()


async def test_backend_failure_is_opaque_and_closes_only_owned_monitor(mocker):
    session, _page, client, domain = backend(mocker)
    domain.getFrameTree.side_effect = LookupError("private endpoint value")
    with pytest.raises(RuntimeError, match="^Page wait unavailable$") as error:
        await waiting.wait_for_current_page(session, timeout=1)
    assert isinstance(error.value.__cause__, LookupError)
    client.manager.__aexit__.assert_awaited_once()
    session.get_or_create_cdp_session.assert_not_awaited()


async def test_cancel_closes_owned_monitor_without_swallowing_cancellation(mocker):
    session, _page, client, domain = backend(mocker)
    started = asyncio.Event()

    async def pending(**_kwargs):
        started.set()
        await asyncio.Future()

    domain.setLifecycleEventsEnabled.side_effect = pending
    task = asyncio.create_task(waiting.wait_for_current_page(session, timeout=1))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    client.manager.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("visible", [{"visible": True}, '{"visible": true}'])
async def test_explicit_selector_is_passed_as_data_to_native_visibility_check(mocker, visible):
    session, page, _client, _domain = backend(mocker)
    selector = 'input[data-key="private-value"]'
    page.evaluate.side_effect = ["invalid-json", {"visible": False}, visible]
    await waiting.wait_for_current_page(session, selector=selector, timeout=1)
    assert all(call.args == (waiting._VISIBLE, selector) for call in page.evaluate.await_args_list)
    session.get_or_create_cdp_session.assert_not_awaited()


@pytest.mark.parametrize("visible", [None, "True", {"visible": "true"}, {}, {"visible": False}])
async def test_selector_probe_must_be_a_valid_true_boolean(mocker, visible):
    session, page, _client, _domain = backend(mocker)
    page.evaluate.return_value = visible
    with pytest.raises(TimeoutError):
        await waiting.wait_for_current_page(session, selector="#target", timeout=0.05)


async def test_completed_probe_after_deadline_cannot_be_success(mocker, monkeypatch):
    session, page, _client, _domain = backend(mocker)
    clock = [0.0]
    monkeypatch.setattr(waiting, "time", SimpleNamespace(monotonic=lambda: clock[0]))

    async def late(*_args):
        clock[0] = 2.0
        return {"visible": True}

    page.evaluate.side_effect = late
    with pytest.raises(TimeoutError):
        await waiting.wait_for_current_page(session, selector="#target", timeout=1)


async def test_hanging_probe_consumes_the_same_budget_and_external_cancel_propagates(mocker):
    session, page, _client, _domain = backend(mocker)
    started = asyncio.Event()

    async def hanging(*_args):
        started.set()
        await asyncio.Future()

    page.evaluate.side_effect = hanging
    with pytest.raises(TimeoutError):
        await waiting.wait_for_current_page(session, selector="#target", timeout=0.05)
    started.clear()
    task = asyncio.create_task(waiting.wait_for_current_page(session, selector="#target", timeout=1))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.parametrize("args", [
    ["browser", "wait", "--timeout", "0"], ["browser", "wait", "--timeout", "-1"],
    ["browser", "wait", "--state", "unknown"],
    ["browser", "navigate", "https://example.com", "--timeout", "0"],
])
def test_invalid_conditions_stop_before_browser_work(mocker, no_llm, args):
    available = mocker.patch("cliany_site.browser.cdp.CDPConnection.check_available", new_callable=AsyncMock)
    result = CliRunner().invoke(cli, [*args, "--json"])
    assert result.exit_code != 0 and '"E_INVALID_PARAM"' in result.output
    available.assert_not_awaited()


@pytest.mark.parametrize("error", [None, RuntimeError("private-value"), asyncio.CancelledError()])
async def test_wait_always_disconnects_preserves_cancel_and_omits_error_payload(mocker, monkeypatch, error):
    session, _page, _client, _domain = backend(mocker)
    cdp = SimpleNamespace(check_available=AsyncMock(return_value=True), connect=AsyncMock(return_value=session),
                          disconnect=AsyncMock())
    run = AsyncMock(side_effect=error)
    monkeypatch.setattr(wait_module, "wait_for_current_page", run)
    if isinstance(error, asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            await wait_module._run_wait(cdp, None, "networkidle", 1)
    else:
        result = await wait_module._run_wait(cdp, None, "networkidle", 1)
        assert result["ok"] is (error is None)
        assert "private-value" not in str(result)
    cdp.disconnect.assert_awaited_once()
