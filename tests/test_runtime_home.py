import json
import os
import shlex
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site import config
from cliany_site.commands import demo
from cliany_site.marketplace import pack_adapter, package_sha256

DOMAIN = "isolated.example"
ROOT = Path(__file__).resolve().parents[1]


def _adapter(runtime_home: Path, value: str) -> None:
    target = runtime_home / "adapters" / DOMAIN
    target.mkdir(parents=True)
    metadata = {
        "schema_version": 3,
        "domain": DOMAIN,
        "generated_at": "2026-10-08T00:00:00Z",
        "generator_version": "test",
        "capability": "api",
        "commands": [{"name": "read", "source": "api", "description": value}],
        "canonical_actions": [],
        "selector_pool": [],
        "smoke": [],
        "heal_history": [],
    }
    (target / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (target / "commands.py").write_text(
        "import json\nimport click\n\n"
        "@click.group()\ndef cli():\n    pass\n\n"
        "@cli.command('read')\n@click.option('--json', 'json_mode', is_flag=True)\n"
        "def read(json_mode):\n"
        f"    click.echo(json.dumps({{'ok': True, 'data': {{'issues': [{{'key': '{value}'}}]}}, "
        "'error': None}))\n",
        encoding="utf-8",
    )


def _snapshot(directory: Path) -> dict[str, bytes]:
    return {str(path.relative_to(directory)): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


def test_demo_subprocesses_use_selected_runtime_and_preserve_default(tmp_home, monkeypatch):
    default = tmp_home / ".cliany-site"
    _adapter(default, "DEFAULT-1")
    (default / "sessions").mkdir()
    (default / "sessions" / "sentinel.json").write_text("default session", encoding="utf-8")
    (default / "cli-manifest.json").write_text("default manifest", encoding="utf-8")
    before = _snapshot(default)

    staging = tmp_home / "package-source"
    _adapter(staging, "ISOLATED-1")
    monkeypatch.setattr(config, "_config", replace(config.get_config(), home_dir=staging))
    package = pack_adapter(DOMAIN)
    selected = tmp_home / "selected-runtime"
    monkeypatch.delenv("CLIANY_RUNTIME_HOME", raising=False)
    monkeypatch.setattr(config, "_config", replace(config.get_config(), home_dir=selected))
    commands = [
        f"cliany-site market install {shlex.quote(str(package))} --sha256 {package_sha256(package)}",
        f"cliany-site verify {DOMAIN} --strict --json",
        f"cliany-site {DOMAIN} read --json",
    ]
    case = {
        "id": "isolated-read",
        "status": "active",
        "adapter_domain": DOMAIN,
        "commands": commands,
        "validation": {"online": "read-only fixture", "expected_rows": {
            "path": ["data", "issues"], "min_count": 1,
        }},
    }
    monkeypatch.setattr(demo, "_load_cases_manifest", lambda: ([case], ROOT, []))
    monkeypatch.setattr(demo, "_active_case_quickstart_commands", lambda item: commands)
    parent_home = os.environ.get("HOME")

    result = demo.run_demo("isolated-read")

    assert result["ok"] is True, result
    assert result["data"]["installed_now"] is True
    assert result["data"]["result"]["data"]["issues"] == [{"key": "ISOLATED-1"}]
    assert (selected / "adapters" / DOMAIN / "commands.py").is_file()
    assert _snapshot(default) == before
    assert os.environ.get("HOME") == parent_home


def test_benchmark_runner_propagates_runtime_to_fresh_cli(tmp_home, monkeypatch):
    from tests.embodied import benchmark_cli

    default = tmp_home / ".cliany-site"
    _adapter(default, "DEFAULT-1")
    (default / "cli-manifest.json").write_text("default manifest", encoding="utf-8")
    before = _snapshot(default)
    selected = tmp_home / "selected-runtime"
    _adapter(selected, "ISOLATED-1")
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(selected))
    config.reset_config()
    import cliany_site.cli as cli_module

    captured = []

    def invoke_child(*, args, prog_name):
        result = subprocess.run(
            [sys.executable, "-m", "cliany_site", *args],
            capture_output=True, text=True, timeout=30, check=False,
        )
        assert result.returncode == 0, result.stderr
        captured.append(json.loads(result.stdout))

    monkeypatch.setattr(cli_module, "cli", invoke_child)
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(default))
    monkeypatch.setattr(sys, "argv", [
        "benchmark_cli", "--runtime-home", str(selected), "--", "list", "--detail", "--json",
    ])
    benchmark_cli.main()

    assert captured[0]["data"]["adapters"][0]["commands"][0]["description"] == "ISOLATED-1"
    assert _snapshot(default) == before


