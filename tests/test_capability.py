import pytest

from cliany_site.capability import (
    ApiEndpoint,
    RouteDecision,
    sniff_api_endpoints,
    route_action,
)


def _req(url="https://api.example.com/data", method="GET", status=200,
         content_type="application/json", timestamp=1000.0, mime="",
         response_keys=None):
    r = {"url": url, "method": method, "status": status,
         "content_type": content_type, "timestamp": timestamp, "mime": mime}
    if response_keys is not None:
        r["response_keys"] = response_keys
    return r


def _step(timestamp=1000.0):
    return {"type": "click", "selector": "#btn", "timestamp": timestamp}


def test_sniff_empty_requests():
    result = sniff_api_endpoints([], _step())
    assert result == []


def test_sniff_json_xhr_hit():
    req = _req(url="https://api.example.com/v1/items", status=200,
               content_type="application/json", timestamp=1001.0,
               response_keys=["id", "name"])
    result = sniff_api_endpoints([req], _step(timestamp=1000.0))
    assert len(result) == 1
    ep = result[0]
    assert isinstance(ep, ApiEndpoint)
    assert ep.url == "https://api.example.com/v1/items"
    assert ep.status == 200
    assert ep.sample_response_keys == ["id", "name"]
    assert ep.content_type == "application/json"


def test_sniff_non_json_filtered():
    req = _req(content_type="text/html", mime="text/html", timestamp=1000.5)
    result = sniff_api_endpoints([req], _step(timestamp=1000.0))
    assert result == []


def test_sniff_time_window_boundary():
    req_inside = _req(content_type="application/json", timestamp=1002.0)
    req_outside = _req(content_type="application/json", timestamp=1002.1)
    step = _step(timestamp=1000.0)
    assert len(sniff_api_endpoints([req_inside], step)) == 1
    assert len(sniff_api_endpoints([req_outside], step)) == 0


def test_sniff_mime_json_fallback():
    req = _req(content_type="", mime="application/json", timestamp=1000.0)
    result = sniff_api_endpoints([req], _step(timestamp=1000.0))
    assert len(result) == 1


def test_route_force_browser():
    ep = ApiEndpoint(url="https://x.com/api", method="POST", status=200,
                     sample_response_keys=[], content_type="application/json")
    decision = route_action({}, [ep], force_browser=True)
    assert isinstance(decision, RouteDecision)
    assert decision.mode == "browser"
    assert decision.endpoint is None
    assert decision.reason == "force_browser"


def test_route_no_endpoints():
    decision = route_action({"type": "click"}, [])
    assert decision.mode == "browser"
    assert decision.endpoint is None
    assert decision.reason == "no_endpoints"


def test_route_multiple_endpoints_takes_first():
    ep1 = ApiEndpoint(url="https://api.example.com/first", method="GET",
                      status=200, sample_response_keys=["a"], content_type="application/json")
    ep2 = ApiEndpoint(url="https://api.example.com/second", method="POST",
                      status=201, sample_response_keys=["b"], content_type="application/json")
    decision = route_action({}, [ep1, ep2])
    assert decision.mode == "api"
    assert decision.endpoint is ep1
    assert decision.reason == "json_xhr_detected"


def test_sniff_no_response_keys_defaults_empty():
    req = _req(content_type="application/json", timestamp=1000.0)
    result = sniff_api_endpoints([req], _step(timestamp=1000.0))
    assert result[0].sample_response_keys == []


def test_route_mode_values_are_api_or_browser():
    ep = ApiEndpoint(url="u", method="GET", status=200,
                     sample_response_keys=[], content_type="application/json")
    for d in (route_action({}, [ep]),
              route_action({}, [ep], force_browser=True),
              route_action({}, [])):
        assert d.mode in ("api", "browser")
