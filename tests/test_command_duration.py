import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from threading import Barrier, local
from unittest.mock import AsyncMock

import click
import pytest
from click.testing import CliRunner

from cliany_site.envelope import err, ok
from cliany_site.response import print_response


@pytest.fixture
def root_cli(tmp_home, clean_env):
    from cliany_site.cli import cli

    return cli


@pytest.fixture
def clock(monkeypatch):
    current = [0]
    monkeypatch.setattr("cliany_site.envelope.time.monotonic_ns", lambda: current[0])
    return current


@pytest.mark.parametrize("failure", [False, True])
def test_cli_duration_measures_success_and_rendered_errors(root_cli, monkeypatch, clock, failure):
    @click.command("duration-probe")
    def probe():
        clock[0] += 32_900_000
        if failure:
            raise click.UsageError("probe failure")
        print_response(ok("duration-probe", {"value": "done"}), json_mode=True)

    monkeypatch.setitem(root_cli.commands, "duration-probe", probe)
    result = CliRunner().invoke(root_cli, ["--json", "duration-probe"])
    assert result.exit_code == (1 if failure else 0), result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is not failure
    assert payload["meta"]["duration_ms"] == 32
    assert payload["meta"]["duration_measured"] is True
    assert ok("after-cli", {})["meta"]["duration_measured"] is False


@pytest.mark.parametrize("builder", [lambda: ok("outside", {}), lambda: err("outside", "E_TEST", "failure")])
def test_envelopes_outside_cli_mark_duration_unavailable(tmp_home, builder):
    payload = builder()
    assert payload["version"] == "1"
    assert payload["meta"]["duration_ms"] == 0
    assert payload["meta"]["duration_measured"] is False


@pytest.mark.parametrize("failure", [False, True])
def test_generated_parent_and_child_invocations_use_separate_clocks(root_cli, monkeypatch, clock, failure):
    from cliany_site.codegen.generator import AdapterGenerator, save_adapter
    from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
    from cliany_site.loader import register_adapters

    @click.group()
    def browser():
        pass

    @browser.command("navigate")
    @click.argument("url")
    @click.option("--session")
    @click.option("--json", "json_mode", is_flag=True)
    def navigate(url, session, json_mode):
        clock[0] += 10_000_000
        print_response(ok("browser navigate", {"url": url}), json_mode=True)

    @browser.command("click")
    @click.option("--text")
    @click.option("--role")
    @click.option("--session")
    @click.option("--json", "json_mode", is_flag=True)
    def click_target(text, role, session, json_mode):
        clock[0] += 30_000_000
        if failure:
            raise click.ClickException("child failed")
        print_response(ok("browser click", {"target": text}), json_mode=True)

    result = ExploreResult(
        pages=[PageInfo("https://example.com", "Fixture")],
        actions=[ActionStep(
            "click", "https://example.com", target_name="Inspect Beta", target_role="button",
        )],
        commands=[CommandSuggestion("inspect", "Inspect", [], [0])],
    )
    save_adapter("example.com", AdapterGenerator().generate(result, "example.com"), explore_result=result)
    monkeypatch.setattr(root_cli, "commands", dict(root_cli.commands))
    monkeypatch.setattr(root_cli, "_adapter_load_errors", {}, raising=False)
    monkeypatch.setitem(root_cli.commands, "browser", browser)
    registration = register_adapters(root_cli)
    root_cli.set_adapter_load_errors(registration["adapter_load_errors"])
    invoked = CliRunner().invoke(root_cli, [
        "--cdp-url", "ws://qa.invalid:9999", "--json", "example.com", "inspect",
    ])
    assert invoked.exit_code == (1 if failure else 0), invoked.output
    payload = json.loads(invoked.stdout)
    children = payload["data"]["results"]
    assert [child["meta"]["duration_ms"] for child in children] == [10, 30]
    assert all(child["meta"]["duration_measured"] is True for child in children)
    assert payload["meta"]["duration_ms"] == 40
    assert payload["meta"]["duration_measured"] is True
    assert ok("outside", {})["meta"]["duration_measured"] is False


def test_overlapping_same_command_cli_calls_keep_thread_local_spans(root_cli, monkeypatch):
    from cliany_site.cli import SafeGroup

    clock = local()
    rendezvous = Barrier(2)
    records = {}
    monkeypatch.setattr("cliany_site.envelope.time.monotonic_ns", lambda: clock.ns)
    monkeypatch.setattr("cliany_site.cli._print_startup_banner", lambda *_args: None)

    @click.group(cls=SafeGroup)
    def app():
        pass

    @app.command("same")
    @click.argument("key")
    @click.argument("milliseconds", type=int)
    def same(key, milliseconds):
        rendezvous.wait(timeout=5)
        clock.ns += milliseconds * 1_000_000
        records[key] = ok("same", {})

    def invoke(key, milliseconds):
        clock.ns = 0
        with pytest.raises(SystemExit) as exc_info:
            app.main(["same", key, str(milliseconds)])
        assert exc_info.value.code == 0
        assert ok("after", {})["meta"]["duration_measured"] is False

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(invoke, key, milliseconds) for key, milliseconds in [("a", 10), ("b", 40)]]
        for future in futures:
            future.result(timeout=10)
    assert records["a"]["meta"]["duration_ms"] == 10
    assert records["b"]["meta"]["duration_ms"] == 40
    assert all(record["meta"]["duration_measured"] is True for record in records.values())


