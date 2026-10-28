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
def test_real_startup_sigint_closes_owned_browser_and_same_port_can_retry(tmp_home, monkeypatch):
    import pwd

    from cliany_site.browser import launcher

    monkeypatch.setenv("HOME", pwd.getpwuid(os.getuid()).pw_dir)
    with playwright.sync_playwright() as browser_api:
        binary = launcher.find_chrome_binary() or browser_api.chromium.executable_path
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = dict(os.environ, CLIANY_RUNTIME_HOME=str(tmp_home / "runtime"), CLIANY_QA_OFFLINE="1",
               CLIANY_NO_AGENT_MD="1", CLIANY_TEST_CHROME=str(binary), CLIANY_TEST_PORT=str(port))
    script = textwrap.dedent("""
        import json
        import os
        from pathlib import Path
        import signal
        from click.testing import CliRunner
        from cliany_site.browser import launcher
        from cliany_site.cli import cli

        assert not Path(f'/tmp/cliany-site-chrome-{os.getpid()}').exists()
        port = int(os.environ['CLIANY_TEST_PORT'])
        original_popen = launcher.subprocess.Popen
        original_sleep = launcher.time.sleep
        owned = []
        sent = []
        launcher.find_chrome_binary = lambda: Path(os.environ['CLIANY_TEST_CHROME'])

        def capture(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            owned.append(process)
            return process

        def interrupt_first_sleep(seconds):
            if owned and not sent:
                sent.append(True)
                os.kill(os.getpid(), signal.SIGINT)
            original_sleep(seconds)

        launcher.subprocess.Popen = capture
        launcher.time.sleep = interrupt_first_sleep
        try:
            result = CliRunner().invoke(cli, ['--headless', '--cdp-url', f'http://127.0.0.1:{port}',
                                              'doctor', '--json'])
            payload = json.loads(result.stdout)
            stopped = len(owned) == 1 and owned[0].poll() is not None
            closed_port = not launcher._tcp_port_open(port)
            launcher.time.sleep = original_sleep
            retry_ready = False
            if stopped and closed_port:
                retry = launcher.launch_chrome(port, headless=True)
                retry_ready = retry.poll() is None and launcher.detect_running_chrome(port) is not None
            print(json.dumps({'signal_sent': sent == [True], 'exit_code': result.exit_code,
                'error_code': (payload.get('error') or {}).get('code'),
                'owned_browser_stopped': stopped, 'port_closed': closed_port, 'retry_ready': retry_ready}))
        finally:
            launcher.time.sleep = original_sleep
            for process in owned:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except launcher.subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
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
    result = json.loads(stdout)
    assert result == {"signal_sent": True, "exit_code": 130, "error_code": "E_CANCELLED",
                      "owned_browser_stopped": True, "port_closed": True, "retry_ready": True}
