from __future__ import annotations

import hashlib
import json

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.commands import verify as verify_module
from cliany_site.errors import ADAPTER_NOT_FOUND

VALID_V3_METADATA = {
    "schema_version": 3,
    "domain": "test.com",
    "generated_at": "2024-01-01T00:00:00Z",
    "generator_version": "1.0.0",
    "commands": [{"name": "search"}],
}

SAFE_COMMANDS_PY = "import click\n\n@click.group()\ndef cli():\n    pass\n"

UNSAFE_COMMANDS_PY = (
    "import click\n\n@click.group()\ndef cli():\n    eval('1+1')\n"
)

NON_GROUP_COMMANDS_PY = "import click\n\ncli = click.Command('not-a-group')\n"


@pytest.fixture()
def adapters_dir(tmp_home):
    d = tmp_home / ".cliany-site" / "adapters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_adapter(adapters_dir, domain: str, metadata: dict, commands_py: str = SAFE_COMMANDS_PY):
    adapter_dir = adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)
    (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (adapter_dir / "commands.py").write_text(commands_py, encoding="utf-8")
    return adapter_dir


def _write_manifest(adapter_dir, domain: str, *, manifest_domain: str | None = None, bad_hash: bool = False):
    commands_hash = hashlib.sha256((adapter_dir / "commands.py").read_bytes()).hexdigest()
    metadata_hash = hashlib.sha256((adapter_dir / "metadata.json").read_bytes()).hexdigest()
    if bad_hash:
        metadata_hash = "0" * 64

    manifest = {
        "manifest_version": "1",
        "domain": manifest_domain or domain,
        "version": "1.0.0",
        "files": ["commands.py", "metadata.json"],
        "file_hashes": {
            "commands.py": commands_hash,
            "metadata.json": metadata_hash,
        },
    }
    (adapter_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_verify_missing_explicit_adapter_returns_not_found(tmp_home, no_llm):
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "nonexistent.com"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["code"] == ADAPTER_NOT_FOUND
    assert data["error"]["details"] == {"domain": "nonexistent.com"}
    assert "--dry-run" in data["error"]["hint"]
    assert "移除" in data["error"]["hint"]


def test_verify_all_no_adapters_returns_empty_success(tmp_home, no_llm):
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["domain"] == "all"
    assert data["data"]["results"] == []


def test_verify_ok_adapter(tmp_home, no_llm, adapters_dir):
    _make_adapter(adapters_dir, "test.com", VALID_V3_METADATA, SAFE_COMMANDS_PY)
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "test.com"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    results = data["data"]["results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "ok"
    assert results[0]["domain"] == "test.com"
    assert results[0]["issues"] == []
    assert results[0]["manifest"]["status"] == "missing"


def test_verify_strict_ok_adapter(tmp_home, no_llm, adapters_dir):
    _make_adapter(adapters_dir, "test.com", VALID_V3_METADATA, SAFE_COMMANDS_PY)
    runner = CliRunner()

    result = runner.invoke(cli, ["verify", "test.com", "--strict", "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["results"][0]["verdict"] == "ok"


@pytest.mark.parametrize(
    ("domain", "make_commands_directory", "expected_issue"),
    [
        ("missing-commands.com", False, "commands.py 不存在"),
        ("commands-directory.com", True, "commands.py 不是可加载的普通文件"),
    ],
)
def test_verify_reports_unloadable_commands_file_without_breaking_default_diagnostics(
    tmp_home,
    no_llm,
    adapters_dir,
    domain,
    make_commands_directory,
    expected_issue,
):
    adapter_dir = _make_adapter(adapters_dir, domain, VALID_V3_METADATA | {"domain": domain})
    commands_path = adapter_dir / "commands.py"
    commands_path.unlink()
    if make_commands_directory:
        commands_path.mkdir()

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", domain, "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    verified = data["data"]["results"][0]
    assert verified["verdict"] == "commands_missing"
    assert verified["issues"] == [expected_issue]


@pytest.mark.parametrize(
    ("domain", "make_commands_directory"),
    [
        ("missing-commands.com", False),
        ("commands-directory.com", True),
    ],
)
def test_verify_strict_rejects_unloadable_commands_file(
    tmp_home,
    no_llm,
    adapters_dir,
    domain,
    make_commands_directory,
):
    adapter_dir = _make_adapter(adapters_dir, domain, VALID_V3_METADATA | {"domain": domain})
    commands_path = adapter_dir / "commands.py"
    commands_path.unlink()
    if make_commands_directory:
        commands_path.mkdir()

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", domain, "--strict", "--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["code"] == "E_VERIFY_STATIC"
    verified = data["error"]["details"]["results"][0]
    assert verified["verdict"] == "commands_missing"


def test_verify_strict_rejects_commands_that_runtime_cannot_register(tmp_home, no_llm, adapters_dir):
    _make_adapter(
        adapters_dir,
        "non-group.com",
        VALID_V3_METADATA | {"domain": "non-group.com"},
        NON_GROUP_COMMANDS_PY,
    )
    runner = CliRunner()

    diagnostic = runner.invoke(cli, ["verify", "non-group.com", "--json"])
    strict = runner.invoke(cli, ["verify", "non-group.com", "--strict", "--json"])

    assert diagnostic.exit_code == 0
    diagnostic_result = json.loads(diagnostic.output)["data"]["results"][0]
    assert diagnostic_result["verdict"] == "commands_unloadable"
    assert diagnostic_result["issues"] == ["commands.py 必须导出 click.Group 类型的 cli"]

    assert strict.exit_code == 1
    strict_result = json.loads(strict.output)
    assert strict_result["error"]["code"] == "E_VERIFY_STATIC"
    assert strict_result["error"]["details"]["results"][0]["verdict"] == "commands_unloadable"


def test_verify_security_issue(tmp_home, no_llm, adapters_dir):
    _make_adapter(adapters_dir, "evil.com", VALID_V3_METADATA, UNSAFE_COMMANDS_PY)
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "evil.com"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    results = data["data"]["results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "security_issue"
    assert len(results[0]["issues"]) > 0
    assert any("eval(" in issue for issue in results[0]["issues"])


def test_verify_strict_security_issue_returns_failure_envelope(tmp_home, no_llm, adapters_dir):
    _make_adapter(adapters_dir, "evil.com", VALID_V3_METADATA, UNSAFE_COMMANDS_PY)
    runner = CliRunner()

    result = runner.invoke(cli, ["verify", "evil.com", "--strict", "--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["code"] == "E_VERIFY_STATIC"
    assert data["error"]["details"]["failed_domains"] == ["evil.com"]
    assert data["error"]["details"]["results"][0]["verdict"] == "security_issue"


def test_verify_market_manifest_ok(tmp_home, no_llm, adapters_dir):
    adapter_dir = _make_adapter(adapters_dir, "market-ok.com", VALID_V3_METADATA | {"domain": "market-ok.com"})
    _write_manifest(adapter_dir, "market-ok.com")

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "market-ok.com"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    verified = data["data"]["results"][0]
    assert verified["verdict"] == "ok"
    assert verified["manifest"]["status"] == "ok"
    assert verified["manifest"]["issues"] == []


def test_verify_accepts_api_capability_with_legacy_endpoint_strings(tmp_home, no_llm, adapters_dir):
    metadata = VALID_V3_METADATA | {
        "domain": "api.example",
        "capability": "api",
        "api_endpoints": ["https://api.example/v1/search"],
    }
    adapter_dir = _make_adapter(adapters_dir, "api.example", metadata)
    _write_manifest(adapter_dir, "api.example")

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "api.example"])

    assert result.exit_code == 0, result.output
    verified = json.loads(result.output)["data"]["results"][0]
    assert verified["verdict"] == "ok"
    assert verified["manifest"]["status"] == "ok"


def test_verify_accepts_api_capability_with_legacy_command_strings(tmp_home, no_llm, adapters_dir):
    metadata = VALID_V3_METADATA | {
        "domain": "api.example",
        "capability": "api",
        "commands": ["list-issues"],
        "api_endpoints": ["https://api.example/v1/search"],
    }
    adapter_dir = _make_adapter(adapters_dir, "api.example", metadata)
    _write_manifest(adapter_dir, "api.example")

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "api.example"])

    assert result.exit_code == 0, result.output
    verified = json.loads(result.output)["data"]["results"][0]
    assert verified["verdict"] == "ok"
    assert verified["manifest"]["status"] == "ok"


def test_verify_manifest_hash_mismatch(tmp_home, no_llm, adapters_dir):
    adapter_dir = _make_adapter(adapters_dir, "hash-bad.com", VALID_V3_METADATA | {"domain": "hash-bad.com"})
    _write_manifest(adapter_dir, "hash-bad.com", bad_hash=True)

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "hash-bad.com"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    verified = data["data"]["results"][0]
    assert verified["verdict"] == "manifest_error"
    assert verified["manifest"]["status"] == "error"
    assert any("文件哈希不匹配: metadata.json" in issue for issue in verified["issues"])


def test_verify_strict_manifest_hash_mismatch_returns_failure_envelope(tmp_home, no_llm, adapters_dir):
    adapter_dir = _make_adapter(
        adapters_dir,
        "hash-bad.com",
        VALID_V3_METADATA | {"domain": "hash-bad.com"},
    )
    _write_manifest(adapter_dir, "hash-bad.com", bad_hash=True)
    runner = CliRunner()

    result = runner.invoke(cli, ["verify", "hash-bad.com", "--strict", "--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["code"] == "E_VERIFY_STATIC"
    verified = data["error"]["details"]["results"][0]
    assert verified["verdict"] == "manifest_error"
    assert any("文件哈希不匹配: metadata.json" in issue for issue in verified["issues"])


def test_verify_manifest_domain_mismatch(tmp_home, no_llm, adapters_dir):
    adapter_dir = _make_adapter(adapters_dir, "domain-bad.com", VALID_V3_METADATA | {"domain": "domain-bad.com"})
    _write_manifest(adapter_dir, "domain-bad.com", manifest_domain="other.com")

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "domain-bad.com"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    verified = data["data"]["results"][0]
    assert verified["verdict"] == "manifest_error"
    assert any("manifest.domain" in issue for issue in verified["issues"])


def test_verify_legacy_adapter(tmp_home, no_llm, adapters_dir):
    legacy_metadata = {"domain": "old.com", "commands": []}
    _make_adapter(adapters_dir, "old.com", legacy_metadata, SAFE_COMMANDS_PY)
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json", "old.com"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    results = data["data"]["results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "legacy_adapter"


def test_verify_strict_legacy_adapter_returns_failure_envelope(tmp_home, no_llm, adapters_dir):
    _make_adapter(adapters_dir, "old.com", {"domain": "old.com", "commands": []}, SAFE_COMMANDS_PY)
    runner = CliRunner()

    result = runner.invoke(cli, ["verify", "old.com", "--strict", "--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["error"]["code"] == "E_VERIFY_STATIC"
    assert data["error"]["details"]["results"][0]["verdict"] == "legacy_adapter"


def test_verify_strict_schema_error_returns_failure_envelope(tmp_home, no_llm, adapters_dir):
    invalid_metadata = {
        "schema_version": 3,
        "domain": "schema-bad.com",
        "generated_at": "2024-01-01T00:00:00Z",
        "generator_version": "1.0.0",
    }
    _make_adapter(adapters_dir, "schema-bad.com", invalid_metadata, SAFE_COMMANDS_PY)
    runner = CliRunner()

    result = runner.invoke(cli, ["verify", "schema-bad.com", "--strict", "--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["error"]["code"] == "E_VERIFY_STATIC"
    assert data["error"]["details"]["results"][0]["verdict"] == "schema_error"


def test_verify_strict_smoke_failure_returns_failure_envelope(tmp_home, no_llm, adapters_dir, monkeypatch):
    _make_adapter(adapters_dir, "test.com", VALID_V3_METADATA, SAFE_COMMANDS_PY)
    monkeypatch.setattr(verify_module, "_run_smoke", lambda _domain: False)
    runner = CliRunner()

    result = runner.invoke(cli, ["verify", "test.com", "--smoke", "--strict", "--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["error"]["code"] == "E_VERIFY_SMOKE"
    assert data["error"]["details"]["results"][0]["verdict"] == "smoke_failed"


def test_verify_all_adapters(tmp_home, no_llm, adapters_dir):
    _make_adapter(adapters_dir, "a.com", VALID_V3_METADATA | {"domain": "a.com"}, SAFE_COMMANDS_PY)
    legacy = {"domain": "b.com", "commands": []}
    _make_adapter(adapters_dir, "b.com", legacy, SAFE_COMMANDS_PY)
    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["domain"] == "all"
    domains = {r["domain"] for r in data["data"]["results"]}
    assert "a.com" in domains
    assert "b.com" in domains