def test_runtime_artifacts_stay_in_selected_home(tmp_home, monkeypatch):
    from cliany_site import healer, repair_cache
    from cliany_site.binary.cache import CacheManager
    from cliany_site.binary.process import ProcessManager
    from cliany_site.explorer.engine import load_existing_adapter_context
    from cliany_site.explorer.models import StepRecord
    from cliany_site.explorer.recording import RecordingManager
    from cliany_site.loader import LazyAdapterRegistry, load_or_rebuild

    default = tmp_home / ".cliany-site"
    _adapter(default, "DEFAULT-1")
    (default / "cli-manifest.json").write_text("default manifest", encoding="utf-8")
    before = _snapshot(default)
    selected = tmp_home / "selected runtime"
    _adapter(selected, "ISOLATED-1")
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(selected))
    monkeypatch.setenv("CLIANY_CAPTURE_NETWORK", "0")
    monkeypatch.setenv("CLIANY_CAPTURE_CONSOLE", "0")
    config.reset_config()
    parent_home = os.environ.get("HOME")

    registry = LazyAdapterRegistry(config.get_config().adapters_dir)
    assert DOMAIN in load_or_rebuild(registry)["adapters"]
    assert load_existing_adapter_context(DOMAIN)["existing_commands"][0]["description"] == "ISOLATED-1"
    repair_cache.record(DOMAIN, "old-ref", "new-ref", "tree")
    assert repair_cache.lookup(DOMAIN, "old-ref", "tree") == "new-ref"
    healer._heal_cache_save(DOMAIN, "entry", {"new_selectors": {"old-ref": "new-ref"}})
    assert "entry" in healer._heal_cache_load(DOMAIN)
    recording = RecordingManager()
    manifest = recording.start_recording(DOMAIN, f"https://{DOMAIN}", "read", "probe")
    recording.save_step(manifest, StepRecord(
        step_index=0, action_data={"type": "extract"}, llm_response_raw="",
        timestamp="2026-10-08T00:00:00Z",
    ), screenshot_bytes=b"image", axtree_json={"role": "document"})
    process = ProcessManager()
    process._write_pid_file(4321)

    for relative in [
        "cli-manifest.json", f"adapters/{DOMAIN}/repair-cache.json",
        f"adapters/{DOMAIN}/heal-cache.json", f"recordings/{DOMAIN}/probe/step_0.png",
        f"recordings/{DOMAIN}/probe/step_0_axtree.json", "run/obscura.pid",
    ]:
        assert (selected / relative).is_file(), relative
    assert CacheManager().cache_root == selected / "bin" / "obscura"
    assert _snapshot(default) == before
    assert os.environ.get("HOME") == parent_home


@pytest.mark.asyncio
async def test_browser_screenshot_uses_selected_runtime(tmp_home, monkeypatch):
    from cliany_site.commands.browser.screenshot import _run_screenshot

    selected = tmp_home / "selected runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(selected))
    monkeypatch.delenv("CLIANY_BROWSER_PROVIDER", raising=False)
    config.reset_config()
    cdp = SimpleNamespace(
        check_available=AsyncMock(return_value=True),
        connect=AsyncMock(return_value=object()),
        disconnect=AsyncMock(),
    )
    monkeypatch.setattr("cliany_site.browser.screenshot.capture_screenshot", AsyncMock(return_value=b"image"))

    result = await _run_screenshot(cdp, None, False)

    assert result["ok"] is True
    output = Path(result["data"]["path"])
    assert output.parent == selected / "snapshots"
    assert output.read_bytes() == b"image"
    assert not (tmp_home / ".cliany-site" / "snapshots").exists()
