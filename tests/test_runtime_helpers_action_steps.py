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
