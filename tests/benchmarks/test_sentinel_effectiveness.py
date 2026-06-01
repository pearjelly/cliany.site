# pyright: reportMissingImports=false
import copy
import json
from typing import Any

import pytest

from cliany_site.explorer.engine import _parse_llm_response, _sanitize_actions_data

from tests.benchmarks.test_generation_regression import (
    SCENARIOS,
    _adapter_structure_fingerprint,
    _domain_from_expected,
    _explore_result_from_dict,
    _generate_adapter,
    _load_json,
    _scenario_dir,
)


def _tamper_first_command_name(response_text: str) -> str:
    payload = json.loads(response_text)
    commands = payload.get("commands")
    assert commands, "测试数据必须包含可篡改的 command"

    commands[0]["name"] = "TAMPERED_NAME_SENTINEL_TEST"
    return json.dumps(payload, ensure_ascii=False)


def _tamper_first_action_ref(response: dict[str, Any]) -> dict[str, Any]:
    tampered = copy.deepcopy(response)
    actions = tampered.get("actions")
    assert actions, "测试数据必须包含可篡改的 action"

    actions[0]["ref"] = "TAMPERED_REF_SENTINEL_TEST"
    return tampered


def _tamper_first_explore_action(result_data: dict[str, Any]) -> dict[str, Any]:
    tampered = copy.deepcopy(result_data)
    actions = tampered.get("actions")
    assert actions, "测试数据必须包含可篡改的 ExploreResult action"

    actions[0]["target_ref"] = "TAMPERED_REF_SENTINEL_TEST"
    actions[0]["description"] = "TAMPERED_DESCRIPTION_SENTINEL_TEST"
    return tampered


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_sentinel_parse_detects_tampered_response(scenario: str, tmp_home):  # noqa: ARG001 — fixture 通过副作用隔离 ~/.cliany-site，无需在函数体引用
    scenario_dir = _scenario_dir(scenario)
    fake_responses = _load_json(scenario_dir / "fake_llm_responses.json")
    expected_parsed = _load_json(scenario_dir / "expected_parsed.json")

    command_response_index = next(
        index
        for index, text in enumerate(fake_responses)
        if json.loads(text).get("commands")
    )
    response_text = fake_responses[command_response_index]
    expected = expected_parsed[command_response_index]

    baseline_result = _parse_llm_response(response_text)
    assert baseline_result == expected, "未篡改响应应匹配解析基线，避免哨兵误报"

    tampered_result = _parse_llm_response(_tamper_first_command_name(response_text))
    assert tampered_result != expected, "篡改 command.name 后应偏离解析基线，证明哨兵敏感"
    assert tampered_result["commands"][0]["name"] == "TAMPERED_NAME_SENTINEL_TEST"


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_sentinel_sanitize_detects_tampered_actions(scenario: str, tmp_home):  # noqa: ARG001 — fixture 通过副作用隔离 ~/.cliany-site，无需在函数体引用
    scenario_dir = _scenario_dir(scenario)
    parsed_responses = _load_json(scenario_dir / "expected_parsed.json")
    expected_sanitized = _load_json(scenario_dir / "expected_sanitized.json")
    source_url = _load_json(scenario_dir / "expected.json")["pages"][0]["url"]

    actionable_index = next(
        index
        for index, parsed in enumerate(parsed_responses)
        if parsed.get("actions") and parsed["actions"][0].get("type") != "navigate"
    )
    parsed = parsed_responses[actionable_index]
    expected = expected_sanitized[actionable_index]

    baseline_result = _sanitize_actions_data(parsed["actions"], source_url)
    assert baseline_result == expected, "未篡改 action 应匹配清洗基线，避免哨兵误报"

    tampered = _tamper_first_action_ref(parsed)
    tampered_result = _sanitize_actions_data(tampered["actions"], source_url)
    assert tampered_result != expected, "篡改 action.ref 后应偏离清洗基线，证明哨兵敏感"
    assert tampered_result[0]["ref"] == "TAMPERED_REF_SENTINEL_TEST"


def test_sentinel_codegen_detects_tampered_explore_result(tmp_home):  # noqa: ARG001 — fixture 通过副作用隔离 ~/.cliany-site，无需在函数体引用
    scenario_dir = _scenario_dir("simple-search")
    expected = _load_json(scenario_dir / "expected.json")
    expected_commands = (scenario_dir / "expected_adapter" / "commands.py").read_text(encoding="utf-8")

    baseline_result = _explore_result_from_dict(expected)
    baseline_code, _baseline_metadata = _generate_adapter(
        baseline_result,
        _domain_from_expected(expected),
    )
    baseline_fingerprint = _adapter_structure_fingerprint(baseline_code)
    assert baseline_fingerprint == _adapter_structure_fingerprint(expected_commands), (
        "未篡改 ExploreResult 应匹配 codegen 结构基线，避免哨兵误报"
    )

    tampered_result = _explore_result_from_dict(_tamper_first_explore_action(expected))
    tampered_code, _tampered_metadata = _generate_adapter(
        tampered_result,
        _domain_from_expected(expected),
    )
    tampered_fingerprint = _adapter_structure_fingerprint(tampered_code)
    assert tampered_fingerprint != baseline_fingerprint, (
        "篡改 ExploreResult action 后生成结构应偏离 codegen 基线，证明哨兵敏感"
    )
    assert (
        tampered_fingerprint["commands"][0]["action_payloads"][0][0]["ref"]
        == "TAMPERED_REF_SENTINEL_TEST"
    )
