from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "legacy_v2_adapter"


def _make_v2_adapter(adapters_dir: Path, domain: str = "example.com") -> Path:
    adapter_dir = adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURE_DIR / "metadata.json", adapter_dir / "metadata.json")
    shutil.copy2(FIXTURE_DIR / "commands.py", adapter_dir / "commands.py")
    return adapter_dir


def _make_v3_adapter(adapters_dir: Path, domain: str, commands_py_content: str) -> Path:
    adapter_dir = adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)
    commands_py = adapter_dir / "commands.py"
    commands_py.write_text(commands_py_content, encoding="utf-8")
    sig = hashlib.sha256(commands_py.read_bytes()).hexdigest()
    metadata = {
        "schema_version": 3,
        "domain": domain,
        "generated_at": "2024-01-01T00:00:00Z",
        "generator_version": "1.0.0",
        "commands": [],
        "signature": sig,
        "capability": "browser",
        "api_endpoints": [],
        "axtree": {
            "compounds": {},
            "pruning_meta": {"original_count": 0, "pruned_count": 0, "pruning_ratio": 0.0},
        },
    }
    (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return adapter_dir


def test_migrate_v2_happy_path(tmp_home):
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir = _make_v2_adapter(adapters_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["migrate", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert data["ok"] is True
    assert "example.com" in data["data"]["migrated"]
    assert data["data"]["skipped"] == []
    assert data["data"]["warnings"] == []

    metadata_path = adapter_dir / "metadata.json"
    bak_path = adapter_dir / "metadata.json.bak"
    assert bak_path.exists()

    new_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert new_metadata["schema_version"] == 3
    assert "signature" in new_metadata
    assert len(new_metadata["signature"]) == 64

    expected_sig = hashlib.sha256((adapter_dir / "commands.py").read_bytes()).hexdigest()
    assert new_metadata["signature"] == expected_sig

    assert new_metadata["capability"] == "browser"
    assert new_metadata["api_endpoints"] == []
    assert new_metadata["axtree"]["compounds"] == {}
    assert new_metadata["axtree"]["pruning_meta"]["original_count"] == 0


def test_migrate_v3_already_skip(tmp_home):
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True, exist_ok=True)
    _make_v3_adapter(adapters_dir, "already.com", "import click\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["migrate", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["migrated"] == []
    assert "already.com" in data["data"]["skipped"]
    assert data["data"]["warnings"] == []


def test_migrate_v3_drift_warning(tmp_home):
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir = _make_v3_adapter(adapters_dir, "drifted.com", "import click\n")

    (adapter_dir / "commands.py").write_text("import click\n# modified\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["migrate", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert data["ok"] is True
    assert "drifted.com" in data["data"]["skipped"]
    assert any("drift" in w for w in data["data"]["warnings"])


def test_migrate_no_adapters(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["migrate", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["migrated"] == []
    assert data["data"]["skipped"] == []
    assert data["data"]["warnings"] == []


def test_migrate_bak_preserved(tmp_home):
    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir = _make_v2_adapter(adapters_dir)

    original_metadata = json.loads((adapter_dir / "metadata.json").read_text(encoding="utf-8"))

    runner = CliRunner()
    runner.invoke(cli, ["migrate", "--json"])

    bak = json.loads((adapter_dir / "metadata.json.bak").read_text(encoding="utf-8"))
    assert bak["schema_version"] == original_metadata["schema_version"]
    assert bak["domain"] == original_metadata["domain"]
