# Candidate Preflight Evidence State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact ready/blocked/missing-fields state to doctor preflight evidence extraction so candidate promotion can act on live preflight evidence without hand-reading raw fields.

**Architecture:** Keep the state derivation inside `scripts/extract_doctor_preflight_evidence.py`, beside the existing selector extraction logic. Tests exercise the extractor directly with deterministic doctor JSON fixtures and verify both JSON and Markdown surfaces.

**Tech Stack:** Python 3.11, pytest, existing `validate_cases.DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS`, existing JSON/Markdown extractor output.

---

## File Structure

- Modify `scripts/extract_doctor_preflight_evidence.py`: add preflight state constants and a pure `_build_preflight_state(values, missing_fields)` helper; include `preflight_state` in `extract_payload()` and Markdown output.
- Modify `tests/test_doctor_preflight_evidence.py`: add ready and missing-fields fixtures plus assertions for blocked, ready, missing-fields, and Markdown rendering.
- Modify `CHANGELOG.md`: document the new extractor state under `[Unreleased]`.
- Modify `docs/releases/v0.16.257-draft.md`: document the release value and validation command.

### Task 1: Extractor State Helper

**Files:**
- Modify: `tests/test_doctor_preflight_evidence.py`
- Modify: `scripts/extract_doctor_preflight_evidence.py`

- [ ] **Step 1: Write the failing blocked-state test**

Add assertions to `test_extracts_doctor_preflight_evidence_from_named_checks`:

```python
    assert evidence["preflight_state"] == {
        "status": "blocked",
        "ready_for_adapter_package": False,
        "primary_reason": "Live LLM preflight is warning.",
        "reason_codes": [
            "ready_for_explore_false",
            "generate_adapters_not_ready",
            "llm_live_status_warning",
        ],
        "next_action": (
            "Attach the doctor preflight evidence to the candidate issue and do "
            "not run candidate explore until live preflight is ready."
        ),
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_doctor_preflight_evidence.py::test_extracts_doctor_preflight_evidence_from_named_checks -q --no-cov --tb=short
```

Expected: FAIL with `KeyError: 'preflight_state'`.

- [ ] **Step 3: Implement minimal state helper**

Add to `scripts/extract_doctor_preflight_evidence.py`:

```python
READY_NEXT_ACTION = (
    "Run the candidate explore command, then package the adapter and attach "
    "the package path or release asset name."
)
BLOCKED_NEXT_ACTION = (
    "Attach the doctor preflight evidence to the candidate issue and do "
    "not run candidate explore until live preflight is ready."
)
MISSING_FIELDS_NEXT_ACTION = (
    "Attach the missing field list and original doctor JSON summary before "
    "continuing candidate promotion."
)


def _build_preflight_state(
    values: dict[str, Any],
    missing_fields: list[str],
) -> dict[str, Any]:
    if missing_fields:
        return {
            "status": "missing_fields",
            "ready_for_adapter_package": False,
            "primary_reason": f"Missing required doctor evidence field: {missing_fields[0]}.",
            "reason_codes": ["missing_fields"],
            "next_action": MISSING_FIELDS_NEXT_ACTION,
        }

    checks = [
        (
            "summary.ready_for_explore",
            values.get("summary.ready_for_explore") is True,
            "ready_for_explore_false",
            "Doctor summary is not ready for explore.",
        ),
        (
            "summary.capabilities.run_browser_workflows.ready",
            values.get("summary.capabilities.run_browser_workflows.ready") is True,
            "run_browser_workflows_not_ready",
            "Browser workflow capability is not ready.",
        ),
        (
            "summary.capabilities.generate_adapters.ready",
            values.get("summary.capabilities.generate_adapters.ready") is True,
            "generate_adapters_not_ready",
            "Adapter generation capability is not ready.",
        ),
        (
            "checks[cdp].status",
            values.get("checks[cdp].status") == "ok",
            f"cdp_status_{values.get('checks[cdp].status')}",
            f"CDP check is {values.get('checks[cdp].status')}.",
        ),
        (
            "checks[llm_live].status",
            values.get("checks[llm_live].status") == "ok",
            f"llm_live_status_{values.get('checks[llm_live].status')}",
            f"Live LLM preflight is {values.get('checks[llm_live].status')}.",
        ),
    ]
    failures = [
        {"field": field, "reason_code": reason_code, "reason": reason}
        for field, ok, reason_code, reason in checks
        if not ok
    ]
    if failures:
        return {
            "status": "blocked",
            "ready_for_adapter_package": False,
            "primary_reason": failures[-1]["reason"],
            "reason_codes": [failure["reason_code"] for failure in failures],
            "next_action": BLOCKED_NEXT_ACTION,
        }
    return {
        "status": "ready",
        "ready_for_adapter_package": True,
        "primary_reason": "Doctor preflight is ready for candidate adapter generation.",
        "reason_codes": [],
        "next_action": READY_NEXT_ACTION,
    }
```

Then add `"preflight_state": _build_preflight_state(values, missing_fields)` to the returned evidence payload.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_doctor_preflight_evidence.py::test_extracts_doctor_preflight_evidence_from_named_checks -q --no-cov --tb=short
```

Expected: PASS.

### Task 2: Ready and Missing Field Coverage

**Files:**
- Modify: `tests/test_doctor_preflight_evidence.py`

- [ ] **Step 1: Write failing ready and missing-field tests**

Add:

```python
def _ready_doctor_payload() -> dict:
    payload = _doctor_payload()
    payload["data"]["summary"]["ready_for_explore"] = True
    payload["data"]["summary"]["capabilities"]["generate_adapters"]["ready"] = True
    payload["data"]["summary"]["llm_live_preflight"] = {"ready": True, "status": "ok"}
    payload["data"]["checks"][1] = {
        "name": "llm_live",
        "status": "ok",
        "details": {
            "error_code": "",
            "retryable": False,
            "phase": "llm_preflight",
            "message": "Live LLM preflight passed",
        },
    }
    return payload


