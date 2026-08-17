import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capture_active_demo_evidence.py"
SPEC = importlib.util.spec_from_file_location("capture_active_demo_evidence", SCRIPT)
assert SPEC is not None
capture = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = capture
SPEC.loader.exec_module(capture)


def _case(*, status="active"):
    return {
        "id": "demo-case",
        "title": "Demo case",
        "status": status,
        "target_url": "https://example.test/",
        "adapter_domain": "example.test",
        "source_release": "v0.14.1",
        "commands": ["cliany-site market install https://example.test/package.tar.gz --sha256 " + "a" * 64,
                      "cliany-site example.test list-items --limit 2 --json"],
        "validation": {"online": "read-only item listing returns rows"},
    }


def _runner_for(*, verify_ok=True, read_only_ok=True):
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        is_verify = "verify" in argv
        ok = verify_ok if is_verify else read_only_ok
        payload = {"ok": ok, "data": {"kind": "verify" if is_verify else "read-only"}, "error": None}
        return SimpleNamespace(returncode=0 if ok else 1, stdout=json.dumps(payload), stderr="")

    runner.calls = calls
    return runner


def test_declared_commands_adds_strict_verify_and_preserves_read_only_command():
    verify, read_only = capture.declared_commands(_case())

    assert verify == "cliany-site verify example.test --strict --json"
    assert read_only == "cliany-site example.test list-items --limit 2 --json"


def test_capture_runs_read_only_only_after_successful_verify():
    runner = _runner_for()
    report = capture.capture_case(_case(), captured="2026-08-17", runner=runner)

    assert report["ok"] is True
    assert report["verify"].ok is True
    assert report["read_only"].ok is True
    assert [call[3] for call in runner.calls] == ["verify", "example.test"]


def test_capture_skips_read_only_after_verify_failure():
    runner = _runner_for(verify_ok=False)
    report = capture.capture_case(_case(), runner=runner)

    assert report["ok"] is False
    assert report["verify"].ok is False
    assert report["read_only"].skipped is True
    assert len(runner.calls) == 1


def test_candidate_and_non_read_only_cases_are_rejected():
    with pytest.raises(ValueError, match="不是 active"):
        capture.select_case([_case(status="candidate")], "demo-case")

    invalid = _case()
    invalid["validation"] = {"online": "writes an item"}
    with pytest.raises(ValueError, match="read-only"):
        capture.declared_commands(invalid)


def test_markdown_keeps_boundary_and_result_payload():
    runner = _runner_for()
    report = capture.capture_case(_case(), captured="2026-08-17", runner=runner)
    markdown = capture.render_markdown(report)

    assert "**Captured:** 2026-08-17" in markdown
    assert "read-only command is run only after strict static verification" in markdown
    assert '"kind": "verify"' in markdown
    assert "candidate package promotion" in markdown
