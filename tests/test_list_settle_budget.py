import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site import extract
from cliany_site.commands.browser.extract import _do_structured_extract


@pytest.mark.asyncio
async def test_stable_result_after_deadline_is_not_accepted(monkeypatch):
    ticks = iter([0.0, 0.0, 0.0, 11.0])
    monkeypatch.setattr(extract, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    monkeypatch.setattr(extract.asyncio, "sleep", AsyncMock())
    page = SimpleNamespace(evaluate=AsyncMock(return_value={"count": 3, "loading": False}))

    assert await extract._wait_for_list_settle(page, "li.result") is False


@pytest.mark.asyncio
async def test_probe_that_never_returns_is_bounded(monkeypatch):
    monkeypatch.setattr(extract, "_LIST_SETTLE_TIMEOUT_SECONDS", 0.02, raising=False)
    cancelled = asyncio.Event()

    async def blocked(_script):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    page = SimpleNamespace(evaluate=blocked)
    diagnostics = {}
    assert await asyncio.wait_for(
        extract._wait_for_list_settle(page, "li.result", diagnostics=diagnostics), 0.2,
    ) is False
    assert cancelled.is_set()
    assert diagnostics == {"reason": "settle_probe_timeout"}


@pytest.mark.asyncio
@pytest.mark.parametrize("state", [
    {"count": -1, "loading": False},
    {"count": True, "loading": False},
    {"count": 1.5, "loading": False},
    {"count": "3", "loading": False},
    {"count": 3, "loading": 0},
    {"count": 3, "loading": ""},
    {"count": None, "loading": False},
])
async def test_invalid_probe_contract_fails_closed_without_extract(state, tmp_home):
    page = SimpleNamespace(evaluate=AsyncMock(return_value=state))
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=page))

    result = await _do_structured_extract(session, "li.result", "list", {"title": ""})

    assert result["ok"] is False
    assert result["error"]["code"] == "E_PAGE_NOT_READY"
    assert result["error"]["details"]["reason"] == "settle_probe_invalid"
    page.evaluate.assert_awaited_once()


@pytest.mark.asyncio
async def test_probe_exception_has_safe_distinct_reason(tmp_home):
    secret = "PRIVATE_TOKEN=https://secret.example/private?key=do-not-echo"
    page = SimpleNamespace(evaluate=AsyncMock(side_effect=RuntimeError(secret)))
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=page))

    result = await _do_structured_extract(session, "li.result", "list", {"title": ""})

    assert result["error"]["details"]["reason"] == "settle_probe_failed"
    assert "PRIVATE_TOKEN" not in str(result)
    assert "secret.example" not in str(result)
    page.evaluate.assert_awaited_once()


@pytest.mark.asyncio
async def test_external_cancellation_is_not_reported_as_page_failure():
    started = asyncio.Event()

    async def blocked(_script):
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(extract._wait_for_list_settle(SimpleNamespace(evaluate=blocked), "li.result"))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [0, 3, 100])
@pytest.mark.parametrize("encoded", [False, True])
async def test_valid_probe_contract_remains_accepted(monkeypatch, count, encoded):
    import json

    ticks = iter([0.0, 0.0, 0.0, 0.5, 1.1])
    monkeypatch.setattr(extract, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    monkeypatch.setattr(extract.asyncio, "sleep", AsyncMock())
    state = {"count": count, "loading": False}
    page = SimpleNamespace(evaluate=AsyncMock(return_value=json.dumps(state) if encoded else state))

    assert await extract._wait_for_list_settle(page, "li.result") is True
    assert page.evaluate.await_count == 3
