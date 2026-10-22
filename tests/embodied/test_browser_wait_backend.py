import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import pytest

playwright = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.mark.embodied
@pytest.mark.parametrize("case", ["idle", "dom", "selector", "navigate_idle", "navigate_dom", "missing"])
async def test_browser_wait_uses_actual_backend_and_keeps_external_page(
    tmp_home, clean_env, no_llm, monkeypatch, local_server, unused_tcp_port, case,
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / "runtime"))
    url = local_server + "/sample_form.html"
    args = {
        "idle": ["browser", "wait", "--state", "networkidle", "--timeout", "5"],
        "dom": ["browser", "wait", "--state", "domcontentloaded", "--timeout", "5"],
        "selector": ["browser", "wait", "--selector", "input#query", "--timeout", "5"],
        "navigate_idle": ["browser", "navigate", url, "--wait", "networkidle", "--timeout", "5"],
        "navigate_dom": ["browser", "navigate", url, "--wait", "domcontentloaded", "--timeout", "5"],
        "missing": ["browser", "wait", "--selector", "#missing", "--timeout", "1"],
    }[case]
    async with playwright.async_playwright() as browser_runtime:
        context = await browser_runtime.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, env={**os.environ, **BROWSER_HOME},
            args=[f"--remote-debugging-port={unused_tcp_port}"],
        )
        try:
            page = context.pages[0]
            await page.goto(url, wait_until="domcontentloaded")
            await page.get_by_role("searchbox").fill("keep this value")
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "cliany_site", "--cdp-url", f"http://127.0.0.1:{unused_tcp_port}",
                *args, "--json", cwd=tmp_home, env=os.environ.copy(),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), 30)
            except TimeoutError:
                process.kill()
                await process.communicate()
                raise
            (tmp_home / f"{case}-stdout.json").write_bytes(stdout)
            (tmp_home / f"{case}-stderr.log").write_bytes(stderr)
            result = json.loads(stdout)
            if case == "missing":
                assert process.returncode != 0 and result["ok"] is False
                assert result["error"]["code"] == "E_TIMEOUT"
            else:
                assert process.returncode == 0 and result["ok"] is True, result
            assert not page.is_closed() and page.url == url and len(context.pages) == 1
            if not case.startswith("navigate_"):
                assert await page.get_by_role("searchbox").input_value() == "keep this value"
        finally:
            await context.close()


@pytest.fixture
def pending_request_server():
    started, release = Event(), Event()
    navigation_count = [0]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/slow":
                started.set()
                release.wait(timeout=20)
                body = b"complete"
            elif self.path == "/busy":
                navigation_count[0] += 1
                body = b'''<h1>Owned delayed response</h1><button id="finished" style="display:none">Finished</button>
                <script>fetch('/slow').then(r=>r.text()).then(()=>{
                    document.getElementById('finished').style.display='block';
                    document.body.dataset.done='yes';
                });</script>'''
            else:
                body = b""
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/busy", started, release, navigation_count
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
async def wait_browser(tmp_home, clean_env, no_llm, monkeypatch, unused_tcp_port):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / "runtime"))
    async with playwright.async_playwright() as browser_runtime:
        context = await browser_runtime.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, env={**os.environ, **BROWSER_HOME},
            args=[f"--remote-debugging-port={unused_tcp_port}"],
        )
        try:
            yield context, f"http://127.0.0.1:{unused_tcp_port}"
        finally:
            await context.close()


@pytest.mark.embodied
@pytest.mark.parametrize("condition", ["networkidle", "selector"])
async def test_wait_does_not_succeed_while_existing_request_or_condition_is_pending(
    wait_browser, tmp_home, pending_request_server, condition,
):
    context, endpoint = wait_browser
    url, started, release, navigation_count = pending_request_server
    page = context.pages[0]
    await page.goto(url, wait_until="domcontentloaded")
    assert await asyncio.to_thread(started.wait, 5)
    condition_args = ["--state", "networkidle"] if condition == "networkidle" else ["--selector", "#finished"]

    async def invoke(stage, timeout):
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "cliany_site", "--cdp-url", endpoint,
            "browser", "wait", *condition_args, "--timeout", str(timeout), "--json",
            cwd=tmp_home, env=os.environ.copy(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), 30)
        except TimeoutError:
            process.kill()
            await process.communicate()
            raise
        (tmp_home / f"{condition}-{stage}-stdout.json").write_bytes(stdout)
        (tmp_home / f"{condition}-{stage}-stderr.log").write_bytes(stderr)
        return process.returncode, json.loads(stdout)

    try:
        code, result = await invoke("pending", 1)
        assert code != 0 and result["error"]["code"] == "E_TIMEOUT"
        assert await page.evaluate("document.body.dataset.done || null") is None
        release.set()
        code, result = await invoke("ready", 5)
        assert code == 0 and result["ok"] is True
        assert await page.evaluate("document.body.dataset.done") == "yes"
        assert navigation_count == [1] and not page.is_closed() and page.url == url
    finally:
        release.set()


@pytest.mark.embodied
async def test_wait_respects_focused_target_with_identical_urls(wait_browser, local_server):
    from cliany_site.browser.cdp import CDPConnection
    from cliany_site.browser.waiting import wait_for_current_page

    context, endpoint = wait_browser
    url = local_server + "/sample_form.html"
    other = context.pages[0]
    await other.goto(url)
    await other.get_by_role("searchbox").fill("other page stays unchanged")
    selected = await context.new_page()
    await selected.goto(url)
    await selected.get_by_role("searchbox").evaluate("element => element.style.visibility = 'hidden'")
    probe = await context.new_cdp_session(selected)
    target = (await probe.send("Target.getTargetInfo"))["targetInfo"]["targetId"]
    await probe.detach()
    cdp = CDPConnection(cdp_url=endpoint)
    session = await cdp.connect()
    try:
        await session.get_or_create_cdp_session(target, focus=True)
        assert (await (await session.get_current_page()).get_target_info())["targetId"] == target
        with pytest.raises(TimeoutError):
            await wait_for_current_page(session, selector="input#query", timeout=0.2)
        await selected.get_by_role("searchbox", include_hidden=True).evaluate(
            "element => element.style.visibility = 'visible'",
        )
        await wait_for_current_page(session, selector="input#query", timeout=1)
    finally:
        await cdp.disconnect()
    assert not selected.is_closed() and not other.is_closed() and len(context.pages) == 2
    assert await other.get_by_role("searchbox").input_value() == "other page stays unchanged"
