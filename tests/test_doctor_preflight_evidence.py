import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "extract_doctor_preflight_evidence.py"
SPEC = importlib.util.spec_from_file_location("extract_doctor_preflight_evidence", SCRIPT)
assert SPEC is not None
extract_doctor_preflight_evidence = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = extract_doctor_preflight_evidence
SPEC.loader.exec_module(extract_doctor_preflight_evidence)


def _doctor_payload() -> dict:
    return {
        "ok": True,
        "data": {
            "summary": {
                "ready_for_explore": False,
                "capabilities": {
                    "run_browser_workflows": {"ready": True},
                    "generate_adapters": {"ready": False},
                },
                "llm_live_preflight": {
                    "ready": False,
                    "status": "warning",
                    "error_code": "E_LLM_UNAVAILABLE",
                },
            },
            "checks": [
                {"name": "cdp", "status": "ok", "action": "Chrome/CDP 可用"},
                {
                    "name": "llm_live",
                    "status": "warning",
                    "details": {
                        "error_code": "E_LLM_UNAVAILABLE",
                        "retryable": True,
                        "phase": "llm_preflight",
                        "message": "LLM upstream returned 502 Bad Gateway",
                    },
                },
            ],
        },
    }


def test_extracts_doctor_preflight_evidence_from_named_checks(tmp_path):
    payload_path = tmp_path / "doctor.json"
    payload_path.write_text(json.dumps(_doctor_payload()), encoding="utf-8")

    evidence = extract_doctor_preflight_evidence.extract_file(payload_path)

    assert evidence["ok"] is True
    assert evidence["field_count"] == 10
    assert evidence["missing_count"] == 0
    assert evidence["values"]["summary.ready_for_explore"] is False
    assert evidence["values"]["summary.capabilities.run_browser_workflows.ready"] is True
    assert evidence["values"]["summary.capabilities.generate_adapters.ready"] is False
    assert evidence["values"]["checks[cdp].status"] == "ok"
    assert evidence["values"]["checks[llm_live].status"] == "warning"
    assert evidence["values"]["checks[llm_live].details.error_code"] == (
        "E_LLM_UNAVAILABLE"
    )
    assert evidence["values"]["checks[llm_live].details.retryable"] is True
    assert evidence["values"]["checks[llm_live].details.message"] == (
        "LLM upstream returned 502 Bad Gateway"
    )
    assert evidence["selectors"]["checks[llm_live].details.error_code"] == (
        'data.checks[name="llm_live"].details.error_code'
    )
    assert evidence["selectors_sha256"]


def test_cli_outputs_evidence_json(tmp_path, capsys):
    payload_path = tmp_path / "doctor.json"
    payload_path.write_text(json.dumps(_doctor_payload()), encoding="utf-8")

    exit_code = extract_doctor_preflight_evidence.main([str(payload_path)])

    assert exit_code == 0
    evidence = json.loads(capsys.readouterr().out)
    assert evidence["ok"] is True
    assert evidence["values"]["checks[llm_live].details.error_code"] == (
        "E_LLM_UNAVAILABLE"
    )


def test_cli_outputs_markdown_blocker_comment(tmp_path, capsys):
    payload_path = tmp_path / "doctor.json"
    payload_path.write_text(json.dumps(_doctor_payload()), encoding="utf-8")

    exit_code = extract_doctor_preflight_evidence.main(
        [str(payload_path), "--markdown"]
    )

    assert exit_code == 0
    text = capsys.readouterr().out
    assert "## Doctor Preflight Evidence" in text
    assert "- ok: `true`" in text
    assert "- missing_count: `0`" in text
    assert "- selectors_sha256:" in text
    assert "| `summary.ready_for_explore` | `false` |" in text
    assert "| `summary.capabilities.generate_adapters.ready` | `false` |" in text
    assert "| `checks[llm_live].details.error_code` | `E_LLM_UNAVAILABLE` |" in text
    assert (
        "| `checks[llm_live].details.message` | "
        "`LLM upstream returned 502 Bad Gateway` |"
    ) in text
