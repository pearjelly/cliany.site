import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cliany_site.loader import (
    LazyAdapterRegistry,
    build_manifest,
    load_or_rebuild,
    manifest_path,
    validate_manifest,
)

_V3_META = {
    "schema_version": 3,
    "domain": "example.com",
    "generated_at": "2026-01-01T00:00:00Z",
    "generator_version": "1.0.0",
    "commands": [{"name": "search"}, {"name": "view"}],
    "signature": "abc123",
    "canonical_actions": [],
    "selector_pool": [],
    "smoke": [],
    "heal_history": [],
}


def _mock_registry(tmp_path: Path, domains: dict | None = None) -> MagicMock:
    domains = domains or {}
    registry = MagicMock(spec=LazyAdapterRegistry)
    registry._adapters_dir = tmp_path
    registry.discover.return_value = domains
    registry.domains.return_value = list(domains.keys())
    return registry


def test_manifest_path_returns_home_based_path():
    path = manifest_path()
    assert path == Path.home() / ".cliany-site" / "cli-manifest.json"


def test_build_manifest_correct_fields(tmp_path):
    adapter_dir = tmp_path / "example.com"
    adapter_dir.mkdir()
    (adapter_dir / "metadata.json").write_text(json.dumps(_V3_META))

    registry = _mock_registry(tmp_path, {"example.com": _V3_META})
    result = build_manifest(registry)

    assert result["schema_version"] == 3
    assert "generated_at" in result
    assert "adapters" in result
    assert "example.com" in result["adapters"]

    info = result["adapters"]["example.com"]
    assert info["schema_version"] == 3
    assert info["signature"] == "abc123"
    assert info["command_count"] == 2
    assert "last_modified" in info
    assert info["last_modified"] != ""


def test_build_manifest_empty_registry(tmp_path):
    registry = _mock_registry(tmp_path)
    result = build_manifest(registry)

    assert result["schema_version"] == 3
    assert result["adapters"] == {}
    assert "generated_at" in result


def test_build_manifest_missing_metadata_file(tmp_path):
    registry = _mock_registry(tmp_path, {"ghost.com": {"schema_version": 3, "signature": "", "commands": []}})
    result = build_manifest(registry)

    assert "ghost.com" in result["adapters"]
    assert result["adapters"]["ghost.com"]["last_modified"] == ""


def test_validate_manifest_valid():
    registry = _mock_registry(Path("/tmp"), {"example.com": _V3_META})
    manifest = {"schema_version": 3, "generated_at": "2026-01-01T00:00:00Z", "adapters": {"example.com": {}}}
    assert validate_manifest(manifest, registry) is True


def test_validate_manifest_wrong_schema_version():
    registry = _mock_registry(Path("/tmp"))
    assert validate_manifest({"schema_version": 2, "adapters": {}}, registry) is False
    assert validate_manifest({}, registry) is False


def test_validate_manifest_domain_mismatch():
    registry = _mock_registry(Path("/tmp"), {"a.com": {}, "b.com": {}})
    manifest = {"schema_version": 3, "adapters": {"a.com": {}}}
    assert validate_manifest(manifest, registry) is False


def test_validate_manifest_extra_domain_in_manifest():
    registry = _mock_registry(Path("/tmp"), {"a.com": {}})
    manifest = {"schema_version": 3, "adapters": {"a.com": {}, "extra.com": {}}}
    assert validate_manifest(manifest, registry) is False


def test_load_or_rebuild_creates_manifest_when_missing(tmp_path):
    manifest_file = tmp_path / "cli-manifest.json"
    registry = _mock_registry(tmp_path)

    with patch("cliany_site.loader.manifest_path", return_value=manifest_file):
        result = load_or_rebuild(registry)

    assert result["schema_version"] == 3
    assert manifest_file.exists()
    written = json.loads(manifest_file.read_text())
    assert written["schema_version"] == 3


def test_load_or_rebuild_rebuilds_corrupted_json(tmp_path):
    manifest_file = tmp_path / "cli-manifest.json"
    manifest_file.write_text("NOT VALID JSON {{{{")
    registry = _mock_registry(tmp_path)

    with patch("cliany_site.loader.manifest_path", return_value=manifest_file):
        result = load_or_rebuild(registry)

    assert result["schema_version"] == 3
    assert json.loads(manifest_file.read_text())["schema_version"] == 3


def test_load_or_rebuild_rebuilds_on_wrong_schema_version(tmp_path):
    manifest_file = tmp_path / "cli-manifest.json"
    manifest_file.write_text(json.dumps({"schema_version": 2, "adapters": {}}))
    registry = _mock_registry(tmp_path)

    with patch("cliany_site.loader.manifest_path", return_value=manifest_file):
        result = load_or_rebuild(registry)

    assert result["schema_version"] == 3


def test_load_or_rebuild_returns_valid_manifest_without_rebuild(tmp_path):
    manifest_file = tmp_path / "cli-manifest.json"
    manifest_file.write_text(json.dumps({"schema_version": 3, "generated_at": "2026-01-01", "adapters": {}}))
    registry = _mock_registry(tmp_path)

    with patch("cliany_site.loader.manifest_path", return_value=manifest_file):
        result = load_or_rebuild(registry)

    assert result["schema_version"] == 3
    assert result["generated_at"] == "2026-01-01"


def test_load_or_rebuild_does_not_raise_on_exception(tmp_path):
    registry = MagicMock(spec=LazyAdapterRegistry)
    registry._adapters_dir = tmp_path
    registry.domains.side_effect = RuntimeError("boom")
    registry.discover.side_effect = RuntimeError("boom")

    manifest_file = tmp_path / "cli-manifest.json"

    with patch("cliany_site.loader.manifest_path", return_value=manifest_file):
        result = load_or_rebuild(registry)

    assert isinstance(result, dict)
    assert result.get("schema_version") == 3
