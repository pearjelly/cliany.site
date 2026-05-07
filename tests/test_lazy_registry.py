import json
import sys
from pathlib import Path

import click
import pytest

_V3_METADATA = {
    "schema_version": 3,
    "domain": "lazy.local",
    "generated_at": "2026-05-07T00:00:00Z",
    "generator_version": "1.0.0",
    "commands": [{"name": "search"}],
    "canonical_actions": [],
    "selector_pool": [],
    "smoke": [],
    "heal_history": [],
}

_COMMANDS_PY = """\
import click

@click.group()
def cli():
    pass

@cli.command("search")
@click.option("--query", default="")
def search(query):
    click.echo(query)
"""

_COMMANDS_PY_MINIMAL = "import click\n\n@click.group()\ndef cli():\n    pass\n"


def _make_adapter(adapters_dir: Path, domain: str, metadata: dict, commands_src: str = _COMMANDS_PY_MINIMAL) -> Path:
    adapter_dir = adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)
    (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (adapter_dir / "commands.py").write_text(commands_src, encoding="utf-8")
    return adapter_dir


def test_discover_no_command_import(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    domain = _V3_METADATA["domain"]
    _make_adapter(adapters_dir, domain, _V3_METADATA, _COMMANDS_PY)

    module_name = f"cliany_site_adapters.{domain.replace('.', '_').replace('-', '_')}"
    sys.modules.pop(module_name, None)

    registry = LazyAdapterRegistry(adapters_dir)
    discovered = registry.discover()

    assert domain in discovered
    assert module_name not in sys.modules


def test_get_triggers_import(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    domain = _V3_METADATA["domain"]
    _make_adapter(adapters_dir, domain, _V3_METADATA, _COMMANDS_PY)

    registry = LazyAdapterRegistry(adapters_dir)
    cmd = registry.get(domain, "search")

    assert cmd is not None
    assert isinstance(cmd, click.Command)


def test_get_triggers_import_callable(tmp_path):
    from click.testing import CliRunner

    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    domain = _V3_METADATA["domain"]
    _make_adapter(adapters_dir, domain, _V3_METADATA, _COMMANDS_PY)

    registry = LazyAdapterRegistry(adapters_dir)
    cmd = registry.get(domain, "search")

    runner = CliRunner()
    result = runner.invoke(cmd, ["--query", "hello"])
    assert result.exit_code == 0
    assert "hello" in result.output


def test_legacy_v2_skipped(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    domain = "old.local"
    v2_meta = {"schema_version": 2, "domain": domain, "commands": []}
    _make_adapter(adapters_dir, domain, v2_meta)

    registry = LazyAdapterRegistry(adapters_dir)
    discovered = registry.discover()

    assert domain not in discovered


def test_legacy_v1_skipped(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    domain = "veryold.local"
    v1_meta = {"schema_version": "1", "domain": domain, "commands": []}
    _make_adapter(adapters_dir, domain, v1_meta)

    registry = LazyAdapterRegistry(adapters_dir)
    discovered = registry.discover()

    assert domain not in discovered


def test_discover_caches_result(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    domain = _V3_METADATA["domain"]
    _make_adapter(adapters_dir, domain, _V3_METADATA, _COMMANDS_PY)

    registry = LazyAdapterRegistry(adapters_dir)
    first = registry.discover()
    second = registry.discover()

    assert first is second


def test_get_caches_module(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    domain = _V3_METADATA["domain"]
    _make_adapter(adapters_dir, domain, _V3_METADATA, _COMMANDS_PY)

    registry = LazyAdapterRegistry(adapters_dir)
    registry.get(domain, "search")
    registry.get(domain, "search")

    assert domain in registry._cache


def test_get_unknown_command_returns_none(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    domain = _V3_METADATA["domain"]
    _make_adapter(adapters_dir, domain, _V3_METADATA, _COMMANDS_PY)

    registry = LazyAdapterRegistry(adapters_dir)
    result = registry.get(domain, "nonexistent")

    assert result is None


def test_get_missing_commands_py_returns_none(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    domain = "no-commands.local"
    adapter_dir = adapters_dir / domain
    adapter_dir.mkdir(parents=True)
    (adapter_dir / "metadata.json").write_text(json.dumps({**_V3_METADATA, "domain": domain}))

    registry = LazyAdapterRegistry(adapters_dir)
    result = registry.get(domain, "search")

    assert result is None


def test_domains_returns_v3_list(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "adapters"
    v3_domain = "v3.local"
    legacy_domain = "legacy.local"

    _make_adapter(adapters_dir, v3_domain, {**_V3_METADATA, "domain": v3_domain})
    _make_adapter(adapters_dir, legacy_domain, {"schema_version": 2, "domain": legacy_domain, "commands": []})

    registry = LazyAdapterRegistry(adapters_dir)
    domains = registry.domains()

    assert v3_domain in domains
    assert legacy_domain not in domains


def test_discover_empty_when_dir_missing(tmp_path):
    from cliany_site.loader import LazyAdapterRegistry

    adapters_dir = tmp_path / "nonexistent"

    registry = LazyAdapterRegistry(adapters_dir)
    discovered = registry.discover()

    assert discovered == {}
