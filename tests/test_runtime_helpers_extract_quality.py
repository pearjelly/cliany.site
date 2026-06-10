from cliany_site.codegen import runtime_helpers


def test_execute_single_extract_step_passes_mode_and_fields(monkeypatch):
    calls: list[list[str]] = []

    def fake_run_atom(command, session=None, heal_on_failure=False):  # noqa: ARG001
        calls.append(command)
        return {
            "ok": True,
            "command": "browser extract",
            "data": {
                "content": [{"title": "A", "url": "https://example.com"}],
                "mode": "list",
            },
        }

    monkeypatch.setattr(runtime_helpers, "run_atom", fake_run_atom)

    result = runtime_helpers._execute_single_step(
        {
            "type": "extract",
            "selector": ".result",
            "extract_mode": "list",
            "fields": {"title": "h3", "url": "a@href"},
        },
        "example.com",
    )

    assert result["ok"] is True
    assert calls == [
        [
            "browser",
            "extract",
            "--selector",
            ".result",
            "--mode",
            "list",
            "--fields-json",
            '{"title": "h3", "url": "a@href"}',
        ]
    ]


def test_summarize_extract_quality_matches_extract_results_after_navigation():
    results = [
        {"ok": True, "command": "browser navigate", "data": {}},
        {
            "ok": True,
            "command": "browser extract",
            "data": {"content": [{"title": "", "url": ""}]},
        },
    ]
    action_steps = [
        {
            "type": "extract",
            "description": "提取搜索结果",
            "extract_mode": "list",
            "fields": {"title": "h3", "url": "a@href"},
        }
    ]

    quality = runtime_helpers.summarize_extract_quality(results, action_steps)

    assert quality["ok"] is False
    assert quality["status"] == "empty"
    assert quality["extracts"][0]["step_index"] == 0
    assert "field is blank in all rows: title" in quality["extracts"][0]["issues"]
