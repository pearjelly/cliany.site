import json
import os
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp.test_utils import TestClient, TestServer

playwright = pytest.importorskip("playwright.async_api")


@pytest.mark.embodied
@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
async def test_sdk_first_generation_and_changed_input_replay(tmp_home, monkeypatch, entrypoint):
    import pwd

    from cliany_site.config import get_config
    from cliany_site.explorer import engine
    from cliany_site.sdk import ClanySite
    from cliany_site.server import APIServer

    monkeypatch.setenv("HOME", pwd.getpwuid(os.getuid()).pw_dir)
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / ".cliany-site"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / "config"))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setattr(engine, "_load_dotenv", lambda: None)

    domain = "sdk-browser.example.test"
    url = f"http://{domain}/action_replay.html"
    adapter_dir = get_config().adapters_dir / domain
    snapshots = []
    capture = engine.capture_axtree

    async def observe(session):
        tree = await capture(session)
        snapshots.append(tree)
        return tree

    class ScriptedModel:
        model = "offline-sdk-first-generation"

        async def ainvoke(self, _prompt):
            def ref(role, name):
                return next(
                    key for key, node in snapshots[-1]["selector_map"].items()
                    if node["role"] == role and node["name"] == name
                )

            return SimpleNamespace(content=json.dumps({
                "actions": [
                    {"type": "type", "ref": ref("textbox", "Name"), "value": "Ada"},
                    {"type": "select", "ref": ref("combobox", "Color"), "value": "Blue"},
                    {"type": "click", "ref": ref("button", "Apply")},
                    {"type": "extract", "selector": "#result", "extract_mode": "text"},
                ],
                "commands": [{
                    "name": "apply-and-read", "description": "Apply form and read result",
                    "args": [
                        {"name": "name", "required": True, "action_index": 0},
                        {"name": "color", "required": True, "action_index": 1},
                    ],
                    "action_steps": [0, 1, 2, 3],
                }],
                "done": True,
            }))

    monkeypatch.setattr(engine, "capture_axtree", observe)
    monkeypatch.setattr(engine, "_get_llm", lambda **_kwargs: ScriptedModel())
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    html = (Path(__file__).parent / "pages" / "action_replay.html").read_text()
    async with playwright.async_playwright() as runtime:
        context = await runtime.chromium.launch_persistent_context(
            str(tmp_home / "browser-profile"), headless=True,
            args=[f"--remote-debugging-port={port}"],
        )
        client = None
        try:
            await context.route(
                f"http://{domain}/**",
                lambda route: route.fulfill(status=200, content_type="text/html", body=html),
            )
            async with ClanySite(cdp_url=f"http://127.0.0.1:{port}") as sdk:
                if entrypoint == "sdk":
                    result = await sdk.explore(url, "Apply Ada and Blue and read the result")
                else:
                    server = APIServer()
                    server._sdk = sdk
                    client = TestClient(TestServer(server._build_app()))
                    await client.start_server()
                    response = await client.post("/explore", json={
                        "url": url, "workflow": "Apply Ada and Blue and read the result",
                    })
                    result = await response.json()
                    assert response.status == 200, result

                assert result["success"] is True, result
                assert result["data"]["adapter_mode"] == "created"
                metadata = json.loads((adapter_dir / "metadata.json").read_text())
                assert metadata["source_url"] == url
                assert metadata["explore_model"] == ScriptedModel.model
                assert f"SOURCE_URL = {url!r}" in (adapter_dir / "commands.py").read_text()
                assert list((adapter_dir / "extracts").glob("*.md"))
                if client is None:
                    verification = await sdk.verify(domain)
                    replay = await sdk.execute(domain, "apply-and-read", params={"name": "Grace", "color": "Red"})
                else:
                    response = await client.get("/verify", params={"domain": domain})
                    verification = await response.json()
                    assert response.status == 200, verification
                    response = await client.post("/execute", json={
                        "domain": domain, "command": "apply-and-read", "params": {"name": "Grace", "color": "Red"},
                    })
                    replay = await response.json()
                    assert response.status == 200, replay
                assert verification["success"] is True, verification
                assert replay["success"] is True, replay
                assert replay["data"]["quality"]["ok"] is True
                assert replay["data"]["results"][-1]["data"] == {"text": "Grace:Red"}
                page = next(page for page in context.pages if page.url == url)
                assert await page.locator("#result").inner_text() == "Grace:Red"
        finally:
            if client is not None:
                await client.close()
            await context.close()
