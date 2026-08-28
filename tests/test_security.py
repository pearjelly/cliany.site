from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cliany_site.audit import AuditFinding, audit_adapter, audit_file, audit_source
from cliany_site.sandbox import (
    SandboxPolicy,
    SandboxViolation,
    validate_action,
    validate_action_steps,
    validate_navigation,
)
from cliany_site.security import (
    _ENCRYPTED_HEADER,
    decrypt_data,
    encrypt_data,
    is_encrypted,
)

# ── security.py ──────────────────────────────────────────


class TestEncryptDecrypt:
    def test_round_trip(self) -> None:
        from cryptography.fernet import Fernet

        key = Fernet.generate_key()
        plaintext = '{"cookies": [], "domain": "test.com"}'
        encrypted = encrypt_data(plaintext, key=key)
        assert is_encrypted(encrypted)
        result = decrypt_data(encrypted, key=key)
        assert result == plaintext

    def test_encrypted_header_present(self) -> None:
        from cryptography.fernet import Fernet

        key = Fernet.generate_key()
        encrypted = encrypt_data("hello", key=key)
        assert encrypted.startswith(_ENCRYPTED_HEADER)

    def test_decrypt_wrong_key_raises(self) -> None:
        from cryptography.fernet import Fernet

        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        encrypted = encrypt_data("secret", key=key1)
        from cliany_site.errors import SessionError

        with pytest.raises(SessionError, match="解密失败"):
            decrypt_data(encrypted, key=key2)

    def test_decrypt_non_encrypted_raises(self) -> None:
        from cryptography.fernet import Fernet

        from cliany_site.errors import SessionError

        key = Fernet.generate_key()
        with pytest.raises(SessionError, match="不是加密格式"):
            decrypt_data(b"plain json data", key=key)

    def test_is_encrypted_false_for_json(self) -> None:
        assert not is_encrypted(b'{"domain": "test.com"}')

    def test_is_encrypted_true(self) -> None:
        assert is_encrypted(_ENCRYPTED_HEADER + b"some_token_data")


