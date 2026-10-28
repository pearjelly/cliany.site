import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from cliany_site.browser import launcher
from cliany_site.cli import cli


@contextmanager
def discovery_server(body: bytes):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("body", [
    b"[]", b"null", b"\xff", b"{}", b'{"webSocketDebuggerUrl":123}',
    b'{"Browser":"Chrome/test","webSocketDebuggerUrl":"https://example.test"}',
    b'{"Browser":"Chrome/test","webSocketDebuggerUrl":"ws://host:bad/browser"}',
])
def test_invalid_local_discovery_never_launches_on_occupied_port(body, monkeypatch):
    launch = Mock()
    monkeypatch.setattr(launcher, "launch_chrome", launch)
    with discovery_server(body) as port:
        assert launcher.detect_running_chrome(port) is None
        with pytest.raises(RuntimeError, match="端口.*占用"):
            launcher.ensure_chrome(port, headless=True)
    launch.assert_not_called()


def test_valid_local_discovery_reuses_existing_browser(monkeypatch):
    launch = Mock()
    monkeypatch.setattr(launcher, "launch_chrome", launch)
    websocket = "ws://127.0.0.1:9222/devtools/browser/test"
    body = json.dumps({"Browser": "Chrome/test", "webSocketDebuggerUrl": websocket}).encode()
    with discovery_server(body) as port:
        assert launcher.ensure_chrome(port, headless=True) == (websocket, None)
    launch.assert_not_called()


def test_free_local_port_still_launches_browser(monkeypatch):
    process = Mock()
    monkeypatch.setattr(launcher, "detect_running_chrome", Mock(side_effect=[None, "ws://browser"]))
    monkeypatch.setattr(launcher, "_tcp_port_open", lambda port: False)
    launch = Mock(return_value=process)
    monkeypatch.setattr(launcher, "launch_chrome", launch)
    assert launcher.ensure_chrome(41234, headless=True) == ("ws://browser", process)
    launch.assert_called_once_with(41234, headless=True)


def test_doctor_reports_occupied_non_cdp_port_without_unknown_error(tmp_home, no_llm, monkeypatch):
    launch = Mock()
    monkeypatch.setattr(launcher, "launch_chrome", launch)
    with discovery_server(b"[]") as port:
        result = CliRunner().invoke(cli, ["--cdp-url", f"http://127.0.0.1:{port}", "doctor", "--json"])
    payload = json.loads(result.output)
    assert payload["command"] == "doctor"
    assert payload["error"]["code"] == "E_CDP_UNAVAILABLE"
    check = next(item for item in payload["error"]["details"]["checks"] if item["name"] == "cdp")
    assert check["status"] == "fail"
    assert "占用" in check["action"]
    launch.assert_not_called()