def test_preflight_state_ready_when_all_required_values_pass(tmp_path):
    payload_path = tmp_path / "doctor-ready.json"
    payload_path.write_text(json.dumps(_ready_doctor_payload()), encoding="utf-8")

    evidence = extract_doctor_preflight_evidence.extract_file(payload_path)

    assert evidence["preflight_state"]["status"] == "ready"
    assert evidence["preflight_state"]["ready_for_adapter_package"] is True
    assert evidence["preflight_state"]["reason_codes"] == []
    assert evidence["preflight_state"]["next_action"].startswith("Run the candidate explore command")


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
```

- [ ] **Step 2: Run tests to verify failures or passes after Task 1**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_doctor_preflight_evidence.py -q --no-cov --tb=short
```

Expected after Task 1: PASS for ready and missing-field coverage if helper is complete.

### Task 3: Markdown Output and Release Docs

**Files:**
- Modify: `tests/test_doctor_preflight_evidence.py`
- Modify: `scripts/extract_doctor_preflight_evidence.py`
- Modify: `CHANGELOG.md`
- Modify: `docs/releases/v0.16.257-draft.md`

- [ ] **Step 1: Write failing Markdown assertions**

Add to `test_cli_outputs_markdown_blocker_comment`:

```python
    assert "- preflight_status: `blocked`" in text
    assert "- ready_for_adapter_package: `false`" in text
    assert (
        "- preflight_next_action: `Attach the doctor preflight evidence to the "
        "candidate issue and do not run candidate explore until live preflight is ready.`"
    ) in text
```

- [ ] **Step 2: Run Markdown test to verify it fails**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_doctor_preflight_evidence.py::test_cli_outputs_markdown_blocker_comment -q --no-cov --tb=short
```

Expected before Markdown implementation: FAIL because these lines are absent.

- [ ] **Step 3: Render preflight state in Markdown**

In `render_markdown()`, after the `values_sha256` line, add:

```python
        f"- preflight_status: `{preflight_state.get('status', '-')}`",
        (
            "- ready_for_adapter_package: "
            f"`{str(bool(preflight_state.get('ready_for_adapter_package'))).lower()}`"
        ),
        f"- preflight_primary_reason: `{preflight_state.get('primary_reason', '-')}`",
        f"- preflight_next_action: `{preflight_state.get('next_action', '-')}`",
```

Also define:

```python
    preflight_state = evidence.get("preflight_state")
    preflight_state = preflight_state if isinstance(preflight_state, dict) else {}
```

- [ ] **Step 4: Update release docs**

Add one bullet to `CHANGELOG.md` `[Unreleased]`:

```markdown
- Doctor preflight evidence extraction now classifies candidate promotion preflight as `ready`, `blocked`, or `missing_fields`, with stable reason codes and next actions for the PyPI candidate adapter-package gate.
```

Add one sentence to `docs/releases/v0.16.257-draft.md` user value section:

```markdown
Extractor JSON and Markdown output now include `preflight_state`, so a stored doctor preflight file directly tells maintainers whether to run candidate `explore`, attach blocker evidence, or fix missing selector fields.
```

- [ ] **Step 5: Run focused validation**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_doctor_preflight_evidence.py tests/test_release_draft_docs.py -q --no-cov --tb=short
```

Expected: PASS.

### Task 4: Commit and Release-Readiness Recheck

**Files:**
- Modified files from Tasks 1-3

- [ ] **Step 1: Run formatting/static checks for touched files**

Run:

```bash
uv run --extra dev --frozen ruff check scripts/extract_doctor_preflight_evidence.py tests/test_doctor_preflight_evidence.py
git diff --check
```

Expected: both PASS.

- [ ] **Step 2: Run narrow release readiness**

Run:

```bash
uv run --extra dev --frozen python scripts/release_readiness.py --strict --target-version 0.16.257 --remote --remote-name origin --json
```

Expected on 2026-07-03: FAIL only because `creating target tag v0.16.257 today would exceed the daily release cap 4/3`.

- [ ] **Step 3: Commit**

Run:

```bash
git add scripts/extract_doctor_preflight_evidence.py tests/test_doctor_preflight_evidence.py CHANGELOG.md docs/releases/v0.16.257-draft.md docs/superpowers/specs/2026-07-03-candidate-preflight-evidence-state-design.md docs/superpowers/plans/2026-07-03-candidate-preflight-evidence-state.md
git commit -m "feat(cases): classify doctor preflight evidence"
```

Expected: commit succeeds. Do not create or push `v0.16.257` on 2026-07-03.

## Self-Review

- Spec coverage: Task 1 adds blocked state, Task 2 adds ready and missing-fields state, Task 3 exposes Markdown and release docs, Task 4 verifies and commits without tagging.
- Placeholder scan: no TBD/TODO placeholders remain; commands and expected outcomes are concrete.
- Type consistency: `preflight_state.status`, `ready_for_adapter_package`, `primary_reason`, `reason_codes`, and `next_action` are consistent across tests, implementation, and docs.
