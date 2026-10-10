"""L3.5 跨模块集成测试 — 验证模块间协作路径，不依赖 Chrome/LLM 外部服务。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cliany_site.config import reset_config


class TestSDKIntegration:
    """SDK 模块集成"""

    def test_sdk_class_instantiation(self):
        from cliany_site.sdk import ClanySite

        sdk = ClanySite()
        assert sdk is not None

    @patch("cliany_site.sdk.get_config")
    def test_sdk_sync_list_adapters(self, mock_get_config, tmp_path):
        cfg = MagicMock()
        cfg.home_dir = tmp_path
        cfg.adapters_dir = tmp_path / "adapters"
        cfg.sessions_dir = tmp_path / "sessions"
        cfg.reports_dir = tmp_path / "reports"
        cfg.logs_dir = tmp_path / "logs"
        cfg.activity_log_path = tmp_path / "activity.log"
        cfg.cdp_port = 9222
        cfg.adapters_dir.mkdir(parents=True, exist_ok=True)
        cfg.sessions_dir.mkdir(parents=True, exist_ok=True)
        cfg.to_dict.return_value = {"cdp_port": 9222, "home_dir": str(tmp_path)}
        mock_get_config.return_value = cfg

        from cliany_site.sdk import list_adapters

        result = list_adapters()
        assert isinstance(result, dict)
        assert "success" in result


class TestSecurityIntegration:
    """安全模块跨组件集成"""

    def test_encrypt_decrypt_roundtrip(self, tmp_path, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_HOME", str(tmp_path))
        monkeypatch.setattr("cliany_site.security._load_key_from_keyring", lambda: None)
        monkeypatch.setattr("cliany_site.security._save_key_to_keyring", lambda _key: False)
        reset_config()

        from cliany_site.security import decrypt_data, encrypt_data

        original = {"cookies": [{"name": "token", "value": "abc123"}]}
        plaintext = json.dumps(original, ensure_ascii=False)
        encrypted = encrypt_data(plaintext)
        assert encrypted != plaintext.encode()

        decrypted_str = decrypt_data(encrypted)
        decrypted = json.loads(decrypted_str)
        assert decrypted == original

    def test_encrypted_data_has_header(self, tmp_path, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_HOME", str(tmp_path))
        monkeypatch.setattr("cliany_site.security._load_key_from_keyring", lambda: None)
        monkeypatch.setattr("cliany_site.security._save_key_to_keyring", lambda _key: False)
        reset_config()

        from cliany_site.security import encrypt_data, is_encrypted

        encrypted = encrypt_data("test data")
        assert is_encrypted(encrypted)
        assert encrypted.startswith(b"CLIANY_ENC_V1:")

    def test_audit_detects_dangerous_patterns(self):
        from cliany_site.audit import audit_source

        dangerous_code = 'import os\nresult = eval(user_input)\nos.system("rm -rf /")\n'
        findings = audit_source(dangerous_code)
        assert len(findings) > 0
        categories = [f.category for f in findings]
        assert any("dangerous_call" in c for c in categories)

    def test_audit_passes_clean_code(self):
        from cliany_site.audit import audit_source

        clean_code = 'import click\n\n@click.command()\ndef hello():\n    click.echo("Hello World")\n'
        findings = audit_source(clean_code)
        assert len(findings) == 0

    def test_audit_reports_severity_and_location(self):
        from cliany_site.audit import audit_source

        findings = audit_source("exec(code)")
        assert len(findings) == 1
        f = findings[0]
        assert f.severity == "critical"
        assert f.category == "dangerous_call"
        assert f.line > 0
        assert f.col >= 0

    def test_sandbox_blocks_cross_domain(self):
        from cliany_site.sandbox import SandboxPolicy

        policy = SandboxPolicy.from_domain("github.com")
        assert policy.enabled is True
        assert "github.com" in policy.allowed_domains

    def test_sandbox_blocks_dangerous_urls(self):
        from cliany_site.sandbox import SandboxPolicy, SandboxViolation, validate_navigation

        policy = SandboxPolicy.from_domain("github.com")
        with pytest.raises(SandboxViolation):
            validate_navigation("javascript:alert(1)", policy)
        with pytest.raises(SandboxViolation):
            validate_navigation("file:///etc/passwd", policy)


class TestMarketplaceIntegration:
    """适配器市场打包 → 安装往返"""

    @patch("cliany_site.marketplace.get_config")
    def test_pack_and_install_roundtrip(self, mock_cfg, tmp_path, monkeypatch):
        cfg = MagicMock()
        cfg.adapters_dir = tmp_path / "adapters"
        cfg.home_dir = tmp_path
        mock_cfg.return_value = cfg

        from cliany_site.marketplace import install_adapter, pack_adapter

        adapter_dir = tmp_path / "adapters" / "test-roundtrip.com"
        adapter_dir.mkdir(parents=True)
        (adapter_dir / "commands.py").write_text("import click\n\n@click.group()\ndef cli():\n    pass\n")
        (adapter_dir / "metadata.json").write_text(json.dumps({"domain": "test-roundtrip.com", "commands": []}))

        pack_path = pack_adapter("test-roundtrip.com", version="1.0.0")
        assert pack_path.exists()
        assert ".tar.gz" in str(pack_path)

        manifest = install_adapter(str(pack_path), force=True)
        assert manifest.domain == "test-roundtrip.com"
        assert manifest.version == "1.0.0"


class TestWorkflowIntegration:
    """工作流解析 + 批量数据"""

    def test_yaml_parse_valid_workflow(self, tmp_path):
        from cliany_site.workflow.parser import load_workflow_file

        yaml_content = (
            "name: 测试工作流\n"
            "description: 集成测试用\n"
            "steps:\n"
            "  - name: 第一步\n"
            "    adapter: example.com\n"
            "    command: search\n"
            "    params:\n"
            "      query: test\n"
            "  - name: 第二步\n"
            "    adapter: example.com\n"
            "    command: view\n"
            "    params:\n"
            '      id: "123"\n'
        )
        yaml_file = tmp_path / "test_workflow.yaml"
        yaml_file.write_text(yaml_content)

        workflow = load_workflow_file(str(yaml_file))
        assert workflow.name == "测试工作流"
        assert len(workflow.steps) == 2
        assert workflow.steps[0].adapter == "example.com"
        assert workflow.steps[0].params == {"query": "test"}

    def test_yaml_parse_invalid_workflow(self, tmp_path):
        from cliany_site.workflow.parser import WorkflowParseError, load_workflow_file

        yaml_content = "steps:\n  - adapter: example.com\n"
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(WorkflowParseError):
            load_workflow_file(str(yaml_file))

    def test_batch_data_csv_parse(self, tmp_path):
        from cliany_site.workflow.batch import load_batch_data

        csv_content = "query,limit\ntest1,10\ntest2,20\n"
        csv_file = tmp_path / "batch.csv"
        csv_file.write_text(csv_content)

        data = load_batch_data(str(csv_file))
        assert len(data) == 2
        assert data[0]["query"] == "test1"
        assert data[1]["limit"] == "20"

    def test_batch_data_json_parse(self, tmp_path):
        from cliany_site.workflow.batch import load_batch_data

        json_content = json.dumps(
            [
                {"query": "test1", "limit": 10},
                {"query": "test2", "limit": 20},
            ]
        )
        json_file = tmp_path / "batch.json"
        json_file.write_text(json_content)

        data = load_batch_data(str(json_file))
        assert len(data) == 2

    def test_batch_data_unsupported_format(self, tmp_path):
        from cliany_site.workflow.batch import BatchDataError, load_batch_data

        txt_file = tmp_path / "data.txt"
        txt_file.write_text("not supported")
        with pytest.raises(BatchDataError):
            load_batch_data(str(txt_file))


class TestAxtreeIntegration:
    """AXTree 序列化"""

    def test_serialize_axtree_with_element_tree(self):
        from cliany_site.browser.axtree import serialize_axtree

        mock_tree = {
            "element_tree": "[1] button 'Submit'\n[2] link 'Home'",
            "selector_map": {},
        }
        result = serialize_axtree(mock_tree)
        assert isinstance(result, str)
        assert "Submit" in result
        assert "Home" in result

    def test_serialize_axtree_empty(self):
        from cliany_site.browser.axtree import serialize_axtree

        result = serialize_axtree({})
        assert "empty" in result.lower()

    def test_serialize_axtree_truncation(self):
        from cliany_site.browser.axtree import MAX_CHARS, serialize_axtree

        long_tree = {"element_tree": "x" * (MAX_CHARS + 1000)}
        result = serialize_axtree(long_tree)
        assert "truncated" in result
