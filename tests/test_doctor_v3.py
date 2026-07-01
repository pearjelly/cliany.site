import json

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.commands.doctor import _run_checks


def test_doctor_has_schema_version(tmp_home, no_llm, monkeypatch):
    """Test that doctor data includes schema_version=3"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr("cliany_site.commands.doctor.Path.cwd", lambda: tmp_home)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "data" in data
    assert "schema_version" in data["data"]
    assert data["data"]["schema_version"] == 3


def test_doctor_has_capability_fields(tmp_home, no_llm, monkeypatch):
    """Test that doctor data includes capability fields"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "data" in data
    required_fields = ["capability_router", "network_capture", "console_capture", "diagnose_llm"]
    for field in required_fields:
        assert field in data["data"]


def test_doctor_no_llm_key_returns_ok(tmp_home, no_llm, monkeypatch):
    """Test that doctor returns ok=True even without LLM key, with llm status=warning"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    # Ensure no LLM keys
    monkeypatch.delenv("CLIANY_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLIANY_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    checks = data["data"]["checks"]
    llm_check = next(c for c in checks if c["name"] == "llm")
    assert llm_check["status"] == "warning"
    assert llm_check["severity"] == "should_fix"
    assert "只安装/执行已有 adapter 可暂时忽略" in llm_check["action"]

    summary = data["data"]["summary"]
    assert summary["counts"]["must_fix"] == 0
    assert any(item["name"] == "llm" for item in summary["should_fix"])
    assert summary["ready_for_demo_adapters"] is True
    assert summary["ready_for_explore"] is False
    assert summary["recommended_next_step"] == "先运行真实 demo adapter；需要生成新 adapter 时再配置 LLM key。"
    capabilities = summary["capabilities"]
    assert capabilities["manage_adapters"]["ready"] is True
    assert capabilities["run_browser_workflows"]["ready"] is True
    assert capabilities["generate_adapters"]["ready"] is False
    assert capabilities["generate_adapters"]["blockers"] == ["llm"]
    demo_quickstart = summary["demo_adapter_quickstart"]
    assert demo_quickstart["docs"] == "docs/quickstart-10min.md"
    assert demo_quickstart["commands"] == [
        "cliany-site market install ./issues.apache.org.cliany-adapter-v0.14.0.tar.gz",
        "cliany-site list --json",
        "cliany-site verify issues.apache.org --json",
        "cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json",
    ]


def test_doctor_human_output_groups_action_items(tmp_home, no_llm, monkeypatch):
    """Test that non-JSON doctor output is readable for first-run users"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.delenv("CLIANY_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLIANY_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "cliany-site doctor" in result.output
    assert "状态: 可继续" in result.output
    assert "Demo adapter ready: yes" in result.output
    assert "Explore ready: no" in result.output
    assert "下一步: 先运行真实 demo adapter；需要生成新 adapter 时再配置 LLM key。" in result.output
    assert "Demo adapter 快速路径:" in result.output
    assert "cliany-site market install ./issues.apache.org.cliany-adapter-v0.14.0.tar.gz" in result.output
    assert "cliany-site verify issues.apache.org --json" in result.output
    assert "cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json" in result.output
    assert "可用能力:" in result.output
    assert "manage_adapters: yes" in result.output
    assert "run_browser_workflows: yes" in result.output
    assert "generate_adapters: no" in result.output
    assert "blocked by: llm" in result.output
    assert "建议处理:" in result.output
    assert "llm" in result.output
    assert "只安装/执行已有 adapter 可暂时忽略" in result.output


@pytest.mark.asyncio
async def test_doctor_cdp_failure_includes_must_fix_summary(tmp_home, no_llm, monkeypatch):
    """Test that fatal checks include actionable summary in error details"""
    class UnavailableCDP:
        async def check_available(self):
            return False

    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")
    (tmp_home / ".cliany-site" / "adapters").mkdir(parents=True)

    result = await _run_checks(UnavailableCDP())

    assert result["ok"] is False
    assert result["error"] is not None
    details = result["error"]["details"]
    assert details is not None
    summary = details["summary"]
    assert summary["counts"]["must_fix"] >= 1
    assert summary["ready_for_demo_adapters"] is False
    assert summary["ready_for_explore"] is False
    assert summary["recommended_next_step"] == "先处理必须修复项，然后重新运行 cliany-site doctor。"
    capabilities = summary["capabilities"]
    assert capabilities["manage_adapters"]["ready"] is True
    assert capabilities["run_browser_workflows"]["ready"] is False
    assert capabilities["run_browser_workflows"]["blockers"] == ["cdp"]
    assert capabilities["generate_adapters"]["ready"] is False
    assert "cdp" in capabilities["generate_adapters"]["blockers"]
    cdp_item = next(item for item in summary["must_fix"] if item["name"] == "cdp")
    assert "CDP" in cdp_item["action"]

    cdp_check = next(c for c in details["checks"] if c["name"] == "cdp")
    assert cdp_check["severity"] == "must_fix"
    assert "CDP" in cdp_check["action"]