def test_timer_keeps_multiple_snapshots_and_marks_submillisecond_zero(tmp_home, clock):
    from cliany_site.envelope import command_timing

    with command_timing():
        clock[0] = 900_000
        first = ok("same", {})
        assert first["meta"]["duration_ms"] == 0
        assert first["meta"]["duration_measured"] is True
        clock[0] = 12_000_000
        assert err("same", "E_TEST", "failure")["meta"]["duration_ms"] == 12


def test_copied_context_cannot_measure_after_invocation_ends(tmp_home, clock):
    from cliany_site.envelope import command_timing

    with command_timing():
        copied = copy_context()
        clock[0] = 10_000_000
        assert copied.run(ok, "same", {})["meta"]["duration_measured"] is True
    clock[0] = 50_000_000
    payload = copied.run(ok, "same", {})
    assert payload["meta"]["duration_ms"] == 0
    assert payload["meta"]["duration_measured"] is False


def test_parse_error_is_measured_and_exit_restores_context(root_cli, monkeypatch, clock):
    parsed = CliRunner().invoke(root_cli, ["--json", "--not-a-real-option"])
    payload = json.loads(parsed.stdout)
    assert parsed.exit_code == 1
    assert payload["error"]["code"] == "E_INVALID_PARAM"
    assert payload["meta"]["duration_measured"] is True

    @click.command("exit-probe")
    def exit_probe():
        raise SystemExit(2)

    monkeypatch.setitem(root_cli.commands, "exit-probe", exit_probe)
    assert CliRunner().invoke(root_cli, ["exit-probe"]).exit_code == 2
    assert ok("after-exit", {})["meta"]["duration_measured"] is False


def test_schema_keeps_old_metadata_and_rejects_nonboolean_availability(tmp_home):
    from pathlib import Path

    from jsonschema import ValidationError, validate

    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/envelope.v1.json").read_text())
    payload = ok("schema-probe", {})
    validate(payload, schema)
    payload["meta"].pop("duration_measured")
    validate(payload, schema)
    payload["meta"]["duration_measured"] = "false"
    with pytest.raises(ValidationError):
        validate(payload, schema)


@pytest.mark.asyncio
async def test_overlapping_async_spans_restore_parent_without_leaking(tmp_home, monkeypatch):
    from cliany_site.envelope import command_timing

    clocks = {}
    entered = asyncio.Event()
    count = 0
    monkeypatch.setattr("cliany_site.envelope.time.monotonic_ns", lambda: clocks[asyncio.current_task()])

    async def measure(milliseconds):
        nonlocal count
        clocks[asyncio.current_task()] = 0
        with command_timing():
            count += 1
            if count == 2:
                entered.set()
            await entered.wait()
            clocks[asyncio.current_task()] = milliseconds * 1_000_000
            return ok("same", {})

    first, second = await asyncio.gather(measure(10), measure(40))
    assert first["meta"]["duration_ms"] == 10
    assert second["meta"]["duration_ms"] == 40
    assert ok("after", {})["meta"]["duration_measured"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_sdk_and_http_doctor_keep_legacy_envelopes(tmp_home, clean_env, monkeypatch, failure):
    from aiohttp.test_utils import TestClient, TestServer

    from cliany_site.sdk import ClanySite
    from cliany_site.server import APIServer

    diagnostics = {"checks": [], "summary": {"ready_for_explore": False}}
    snapshots = []

    async def checks(*_args, **_kwargs):
        payload = err("doctor", "E_CDP_UNAVAILABLE", "unavailable", details=diagnostics) if failure else ok(
            "doctor", diagnostics,
        )
        snapshots.append(payload["meta"])
        return payload

    monkeypatch.setattr("cliany_site.commands.doctor._run_checks", checks)
    monkeypatch.setattr(ClanySite, "_ensure_cdp", AsyncMock(return_value=object()))
    sdk = ClanySite()
    direct = await sdk.doctor()
    assert set(direct) == {"success", "data", "error"}
    assert direct["success"] is not failure

    server = APIServer()
    server._sdk = sdk
    async with TestClient(TestServer(server._build_app())) as client:
        response = await client.get("/doctor")
        assert response.status == (503 if failure else 200)
        assert await response.json() == direct
    assert len(snapshots) == 2
    assert all(meta["duration_ms"] == 0 and meta["duration_measured"] is False for meta in snapshots)
