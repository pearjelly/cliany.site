# pyright: reportMissingImports=false
import ast
import json
from pathlib import Path
from typing import Any

import pytest

from cliany_site.codegen.generator import AdapterGenerator
from cliany_site.explorer.engine import _parse_llm_response, _sanitize_actions_data
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo


SCENARIOS_DIR = Path(__file__).parent / "data"
SCENARIOS = ("simple-search", "multi-step")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _scenario_dir(name: str) -> Path:
    return SCENARIOS_DIR / name


def _explore_result_from_dict(data: dict[str, Any]) -> ExploreResult:
    return ExploreResult(
        pages=[PageInfo(**page) for page in data.get("pages", [])],
        actions=[ActionStep(**action) for action in data.get("actions", [])],
        commands=[CommandSuggestion(**command) for command in data.get("commands", [])],
        explore_model=data.get("explore_model", ""),
        smoke=data.get("smoke", []),
        canonical_actions=data.get("canonical_actions", []),
        selector_pool=data.get("selector_pool", []),
        api_endpoints=data.get("api_endpoints", []),
        capability=data.get("capability", {}),
    )


def _canonical_actions_from_result(result: ExploreResult) -> list[dict[str, Any]]:
    return [
        {
            "action_type": action.action_type,
            "target_ref": action.target_ref,
            "target_name": action.target_name,
            "target_url": action.target_url,
            "description": action.description,
        }
        for action in result.actions
        if action.action_type
    ]


def _generate_adapter(result: ExploreResult, domain: str) -> tuple[str, dict[str, Any]]:
    generated = AdapterGenerator().generate(result, domain)
    if isinstance(generated, tuple):
        commands_code, metadata = generated
        return commands_code, metadata
    return generated, {"canonical_actions": _canonical_actions_from_result(result)}


def _domain_from_expected(expected: dict[str, Any]) -> str:
    source_url = expected["pages"][0]["url"]
    return source_url.split("//", 1)[1].split("/", 1)[0]


def _literal_or_source(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return ast.unparse(node)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_call_name(node.value)}.{node.attr}"
    return ast.unparse(node)


def _click_command_name(node: ast.FunctionDef) -> str | None:
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if _call_name(decorator.func) != "cli.command" or not decorator.args:
            continue
        value = _literal_or_source(decorator.args[0])
        return value if isinstance(value, str) else str(value)
    return None


def _click_options(node: ast.FunctionDef) -> list[dict[str, Any]]:
    options = []
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if _call_name(decorator.func) != "click.option":
            continue
        options.append(
            {
                "args": [_literal_or_source(arg) for arg in decorator.args],
                "kwargs": {
                    keyword.arg: _literal_or_source(keyword.value)
                    for keyword in decorator.keywords
                    if keyword.arg is not None
                },
            }
        )
    return options


def _json_loads_payloads(node: ast.FunctionDef) -> list[Any]:
    payloads = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if _call_name(child.func) != "json.loads" or not child.args:
            continue
        raw_payload = _literal_or_source(child.args[0])
        if isinstance(raw_payload, str):
            payloads.append(json.loads(raw_payload))
        else:
            payloads.append(raw_payload)
    return payloads


def _runtime_calls(node: ast.FunctionDef) -> dict[str, int]:
    interesting = {"execute_steps_via_atoms", "substitute_parameters", "diagnose_if_enabled"}
    counts = {name: 0 for name in interesting}
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _call_name(child.func)
            if name in counts:
                counts[name] += 1
    return counts


def _adapter_structure_fingerprint(code: str) -> dict[str, Any]:
    module = ast.parse(code)
    constants: dict[str, Any] = {}
    commands: list[dict[str, Any]] = []

    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"DOMAIN", "SOURCE_URL"}:
                    constants[target.id] = _literal_or_source(node.value)
        if isinstance(node, ast.FunctionDef):
            command_name = _click_command_name(node)
            if command_name is None:
                continue
            commands.append(
                {
                    "command_name": command_name,
                    "function_name": node.name,
                    "parameters": [arg.arg for arg in node.args.args],
                    "click_options": _click_options(node),
                    "action_payloads": _json_loads_payloads(node),
                    "runtime_calls": _runtime_calls(node),
                }
            )

    return {"constants": constants, "commands": commands}


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_parse_llm_response_regression(scenario: str, tmp_home):  # noqa: ARG001 — fixture 通过副作用隔离 ~/.cliany-site，无需在函数体引用
    scenario_dir = _scenario_dir(scenario)
    fake_responses = _load_json(scenario_dir / "fake_llm_responses.json")
    expected_parsed = _load_json(scenario_dir / "expected_parsed.json")

    assert len(fake_responses) == len(expected_parsed)
    for text, expected in zip(fake_responses, expected_parsed, strict=True):
        assert _parse_llm_response(text) == expected


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_sanitize_actions_regression(scenario: str, tmp_home):  # noqa: ARG001 — fixture 通过副作用隔离 ~/.cliany-site，无需在函数体引用
    scenario_dir = _scenario_dir(scenario)
    parsed_responses = _load_json(scenario_dir / "expected_parsed.json")
    expected_sanitized = _load_json(scenario_dir / "expected_sanitized.json")
    source_url = _load_json(scenario_dir / "expected.json")["pages"][0]["url"]

    assert len(parsed_responses) == len(expected_sanitized)
    for parsed, expected in zip(parsed_responses, expected_sanitized, strict=True):
        assert _sanitize_actions_data(parsed["actions"], source_url) == expected


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_codegen_regression(scenario: str, tmp_home):  # noqa: ARG001 — fixture 通过副作用隔离 ~/.cliany-site，无需在函数体引用
    scenario_dir = _scenario_dir(scenario)
    expected = _load_json(scenario_dir / "expected.json")
    expected_adapter_dir = scenario_dir / "expected_adapter"
    expected_commands = (expected_adapter_dir / "commands.py").read_text(encoding="utf-8")
    expected_metadata = _load_json(expected_adapter_dir / "metadata.json")

    explore_result = _explore_result_from_dict(expected)
    commands_code, metadata = _generate_adapter(explore_result, _domain_from_expected(expected))

    assert _adapter_structure_fingerprint(commands_code) == _adapter_structure_fingerprint(expected_commands)
    assert metadata["canonical_actions"] == expected_metadata["canonical_actions"]
