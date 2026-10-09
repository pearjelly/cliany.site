from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.commands.browser.extract import _do_structured_extract, _parse_target_json, _run_extract
from cliany_site.envelope import ErrorCode
from cliany_site.extract import prepare_semantic_extract_selector, resolve_semantic_extract_selector


@pytest.mark.parametrize(
    "value",
    [
        "",
        "[]",
        "null",
        "{}",
        '{"role":3}',
        '{"role":"list","name":[]}',
        '{"role":"list","attributes":[]}',
        '{"role":"list","attributes":{"id":1}}',
        '{"role":"list","suffix":[]}',
        '{"role":"status","suffix":" li"}',
        '{"role":"list","unknown":1}',
    ],
)
def test_invalid_target_json_is_rejected(value):
    assert _parse_target_json(value)["error"]["code"] == ErrorCode.E_INVALID_PARAM


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [0, 2])
async def test_mapped_root_must_exist_uniquely_before_empty_results_are_allowed(mocker, count):
    mocker.patch("cliany_site.extract.get_config", return_value=SimpleNamespace(resolve_max_retries=0))
    mocker.patch(
        "cliany_site.extract.capture_axtree",
        new=AsyncMock(
            return_value={
                "extract_candidates": [
                    {"role": "list", "name": "Package results", "selectors": ["#new"], "root_selector": "#new"}
                ]
            }
        ),
    )
    page = SimpleNamespace(evaluate=AsyncMock(return_value=count))
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=page))
    assert await resolve_semantic_extract_selector(session, {"role": "list", "name": "Package results"}) is None


@pytest.mark.asyncio
async def test_resolved_selector_uses_current_dom_mapping(mocker):
    mocker.patch("cliany_site.extract.get_config", return_value=SimpleNamespace(resolve_max_retries=0))
    mocker.patch(
        "cliany_site.extract.capture_axtree",
        new=AsyncMock(
            return_value={
                "extract_candidates": [
                    {"role": "list", "name": "Package results", "selectors": ["#new"], "root_selector": "#new"}
                ]
            }
        ),
    )
    page = SimpleNamespace(evaluate=AsyncMock(return_value="1"))
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=page))
    assert (
        await resolve_semantic_extract_selector(session, {"role": "list", "name": "Package results", "suffix": " li"})
        == "#new li"
    )
    assert "#new" in page.evaluate.call_args.args[0]


@pytest.mark.asyncio
async def test_unresolved_target_is_not_successful_empty_and_disconnects(mocker):
    session = object()
    cdp = SimpleNamespace(
        check_available=AsyncMock(return_value=True), connect=AsyncMock(return_value=session), disconnect=AsyncMock()
    )
    mocker.patch(
        "cliany_site.commands.browser.extract.prepare_semantic_extract_selector",
        new=AsyncMock(return_value=(None, "E_SELECTOR_NOT_FOUND")),
    )
    extraction = mocker.patch("cliany_site.commands.browser.extract._do_structured_extract", new=AsyncMock())
    result = await _run_extract(cdp, "#old", "text", "list", extract_target={"role": "list", "name": "Package results"})
    assert result["ok"] is False and result["error"]["code"] == ErrorCode.E_SELECTOR_NOT_FOUND
    extraction.assert_not_awaited()
    cdp.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_target_is_recaptured_after_settling_changes_the_mapping(mocker):
    resolve = mocker.patch(
        "cliany_site.extract.resolve_semantic_extract_selector",
        new=AsyncMock(side_effect=["#before", "#after", "#after"]),
    )
    settle = mocker.patch("cliany_site.extract._wait_for_list_settle", new=AsyncMock(return_value=True))
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=object()))
    assert await prepare_semantic_extract_selector(session, {"role": "list"}, "list") == ("#after", None)
    assert [call.args[1] for call in settle.call_args_list] == ["#before", "#after"]
    assert resolve.await_count == 3


@pytest.mark.asyncio
async def test_atomic_guard_does_not_turn_a_removed_container_into_zero_rows(mocker):
    page = SimpleNamespace(evaluate=AsyncMock(return_value={"__cliany_extract_target_missing__": True}))
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=page))
    result = await _do_structured_extract(
        session, "#results li", "list", None, extract_target={"role": "list", "suffix": " li"}
    )
    assert result["ok"] is False and result["error"]["code"] == ErrorCode.E_SELECTOR_NOT_FOUND
    assert 'document.querySelectorAll("#results")' in page.evaluate.call_args.args[0]
    assert "regions.length !== 1" in page.evaluate.call_args.args[0]


@pytest.mark.asyncio
async def test_unsupported_collection_shape_is_not_a_valid_empty_result():
    page = SimpleNamespace(evaluate=AsyncMock(return_value={"__cliany_extract_mode_mismatch__": True}))
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=page))
    result = await _do_structured_extract(session, "#list", "table", None, extract_target={"role": "list"})
    assert result["ok"] is False and result["error"]["code"] == ErrorCode.E_PARSE_FAILED
