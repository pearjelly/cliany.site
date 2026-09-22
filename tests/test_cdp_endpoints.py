from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web

from cliany_site.browser.cdp import CDPConnection, _parse_cdp_url


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "wss://remote.example/cdp/session?token=test-token",
    "ws://127.0.0.1:9333/devtools/browser/test?token=test-token",
    "https://remote.example/proxy/cdp?token=test-token",
    "http://[::1]:9333/proxy?token=test-token",
])
async def test_connect_preserves_endpoint(url):
    with patch("cliany_site.browser.cdp.BrowserSession") as session_class:
        session_class.return_value.start = AsyncMock()
        with patch("cliany_site.browser.cdp.BrowserProfile") as profile:
            await CDPConnection(cdp_url=url).connect()
            assert profile.call_args.kwargs["cdp_url"] == url


@pytest.mark.parametrize("path", ["/proxy/", "/proxy/json/version"])
def test_secure_endpoint_defaults_and_resource_path(path):
    assert _parse_cdp_url("wss://remote.example/cdp") == ("remote.example", 443)
    cdp = CDPConnection(cdp_url=f"https://remote.example{path}?token=test-token")
    assert cdp._http_resource_url("json/version") == "https://remote.example/proxy/json/version?token=test-token"
    assert cdp._http_resource_url("json/list") == "https://remote.example/proxy/json/list?token=test-token"


@pytest.mark.asyncio
async def test_http_discovery_preserves_proxy_prefix_and_query(unused_tcp_port):
    paths = []

    async def handle(request):
        assert request.query["token"] == "test-token"
        paths.append(request.path)
        return web.json_response([] if request.path.endswith("/list") else {
            "Browser": "Chrome/test", "webSocketDebuggerUrl": f"ws://127.0.0.1:{unused_tcp_port}/devtools/browser/test",
        })

    app = web.Application()
    app.router.add_get("/proxy/json/{resource}", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        await web.TCPSite(runner, "127.0.0.1", unused_tcp_port).start()
        cdp = CDPConnection(cdp_url=f"http://127.0.0.1:{unused_tcp_port}/proxy/json/version?token=test-token")
        with patch("cliany_site.browser.cdp.ensure_chrome") as launch:
            assert await cdp.check_available()
            assert await cdp.get_pages() == []
            launch.assert_not_called()
        assert paths == ["/proxy/json/version", "/proxy/json/list"]
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    "<html>Sign in</html>", [], {}, {"Browser": "Chrome/test"},
    {"Browser": "", "webSocketDebuggerUrl": "ws://remote/browser"},
    {"Browser": "Chrome/test", "webSocketDebuggerUrl": "https://remote/login"},
    {"Browser": "Chrome/test", "webSocketDebuggerUrl": "ws:///missing-host"},
    {"Browser": "Chrome/test", "webSocketDebuggerUrl": "ws://remote:invalid/browser"},
    {"Browser": "Chrome/test", "webSocketDebuggerUrl": 123},
])
async def test_http_200_without_cdp_discovery_is_not_available(unused_tcp_port, payload):
    async def handle(request):
        if isinstance(payload, str):
            return web.Response(text=payload, content_type="text/html")
        return web.json_response(payload)

    app = web.Application()
    app.router.add_get("/proxy/json/version", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        await web.TCPSite(runner, "127.0.0.1", unused_tcp_port).start()
        cdp = CDPConnection(cdp_url=f"http://127.0.0.1:{unused_tcp_port}/proxy")
        assert await cdp.check_available() is False
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
@pytest.mark.parametrize("reject", [False, True])
async def test_websocket_probe_and_targets_preserve_path_and_query(unused_tcp_port, reject):
    requests = []

    async def handle(request):
        assert request.query["token"] == "test-token"
        socket = web.WebSocketResponse()
        await socket.prepare(request)
        message = await socket.receive_json()
        requests.append(message["method"])
        await socket.send_json({"method": "Target.targetCreated", "params": {}})
        if reject:
            await socket.send_json({"id": message["id"], "error": {"message": "denied"}})
        else:
            result = {"product": "Chrome/test"} if message["method"] == "Browser.getVersion" else {
                "targetInfos": [{"targetId": "page-1", "type": "page", "url": "about:blank", "title": ""}],
            }
            await socket.send_json({"id": message["id"], "result": result})
        await socket.close()
        return socket

    app = web.Application()
    app.router.add_get("/devtools/browser/test", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        await web.TCPSite(runner, "127.0.0.1", unused_tcp_port).start()
        cdp = CDPConnection(cdp_url=f"ws://127.0.0.1:{unused_tcp_port}/devtools/browser/test?token=test-token")
        with patch("cliany_site.browser.cdp.ensure_chrome") as launch:
            assert await cdp.check_available() is not reject
            pages = await cdp.get_pages()
            assert pages == ([] if reject else [{
                "id": "page-1", "targetId": "page-1", "type": "page", "url": "about:blank", "title": "",
            }])
            launch.assert_not_called()
        assert requests == ["Browser.getVersion", "Target.getTargets"]
    finally:
        await runner.cleanup()
