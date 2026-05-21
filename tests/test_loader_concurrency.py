# pyright: reportMissingImports=false
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from cliany_site.codegen.generator import METADATA_SCHEMA_VERSION
from cliany_site.loader import LazyAdapterRegistry, load_or_rebuild


def _empty_manifest() -> dict:
    return {
        "schema_version": METADATA_SCHEMA_VERSION,
        "generated_at": "2026-05-21T00:00:00+00:00",
        "adapters": {},
    }


def test_concurrent_load_or_rebuild_no_corruption(tmp_path):
    manifest_file = tmp_path / "cli-manifest.json"
    registry = LazyAdapterRegistry(tmp_path / "adapters")

    with patch("cliany_site.loader.manifest_path", return_value=manifest_file):
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: load_or_rebuild(registry), range(5)))

    for result in results:
        assert isinstance(result, dict)
        json.loads(json.dumps(result))

    json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest_file.with_suffix(".lock").exists()


def test_load_or_rebuild_propagates_syntax_error(tmp_path):
    manifest_file = tmp_path / "cli-manifest.json"
    registry = LazyAdapterRegistry(tmp_path / "adapters")

    with patch("cliany_site.loader.manifest_path", return_value=manifest_file):
        with patch("cliany_site.loader.build_manifest", side_effect=SyntaxError("bad syntax in adapter")):
            with pytest.raises(SyntaxError, match="bad syntax in adapter"):
                load_or_rebuild(registry)


def test_manifest_write_is_atomic(tmp_path):
    manifest_file = tmp_path / "cli-manifest.json"
    original_manifest = _empty_manifest() | {"generated_at": "original"}
    manifest_file.write_text(json.dumps(original_manifest), encoding="utf-8")
    registry = LazyAdapterRegistry(tmp_path / "adapters")

    with patch("cliany_site.loader.manifest_path", return_value=manifest_file):
        with patch("cliany_site.loader.validate_manifest", return_value=False):
            with patch("cliany_site.loader.os.replace", side_effect=OSError("replace failed")):
                result = load_or_rebuild(registry)

    assert result["schema_version"] == METADATA_SCHEMA_VERSION
    assert json.loads(manifest_file.read_text(encoding="utf-8")) == original_manifest
    assert list(tmp_path.glob("*.tmp")) == []
