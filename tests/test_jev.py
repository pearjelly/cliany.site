import json

import httpx
import pytest
from click.testing import CliRunner

from cliany_site.browser import jev
from cliany_site.cli import cli

NODES = {"12": {"name": "Name", "role": "textbox", "attributes": {"value": "private", "cookie": "secret"}},
         "20": {"name": "Apply", "role": "button"}}


def answer(choice="element_0", confidence=0.95, probabilities=None):
    return {"model": "jev-test", "answers": {"target": {
        "type": "choice", "choice": choice, "confidence": confidence,
        "probabilities": probabilities or {"element_0": 0.97, "element_1": 0.01, "none": 0.02},
    }}}


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-only-key")
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "0")
    calls = []
    response = {"body": answer(), "status": 200}
    real_client = httpx.AsyncClient

    def handle(request):
        calls.append(request)
        return httpx.Response(response["status"], content=json.dumps(response["body"]))

    monkeypatch.setattr(jev, "AsyncClient", lambda **kwargs: real_client(
        **kwargs, transport=httpx.MockTransport(handle),
    ))
    return calls, response


@pytest.mark.asyncio
async def test_finite_choice_uses_minimal_state(transport):
    calls, _ = transport
    result = await jev.choose_element(NODES, "Where should I enter my name?", allow_remote=True)
    assert result["ok"] is True
    assert result["data"][0]["ref"] == "12"
    assert result["data"][0]["alternatives"] == [
        {"ref": "12", "name": "Name", "role": "textbox", "probability": 0.97},
        {"ref": "20", "name": "Apply", "role": "button", "probability": 0.01},
    ]
    assert result["data"][0]["none_probability"] == 0.02
    payload = json.loads(calls[0].content)
    assert str(calls[0].url) == jev.ENDPOINT
    assert set(payload["questions"]["target"]["criteria"]) == {"element_0", "element_1", "none"}
    assert "private" not in calls[0].content.decode()
    assert "secret" not in calls[0].content.decode()
    assert "attributes" not in calls[0].content.decode()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,code", [
    (answer(confidence=0.2), "E_SELECTOR_NOT_FOUND"),
    (answer(probabilities={"element_0": 0.5, "element_1": 0.5, "none": 0}), "E_SELECTOR_NOT_FOUND"),
    (answer("none", probabilities={"element_0": 0, "element_1": 0, "none": 1}), "E_SELECTOR_NOT_FOUND"),
    (answer("invented"), "E_PARSE_FAILED"),
    (answer(confidence=True), "E_PARSE_FAILED"),
    (answer(confidence=float("nan")), "E_PARSE_FAILED"),
    (answer(confidence=10 ** 400), "E_PARSE_FAILED"),
    (answer(confidence=-(10 ** 400)), "E_PARSE_FAILED"),
    (answer(probabilities={"element_0": 10 ** 400, "element_1": 0, "none": 0}), "E_PARSE_FAILED"),
    (answer(probabilities={"element_0": 1}), "E_PARSE_FAILED"),
    (answer(probabilities={"element_0": 0.2, "element_1": 0.7, "none": 0.1}), "E_PARSE_FAILED"),
    (answer(probabilities={"element_0": 1, "element_1": 1, "none": 0}), "E_PARSE_FAILED"),
    ({}, "E_PARSE_FAILED"), ([], "E_PARSE_FAILED"),
])
async def test_invalid_or_uncertain_decisions_fail_closed(transport, payload, code):
    _, response = transport
    response["body"] = payload
    result = await jev.choose_element(NODES, "Name", allow_remote=True)
    assert result["ok"] is False
    assert result["error"]["code"] == code


@pytest.mark.asyncio
async def test_uncertain_choice_returns_ranked_evidence_without_success(transport):
    _, response = transport
    response["body"] = answer(confidence=0.4, probabilities={"element_0": 0.6, "element_1": 0.3, "none": 0.1})
    result = await jev.choose_element(NODES, "Name", allow_remote=True)
    assert result["ok"] is False
    assert result["error"]["code"] == "E_SELECTOR_NOT_FOUND"
    details = result["error"]["details"]
    assert [item["ref"] for item in details["alternatives"]] == ["12", "20"]
    assert [item["probability"] for item in details["alternatives"]] == [0.6, 0.3]
    assert details["none_probability"] == 0.1


