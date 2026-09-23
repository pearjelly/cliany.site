from __future__ import annotations

from cliany_site.codegen import runtime_helpers


def test_execute_steps_routes_select_and_submit_to_browser_atoms(monkeypatch):
    calls: list[tuple[list[str], str | None]] = []

    def fake_run_atom(command: list[str], session: str | None = None, heal_on_failure: bool = False):
        assert heal_on_failure is False
        calls.append((command, session))
        return {"ok": True, "command": " ".join(command), "data": {}}

    monkeypatch.setattr(runtime_helpers, "run_atom", fake_run_atom)

    results = runtime_helpers.execute_steps_via_atoms(
        [
            {"type": "select", "ref": "6", "value": "high"},
            {"type": "submit", "ref": "2"},
        ],
        source_url="",
        domain="example.test",
    )

    assert [result["ok"] for result in results] == [True, True]
    assert calls == [
        (["browser", "select", "--ref", "6", "--value", "high"], "example.test"),
        (["browser", "submit", "--ref", "2"], "example.test"),
    ]


def test_execute_steps_routes_submit_without_a_target_to_enter(monkeypatch):
    calls: list[list[str]] = []

    def fake_run_atom(command: list[str], session: str | None = None, heal_on_failure: bool = False):
        assert session == "example.test"
        assert heal_on_failure is False
        calls.append(command)
        return {"ok": True, "command": " ".join(command), "data": {}}

    monkeypatch.setattr(runtime_helpers, "run_atom", fake_run_atom)

    runtime_helpers.execute_steps_via_atoms(
        [{"type": "submit"}],
        source_url="",
        domain="example.test",
    )

    assert calls == [["browser", "submit"]]


def test_execute_steps_sandbox_blocks_cross_domain_before_atoms(monkeypatch):
    def unexpected_atom(*_args, **_kwargs):
        raise AssertionError("sandbox preflight must run before atoms")

    monkeypatch.setattr(runtime_helpers, "run_atom", unexpected_atom)

    results = runtime_helpers.execute_steps_via_atoms(
        [{"type": "navigate", "url": "https://evil.example/path"}],
        source_url="https://example.test",
        domain="example.test",
        sandbox=True,
    )

    assert results[0]["ok"] is False
    assert results[0]["error"]["code"] == "E_SANDBOX_VIOLATION"
    assert results[0]["error"]["details"]["action"] == "navigate"


def test_empty_list_extract_retries_until_rows_arrive(monkeypatch):
    calls: list[list[str]] = []
    delays: list[float] = []

    def fake_run_atom(command: list[str], session: str | None = None, heal_on_failure: bool = False):
        assert session == "example.test"
        calls.append(command)
        row_count = 0 if len(calls) == 1 else 1
        return {
            "ok": True,
            "data": {
                "content": [] if row_count == 0 else [{"title": "Result"}],
                "quality": {"status": "empty" if row_count == 0 else "ok", "row_count": row_count},
            },
        }

    monkeypatch.setattr(runtime_helpers, "run_atom", fake_run_atom)
    monkeypatch.setattr(runtime_helpers.time, "sleep", delays.append)

    results = runtime_helpers.execute_steps_via_atoms(
        [{"type": "extract", "selector": "a.result", "extract_mode": "list"}],
        source_url="",
        domain="example.test",
    )

    assert len(calls) == 2
    assert delays == [0.5]
    assert results[0]["data"]["content"] == [{"title": "Result"}]


def test_empty_list_extract_retry_is_bounded(monkeypatch):
    calls: list[list[str]] = []
    delays: list[float] = []

    def fake_run_atom(command: list[str], session: str | None = None, heal_on_failure: bool = False):
        calls.append(command)
        return {"ok": True, "data": {"content": [], "quality": {"status": "empty"}}}

    monkeypatch.setattr(runtime_helpers, "run_atom", fake_run_atom)
    monkeypatch.setattr(runtime_helpers.time, "sleep", delays.append)

    results = runtime_helpers.execute_steps_via_atoms(
        [{"type": "extract", "selector": "a.result", "extract_mode": "list"}],
        source_url="",
        domain="example.test",
    )

    assert len(calls) == 3
    assert delays == [0.5, 1.0]
    assert results[0]["data"]["quality"]["status"] == "empty"


def test_partial_extract_does_not_retry(monkeypatch):
    calls: list[list[str]] = []

    def fake_run_atom(command: list[str], session: str | None = None, heal_on_failure: bool = False):
        calls.append(command)
        return {"ok": True, "data": {"content": [{"title": ""}], "quality": {"status": "partial"}}}

    monkeypatch.setattr(runtime_helpers, "run_atom", fake_run_atom)
    monkeypatch.setattr(runtime_helpers.time, "sleep", lambda _: (_ for _ in ()).throw(AssertionError("unexpected retry")))

    runtime_helpers.execute_steps_via_atoms(
        [{"type": "extract", "selector": "a.result", "extract_mode": "list"}],
        source_url="",
        domain="example.test",
    )

    assert len(calls) == 1
