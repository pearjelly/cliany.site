import json
from pathlib import Path

import click
from click.testing import CliRunner

from cliany_site.cli import cli

_FIXTURES = Path(__file__).parent / "fixtures"

_V2_METADATA = {
    "schema_version": 3,
    "domain": "new.local",
    "generated_at": "2026-04-26T12:00:00Z",
    "generator_version": "1.0.0",
    "commands": [],
    "canonical_actions": [],
    "selector_pool": [],
    "smoke": [],
    "heal_history": [],
}

_COMMANDS_PY = "import click\n\n@click.group()\ndef cli():\n    pass\n"


def _make_adapter(
    adapters_dir: Path,
    domain: str,
    metadata: dict,
    commands_py: str = _COMMANDS_PY,
) -> Path:
    adapter_dir = adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)
    (adapter_dir / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (adapter_dir / "commands.py").write_text(commands_py, encoding="utf-8")
    return adapter_dir


def test_register_adapters_skips_legacy(tmp_home, no_llm):
    from cliany_site.config import get_config
    from cliany_site.loader import register_adapters

    legacy_meta = json.loads((_FIXTURES / "legacy_metadata.json").read_text())
    domain = legacy_meta["domain"]

    adapters_dir = get_config().adapters_dir
    _make_adapter(adapters_dir, domain, legacy_meta)

    main_cli = click.Group("test")
    result = register_adapters(main_cli)

    assert domain in result["legacy_adapters"]
    assert domain not in main_cli.commands


def test_register_adapters_ok_v2(tmp_home, no_llm):
    from cliany_site.config import get_config
    from cliany_site.loader import register_adapters

    domain = _V2_METADATA["domain"]
    adapters_dir = get_config().adapters_dir
    _make_adapter(adapters_dir, domain, _V2_METADATA)

    main_cli = click.Group("test")
    result = register_adapters(main_cli)

    assert domain not in result["legacy_adapters"]
    assert domain in main_cli.commands


def test_register_adapters_skips_command_module_without_click_group(tmp_home, no_llm):
    from cliany_site.config import get_config
    from cliany_site.loader import load_adapter_with_error, register_adapters

    domain = "not-a-group.local"
    adapters_dir = get_config().adapters_dir
    _make_adapter(
        adapters_dir,
        domain,
        _V2_METADATA | {"domain": domain},
        "import click\n\ncli = click.Command('not-a-group')\n",
    )

    main_cli = click.Group("test")
    result = register_adapters(main_cli)
    loaded, reason = load_adapter_with_error(domain)

    assert domain not in main_cli.commands
    assert loaded is None
    assert reason == "commands.py 必须导出 click.Group 类型的 cli"
    assert result["adapter_load_errors"] == {
        domain: {
            "verdict": "commands_unloadable",
            "reason": "commands.py 必须导出 click.Group 类型的 cli",
        }
    }


def test_register_adapters_reports_unsupported_metadata_schema(tmp_home, no_llm):
    from cliany_site.config import get_config
    from cliany_site.loader import register_adapters

    domain = "unsupported-schema.local"
    adapters_dir = get_config().adapters_dir
    _make_adapter(
        adapters_dir,
        domain,
        _V2_METADATA | {"domain": domain, "schema_version": 4},
    )

    main_cli = click.Group("test")
    result = register_adapters(main_cli)

    assert domain not in main_cli.commands
    assert result["adapter_load_errors"] == {
        domain: {
            "verdict": "schema_error",
            "reason": "Unsupported schema version: 4",
        }
    }


def test_list_legacy_returns_domain(tmp_home, no_llm):
    from cliany_site.config import get_config

    legacy_meta = json.loads((_FIXTURES / "legacy_metadata.json").read_text())
    domain = legacy_meta["domain"]

    adapters_dir = get_config().adapters_dir
    _make_adapter(adapters_dir, domain, legacy_meta)

    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--legacy", "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    domains = [item["domain"] for item in data["data"]]
    assert domain in domains


def test_list_legacy_contains_suggested_command(tmp_home, no_llm):
    from cliany_site.config import get_config

    legacy_meta = json.loads((_FIXTURES / "legacy_metadata.json").read_text())
    domain = legacy_meta["domain"]

    adapters_dir = get_config().adapters_dir
    _make_adapter(adapters_dir, domain, legacy_meta)

    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--legacy", "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    for item in data["data"]:
        assert "cliany-site explore" in item["suggested_command"]
