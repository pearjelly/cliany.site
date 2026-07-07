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
                    "status_code": 502,
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
                        "status_code": 502,
                        "phase": "llm_preflight",
                        "message": "LLM upstream returned 502 Bad Gateway",
                    },
                },
            ],
        },
    }


def _ready_doctor_payload() -> dict:
    payload = _doctor_payload()
    payload["data"]["summary"]["ready_for_explore"] = True
    payload["data"]["summary"]["capabilities"]["generate_adapters"]["ready"] = True
    payload["data"]["summary"]["llm_live_preflight"] = {
        "ready": True,
        "status": "ok",
    }
    payload["data"]["checks"][1] = {
        "name": "llm_live",
        "status": "ok",
        "details": {
            "error_code": "",
            "retryable": False,
            "status_code": 200,
            "phase": "llm_preflight",
            "message": "Live LLM preflight passed",
        },
    }
    return payload


def test_extracts_doctor_preflight_evidence_from_named_checks(tmp_path):
    payload_path = tmp_path / "doctor.json"
    payload_path.write_text(json.dumps(_doctor_payload()), encoding="utf-8")

    evidence = extract_doctor_preflight_evidence.extract_file(payload_path)

    assert evidence["ok"] is True
    assert evidence["field_count"] == 12
    assert evidence["missing_count"] == 0
    assert evidence["values"]["summary.ready_for_explore"] is False
    assert evidence["values"]["summary.llm_live_preflight"] == {
        "ready": False,
        "status": "warning",
        "error_code": "E_LLM_UNAVAILABLE",
        "status_code": 502,
    }
    assert evidence["values"]["summary.capabilities.run_browser_workflows.ready"] is True
    assert evidence["values"]["summary.capabilities.generate_adapters.ready"] is False
    assert evidence["values"]["checks[cdp].status"] == "ok"
    assert evidence["values"]["checks[llm_live].status"] == "warning"
    assert evidence["values"]["checks[llm_live].details.error_code"] == (
        "E_LLM_UNAVAILABLE"
    )
    assert evidence["values"]["checks[llm_live].details.retryable"] is True
    assert evidence["values"]["checks[llm_live].details.status_code"] == 502
    assert evidence["values"]["checks[llm_live].details.message"] == (
        "LLM upstream returned 502 Bad Gateway"
    )
    assert evidence["selectors"]["checks[llm_live].details.error_code"] == (
        'data.checks[name="llm_live"].details.error_code'
    )
    assert evidence["selectors_sha256"]
    assert evidence["preflight_state"] == {
        "status": "blocked",
        "ready_for_adapter_package": False,
        "primary_reason": "Live LLM preflight is warning.",
        "reason_codes": [
            "ready_for_explore_false",
            "llm_live_preflight_not_ready",
            "generate_adapters_not_ready",
            "llm_live_status_warning",
        ],
        "next_action": (
            "Attach the doctor preflight evidence to the candidate issue and do "
            "not run candidate explore until live preflight is ready."
        ),
    }


def test_preflight_state_ready_when_all_required_values_pass(tmp_path):
    payload_path = tmp_path / "doctor-ready.json"
    payload_path.write_text(json.dumps(_ready_doctor_payload()), encoding="utf-8")

    evidence = extract_doctor_preflight_evidence.extract_file(payload_path)

    assert evidence["preflight_state"]["status"] == "ready"
    assert evidence["preflight_state"]["ready_for_adapter_package"] is True
    assert evidence["preflight_state"]["reason_codes"] == []
    assert evidence["preflight_state"]["next_action"].startswith(
        "Run the candidate explore command"
    )


def test_preflight_state_blocks_when_summary_llm_live_preflight_is_not_ready(tmp_path):
    payload = _ready_doctor_payload()
    payload["data"]["summary"]["llm_live_preflight"]["ready"] = False
    payload_path = tmp_path / "doctor-llm-summary-blocked.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    evidence = extract_doctor_preflight_evidence.extract_file(payload_path)

    assert evidence["preflight_state"]["status"] == "blocked"
    assert evidence["preflight_state"]["ready_for_adapter_package"] is False
    assert "llm_live_preflight_not_ready" in evidence["preflight_state"]["reason_codes"]


def test_preflight_state_missing_fields_when_named_check_absent(tmp_path):
    payload = _doctor_payload()
    payload["data"]["checks"] = [payload["data"]["checks"][0]]
    payload_path = tmp_path / "doctor-missing.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    evidence = extract_doctor_preflight_evidence.extract_file(payload_path)

    assert evidence["ok"] is False
    assert evidence["preflight_state"]["status"] == "missing_fields"
    assert evidence["preflight_state"]["ready_for_adapter_package"] is False
    assert evidence["preflight_state"]["reason_codes"] == ["missing_fields"]
    assert evidence["preflight_state"]["primary_reason"].startswith(
        "Missing required doctor evidence field:"
    )


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
    assert "- preflight_status: `blocked`" in text
    assert "- ready_for_adapter_package: `false`" in text
    assert (
        "- preflight_next_action: `Attach the doctor preflight evidence to the "
        "candidate issue and do not run candidate explore until live preflight is ready.`"
    ) in text
    assert "| `summary.ready_for_explore` | `false` |" in text
    assert "| `summary.llm_live_preflight` | `{'ready': False" in text
    assert "| `summary.capabilities.generate_adapters.ready` | `false` |" in text
    assert "| `checks[llm_live].details.error_code` | `E_LLM_UNAVAILABLE` |" in text
    assert "| `checks[llm_live].details.status_code` | `502` |" in text
    assert (
        "| `checks[llm_live].details.message` | "
        "`LLM upstream returned 502 Bad Gateway` |"
    ) in text
