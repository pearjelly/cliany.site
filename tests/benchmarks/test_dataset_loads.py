import json


REQUIRED_ARTIFACTS = [
    "axtree.json",
    "fake_llm_responses.json",
    "expected_parsed.json",
    "expected_sanitized.json",
    "expected.json",
    "expected_adapter/commands.py",
    "expected_adapter/metadata.json",
]


def test_scenario_artifacts_exist_and_parse(scenario):
    for relative_path in REQUIRED_ARTIFACTS:
        path = scenario["dir"] / relative_path
        assert path.exists(), f"{scenario['name']} 缺少 {relative_path}"
        assert path.stat().st_size > 0, f"{scenario['name']} 的 {relative_path} 为空"

    for relative_path in [
        "axtree.json",
        "fake_llm_responses.json",
        "expected_parsed.json",
        "expected_sanitized.json",
        "expected.json",
        "expected_adapter/metadata.json",
    ]:
        json.loads((scenario["dir"] / relative_path).read_text(encoding="utf-8"))


def test_fake_llm_responses_follow_prompt_contract(scenario):
    assert isinstance(scenario["fake_responses"], list)
    assert scenario["fake_responses"], f"{scenario['name']} fake 响应不能为空"

    for raw_response in scenario["fake_responses"]:
        assert isinstance(raw_response, str)
        parsed = json.loads(raw_response)
        assert "actions" in parsed or "commands" in parsed
        assert "done" in parsed
        assert "reasoning" in parsed
        if parsed.get("done") is True:
            assert "commands" in parsed
            for command in parsed["commands"]:
                assert "args" in command
                assert "action_steps" in command


def test_expected_adapter_excludes_nondeterministic_fields(scenario):
    metadata = json.loads((scenario["dir"] / "expected_adapter" / "metadata.json").read_text(encoding="utf-8"))
    assert "signature" not in metadata
    assert "generated_at" not in metadata

    commands_py = (scenario["dir"] / "expected_adapter" / "commands.py").read_text(encoding="utf-8")
    assert "# 生成时间:" not in commands_py
    assert "# 自动生成 — DO NOT EDIT" in commands_py


def test_expected_baseline_shapes(scenario):
    axtree = scenario["axtree"]
    assert {"element_tree", "selector_map", "url", "title", "pruning_meta"} <= set(axtree)
    assert isinstance(scenario["expected_parsed"], list)
    assert isinstance(scenario["expected_sanitized"], list)
    assert {"pages", "actions", "commands", "canonical_actions"} <= set(scenario["expected"])
