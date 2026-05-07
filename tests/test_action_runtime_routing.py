import asyncio
import warnings
from unittest import mock

import pytest

from cliany_site.action_runtime import _execute_api_step, execute_action_steps
from cliany_site.capability import ApiEndpoint, RouteDecision, route_action


def _make_endpoint(url="http://api.example.com/data", method="GET"):
    return ApiEndpoint(
        url=url,
        method=method,
        status=200,
        sample_response_keys=["result"],
        content_type="application/json",
    )


def _make_browser_session():
    session = mock.AsyncMock()
    session.get_current_page_url = mock.AsyncMock(return_value="http://example.com")
    return session


async def test_api_route_calls_aiohttp():
    endpoint = _make_endpoint()

    mock_resp = mock.MagicMock()
    mock_resp.__aenter__ = mock.AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = mock.AsyncMock(return_value=False)
    mock_resp.raise_for_status = mock.Mock()
    mock_resp.json = mock.AsyncMock(return_value={"result": "ok"})

    mock_session = mock.MagicMock()
    mock_session.__aenter__ = mock.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mock.AsyncMock(return_value=False)
    mock_session.get = mock.MagicMock(return_value=mock_resp)

    with mock.patch("aiohttp.ClientSession", return_value=mock_session):
        result = await _execute_api_step(endpoint, {"type": "click", "description": "test"})

    assert result["success"] is True
    assert result["mode"] == "api"
    assert result["data"] == {"result": "ok"}
    mock_session.get.assert_called_once_with(endpoint.url)


async def test_api_failure_falls_back_to_browser():
    endpoint = _make_endpoint()
    api_decision = RouteDecision(mode="api", endpoint=endpoint, reason="json_xhr_detected")
    metadata = {
        "api_endpoints": [
            {
                "url": endpoint.url,
                "method": endpoint.method,
                "status": endpoint.status,
                "sample_response_keys": endpoint.sample_response_keys,
                "content_type": endpoint.content_type,
            }
        ]
    }

    browser_session = _make_browser_session()

    with mock.patch("cliany_site.action_runtime.route_action", return_value=api_decision):
        with mock.patch(
            "cliany_site.action_runtime._execute_api_step",
            side_effect=RuntimeError("connection refused"),
        ):
            with mock.patch(
                "cliany_site.action_runtime._resolve_action_node",
                new_callable=mock.AsyncMock,
                return_value=None,
            ):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    await execute_action_steps(
                        browser_session,
                        [{"type": "click", "description": "test btn"}],
                        continue_on_error=True,
                        metadata=metadata,
                    )

    assert any("API step failed" in str(w.message) for w in caught), "应发出 API 失败 warning"


async def test_force_browser_skips_api():
    endpoint = _make_endpoint()
    metadata = {
        "api_endpoints": [
            {
                "url": endpoint.url,
                "method": endpoint.method,
                "status": endpoint.status,
                "sample_response_keys": endpoint.sample_response_keys,
                "content_type": endpoint.content_type,
            }
        ]
    }

    browser_session = _make_browser_session()

    with mock.patch("cliany_site.action_runtime.route_action", wraps=route_action) as mock_route:
        with mock.patch(
            "cliany_site.action_runtime._resolve_action_node",
            new_callable=mock.AsyncMock,
            return_value=None,
        ):
            import click

            group = click.Group()
            with click.Context(group, obj={"force_browser": True}):
                await execute_action_steps(
                    browser_session,
                    [{"type": "click", "description": "test btn"}],
                    continue_on_error=True,
                    metadata=metadata,
                )

    assert mock_route.call_count >= 1
    _, kwargs = mock_route.call_args
    assert kwargs.get("force_browser") is True


def test_no_endpoints_always_browser():
    decision = route_action({"type": "click"}, [])
    assert decision.mode == "browser"
    assert decision.reason == "no_endpoints"
