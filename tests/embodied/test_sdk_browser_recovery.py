import os
import socket
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

playwright = pytest.importorskip("playwright.async_api")


@pytest.mark.embodied
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
async def test_acquisition_error_then_same_instance_real_browser_success(tmp_home, monkeypatch, entrypoint):
    import pwd

    from cryptography.fernet import Fernet

    from cliany_site.browser.cdp import CDPConnection
    from cliany_site.codegen.generator import AdapterGenerator, save_adapter
    from cliany_site.config import get_config
    from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
    from cliany_site.sdk import ClanySite
    from cliany_site.security import load_encrypted_session
    from cliany_site.server import APIServer

    monkeypatch.setenv("HOME", pwd.getpwuid(os.getuid()).pw_dir)
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / ".cliany-site"))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    key = Fernet.generate_key()
    monkeypatch.setattr("cliany_site.security.get_encryption_key", lambda: key)
    domain = "sdk-recovery.example.test"
    url = f"http://{domain}/action_replay.html"
    result = ExploreResult(
        pages=[PageInfo(url, "Form")],
        actions=[ActionStep("type", url, target_ref="999", target_name="Name", target_role="textbox", value="Ada")],
        commands=[CommandSuggestion("enter-name", "Enter name", [{
            "name": "name", "required": True, "default": "Ada", "action_index": 0,
        }], [0])],
    )
    save_adapter(domain, AdapterGenerator().generate(result, domain), {"source_url": url}, result)
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    html = (Path(__file__).parent / "pages" / "action_replay.html").read_text()
    async with playwright.async_playwright() as runtime:
        context = await runtime.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, args=[f"--remote-debugging-port={port}"],
        )
        client = None
        try:
            await context.route(f"http://{domain}/**", lambda route: route.fulfill(
                status=200, content_type="text/html", body=html,
            ))
            await context.add_cookies([{
                "name": "fixture", "value": "local-cookie-only", "domain": domain, "path": "/",
            }])
            async with ClanySite(cdp_url=f"http://127.0.0.1:{port}") as sdk:
                sdk._cdp = CDPConnection(cdp_url=f"http://127.0.0.1:{port}")
                probe = AsyncMock(side_effect=[False, True])
                monkeypatch.setattr(sdk._cdp, "check_available", probe)
                if entrypoint == "http":
                    api = APIServer()
                    api._sdk = sdk
                    client = TestClient(TestServer(api._build_app()))
                    await client.start_server()
                for expected_status in (503, 200):
                    if client is None:
                        payload = await sdk.execute(domain, "enter-name", params={"name": "Grace"})
                    else:
                        response = await client.post("/execute", json={
                            "domain": domain, "command": "enter-name", "params": {"name": "Grace"},
                        })
                        assert response.status == expected_status
                        assert response.content_type == "application/json"
                        payload = await response.json()
                    if expected_status == 503:
                        assert payload["error"]["code"] == "CDP_UNAVAILABLE"
                        assert sdk._session is None
                        assert not list(get_config().sessions_dir.glob("*.json"))
                    else:
                        assert payload["success"] is True, payload
                        page = next(page for page in context.pages if page.url == url)
                        assert await page.get_by_label("Name", exact=True).input_value() == "Grace"
                assert probe.await_count == 2
                assert (await sdk.navigate(url))["success"] is True
                info = await sdk.get_page_info()
                assert info["success"] is True and info["data"]["url"] == url
                assert info["data"]["title"] == "Action replay fixture"
                assert info["data"]["elements_count"] > 0
                if client is None:
                    login = await sdk.login(url)
                else:
                    response = await client.post("/login", json={"url": url})
                    assert response.status == 200
                    login = await response.json()
                assert login["success"] is True and login["data"]["cookies_count"] == 1
                saved = await sdk.save_session(domain)
                assert saved["success"] is True and saved["data"]["cookies_count"] == 1
                session_path = Path(saved["data"]["session_file"])
                assert session_path.is_relative_to(tmp_home)
                assert b"local-cookie-only" not in session_path.read_bytes()
                restored = load_encrypted_session(domain)
                assert restored["cookies"][0]["value"] == "local-cookie-only"
        finally:
            if client is not None:
                await client.close()
            await context.close()
