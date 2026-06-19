from __future__ import annotations

import hashlib
import json
import pathlib

import jsonschema
import pytest

from cliany_site.codegen.generator import save_adapter
from cliany_site.errors import SecurityError
from cliany_site.explorer.models import CommandSuggestion, ExploreResult

_MINIMAL_CODE = """\
# 自动生成 — DO NOT EDIT
# 生成时间: 2026-01-01T00:00:00+00:00
# 来源 URL: https://test.com
# 工作流: test-workflow

import click

@click.group()
def cli():
    pass

@cli.command("search")
def search():
    pass
"""

_SCHEMA_PATH = pathlib.Path("schemas/metadata.v3.json")


def _make_explore_result(command_names: list[str] | None = None) -> ExploreResult:
    commands = [
        CommandSuggestion(name=n, description=n, args=[], action_steps=[])
        for n in (command_names or [])
    ]
    return ExploreResult(commands=commands)


class TestV3FieldsPresent:
    def test_axtree_field_present(self, tmp_home):
        save_adapter("test.com", _MINIMAL_CODE)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        assert "axtree" in meta

    def test_axtree_has_compounds(self, tmp_home):
        save_adapter("test.com", _MINIMAL_CODE)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        assert "compounds" in meta["axtree"]

    def test_axtree_has_pruning_meta(self, tmp_home):
        save_adapter("test.com", _MINIMAL_CODE)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        assert "pruning_meta" in meta["axtree"]

    def test_capability_is_browser_string(self, tmp_home):
        save_adapter("test.com", _MINIMAL_CODE)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        assert meta["capability"] == "browser"

    def test_api_endpoints_is_empty_list(self, tmp_home):
        save_adapter("test.com", _MINIMAL_CODE)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        assert meta["api_endpoints"] == []

    def test_signature_present(self, tmp_home):
        save_adapter("test.com", _MINIMAL_CODE)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        assert "signature" in meta

    def test_signature_is_64_char_hex(self, tmp_home):
        save_adapter("test.com", _MINIMAL_CODE)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        sig = meta["signature"]
        assert isinstance(sig, str)
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)


class TestSignatureCorrectness:
    def test_signature_matches_commands_py_hash(self, tmp_home):
        save_adapter("test.com", _MINIMAL_CODE)
        meta_path = tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json"
        commands_path = tmp_home / ".cliany-site" / "adapters" / "test.com" / "commands.py"
        meta = json.loads(meta_path.read_text())
        expected = hashlib.sha256(commands_path.read_bytes()).hexdigest()
        assert meta["signature"] == expected

    def test_different_code_different_signature(self, tmp_home):
        code_a = _MINIMAL_CODE
        code_b = _MINIMAL_CODE + "\n# extra line\n"
        save_adapter("domain-a.com", code_a)
        save_adapter("domain-b.com", code_b)
        meta_a = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "domain-a.com" / "metadata.json").read_text()
        )
        meta_b = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "domain-b.com" / "metadata.json").read_text()
        )
        assert meta_a["signature"] != meta_b["signature"]


class TestSaveAdapterAudit:
    def test_blocks_critical_audit_findings_before_writing_commands(self, tmp_home):
        dangerous_code = _MINIMAL_CODE + "\nresult = eval('1 + 1')\n"

        with pytest.raises(SecurityError, match="安全审计未通过"):
            save_adapter("evil.com", dangerous_code)

        commands_path = tmp_home / ".cliany-site" / "adapters" / "evil.com" / "commands.py"
        assert not commands_path.exists()


class TestV3DefaultAxtreeValues:
    def test_axtree_compounds_defaults_to_empty_dict(self, tmp_home):
        explore_result = _make_explore_result(["search"])
        save_adapter("test.com", _MINIMAL_CODE, explore_result=explore_result)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        assert meta["axtree"]["compounds"] == {}

    def test_axtree_pruning_meta_defaults_with_zeros(self, tmp_home):
        explore_result = _make_explore_result(["search"])
        save_adapter("test.com", _MINIMAL_CODE, explore_result=explore_result)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        pm = meta["axtree"]["pruning_meta"]
        assert pm["original_count"] == 0
        assert pm["pruned_count"] == 0
        assert pm["pruning_ratio"] == 0.0


class TestV3SchemaValidation:
    def test_metadata_v3_schema_valid(self, tmp_home):
        schema = json.loads(_SCHEMA_PATH.read_text())
        explore_result = _make_explore_result(["search"])
        save_adapter("test.com", _MINIMAL_CODE, explore_result=explore_result)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        jsonschema.validate(meta, schema)


class TestV3BackwardCompatibility:
    def test_v2_fields_still_present(self, tmp_home):
        explore_result = _make_explore_result(["search"])
        save_adapter("test.com", _MINIMAL_CODE, explore_result=explore_result)
        meta = json.loads(
            (tmp_home / ".cliany-site" / "adapters" / "test.com" / "metadata.json").read_text()
        )
        assert meta["schema_version"] == 3
        assert "domain" in meta
        assert "generated_at" in meta
        assert "generator_version" in meta
        assert "commands" in meta
        assert "canonical_actions" in meta
        assert "selector_pool" in meta
        assert "smoke" in meta
        assert "heal_history" in meta
