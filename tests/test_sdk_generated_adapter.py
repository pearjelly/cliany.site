from unittest.mock import AsyncMock, patch

import pytest

from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.sdk import ClanySite


def _generate(*, expects_nonempty=True, args=None, value="recorded", source="https://example.com/form"):
    result = ExploreResult(
        pages=[PageInfo(source, "Form")],
        actions=[
            ActionStep("navigate", source, target_url=source),
            ActionStep("type", source, target_ref="8", target_name="Name", value=value),
            ActionStep("extract", source, selector="output", extract_mode="list", fields_map={"name": ""}),
        ],
        commands=[CommandSuggestion(
            "read-name", "Read name", args if args is not None else [
                {"name": "name", "default": "Ada", "action_index": 1},
            ], [1, 2], expects_nonempty=expects_nonempty,
        )],
    )
    save_adapter("example.com", AdapterGenerator().generate(result, "example.com"), explore_result=result)


@pytest.mark.asyncio
@pytest.mark.parametrize("params,expected", [(None, "Ada"), ({"name": "Grace"}, "Grace")])
async def test_generated_metadata_actions_and_defaults(tmp_home, params, expected):
    _generate()

    async def replay(session, actions, **kwargs):
        from cliany_site.action_runtime import substitute_parameters
        resolved = substitute_parameters(actions, kwargs["params"])
        assert resolved[0] == {"type": "navigate", "url": "https://example.com/form"}
        assert resolved[1]["type"] == "type"
        assert resolved[1]["ref"] == "8"
        assert resolved[1]["value"] == expected
        assert resolved[2]["fields"] == {"name": ""}
        kwargs["extraction_results"].append({
            "step_index": 2, "extract_mode": "list", "fields": {"name": ""}, "data": [{"name": expected}],
        })

    with (
        patch.object(ClanySite, "_ensure_browser_session", new=AsyncMock()),
        patch("cliany_site.session.load_session", new=AsyncMock()),
        patch("cliany_site.action_runtime.execute_action_steps", side_effect=replay),
    ):
        result = await ClanySite().execute("example.com", "read-name", params=params)
    assert result["success"] is True, result
    assert result["data"]["results"][0]["data"] == [{"name": expected}]


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit", [False, True])
async def test_missing_generated_parameter_stops_before_browser(tmp_home, explicit):
    _generate(args=[{"name": "name", "required": True}] if explicit else [], value="{{name}}")
    with patch.object(ClanySite, "_ensure_browser_session", new=AsyncMock()) as connect:
        result = await ClanySite().execute("example.com", "read-name")
    assert result["error"]["code"] == "E_INVALID_PARAM"
    connect.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("rows,expects_nonempty,success", [
    ([], True, False), ([], False, True), ([{"name": ""}], False, False),
    ([{"name": "Ada"}, {}], False, False), ([{"name": "Ada"}], True, True),
])
async def test_generated_extract_quality(tmp_home, rows, expects_nonempty, success):
    _generate(expects_nonempty=expects_nonempty)

    async def replay(session, actions, **kwargs):
        kwargs["extraction_results"].append({
            "step_index": 2, "extract_mode": "list", "fields": {"name": ""}, "data": rows,
        })

    with (
        patch.object(ClanySite, "_ensure_browser_session", new=AsyncMock()),
        patch("cliany_site.session.load_session", new=AsyncMock()),
        patch("cliany_site.action_runtime.execute_action_steps", side_effect=replay),
    ):
        result = await ClanySite().execute("example.com", "read-name")
    assert result["success"] is success, result
    if not success:
        assert result["error"]["code"] == "E_EMPTY_RESULT"
        assert result["error"]["details"]["results"][0]["data"] == rows


@pytest.mark.asyncio
async def test_generated_source_url_is_sandboxed_before_browser(tmp_home):
    _generate(source="https://other.example/form")
    with patch.object(ClanySite, "_ensure_browser_session", new=AsyncMock()) as connect:
        result = await ClanySite().execute("example.com", "read-name", sandbox=True)
    assert result["error"]["code"] == "E_SANDBOX_VIOLATION"
    connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_command_lists_actual_generated_commands(tmp_home):
    _generate()
    with patch.object(ClanySite, "_ensure_browser_session", new=AsyncMock()) as connect:
        result = await ClanySite().execute("example.com", "missing")
    assert result["error"]["code"] == "COMMAND_NOT_FOUND"
    assert "read-name" in result["error"]["fix"]
    connect.assert_not_awaited()
