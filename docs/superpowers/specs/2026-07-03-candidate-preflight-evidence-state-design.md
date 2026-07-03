# Candidate Preflight Evidence State Design

## Context

The current release train is preparing `v0.16.257` while the 2026-07-03 daily release cap is full. Recent versions made candidate promotion handoffs machine-readable, but the primary candidate `pypi-project-search` still depends on a human reading extracted doctor evidence and deciding whether the next step is blocked or ready.

The next useful slice is to make that decision explicit without changing adapter runtime behavior or promoting any candidate early.

## Goal

Add a compact preflight evidence state that tells maintainers and automation whether a `doctor --llm-live --json` evidence file means:

- `ready`: live preflight passed and adapter generation can proceed.
- `blocked`: required doctor fields were present, but CDP, live LLM, ready-for-explore, or adapter generation readiness failed.
- `missing_fields`: the evidence file did not contain all required selector values.

## Non-Goals

- Do not generate a real PyPI adapter package in this slice.
- Do not update `cases/manifest.json` evidence or mark `pypi-project-search` active.
- Do not create or push `v0.16.257` while the daily release cap is blocking.
- Do not write runtime state into the repository.

## Design

`scripts/extract_doctor_preflight_evidence.py` remains the source of truth for reading a doctor JSON file. It will add a `preflight_state` object to both JSON and Markdown output. The state is derived only from the existing selector values, so there is no new dependency on Chrome, an LLM, or live network state during tests.

The state object should include:

- `status`: one of `ready`, `blocked`, or `missing_fields`.
- `ready_for_adapter_package`: `true` only when status is `ready`.
- `primary_reason`: the first human-readable reason to act on.
- `reason_codes`: stable machine-readable reason codes.
- `next_action`: the next maintainer action.

The required ready conditions are:

- `summary.ready_for_explore` is `true`.
- `summary.capabilities.run_browser_workflows.ready` is `true`.
- `summary.capabilities.generate_adapters.ready` is `true`.
- `checks[cdp].status` is `ok`.
- `checks[llm_live].status` is `ok`.

Any missing selector value yields `missing_fields`. Any present-but-not-ready value yields `blocked`.

## Surfaces

This slice starts with the extractor because that is the point where actual doctor evidence becomes concrete. Follow-up slices can lift the same state aliases into `validate_cases.py`, `cliany-site cases`, and `plan_next_iteration.py` if the extractor output proves useful.

For `v0.16.257`, the release notes should say that doctor preflight evidence now classifies the candidate promotion gate as ready, blocked, or missing fields. That is a real maintainer value even if the live provider is still down.

## Testing

Add focused tests in `tests/test_doctor_preflight_evidence.py`:

- Existing blocked fixture returns `preflight_state.status == "blocked"` and a provider-related next action.
- A ready fixture returns `preflight_state.status == "ready"` and `ready_for_adapter_package == true`.
- A fixture with a missing LLM check returns `preflight_state.status == "missing_fields"`.
- Markdown output renders the status and next action.

Run the focused extractor tests, then release draft tests to ensure the release notes remain valid.
