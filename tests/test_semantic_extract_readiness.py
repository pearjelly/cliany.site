import asyncio
import time
from contextlib import suppress
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.extract import prepare_semantic_extract_selector


@pytest.fixture
def short_readiness(monkeypatch, tmp_home, clean_env):
    monkeypatch.setenv("CLIANY_RESOLVE_RETRY_DELAY", "0.005")
    monkeypatch.setattr("cliany_site.extract._LIST_SETTLE_TIMEOUT_SECONDS", 0.05)


@pytest.mark.asyncio
async def test_collection_waits_for_current_semantic_identity(monkeypatch, short_readiness):
    resolve = AsyncMock(side_effect=[None, "#current li", "#current li"])
    monkeypatch.setattr("cliany_site.extract.resolve_semantic_extract_selector", resolve)
    settle = AsyncMock(return_value=True)
    monkeypatch.setattr("cliany_site.extract._wait_for_list_settle", settle)
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=object()))
    result = await prepare_semantic_extract_selector(session, {"role": "list", "name": "Results"}, "list")
    assert result == ("#current li", None) and resolve.await_count == 3
    settle.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_collection_keeps_failure_and_observation_budget(monkeypatch, short_readiness):
    resolve = AsyncMock(return_value=None)
    monkeypatch.setattr("cliany_site.extract.resolve_semantic_extract_selector", resolve)
    started = time.monotonic()
    result = await prepare_semantic_extract_selector(object(), {"role": "list", "name": "Results"}, "list")
    assert result == (None, "E_SELECTOR_NOT_FOUND")
    assert resolve.await_count >= 2 and time.monotonic() - started < 0.5


@pytest.mark.asyncio
@pytest.mark.parametrize("late_success", [False, True])
async def test_collection_resolution_cannot_outlive_readiness_budget(monkeypatch, short_readiness, late_success):
    async def resolve(*_args):
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            if not late_success:
                raise
        return "#late li"

    monkeypatch.setattr("cliany_site.extract.resolve_semantic_extract_selector", resolve)
    settle = AsyncMock(return_value=True)
    monkeypatch.setattr("cliany_site.extract._wait_for_list_settle", settle)
    started = time.monotonic()
    result = await prepare_semantic_extract_selector(object(), {"role": "list"}, "list")
    assert result[0] is None and time.monotonic() - started < 0.5
    settle.assert_not_awaited()


@pytest.mark.asyncio
async def test_collection_settle_and_recapture_share_one_budget(monkeypatch, short_readiness):
    async def resolve(*_args):
        await asyncio.sleep(0.025)
        return "#current li"

    async def settle(*_args):
        await asyncio.sleep(0.025)
        return True

    monkeypatch.setattr("cliany_site.extract.resolve_semantic_extract_selector", resolve)
    monkeypatch.setattr("cliany_site.extract._wait_for_list_settle", settle)
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=object()))
    result = await prepare_semantic_extract_selector(session, {"role": "list"}, "list")
    assert result == (None, "E_PAGE_NOT_READY")


@pytest.mark.asyncio
async def test_late_page_lookup_does_not_start_another_probe(monkeypatch, short_readiness):
    async def get_page():
        with suppress(asyncio.CancelledError):
            await asyncio.sleep(1)
        return object()

    monkeypatch.setattr("cliany_site.extract.resolve_semantic_extract_selector", AsyncMock(return_value="#current li"))
    settle = AsyncMock(return_value=True)
    monkeypatch.setattr("cliany_site.extract._wait_for_list_settle", settle)
    session = SimpleNamespace(get_current_page=get_page)
    assert await prepare_semantic_extract_selector(session, {"role": "list"}, "list") == (None, "E_PAGE_NOT_READY")
    settle.assert_not_awaited()


@pytest.mark.asyncio
async def test_text_extraction_preserves_single_resolution_policy(monkeypatch, short_readiness):
    resolve = AsyncMock(return_value=None)
    monkeypatch.setattr("cliany_site.extract.resolve_semantic_extract_selector", resolve)
    assert await prepare_semantic_extract_selector(object(), {"role": "heading"}, "text") == (
        None, "E_SELECTOR_NOT_FOUND",
    )
    resolve.assert_awaited_once()


@pytest.mark.asyncio
async def test_collection_observation_preserves_external_cancellation(monkeypatch, short_readiness):
    entered = asyncio.Event()

    async def resolve(*_args):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("cliany_site.extract.resolve_semantic_extract_selector", resolve)
    task = asyncio.create_task(prepare_semantic_extract_selector(object(), {"role": "list"}, "list"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
