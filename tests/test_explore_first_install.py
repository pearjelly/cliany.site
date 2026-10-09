import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.codegen.merger import MergeResult
from cliany_site.config import get_config
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.extract_writer import save_extract_markdown

DOMAIN = "fresh.example.test"
URL = f"https://{DOMAIN}/docs/start"


def _explore_result(name="read-result"):
    return ExploreResult(
        pages=[PageInfo(URL, "Fixture")],
        actions=[ActionStep("extract", URL, selector="#result", extract_mode="text")],
        commands=[CommandSuggestion(name, "Read observed result", [], [0])],
        explore_model="fixture-model",
    )


@pytest.fixture
def explore_setup(tmp_home, clean_env, no_llm, monkeypatch):
    import cliany_site.browser.cdp as cdp_module
    import cliany_site.explorer.engine as engine
    from cliany_site.cli import cli

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / "config"))
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("CLIANY_NO_AGENT_MD", "1")
    monkeypatch.chdir(tmp_home)
    monkeypatch.setattr(engine, "_load_dotenv", lambda: None)
    cdp = MagicMock()
    cdp.check_available = AsyncMock(return_value=True)
    monkeypatch.setattr(cdp_module, "cdp_from_context", lambda _ctx: cdp)
    result = _explore_result()
    explore = AsyncMock(return_value=result)
    monkeypatch.setattr(engine.WorkflowExplorer, "explore", explore)
    monkeypatch.setattr(cli, "commands", dict(cli.commands))
    monkeypatch.setattr(cli, "_adapter_load_errors", {}, raising=False)
    return SimpleNamespace(
        cli=cli, result=result, explore=explore,
        adapter_dir=get_config().adapters_dir / DOMAIN,
    )


def _invoke(setup):
    result = CliRunner().invoke(
        setup.cli, ["--cdp-url", "ws://qa.invalid:9999", "explore", URL, "read result", "--json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


@pytest.mark.parametrize("auxiliary", ["empty", "extracts", "snapshots"])
def test_first_explore_creates_adapter_despite_auxiliary_directory(explore_setup, auxiliary):
    setup = explore_setup
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
    payload = _invoke(setup)
    assert payload["data"]["adapter_mode"] == "created"
    assert payload["data"]["commands_added"] == payload["data"]["commands_total"] == 1
    metadata = json.loads((setup.adapter_dir / "metadata.json").read_text())
    assert metadata["source_url"] == URL
    assert metadata["explore_model"] == "fixture-model"
    assert f"SOURCE_URL = {URL!r}" in (setup.adapter_dir / "commands.py").read_text()
    if auxiliary == "extracts":
        assert list((setup.adapter_dir / "extracts").glob("*.md"))
    elif auxiliary == "snapshots":
        assert (setup.adapter_dir / auxiliary).is_dir()


def test_explore_still_merges_existing_adapter_commands(explore_setup):
    setup = explore_setup
    existing = _explore_result("existing-result")
    save_adapter(DOMAIN, AdapterGenerator().generate(existing, DOMAIN), {"source_url": URL}, existing)
    payload = _invoke(setup)
    assert payload["data"]["adapter_mode"] == "merged"
    assert payload["data"]["commands_added"] == 1
    assert payload["data"]["commands_total"] == 2
    metadata = json.loads((setup.adapter_dir / "metadata.json").read_text())
    assert [command["name"] for command in metadata["commands"]] == ["existing-result", "read-result"]


@pytest.mark.parametrize("filename", ["commands.py", "metadata.json"])
@pytest.mark.parametrize("symlink", [False, True], ids=["file", "dangling-symlink"])
def test_core_artifact_is_not_mistaken_for_auxiliary_only_directory(explore_setup, monkeypatch, filename, symlink):
    import cliany_site.codegen.merger as merger_module

    setup = explore_setup
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
    payload = _invoke(setup)
    assert payload["data"]["adapter_mode"] == "merged"
    merge.assert_called_once()
    if symlink:
        assert artifact.is_symlink()
    else:
        assert artifact.read_text() == ("{}" if filename == "metadata.json" else "# fixture\n")
