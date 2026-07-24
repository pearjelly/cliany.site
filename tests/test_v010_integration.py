import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage


def test_fake_chat_model_contract():
    from tests.fixtures.fake_llm import FakeChatModel

    model = FakeChatModel(responses=["first", "second"])
    r1 = model.invoke([HumanMessage(content="hi")])
    r2 = model.invoke([HumanMessage(content="hi")])
    r3 = model.invoke([HumanMessage(content="hi")])
    assert r1.content == "first"
    assert r2.content == "second"
    assert r3.content == "second"


def test_get_llm_qa_offline_returns_fake_chat_model(tmp_path, monkeypatch):
    from cliany_site.testing.fake_llm import FakeChatModel

    fake_responses = [
        json.dumps(
            {
                "actions": [],
                "commands": [],
                "canonical_actions": [],
                "selector_pool": [],
                "done": True,
                "reasoning": "test",
            }
        )
    ]
    fake_path = tmp_path / "fake_responses.json"
    fake_path.write_text(json.dumps(fake_responses))

    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_QA_FAKE_LLM_RESPONSES", str(fake_path))

    from cliany_site.explorer.engine import _get_llm

    result = _get_llm()
    assert isinstance(result, FakeChatModel)


def test_get_llm_qa_offline_missing_path_raises(monkeypatch):
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.delenv("CLIANY_QA_FAKE_LLM_RESPONSES", raising=False)

    from cliany_site.explorer.engine import _get_llm

    with pytest.raises(ValueError, match="CLIANY_QA_FAKE_LLM_RESPONSES"):
        _get_llm()


def test_explore_qa_offline_missing_fake_llm_error(monkeypatch):
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.delenv("CLIANY_QA_FAKE_LLM_RESPONSES", raising=False)

    from click.testing import CliRunner

    from cliany_site.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["explore", "--json", "http://localhost:18080", "test"])
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["code"] == "E_QA_OFFLINE_MISSING_FAKE_LLM"


def test_error_code_new_constants():
    from cliany_site.envelope import ErrorCode

    assert ErrorCode.E_QA_OFFLINE_MISSING_FAKE_LLM == "E_QA_OFFLINE_MISSING_FAKE_LLM"
    assert ErrorCode.E_DIAGNOSE == "E_DIAGNOSE"
    assert ErrorCode.E_LLM_UNAVAILABLE == "E_LLM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_llm_retry_wraps_gateway_failure_without_html():
    from cliany_site.errors import LlmUnavailableError
    from cliany_site.explorer.engine import _invoke_llm_with_retry

    class GatewayError(Exception):
        status_code = 502

    class FailingLLM:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, _prompt):
            self.calls += 1
            raise GatewayError(
                "<html><head><title>502 Bad Gateway</title></head>"
                "<body><h1>502 Bad Gateway</h1></body></html>"
            )

    llm = FailingLLM()
    with pytest.raises(LlmUnavailableError) as exc_info:
        await _invoke_llm_with_retry(llm, "prompt", max_attempts=2, base_delay=0, backoff_factor=1)

    assert llm.calls == 2
    assert exc_info.value.status_code == 502
    assert exc_info.value.retryable is True
    assert "502 Bad Gateway" in str(exc_info.value)
    assert "<html>" not in str(exc_info.value)


def test_explore_llm_gateway_failure_returns_llm_unavailable_json(monkeypatch):
    from click.testing import CliRunner

    from cliany_site.cli import cli
    from cliany_site.errors import LlmUnavailableError

    monkeypatch.delenv("CLIANY_QA_OFFLINE", raising=False)
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("CLIANY_OPENAI_BASE_URL", "https://example.com/v1")

    cdp = SimpleNamespace(check_available=_async_true)
    monkeypatch.setattr("cliany_site.browser.cdp.cdp_from_context", lambda _ctx: cdp)

    class FailingExplorer:
        def __init__(self, **_kwargs):
            pass

        async def explore(self, *_args, **_kwargs):
            raise LlmUnavailableError("LLM upstream returned 502 Bad Gateway", status_code=502)

    monkeypatch.setattr("cliany_site.explorer.engine.WorkflowExplorer", FailingExplorer)

    runner = CliRunner()
    result = runner.invoke(cli, ["explore", "--json", "https://pypi.org", "search packages"])
    payload, json_end = json.JSONDecoder().raw_decode(result.output)

    assert result.exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_LLM_UNAVAILABLE"
    assert "502 Bad Gateway" in payload["error"]["message"]
    assert "<html>" not in payload["error"]["message"]
    assert payload["error"]["details"] == {
        "retryable": True,
        "status_code": 502,
        "phase": "llm_invoke",
    }


def test_explore_data_quality_failure_returns_structured_json(monkeypatch):
    from click.testing import CliRunner

    from cliany_site.cli import cli
    from cliany_site.errors import DataCommandQualityError

    monkeypatch.delenv("CLIANY_QA_OFFLINE", raising=False)
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("CLIANY_OPENAI_BASE_URL", "https://example.com/v1")

    cdp = SimpleNamespace(check_available=_async_true)
    monkeypatch.setattr("cliany_site.browser.cdp.cdp_from_context", lambda _ctx: cdp)

    class FailingExplorer:
        def __init__(self, **_kwargs):
            pass

        async def explore(self, *_args, **_kwargs):
            raise DataCommandQualityError(
                "数据命令未通过提取质量门禁",
                details={"repair_attempts": 1, "data_commands": [{"name": "search-results"}]},
            )

    monkeypatch.setattr("cliany_site.explorer.engine.WorkflowExplorer", FailingExplorer)

    result = CliRunner().invoke(cli, ["explore", "--json", "https://pypi.org", "search packages"])
    payload, json_end = json.JSONDecoder().raw_decode(result.output)

    assert result.exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_EMPTY_RESULT"
    assert payload["error"]["details"] == {
        "repair_attempts": 1,
        "data_commands": [{"name": "search-results"}],
    }
    assert "[explore]" in result.output[json_end:]


async def _async_true():
    return True


def test_migrate_v2_to_v3(tmp_home):
    from click.testing import CliRunner

    from cliany_site.cli import cli

    adapters_dir = tmp_home / ".cliany-site" / "adapters"
    adapters_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir = adapters_dir / "qa-test-migrate-com"
    adapter_dir.mkdir()
    (adapter_dir / "metadata.json").write_text(
        json.dumps({"schema_version": 2, "domain": "qa-test-migrate-com", "commands": []}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["migrate", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert "qa-test-migrate-com" in data["data"]["migrated"]