class TestEncryptedSession:
    def test_save_and_load(self, tmp_path: Path) -> None:
        with patch("cliany_site.security.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.sessions_dir = tmp_path / "sessions"
            cfg.home_dir = tmp_path
            mock_cfg.return_value = cfg

            from cliany_site.security import load_encrypted_session, save_encrypted_session

            with patch("cliany_site.security.get_encryption_key") as mock_key:
                from cryptography.fernet import Fernet

                key = Fernet.generate_key()
                mock_key.return_value = key

                path = save_encrypted_session("test.com", {"cookies": [{"name": "sid", "value": "abc"}]})
                assert Path(path).exists()

                data = load_encrypted_session("test.com")
                assert data is not None
                assert data["domain"] == "test.com"
                assert len(data["cookies"]) == 1

    def test_load_plaintext_migration(self, tmp_path: Path) -> None:
        with patch("cliany_site.security.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.sessions_dir = tmp_path / "sessions"
            cfg.home_dir = tmp_path
            mock_cfg.return_value = cfg

            sessions_dir = tmp_path / "sessions"
            sessions_dir.mkdir(parents=True)
            plain_file = sessions_dir / "old.com.json"
            plain_file.write_text(json.dumps({"domain": "old.com", "cookies": []}))

            from cliany_site.security import load_encrypted_session

            with patch("cliany_site.security.get_encryption_key") as mock_key:
                from cryptography.fernet import Fernet

                mock_key.return_value = Fernet.generate_key()
                data = load_encrypted_session("old.com")
                assert data is not None
                assert data["domain"] == "old.com"

                raw = plain_file.read_bytes()
                assert is_encrypted(raw)

    def test_load_nonexistent_returns_none(self, tmp_path: Path) -> None:
        with patch("cliany_site.security.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.sessions_dir = tmp_path / "sessions"
            cfg.home_dir = tmp_path
            mock_cfg.return_value = cfg

            from cliany_site.security import load_encrypted_session

            assert load_encrypted_session("nonexist.com") is None


# ── sandbox.py ───────────────────────────────────────────


class TestSandboxPolicy:
    def test_from_domain(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        assert policy.enabled
        assert "github.com" in policy.allowed_domains
        assert "www.github.com" in policy.allowed_domains

    def test_permissive(self) -> None:
        policy = SandboxPolicy.permissive()
        assert not policy.enabled


class TestValidateNavigation:
    def test_disabled_allows_all(self) -> None:
        policy = SandboxPolicy.permissive()
        validate_navigation("https://evil.com", policy)

    def test_same_domain_allowed(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        validate_navigation("https://github.com/search", policy)

    def test_subdomain_allowed(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        validate_navigation("https://api.github.com/repos", policy)

    def test_cross_domain_blocked(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        with pytest.raises(SandboxViolation, match="跨域导航"):
            validate_navigation("https://evil.com/phishing", policy)

    def test_javascript_protocol_blocked(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        with pytest.raises(SandboxViolation, match="javascript:"):
            validate_navigation("javascript:alert(1)", policy)

    def test_file_protocol_blocked(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        with pytest.raises(SandboxViolation, match="file://"):
            validate_navigation("file:///etc/passwd", policy)

    def test_data_html_blocked(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        with pytest.raises(SandboxViolation, match="data:text/html"):
            validate_navigation("data:text/html,<script>alert(1)</script>", policy)


class TestValidateAction:
    def test_navigate_same_domain_ok(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        validate_action({"action": "navigate", "url": "https://github.com/settings"}, policy)

    def test_navigate_cross_domain_blocked(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        with pytest.raises(SandboxViolation):
            validate_action({"action": "navigate", "url": "https://evil.com"}, policy)

    def test_runtime_type_navigate_cross_domain_blocked(self) -> None:
        policy = SandboxPolicy.from_domain("github.com")
        with pytest.raises(SandboxViolation):
            validate_action({"type": "navigate", "url": "https://evil.com"}, policy)

    def test_evaluate_js_blocked(self) -> None:
        policy = SandboxPolicy.from_domain("test.com")
        with pytest.raises(SandboxViolation, match="JavaScript"):
            validate_action({"action": "evaluate"}, policy)

    def test_execute_js_blocked(self) -> None:
        policy = SandboxPolicy.from_domain("test.com")
        with pytest.raises(SandboxViolation, match="JavaScript"):
            validate_action({"action": "execute_js"}, policy)

    def test_download_blocked(self) -> None:
        policy = SandboxPolicy.from_domain("test.com")
        with pytest.raises(SandboxViolation, match="下载"):
            validate_action({"action": "download"}, policy)

    def test_click_allowed(self) -> None:
        policy = SandboxPolicy.from_domain("test.com")
        validate_action({"action": "click", "ref": "123"}, policy)

    def test_disabled_allows_all(self) -> None:
        policy = SandboxPolicy.permissive()
        validate_action({"action": "evaluate"}, policy)


class TestValidateActionSteps:
    def test_all_pass(self) -> None:
        policy = SandboxPolicy.from_domain("test.com")
        steps = [
            {"action": "click", "ref": "1"},
            {"action": "type", "ref": "2", "value": "hello"},
        ]
        violations = validate_action_steps(steps, policy)
        assert violations == []

    def test_mixed_violations(self) -> None:
        policy = SandboxPolicy.from_domain("test.com")
        steps = [
            {"action": "click", "ref": "1"},
            {"action": "navigate", "url": "https://evil.com"},
            {"action": "evaluate"},
        ]
        violations = validate_action_steps(steps, policy)
        assert len(violations) == 2
        assert violations[0]["index"] == "1"
        assert violations[1]["index"] == "2"


# ── audit.py ─────────────────────────────────────────────


class TestAuditSource:
    def test_clean_code(self) -> None:
        source = "import click\nx = 1 + 2\nprint(x)\n"
        findings = audit_source(source)
        assert findings == []

    def test_detect_eval(self) -> None:
        source = "result = eval('1+1')\n"
        findings = audit_source(source)
        assert len(findings) == 1
        assert findings[0].severity == "critical"
        assert findings[0].category == "dangerous_call"
        assert "eval" in findings[0].message

    def test_detect_exec(self) -> None:
        source = "exec('print(1)')\n"
        findings = audit_source(source)
        assert len(findings) == 1
        assert "exec" in findings[0].message

    def test_detect_os_system(self) -> None:
        source = "import os\nos.system('rm -rf /')\n"
        findings = audit_source(source)
        assert any(f.category == "dangerous_call" for f in findings)

    def test_detect_subprocess(self) -> None:
        source = "import subprocess\nsubprocess.run(['ls'])\n"
        findings = audit_source(source)
        assert any("subprocess.run" in f.message for f in findings)

    def test_detect_dangerous_import(self) -> None:
        source = "import pickle\n"
        findings = audit_source(source)
        assert len(findings) == 1
        assert findings[0].severity == "warning"
        assert findings[0].category == "dangerous_import"

    def test_detect_from_import(self) -> None:
        source = "from ctypes import cdll\n"
        findings = audit_source(source)
        assert len(findings) == 1
        assert "ctypes" in findings[0].message

    def test_syntax_error(self) -> None:
        source = "def foo(\n"
        findings = audit_source(source)
        assert len(findings) == 1
        assert findings[0].category == "syntax_error"

    def test_compile_builtin(self) -> None:
        source = "code = compile('1+1', '<string>', 'eval')\n"
        findings = audit_source(source)
        assert any("compile" in f.message for f in findings)


class TestAuditFile:
    def test_nonexistent_file(self) -> None:
        findings = audit_file("/nonexistent/path.py")
        assert len(findings) == 1
        assert findings[0].category == "file_error"

    def test_real_file(self, tmp_path: Path) -> None:
        f = tmp_path / "safe.py"
        f.write_text("x = 1\n")
        findings = audit_file(f)
        assert findings == []

    def test_dangerous_file(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("eval(input())\n")
        findings = audit_file(f)
        assert len(findings) == 1


class TestAuditAdapter:
    def test_nonexistent_adapter(self, tmp_path: Path) -> None:
        with patch("cliany_site.config.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.adapters_dir = tmp_path / "adapters"
            mock_cfg.return_value = cfg

            result = audit_adapter("nonexist.com")
            assert result["safe"] is False
            assert "不存在" in result["error"]

    def test_safe_adapter(self, tmp_path: Path) -> None:
        with patch("cliany_site.config.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.adapters_dir = tmp_path / "adapters"
            mock_cfg.return_value = cfg

            adapter_dir = tmp_path / "adapters" / "safe.com"
            adapter_dir.mkdir(parents=True)
            (adapter_dir / "commands.py").write_text("import click\ncli = click.Group()\n")

            result = audit_adapter("safe.com")
            assert result["safe"] is True
            assert result["critical_count"] == 0

    def test_dangerous_adapter(self, tmp_path: Path) -> None:
        with patch("cliany_site.config.get_config") as mock_cfg:
            cfg = MagicMock()
            cfg.adapters_dir = tmp_path / "adapters"
            mock_cfg.return_value = cfg

            adapter_dir = tmp_path / "adapters" / "evil.com"
            adapter_dir.mkdir(parents=True)
            (adapter_dir / "commands.py").write_text("import os\nos.system('rm -rf /')\n")

            result = audit_adapter("evil.com")
            assert result["safe"] is False
            assert result["critical_count"] >= 1


class TestAuditFinding:
    def test_to_dict(self) -> None:
        f = AuditFinding(severity="critical", category="dangerous_call", message="eval()", line=1, col=0)
        d = f.to_dict()
        assert d["severity"] == "critical"
        assert d["line"] == 1
