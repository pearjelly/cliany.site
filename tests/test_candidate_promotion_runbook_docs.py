from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "candidate-promotion-runbook.md"


def test_candidate_promotion_runbook_documents_doctor_state_contract():
    text = RUNBOOK.read_text(encoding="utf-8")

    required = [
        "doctor_preflight_state_fields",
        "doctor_preflight_state_statuses",
        "preflight_state.status",
        "preflight_state.ready_for_adapter_package",
        "preflight_state.primary_reason",
        "preflight_state.reason_codes",
        "preflight_state.next_action",
        "ready",
        "blocked",
        "missing_fields",
    ]
    for snippet in required:
        assert snippet in text