def test_doctor_human_output_exits_nonzero_for_must_fix(tmp_home, no_llm, monkeypatch):
    """Test that fatal checks stay obvious in human output"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return False

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"], catch_exceptions=False)

    assert result.exit_code == 1
    assert "状态: 需要修复" in result.output
    assert "下一步: 先处理必须修复项，然后重新运行 cliany-site doctor。" in result.output
    assert "必须修复:" in result.output
    assert "cdp" in result.output
    assert "CDP" in result.output


def test_doctor_recommends_explore_when_llm_and_cdp_are_ready(tmp_home, no_llm, monkeypatch):
    """Test that first-run guidance moves to explore once all prerequisites are ready."""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)

    assert result.exit_code == 0
    data = json.loads(result.output)
    summary = data["data"]["summary"]
    assert summary["ready_for_demo_adapters"] is True
    assert summary["ready_for_explore"] is True
    assert summary["recommended_next_step"] == "可以运行真实 demo adapter，或使用 explore 生成自己的命令。"
    capabilities = summary["capabilities"]
    assert capabilities["manage_adapters"]["ready"] is True
    assert capabilities["run_browser_workflows"]["ready"] is True
    assert capabilities["generate_adapters"]["ready"] is True
    assert capabilities["generate_adapters"]["blockers"] == []
    assert summary["demo_adapter_quickstart"]["commands"][0] == (
        "cliany-site market install ./issues.apache.org.cliany-adapter-v0.14.0.tar.gz"
    )


def test_doctor_does_not_call_llm_live_by_default(tmp_home, no_llm, monkeypatch):
    """doctor 默认只检查 key/config，不触发真实 LLM 调用。"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("llm live preflight should be opt-in")

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr("cliany_site.explorer.engine._invoke_llm_with_retry", fail_if_called)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)

    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    assert "llm_live" not in {check["name"] for check in checks}
    summary = data["data"]["summary"]
    assert summary["ready_for_explore"] is True
    assert summary["llm_live_preflight"] == {
        "checked": False,
        "ready": None,
        "status": "not_run",
        "blocks_explore": False,
        "action": (
            "Run `cliany-site doctor --llm-live --json` before long explore "
            "or candidate adapter promotion."
        ),
    }


