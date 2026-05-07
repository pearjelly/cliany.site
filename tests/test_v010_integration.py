import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage, AIMessage


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
        '{"actions": [], "commands": [], "canonical_actions": [], "selector_pool": [], "done": true, "reasoning": "test"}'
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
