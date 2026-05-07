# pyright: reportMissingImports=false
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cliany_site.capability import ApiEndpoint
from cliany_site.explorer.engine import WorkflowExplorer


def _make_config(max_steps: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        cdp_port=9222,
        explore_max_steps=max_steps,
        vision_enabled=False,
        screenshot_quality=75,
        screenshot_format="png",
        vision_som_max_labels=50,
        llm_retry_max_attempts=1,
        llm_retry_base_delay=0.01,
        llm_retry_backoff_factor=1.0,
    )


def _make_tree() -> dict:
    return {
        "url": "https://example.com/",
        "title": "Example",
        "selector_map": {
            "1": {"name": "搜索按钮", "role": "button", "attributes": {}},
        },
        "element_tree": "@1 button 搜索按钮",
        "screenshot": b"",
    }


def _one_step_done(actions: list | None = None) -> list[dict]:
    return [
        {
            "actions": actions
            or [{"type": "click", "ref": "1", "description": "点击搜索"}],
            "commands": [
                {
                    "name": "search",
                    "description": "搜索",
                    "args": [],
                    "action_steps": [0],
                }
            ],
            "done": True,
            "next_url": "",
        }
    ]


def _prepare_mocks(mocker, *, parse_results: list[dict], record: bool = False) -> None:
    mocker.patch("cliany_site.explorer.engine.get_config", return_value=_make_config())
    mocker.patch("cliany_site.explorer.engine._get_llm", return_value=SimpleNamespace(model="mock"))

    browser_session = AsyncMock()
    browser_session.navigate_to = AsyncMock()

    cdp_instance = mocker.Mock()
    cdp_instance.check_available = AsyncMock(return_value=True)
    cdp_instance.connect = AsyncMock(return_value=browser_session)
    cdp_instance.disconnect = AsyncMock()
    mocker.patch("cliany_site.explorer.engine.CDPConnection", return_value=cdp_instance)

    mocker.patch(
        "cliany_site.explorer.engine.capture_axtree",
        new_callable=AsyncMock,
        return_value=_make_tree(),
    )
    mocker.patch(
        "cliany_site.explorer.engine.capture_screenshot",
        new_callable=AsyncMock,
        return_value=b"fake-png",
    )

    invoke_responses = [SimpleNamespace(content=f"r{i}") for i in range(len(parse_results))]
    mocker.patch(
        "cliany_site.explorer.engine._invoke_llm_with_retry",
        new_callable=AsyncMock,
        side_effect=invoke_responses,
    )
    mocker.patch("cliany_site.explorer.engine._parse_llm_response", side_effect=parse_results)
    mocker.patch("cliany_site.explorer.engine.execute_action_steps", new_callable=AsyncMock)
    mocker.patch("cliany_site.explorer.engine.save_extract_markdown", return_value=None)
    mocker.patch("cliany_site.explorer.engine.build_atom_inventory_section", return_value="")
    mocker.patch("cliany_site.explorer.engine.format_selector_candidates_section", return_value="")
    mocker.patch("cliany_site.explorer.engine.click.echo")

    if record:
        rm = MagicMock()
        rm.start_recording.return_value = MagicMock()
        mocker.patch("cliany_site.explorer.recording.RecordingManager", return_value=rm)


def _make_endpoint(url: str = "https://api.example.com/v1/items", method: str = "GET") -> ApiEndpoint:
    return ApiEndpoint(
        url=url,
        method=method,
        status=200,
        sample_response_keys=["id", "name"],
        content_type="application/json",
    )


class TestEngineCapabilitySniffing:
    @pytest.mark.asyncio
    async def test_collects_endpoints(self, mocker):
        ep = _make_endpoint()
        _prepare_mocks(mocker, parse_results=_one_step_done())
        mocker.patch(
            "cliany_site.explorer.engine.sniff_api_endpoints",
            return_value=[ep],
        )

        result = await WorkflowExplorer().explore("https://example.com/", "搜索工作流", record=False)

        assert len(result.api_endpoints) == 1
        assert result.api_endpoints[0].url == ep.url
        assert result.api_endpoints[0].method == ep.method

    @pytest.mark.asyncio
    async def test_sniff_failure_warns_only(self, mocker):
        _prepare_mocks(mocker, parse_results=_one_step_done())
        mocker.patch(
            "cliany_site.explorer.engine.sniff_api_endpoints",
            side_effect=RuntimeError("sniff error"),
        )

        with pytest.warns(UserWarning, match="capability sniffing failed"):
            result = await WorkflowExplorer().explore("https://example.com/", "测试工作流", record=False)

        assert result.api_endpoints == []
        assert len(result.actions) >= 1

    @pytest.mark.asyncio
    async def test_deduplication(self, mocker):
        ep = _make_endpoint()
        parse_results = [
            {
                "actions": [
                    {"type": "click", "ref": "1", "description": "第一步"},
                    {"type": "click", "ref": "1", "description": "第二步"},
                ],
                "commands": [
                    {"name": "search", "description": "搜索", "args": [], "action_steps": [0, 1]}
                ],
                "done": True,
                "next_url": "",
            }
        ]
        _prepare_mocks(mocker, parse_results=parse_results)
        mocker.patch(
            "cliany_site.explorer.engine.sniff_api_endpoints",
            return_value=[ep],
        )

        result = await WorkflowExplorer().explore("https://example.com/", "测试去重", record=False)

        assert len(result.api_endpoints) == 1
        assert result.api_endpoints[0].url == ep.url

    @pytest.mark.asyncio
    async def test_capability_field_mode_auto(self, mocker):
        ep = _make_endpoint()
        _prepare_mocks(mocker, parse_results=_one_step_done())
        mocker.patch(
            "cliany_site.explorer.engine.sniff_api_endpoints",
            return_value=[ep],
        )

        result = await WorkflowExplorer().explore("https://example.com/", "测试工作流", record=False)

        assert result.capability["mode"] == "auto"
        assert result.capability["endpoints_count"] == 1
