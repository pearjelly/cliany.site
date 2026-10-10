import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.codegen.merger import MergeResult
from cliany_site.config import get_config
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.extract_writer import save_extract_markdown
from cliany_site.sdk import ClanySite
from cliany_site.server import APIServer

DOMAIN = "sdk-fresh.example.test"
URL = f"https://{DOMAIN}/docs/start"


def _result(name="read-result"):
    return ExploreResult(
        pages=[PageInfo(URL, "Fixture")],
        actions=[ActionStep("extract", URL, selector="#result", extract_mode="text")],
        commands=[CommandSuggestion(name, "Read observed result", [], [0])],
        explore_model="offline-sdk-first-install",
    )


@pytest.fixture
def sdk_setup(tmp_home, clean_env, no_llm, monkeypatch):
    import cliany_site.explorer.engine as engine

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / "config"))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.chdir(tmp_home)
    monkeypatch.setattr(engine, "_load_dotenv", lambda: None)
    result = _result()
    explore = AsyncMock(return_value=result)
    monkeypatch.setattr(engine.WorkflowExplorer, "explore", explore)
    return SimpleNamespace(
        result=result, explore=explore, adapter_dir=get_config().adapters_dir / DOMAIN,
    )


async def _invoke(entrypoint, *, force=False):
    async with ClanySite() as sdk:
        if entrypoint == "sdk":
            return await sdk.explore(URL, "read result", force=force)
        server = APIServer()
        server._sdk = sdk
        async with TestClient(TestServer(server._build_app())) as client:
            response = await client.post(
                "/explore", json={"url": URL, "workflow": "read result", "force": force},
            )
            payload = await response.json()
            assert response.status == 200, payload
            return payload


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("auxiliary", ["empty", "extracts", "snapshots"])
async def test_first_generation_retains_source_and_model(sdk_setup, entrypoint, auxiliary):
    setup = sdk_setup
    assert not setup.adapter_dir.exists()

    async def explore(*_args, **_kwargs):
        if auxiliary == "extracts":
            assert save_extract_markdown(
                [{"extract_mode": "text", "description": "result", "data": {"text": "observed"}}],
                DOMAIN, "read result",
            )
        else:
            directory = setup.adapter_dir if auxiliary == "empty" else setup.adapter_dir / auxiliary
            directory.mkdir(parents=True)
        return setup.result

    setup.explore.side_effect = explore
    payload = await _invoke(entrypoint)
    assert payload["success"] is True
    assert payload["data"]["adapter_mode"] == "created"
    assert payload["data"]["commands_count"] == 1
    metadata = json.loads((setup.adapter_dir / "metadata.json").read_text())
    assert metadata["source_url"] == URL
    assert metadata["explore_model"] == "offline-sdk-first-install"
    assert f"SOURCE_URL = {URL!r}" in (setup.adapter_dir / "commands.py").read_text()
    if auxiliary == "extracts":
        assert list((setup.adapter_dir / "extracts").glob("*.md"))
    elif auxiliary == "snapshots":
        assert (setup.adapter_dir / auxiliary).is_dir()


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
async def test_existing_adapter_still_merges(sdk_setup, entrypoint):
    setup = sdk_setup
    existing = _result("existing-result")
    save_adapter(DOMAIN, AdapterGenerator().generate(existing, DOMAIN), {"source_url": URL}, existing)
    payload = await _invoke(entrypoint)
    assert payload["success"] is True
    assert payload["data"]["adapter_mode"] == "merged"
    assert payload["data"]["commands_added"] == 1
    assert payload["data"]["commands_total"] == 2
    metadata = json.loads((setup.adapter_dir / "metadata.json").read_text())
    assert [command["name"] for command in metadata["commands"]] == ["existing-result", "read-result"]


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("filename", ["commands.py", "metadata.json"])
@pytest.mark.parametrize("symlink", [False, True], ids=["file", "dangling-symlink"])
async def test_partial_core_is_not_overwritten(sdk_setup, monkeypatch, entrypoint, filename, symlink):
    import cliany_site.codegen.merger as merger_module

    setup = sdk_setup
    setup.adapter_dir.mkdir(parents=True)
    artifact = setup.adapter_dir / filename
    if symlink:
        try:
            artifact.symlink_to(setup.adapter_dir / "absent-target")
        except OSError:
            pytest.skip("This host cannot create symbolic links")
    else:
        artifact.write_text("{}" if filename == "metadata.json" else "# fixture\n")
    merge = MagicMock(return_value=MergeResult(merged=[{"name": "retained"}], total_count=1))
    merger = SimpleNamespace(metadata_path=setup.adapter_dir / "metadata.json", merge=merge)
    monkeypatch.setattr(merger_module, "AdapterMerger", lambda _domain: merger)
    payload = await _invoke(entrypoint)
    assert payload["data"]["adapter_mode"] == "merged"
    merge.assert_called_once()
    if symlink:
        assert artifact.is_symlink()
    else:
        assert artifact.read_text() == ("{}" if filename == "metadata.json" else "# fixture\n")


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
async def test_explicit_force_still_replaces(sdk_setup, entrypoint):
    setup = sdk_setup
    existing = _result("existing-result")
    save_adapter(DOMAIN, AdapterGenerator().generate(existing, DOMAIN), {"source_url": URL}, existing)
    payload = await _invoke(entrypoint, force=True)
    assert payload["data"]["adapter_mode"] == "created"
    metadata = json.loads((setup.adapter_dir / "metadata.json").read_text())
    assert [command["name"] for command in metadata["commands"]] == ["read-result"]