def test_uncertain_choice_prints_safe_evidence_to_stderr(capsys):
    from cliany_site.commands.browser.find import _print_envelope
    from cliany_site.envelope import ErrorCode, err

    result = err("browser find", ErrorCode.E_SELECTOR_NOT_FOUND, "未确定", details={
        "alternatives": [{"ref": "12", "role": "button", "name": "Apply\n\x1b[31m", "probability": 0.6}],
    })
    _print_envelope(result, False)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert 'ref="12"' in captured.err
    assert "\\n\\u001b[31m" in captured.err
    assert "\x1b[31m" not in captured.err


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [302, 401, 429, 500])
async def test_http_errors_do_not_leak_secrets_or_follow_redirects(transport, status):
    calls, response = transport
    response.update(status=status, body={"error": "test-only-key"})
    result = await jev.choose_element(NODES, "Name", allow_remote=True)
    assert result["error"]["code"] == "E_LLM_UNAVAILABLE"
    assert "test-only-key" not in json.dumps(result)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_opt_in_offline_and_key_gates_prevent_requests(transport, monkeypatch):
    calls, _ = transport
    assert (await jev.choose_element(NODES, "Name"))["error"]["code"] == "E_LLM_DISABLED"
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    assert (await jev.choose_element(NODES, "Name", allow_remote=True))["error"]["code"] == "E_LLM_DISABLED"
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "0")
    monkeypatch.delenv("TYPESAFE_API_KEY")
    assert (await jev.choose_element(NODES, "Name", allow_remote=True))["error"]["code"] == "E_LLM_UNAVAILABLE"
    assert not calls


@pytest.mark.asyncio
async def test_candidate_limit_does_not_truncate(transport):
    calls, _ = transport
    nodes = {str(i): {"name": str(i), "role": "button"} for i in range(255)}
    assert (await jev.choose_element(nodes, "Name", allow_remote=True))["error"]["code"] == "E_INVALID_PARAM"
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize("field,limit", [("name", 512), ("role", 80)])
async def test_oversized_candidate_semantics_prevent_request(transport, field, limit):
    calls, response = transport
    response["body"] = answer(probabilities={"element_0": 0.98, "none": 0.02})
    nodes = {"12": {"name": "Apply", "role": "button", field: "x" * limit + " not available"}}
    result = await jev.choose_element(nodes, "Apply", allow_remote=True)
    assert result["error"]["code"] == "E_INVALID_PARAM"
    assert not calls


@pytest.mark.asyncio
async def test_candidate_semantics_at_limits_remain_complete(transport):
    calls, response = transport
    response["body"] = answer(probabilities={"element_0": 0.98, "none": 0.02})
    nodes = {"12": {"name": "x" * 512, "role": "r" * 80}}
    result = await jev.choose_element(nodes, "Apply", allow_remote=True)
    assert result["ok"] is True
    criteria = json.loads(calls[0].content)["questions"]["target"]["criteria"]
    assert criteria["element_0"] == nodes["12"]
    assert result["data"][0]["name"] == nodes["12"]["name"]
    assert result["data"][0]["role"] == nodes["12"]["role"]


@pytest.mark.asyncio
async def test_oversized_confidence_threshold_prevents_request(transport):
    calls, _ = transport
    result = await jev.choose_element(NODES, "Name", min_confidence=10 ** 400, allow_remote=True)
    assert result["error"]["code"] == "E_INVALID_PARAM"
    assert not calls


def test_cli_requires_explicit_data_sharing(tmp_home):
    result = CliRunner().invoke(cli, ["browser", "find", "--by", "intent", "--value", "name", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "E_LLM_DISABLED"


@pytest.mark.asyncio
async def test_high_confidence_cannot_disambiguate_identical_labels(transport):
    nodes = {"12": {"name": "Apply", "role": "button"}, "20": {"name": "Apply", "role": "button"}}
    result = await jev.choose_element(nodes, "Apply", allow_remote=True)
    assert result["error"]["code"] == "E_SELECTOR_NOT_FOUND"
