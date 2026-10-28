import json
import os
import signal
import socket
import subprocess
import sys
import textwrap
from contextlib import suppress

import pytest

playwright = pytest.importorskip("playwright.sync_api")


@pytest.mark.embodied
@pytest.mark.parametrize("created_here", [True, False])
def test_cancelled_disconnect_cleans_only_owned_browser(tmp_home, monkeypatch, created_here):
    import pwd

    from cliany_site.browser import launcher

    monkeypatch.setenv("HOME", pwd.getpwuid(os.getuid()).pw_dir)
    with playwright.sync_playwright() as browser_api:
        binary = launcher.find_chrome_binary() or browser_api.chromium.executable_path
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = dict(os.environ, CLIANY_RUNTIME_HOME=str(tmp_home / "runtime"), CLIANY_QA_OFFLINE="1",
               CLIANY_TEST_CHROME=str(binary), CLIANY_TEST_PORT=str(port), CLIANY_TEST_OWNED=str(int(created_here)))
    script = textwrap.dedent("""
        import asyncio
        import json
        import os
        from pathlib import Path
        from cliany_site.browser import launcher
        from cliany_site.browser.cdp import CDPConnection

        async def run():
            assert not Path(f'/tmp/cliany-site-chrome-{os.getpid()}').exists()
            port = int(os.environ['CLIANY_TEST_PORT'])
            owned = os.environ['CLIANY_TEST_OWNED'] == '1'
            launcher.find_chrome_binary = lambda: Path(os.environ['CLIANY_TEST_CHROME'])
            process = launcher.launch_chrome(port, headless=True)
            ready_before = launcher.detect_running_chrome(port) is not None
            entered = asyncio.Event()

            class WaitingSession:
                async def stop(self):
                    entered.set()
                    await asyncio.Event().wait()

            connection = CDPConnection(cdp_url=f'http://127.0.0.1:{port}')
            assert await connection.check_available()
            assert connection._chrome_proc is None
            connection._session = WaitingSession()
            if owned:
                connection._chrome_proc = process
                connection._chrome_auto_launched = True
            processes = [process]
            try:
                task = asyncio.create_task(connection.disconnect())
                await entered.wait()
                task.cancel()
                cancelled = False
                try:
                    await task
                except asyncio.CancelledError:
                    cancelled = True
                stopped = process.poll() is not None
                port_closed = not launcher._tcp_port_open(port)
                retry_ready = False
                if owned and stopped and port_closed:
                    retry = launcher.launch_chrome(port, headless=True)
                    processes.append(retry)
                    retry_ready = retry.poll() is None and launcher.detect_running_chrome(port) is not None
                print(json.dumps({'ready_before': ready_before, 'cancelled': cancelled,
                    'stopped': stopped, 'port_closed': port_closed, 'retry_ready': retry_ready,
                    'session_cleared': connection._session is None,
                    'process_reference_cleared': connection._chrome_proc is None,
                    'auto_launch_flag': connection._chrome_auto_launched}))
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)

        import subprocess
        asyncio.run(run())
    """)
    process = subprocess.Popen([sys.executable, "-c", script], cwd=tmp_home, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=60)
    finally:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
    assert process.returncode == 0, stderr
    assert json.loads(stdout) == {
        "ready_before": True, "cancelled": True, "stopped": created_here,
        "port_closed": created_here, "retry_ready": created_here,
        "session_cleared": True, "process_reference_cleared": True, "auto_launch_flag": False,
    }
