from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.healer import HealResult, Healer


VALID_V2_METADATA = {
    "schema_version": 2,
    "domain": "test.com",
    "generated_at": "2024-01-01T00:00:00Z",
    "generator_version": "0.9.0",
    "commands": [{"name": "search"}],
}

HEALED_JSON = {
    "schema_version": 2,
    "domain": "test.com",
    "healed_command": "search",
    "new_selectors": {"ref_1": "#new-btn"},
    "new_actions": [{"type": "click", "ref": "ref_1"}],
    "heal_meta": {
        "calls_used": 1,
        "tokens_used": 100,
        "timestamp": "2024-01-01T00:00:00Z",
    },
}

FAILURE_ENVELOPE = {
    "ok": False,
    "version": "1",
    "command": "search",
    "data": None,
    "error": {"code": "E_SELECTOR_NOT_FOUND", "message": "element not found", "hint": None, "details": None},
    "meta": {"duration_ms": 10, "source": "builtin"},
}


@pytest.fixture()
def adapters_dir(tmp_home):
    d = tmp_home / ".cliany-site" / "adapters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_adapter(adapters_dir, domain: str, metadata: dict | None = None, commands_py: str | None = None):
    adapter_dir = adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)
    if metadata is not None:
        (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    if commands_py is not None:
        (adapter_dir / "commands.py").write_text(commands_py, encoding="utf-8")
    return adapter_dir


def test_cap_zero_returns_cap_exceeded(tmp_home):
    healer = Healer()
    result = healer.heal(
        domain="test.com",
        command="search",
        failure_envelope=FAILURE_ENVELOPE,
        max_calls=0,
    )
    assert isinstance(result, HealResult)
    assert result.ok is False
    assert result.error == "E_HEAL_CAP_EXCEEDED"


def test_heal_disable_env_returns_cap_exceeded(monkeypatch, tmp_home):
    monkeypatch.setenv("CLIANY_HEAL_DISABLE", "1")
    healer = Healer()
    result = healer.heal(
        domain="test.com",
        command="search",
        failure_envelope=FAILURE_ENVELOPE,
    )
    assert result.ok is False
    assert result.error == "E_HEAL_CAP_EXCEEDED"


def test_accept_heal_no_healed_json_returns_err(tmp_home, adapters_dir, no_llm):
    _make_adapter(adapters_dir, "test.com", metadata=VALID_V2_METADATA)
    runner = CliRunner()
    result = runner.invoke(cli, ["adapter", "accept-heal", "test.com", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["code"] is not None


def test_accept_heal_valid_healed_json_merges(tmp_home, adapters_dir, no_llm):
    adapter_dir = _make_adapter(adapters_dir, "test.com", metadata=VALID_V2_METADATA)
    (adapter_dir / "metadata.healed.json").write_text(json.dumps(HEALED_JSON), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["adapter", "accept-heal", "test.com", "--json"])
    data = json.loads(result.output)
    assert data["ok"] is True, f"expected ok but got: {data}"
    assert data["data"]["merged"] is True

    updated = json.loads((adapter_dir / "metadata.json").read_text(encoding="utf-8"))
    assert "heal_history" in updated
    assert len(updated["heal_history"]) == 1
    assert not (adapter_dir / "metadata.healed.json").exists()


def test_accept_heal_verify_fails_keeps_healed_json(tmp_home, adapters_dir, no_llm):
    unsafe_py = "import click\n\ndef run():\n    eval('1+1')\n"
    adapter_dir = _make_adapter(
        adapters_dir, "test.com", metadata=VALID_V2_METADATA, commands_py=unsafe_py
    )
    (adapter_dir / "metadata.healed.json").write_text(json.dumps(HEALED_JSON), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["adapter", "accept-heal", "test.com", "--json"])
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["code"] == "E_VERIFY_STATIC"
    assert (adapter_dir / "metadata.healed.json").exists()


def test_run_atom_heal_on_failure_false_no_llm_call(tmp_home, no_llm):
    from cliany_site.codegen.runtime_helpers import run_atom

    envelope = run_atom(["nonexistent-command-xyz"], heal_on_failure=False)
    assert isinstance(envelope, dict)
    assert envelope.get("ok") is False or envelope.get("success") is False
