import pytest
from cliany_site.browser.network_capture import (
    NetworkCapture,
    start_network_capture,
    stop_network_capture,
)


class MockSession:
    pass


def _make_entry(url="https://example.com/api", method="GET", status=200,
                mime="application/json", size=100, timestamp=1.0):
    return {"url": url, "method": method, "status": status,
            "mime": mime, "size": size, "timestamp": timestamp}


def test_disabled_via_env(monkeypatch):
    monkeypatch.setenv("CLIANY_CAPTURE_NETWORK", "0")
    capture = start_network_capture(MockSession())
    assert not capture._enabled
    capture._add_request(_make_entry())
    assert len(capture.requests) == 0
    result = stop_network_capture(capture)
    assert result["count"] == 0
    assert result["truncated"] is False
    assert result["total_size"] == 0


def test_enabled_basic():
    capture = start_network_capture(MockSession())
    assert capture._enabled
    entry = _make_entry(size=512)
    capture._add_request(entry)
    result = stop_network_capture(capture)
    assert result["count"] == 1
    assert result["total_size"] == 512
    assert result["truncated"] is False
    assert result["requests"][0]["url"] == "https://example.com/api"


def test_stop_returns_all_fields():
    capture = NetworkCapture()
    capture._add_request(_make_entry(url="https://a.com", method="POST", status=201,
                                     mime="text/html", size=200, timestamp=9.9))
    result = stop_network_capture(capture)
    assert set(result.keys()) == {"requests", "truncated", "total_size", "count"}
    req = result["requests"][0]
    assert req["url"] == "https://a.com"
    assert req["method"] == "POST"
    assert req["status"] == 201
    assert req["mime"] == "text/html"
    assert req["size"] == 200
    assert req["timestamp"] == 9.9


def test_1mb_cap_single_large_request():
    capture = NetworkCapture()
    large_size = 1_500_000
    capture._add_request(_make_entry(size=large_size))
    result = stop_network_capture(capture)
    assert result["truncated"] is True
    assert result["count"] == 0
    assert result["total_size"] == 0
    assert result["total_size"] <= 1_048_576


def test_1mb_cap_accumulation():
    capture = NetworkCapture()
    entry_size = 200_000
    for i in range(10):
        capture._add_request(_make_entry(url=f"https://example.com/{i}", size=entry_size))
    result = stop_network_capture(capture)
    assert result["truncated"] is True
    assert result["total_size"] <= 1_048_576
    assert result["count"] == 5


def test_1mb_cap_stops_accepting_after_truncation():
    capture = NetworkCapture()
    capture._add_request(_make_entry(size=900_000))
    assert not capture.truncated
    capture._add_request(_make_entry(url="https://example.com/big", size=200_000))
    assert capture.truncated
    first_count = len(capture.requests)
    capture._add_request(_make_entry(url="https://example.com/extra", size=10))
    assert len(capture.requests) == first_count


def test_entry_format_no_body_fields():
    capture = NetworkCapture()
    capture._add_request(_make_entry())
    entry = capture.requests[0]
    assert "body" not in entry
    assert "requestBody" not in entry
    assert "responseBody" not in entry


def test_on_event_response_received():
    capture = NetworkCapture()
    event = {
        "method": "GET",
        "timestamp": 5.5,
        "response": {
            "url": "https://api.example.com/data",
            "status": 200,
            "mimeType": "application/json",
            "encodedDataLength": 1024,
        },
    }
    capture._on_event("Network.responseReceived", event)
    assert len(capture.requests) == 1
    req = capture.requests[0]
    assert req["url"] == "https://api.example.com/data"
    assert req["method"] == "GET"
    assert req["status"] == 200
    assert req["mime"] == "application/json"
    assert req["size"] == 1024
    assert req["timestamp"] == 5.5


def test_on_event_response_received_method_from_request_obj():
    capture = NetworkCapture()
    event = {
        "timestamp": 1.0,
        "request": {"method": "POST", "url": "ignored"},
        "response": {
            "url": "https://example.com/submit",
            "status": 201,
            "mimeType": "text/plain",
            "encodedDataLength": 50,
        },
    }
    capture._on_event("Network.responseReceived", event)
    assert capture.requests[0]["method"] == "POST"


def test_on_event_loading_failed():
    capture = NetworkCapture()
    event = {
        "timestamp": 3.14,
        "request": {"url": "https://bad.example.com/img.png", "method": "GET"},
    }
    capture._on_event("Network.loadingFailed", event)
    assert len(capture.requests) == 1
    req = capture.requests[0]
    assert req["url"] == "https://bad.example.com/img.png"
    assert req["method"] == "GET"
    assert req["status"] == -1
    assert req["mime"] == ""
    assert req["size"] == 0
    assert req["timestamp"] == 3.14


def test_on_event_loading_failed_no_request():
    capture = NetworkCapture()
    event = {"timestamp": 1.0}
    capture._on_event("Network.loadingFailed", event)
    assert len(capture.requests) == 1
    req = capture.requests[0]
    assert req["url"] == ""
    assert req["method"] == ""
    assert req["status"] == -1


def test_on_event_response_received_missing_response():
    capture = NetworkCapture()
    capture._on_event("Network.responseReceived", {"timestamp": 1.0})
    assert len(capture.requests) == 0


def test_on_event_disabled_does_not_accumulate():
    capture = NetworkCapture(_enabled=False)
    event = {
        "method": "GET",
        "timestamp": 1.0,
        "response": {
            "url": "https://example.com",
            "status": 200,
            "mimeType": "text/html",
            "encodedDataLength": 100,
        },
    }
    capture._on_event("Network.responseReceived", event)
    assert len(capture.requests) == 0


def test_cdp_client_callbacks_registered():
    registered = {}

    class MockClient:
        def on(self, event_name, cb):
            registered[event_name] = cb

    class MockSessionWithClient:
        cdp_client = MockClient()

    capture = start_network_capture(MockSessionWithClient())
    assert "Network.responseReceived" in registered
    assert "Network.loadingFailed" in registered

    registered["Network.responseReceived"]({
        "method": "GET",
        "timestamp": 1.0,
        "response": {
            "url": "https://cb.test",
            "status": 200,
            "mimeType": "text/plain",
            "encodedDataLength": 10,
        },
    })
    assert len(capture.requests) == 1


def test_multiple_requests_total_size():
    capture = NetworkCapture()
    for i in range(5):
        capture._add_request(_make_entry(size=100))
    result = stop_network_capture(capture)
    assert result["total_size"] == 500
    assert result["count"] == 5