def test_doctor_llm_live_success_keeps_explore_ready(tmp_home, no_llm, monkeypatch):
    """doctor --llm-live 成功时输出 llm_live=ok。"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    class FakeLLM:
        pass

    async def fake_invoke(_llm, _prompt, **_kwargs):
        return object()

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda: FakeLLM())
    monkeypatch.setattr("cliany_site.explorer.engine._invoke_llm_with_retry", fake_invoke)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor", "--llm-live"], catch_exceptions=False)

    assert result.exit_code == 0
    data = json.loads(result.output)
    checks = data["data"]["checks"]
    live_check = next(check for check in checks if check["name"] == "llm_live")
    assert live_check["status"] == "ok"
    assert live_check["details"]["phase"] == "llm_preflight"
    summary = data["data"]["summary"]
    assert summary["ready_for_explore"] is True
    assert summary["capabilities"]["generate_adapters"]["ready"] is True
    assert summary["llm_live_preflight"] == {
        "checked": True,
        "ready": True,
        "status": "ok",
        "blocks_explore": False,
        "action": "LLM provider live preflight 通过，可以发起 explore。",
        "provider": "anthropic",
        "retryable": False,
        "phase": "llm_preflight",
    }


def test_doctor_llm_live_unavailable_blocks_explore_ready(tmp_home, no_llm, monkeypatch):
    """doctor --llm-live 将 LLM 上游 502 前置为 should_fix。"""
    from cliany_site.errors import LlmUnavailableError

    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    class FakeLLM:
        pass

    async def fake_invoke(_llm, _prompt, **_kwargs):
        raise LlmUnavailableError("LLM upstream returned 502 Bad Gateway", status_code=502)

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test")
    monkeypatch.setenv("CLIANY_OPENAI_BASE_URL", "https://example.com/v1")
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda: FakeLLM())
    monkeypatch.setattr("cliany_site.explorer.engine._invoke_llm_with_retry", fake_invoke)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor", "--llm-live"], catch_exceptions=False)

    assert result.exit_code == 0
    data = json.loads(result.output)
    live_check = next(check for check in data["data"]["checks"] if check["name"] == "llm_live")
    assert live_check["status"] == "warning"
    assert live_check["severity"] == "should_fix"
    assert live_check["details"] == {
        "provider": "openai",
        "error_code": "E_LLM_UNAVAILABLE",
        "message": "LLM upstream returned 502 Bad Gateway",
        "retryable": True,
        "status_code": 502,
        "phase": "llm_preflight",
    }

    summary = data["data"]["summary"]
    assert summary["ready_for_demo_adapters"] is True
    assert summary["ready_for_explore"] is False
    assert any(item["name"] == "llm_live" for item in summary["should_fix"])
    assert summary["capabilities"]["generate_adapters"]["ready"] is False
    assert summary["capabilities"]["generate_adapters"]["blockers"] == ["llm_live"]
    assert summary["llm_live_preflight"] == {
        "checked": True,
        "ready": False,
        "status": "warning",
        "blocks_explore": True,
        "action": "LLM 上游暂不可用；请稍后重试，或切换 CLIANY_LLM_PROVIDER / CLIANY_OPENAI_BASE_URL。",
        "provider": "openai",
        "error_code": "E_LLM_UNAVAILABLE",
        "message": "LLM upstream returned 502 Bad Gateway",
        "retryable": True,
        "status_code": 502,
        "phase": "llm_preflight",
    }


def test_doctor_llm_live_connection_error_is_llm_unavailable(tmp_home, no_llm, monkeypatch):
    """doctor --llm-live 将 provider 连接错误归类为 LLM 上游不可用。"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    class APIConnectionError(Exception):
        pass

    class FailingLLM:
        async def ainvoke(self, _prompt):
            raise APIConnectionError("Connection error.")

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test")
    monkeypatch.setenv("CLIANY_OPENAI_BASE_URL", "https://example.com/v1")
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda: FailingLLM())

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor", "--llm-live"], catch_exceptions=False)

    assert result.exit_code == 0
    data = json.loads(result.output)
    live_check = next(check for check in data["data"]["checks"] if check["name"] == "llm_live")
    assert live_check["status"] == "warning"
    assert live_check["severity"] == "should_fix"
    assert live_check["details"]["provider"] == "openai"
    assert live_check["details"]["error_code"] == "E_LLM_UNAVAILABLE"
    assert live_check["details"]["retryable"] is True
    assert live_check["details"]["status_code"] is None
    assert live_check["details"]["phase"] == "llm_preflight"
    assert live_check["details"]["message"] == "LLM upstream unavailable: Connection error."

    summary = data["data"]["summary"]
    assert summary["ready_for_explore"] is False
    assert summary["capabilities"]["generate_adapters"]["blockers"] == ["llm_live"]
    assert summary["llm_live_preflight"] == {
        "checked": True,
        "ready": False,
        "status": "warning",
        "blocks_explore": True,
        "action": "LLM 上游暂不可用；请稍后重试，或切换 CLIANY_LLM_PROVIDER / CLIANY_OPENAI_BASE_URL。",
        "provider": "openai",
        "error_code": "E_LLM_UNAVAILABLE",
        "message": "LLM upstream unavailable: Connection error.",
        "retryable": True,
        "status_code": None,
        "phase": "llm_preflight",
    }


def test_legacy_adapter_count(tmp_home, no_llm, monkeypatch):
    """Test that legacy_adapter_count counts adapters with schema_version != 3"""
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True)
    # Create a v2 adapter
    v2_dir = adapters_dir / "test.com"
    v2_dir.mkdir()
    (v2_dir / "metadata.json").write_text('{"schema_version": 2, "domain": "test.com", "commands": []}')
    # Create a v3 adapter
    v3_dir = adapters_dir / "example.com"
    v3_dir.mkdir()
    (v3_dir / "metadata.json").write_text('{"schema_version": 3, "domain": "example.com", "commands": []}')

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "legacy_adapter_count" in data["data"]
    assert data["data"]["legacy_adapter_count"] == 1


def test_agent_md_reports_warning_for_missing_sentinel(tmp_home, no_llm, monkeypatch):
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")

    class MockPath:
        @classmethod
        def home(cls):
            return tmp_home

        @classmethod
        def cwd(cls):
            return tmp_home

    monkeypatch.setattr("cliany_site.commands.doctor.Path", MockPath)

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    agent_check = next(c for c in data["data"]["checks"] if c["name"] == "agent_md")
    assert agent_check["status"] == "warning"
    assert agent_check["details"]["status"] in {"no_sentinel", "missing"}
    assert agent_check["details"]["path"] in {"AGENT.md", "AGENTS.md"}
    assert "cliany-site explore" in (agent_check["details"]["message"] or "")


def test_agent_md_accepts_manual_agents_md_without_sentinel(tmp_home, no_llm, monkeypatch):
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None):
            pass

        async def check_available(self):
            return True

    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", MockCDP)
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr("cliany_site.commands.doctor.Path.cwd", lambda: tmp_home)

    (tmp_home / "AGENTS.md").write_text("# 项目知识库\n\n人工维护的规则。\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)
    assert result.exit_code == 0

    data = json.loads(result.output)
    agent_check = next(c for c in data["data"]["checks"] if c["name"] == "agent_md")
    assert agent_check["status"] == "ok"
    assert agent_check["details"]["status"] == "manual"
    assert agent_check["details"]["path"] == "AGENTS.md"
    assert agent_check["details"]["managed_path"] == "AGENT.md"
