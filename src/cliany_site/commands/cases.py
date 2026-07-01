from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import click

from cliany_site.envelope import Envelope, ErrorCode, err, ok
from cliany_site.response import print_response

ALLOWED_STATUSES = ("active", "candidate", "degraded", "known-gap", "retired")
PROMOTION_TASKS = ("adapter_package", "metadata_validation", "online_smoke")
PROMOTION_COMMAND_PLAN_TASKS = (
    "llm_live_preflight",
    "adapter_package",
    "metadata_validation",
    "online_smoke",
)
CANDIDATE_PACKAGES_DIR = "~/.cliany-site/packages"
CANDIDATE_PACKAGE_VALIDATION_COMMAND = (
    "python scripts/validate_cases.py "
    f"--packages-dir {CANDIDATE_PACKAGES_DIR} --include-candidate-packages --strict"
)
LLM_LIVE_PREFLIGHT_COMMAND = "cliany-site doctor --llm-live --json"
LLM_LIVE_PREFLIGHT_BLOCKER_NOTE = (
    "Run the live LLM preflight before explore. If generate_adapters.ready=false "
    "or llm_live reports warning/error such as E_LLM_UNAVAILABLE "
    "(including provider connection failure), stop candidate promotion, attach "
    "the doctor JSON/error summary, and leave adapter_package pending or blocked."
)
LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS = (
    "summary.ready_for_explore",
    "summary.capabilities.generate_adapters.ready",
    "checks[llm_live].status",
    "checks[llm_live].details.error_code",
    "checks[llm_live].details.phase",
    "checks[llm_live].details.message",
)
PROMOTION_ACCEPTANCE_CRITERIA = {
    "adapter_package": (
        "Attach the generated <domain>-<version>.cliany-adapter.tar.gz package path "
        "or GitHub Release asset name."
    ),
    "metadata_validation": (
        f"Paste `{CANDIDATE_PACKAGE_VALIDATION_COMMAND}` output showing the candidate "
        "package passed schema v3, manifest hash, and adapter_domain validation."
    ),
    "online_smoke": (
        "Paste the read-only adapter command JSON envelope summary with ok=true, "
        "data.quality.ok=true, and row_count>0."
    ),
}


def _case_catalog_paths() -> list[Path]:
    command_path = Path(__file__).resolve()
    return [
        command_path.parents[1] / "cases" / "manifest.json",
        command_path.parents[3] / "cases" / "manifest.json",
        Path.cwd() / "cases" / "manifest.json",
    ]


def _load_cases_manifest() -> tuple[list[dict[str, Any]], Path | None, list[Path]]:
    checked_paths = _case_catalog_paths()
    for path in checked_paths:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            msg = f"{path} must contain a JSON array"
            raise ValueError(msg)
        cases = [case for case in payload if isinstance(case, dict)]
        return cases, path, checked_paths
    return [], None, checked_paths


def _offline_commands(case: dict[str, Any]) -> list[str]:
    validation = case.get("validation")
    if not isinstance(validation, dict):
        return []
    commands = validation.get("offline_commands")
    if not isinstance(commands, list):
        return []
    return [str(command) for command in commands]


def _candidate_explore_commands(case: dict[str, Any]) -> list[str]:
    raw_commands = case.get("commands")
    commands = raw_commands if isinstance(raw_commands, list) else []
    return [str(command) for command in commands if str(command).startswith("cliany-site explore ")]


def _candidate_adapter_commands(case: dict[str, Any]) -> list[str]:
    raw_commands = case.get("commands")
    commands = raw_commands if isinstance(raw_commands, list) else []
    return [
        str(command)
        for command in commands
        if str(command).startswith("cliany-site ") and not str(command).startswith("cliany-site explore ")
    ]


def _candidate_promotion_command_plan(case: dict[str, Any]) -> list[dict[str, Any]]:
    explore_commands = _candidate_explore_commands(case)
    adapter_commands = _candidate_adapter_commands(case)
    adapter_domain = case.get("adapter_domain")
    plan: list[dict[str, Any]] = [
        {
            "task": "llm_live_preflight",
            "command": LLM_LIVE_PREFLIGHT_COMMAND,
            "source": "doctor.llm_live",
        },
        {
            "task": "adapter_package",
            "command": explore_commands[0] if explore_commands else "",
            "source": "commands.explore",
        },
        {
            "task": "metadata_validation",
            "command": CANDIDATE_PACKAGE_VALIDATION_COMMAND if adapter_domain else "",
            "source": "candidate_package_validation_command",
        },
        {
            "task": "online_smoke",
            "command": adapter_commands[0] if adapter_commands else "",
            "source": "commands.adapter",
        },
    ]
    for item in plan:
        item["missing"] = not bool(item["command"])
    return plan


def _compact_case(case: dict[str, Any], *, detail: bool) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": case.get("id"),
        "title": case.get("title"),
        "category": case.get("category"),
        "status": case.get("status"),
        "target_url": case.get("target_url"),
        "adapter_domain": case.get("adapter_domain"),
        "docs": case.get("docs"),
        "example_output": case.get("example_output"),
        "commands": case.get("commands") if isinstance(case.get("commands"), list) else [],
        "offline_commands": _offline_commands(case),
    }
    if detail:
        for key in ("source_release", "validation", "promotion", "promotion_evidence"):
            if key in case:
                item[key] = case.get(key)
        if case.get("status") == "candidate":
            item["promotion_command_plan"] = _candidate_promotion_command_plan(case)
    return item


def _case_ids(cases: list[dict[str, Any]]) -> list[str]:
    return [str(case.get("id")) for case in cases if case.get("id")]


def _candidate_issue_template(case: dict[str, Any]) -> str:
    case_id = str(case.get("id") or "")
    target_url = str(case.get("target_url") or "")
    raw_commands = case.get("commands")
    commands = raw_commands if isinstance(raw_commands, list) else []
    offline_commands = _offline_commands(case)
    raw_promotion = case.get("promotion")
    promotion: dict[str, Any] = raw_promotion if isinstance(raw_promotion, dict) else {}
    raw_evidence = case.get("promotion_evidence")
    evidence: dict[str, Any] = raw_evidence if isinstance(raw_evidence, dict) else {}
    primary_task = _candidate_issue_primary_task(evidence)

    lines = [
        f"## Scope: promote candidate case `{case_id}`",
        "",
        "Move this candidate case one step closer to `active` without changing its status early.",
        "",
        "## Primary Evidence Task",
    ]
    if primary_task:
        current_evidence = primary_task.get("evidence") or "Not attached yet."
        next_action = primary_task.get("next_action") or "No next action declared."
        acceptance_criteria = PROMOTION_ACCEPTANCE_CRITERIA.get(primary_task["task"], "")
        lines.extend(
            [
                f"- Task: `{primary_task['task']}`",
                f"- Status: `{primary_task['status']}`",
                f"- Current evidence: {current_evidence}",
                f"- Next action: {next_action}",
                f"- Acceptance criteria: {acceptance_criteria}",
            ]
        )
    else:
        lines.append("- All promotion tasks already have complete evidence.")

    lines.extend(
        [
            "",
            "## Reproduction Context",
            f"- Target URL: {target_url}",
            "- Candidate commands:",
        ]
    )
    lines.extend(f"  - `{command}`" for command in commands)
    lines.append("- Offline validation commands:")
    lines.extend(f"  - `{command}`" for command in offline_commands)
    lines.extend(["", "## Promotion Command Plan"])
    for item in _candidate_promotion_command_plan(case):
        command = item["command"] or "Not declared."
        lines.append(f"- `{item['task']}`: `{command}`")

    lines.extend(
        [
            "",
            "## LLM Preflight Gate",
            f"- Command: `{LLM_LIVE_PREFLIGHT_COMMAND}`",
            f"- Blocker handling: {LLM_LIVE_PREFLIGHT_BLOCKER_NOTE}",
            "",
            "## LLM Preflight Evidence Fields",
        ]
    )
    lines.extend(f"- `{field}`" for field in LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS)

    lines.extend(["", "## Acceptance Criteria"])
    for task in PROMOTION_TASKS:
        lines.append(f"- `{task}`: {PROMOTION_ACCEPTANCE_CRITERIA[task]}")

    lines.extend(["", "## Tasks"])

    for task in PROMOTION_TASKS:
        task_evidence = evidence.get(task)
        task_evidence = task_evidence if isinstance(task_evidence, dict) else {}
        status = task_evidence.get("status") or "pending"
        evidence_value = task_evidence.get("evidence")
        current_evidence = evidence_value or "Not attached yet."
        next_action = task_evidence.get("next_action") or "No next action declared."
        description = promotion.get(task) or "No task description declared."
        checkbox = "x" if status == "complete" and bool(evidence_value) else " "
        lines.extend(
            [
                f"- [{checkbox}] `{task}`: {description}",
                f"  - Current status: `{status}`",
                f"  - Current evidence: {current_evidence}",
                f"  - Next action: {next_action}",
                f"  - Acceptance criteria: {PROMOTION_ACCEPTANCE_CRITERIA[task]}",
            ]
        )

    lines.extend(
        [
            "",
            "## Evidence Bundle",
            f"- Human: `cliany-site cases --case-id {case_id} --evidence-bundle`",
            f"- JSON: `cliany-site cases --case-id {case_id} --evidence-bundle --json`",
            "- Attach or paste the JSON output in the issue once evidence changes.",
            "",
            "## Validation Evidence",
            "- Attach the generated `.cliany-adapter.tar.gz` path or release asset name.",
            (
                "- Candidate package validation command: "
                f"`{CANDIDATE_PACKAGE_VALIDATION_COMMAND}`"
            ),
            "- Paste the local `scripts/validate_cases.py --packages-dir` result.",
            "- Paste the read-only JSON envelope summary with `data.quality.ok=true` and `row_count>0`.",
            "",
            "## Non-goals",
            "- Do not mark the case `active` until all three promotion tasks are complete.",
            "- Do not require real LLM keys or write runtime state into the repository.",
        ]
    )
    return "\n".join(lines)


def _candidate_issue_primary_task(evidence: dict[str, Any]) -> dict[str, Any]:
    incomplete_tasks: list[dict[str, Any]] = []
    for task_name in PROMOTION_TASKS:
        task_evidence = evidence.get(task_name)
        task_evidence = task_evidence if isinstance(task_evidence, dict) else {}
        status = str(task_evidence.get("status") or "pending")
        evidence_value = task_evidence.get("evidence") or ""
        complete = status == "complete" and bool(evidence_value)
        if complete:
            continue
        incomplete_tasks.append(
            {
                "task": task_name,
                "status": status,
                "evidence": evidence_value,
                "next_action": str(task_evidence.get("next_action") or ""),
            }
        )

    pending_tasks = [task for task in incomplete_tasks if task["status"] == "pending"]
    blocked_tasks = [task for task in incomplete_tasks if task["status"] == "blocked"]
    primary = (
        pending_tasks[0]
        if pending_tasks
        else (blocked_tasks[0] if blocked_tasks else (incomplete_tasks[0] if incomplete_tasks else {}))
    )
    return dict(primary)


def _candidate_task_handoff(
    *,
    task: str,
    command: str,
    command_missing: bool,
    next_action: str,
) -> str:
    if command_missing:
        followup = next_action or "Attach evidence before promotion."
        return f"No executable command declared for `{task}`; {followup}"
    if next_action:
        return f"Run `{command}`; then {next_action}"
    return f"Run `{command}` and attach the evidence before promotion."


def _candidate_task_runbook(
    *,
    task: str,
    command: str,
    command_missing: bool,
    handoff: str,
    acceptance_criteria: str,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if task == "adapter_package":
        steps.append(
            {
                "step": "llm_live_preflight",
                "command": LLM_LIVE_PREFLIGHT_COMMAND,
                "required": True,
                "handoff": LLM_LIVE_PREFLIGHT_BLOCKER_NOTE,
            }
        )
    steps.append(
        {
            "step": task,
            "command": command,
            "required": not command_missing,
            "handoff": handoff,
        }
    )
    steps.append(
        {
            "step": "acceptance",
            "command": "",
            "required": True,
            "handoff": acceptance_criteria,
        }
    )
    return steps


def _runbook_first_step(runbook: Any) -> dict[str, Any]:
    if not isinstance(runbook, list):
        return {}
    for step in runbook:
        if isinstance(step, dict):
            return step
    return {}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _candidate_evidence_bundle(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("id") or "")
    adapter_domain = case.get("adapter_domain")
    raw_promotion = case.get("promotion")
    promotion: dict[str, Any] = raw_promotion if isinstance(raw_promotion, dict) else {}
    raw_evidence = case.get("promotion_evidence")
    evidence: dict[str, Any] = raw_evidence if isinstance(raw_evidence, dict) else {}
    promotion_command_plan = _candidate_promotion_command_plan(case)
    command_plan_by_task = {
        str(item.get("task") or ""): item for item in promotion_command_plan if isinstance(item, dict)
    }
    tasks: list[dict[str, Any]] = []

    for task in PROMOTION_TASKS:
        task_evidence = evidence.get(task)
        task_evidence = task_evidence if isinstance(task_evidence, dict) else {}
        status = str(task_evidence.get("status") or "pending")
        evidence_value = task_evidence.get("evidence")
        next_action = str(task_evidence.get("next_action") or "")
        acceptance_criteria = PROMOTION_ACCEPTANCE_CRITERIA[task]
        command_plan_item = command_plan_by_task.get(task, {})
        command = str(command_plan_item.get("command") or "")
        command_source = str(command_plan_item.get("source") or "")
        command_missing = bool(command_plan_item.get("missing", not command))
        handoff = _candidate_task_handoff(
            task=task,
            command=command,
            command_missing=command_missing,
            next_action=next_action,
        )
        runbook = _candidate_task_runbook(
            task=task,
            command=command,
            command_missing=command_missing,
            handoff=handoff,
            acceptance_criteria=acceptance_criteria,
        )
        tasks.append(
            {
                "task": task,
                "status": status,
                "description": promotion.get(task) or "",
                "evidence": evidence_value,
                "next_action": next_action,
                "acceptance_criteria": acceptance_criteria,
                "command": command,
                "command_source": command_source,
                "command_missing": command_missing,
                "handoff": handoff,
                "runbook": runbook,
                "complete": status == "complete" and bool(evidence_value),
            }
        )

    status_counts = Counter(str(task["status"]) for task in tasks)
    complete_tasks = [task for task in tasks if task["complete"]]
    pending_tasks = [task for task in tasks if task["status"] == "pending" and not task["complete"]]
    blocked_tasks = [task for task in tasks if task["status"] == "blocked" and not task["complete"]]
    incomplete_tasks = [task for task in tasks if not task["complete"]]
    primary_pending_task = pending_tasks[0] if pending_tasks else None
    primary_blocked_task = blocked_tasks[0] if blocked_tasks else None
    primary_incomplete_task = incomplete_tasks[0] if incomplete_tasks else None
    primary_next_action_task = primary_pending_task or primary_blocked_task or primary_incomplete_task or {}
    primary_next_task = dict(primary_next_action_task) if primary_next_action_task else None
    primary_runbook = primary_next_action_task.get("runbook", [])
    primary_runbook_first_step = _runbook_first_step(primary_runbook)
    primary_runbook_first_command = str(primary_runbook_first_step.get("command") or "")
    return {
        "case_id": case_id,
        "title": case.get("title"),
        "status": case.get("status"),
        "target_url": case.get("target_url"),
        "adapter_domain": adapter_domain,
        "docs": case.get("docs"),
        "example_output": case.get("example_output"),
        "commands": case.get("commands") if isinstance(case.get("commands"), list) else [],
        "offline_commands": _offline_commands(case),
        "llm_live_preflight_command": LLM_LIVE_PREFLIGHT_COMMAND,
        "llm_live_preflight_blocker_note": LLM_LIVE_PREFLIGHT_BLOCKER_NOTE,
        "llm_live_preflight_evidence_fields": list(LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS),
        "candidate_package_validation_command": CANDIDATE_PACKAGE_VALIDATION_COMMAND
        if adapter_domain
        else "",
        "promotion_command_plan": promotion_command_plan,
        "promotion_command_plan_count": len(promotion_command_plan),
        "promotion_command_plan_missing_tasks": [
            item["task"] for item in promotion_command_plan if item["missing"]
        ],
        "acceptance_criteria": {
            task: PROMOTION_ACCEPTANCE_CRITERIA[task] for task in PROMOTION_TASKS
        },
        "tasks": tasks,
        "status_counts": {
            "pending": status_counts.get("pending", 0),
            "blocked": status_counts.get("blocked", 0),
            "complete": status_counts.get("complete", 0),
        },
        "pending_tasks": [task["task"] for task in pending_tasks],
        "blocked_tasks": [task["task"] for task in blocked_tasks],
        "complete_tasks": [task["task"] for task in complete_tasks],
        "incomplete_tasks": [task["task"] for task in incomplete_tasks],
        "primary_pending_task": primary_pending_task,
        "primary_blocked_task": primary_blocked_task,
        "primary_incomplete_task": primary_incomplete_task,
        "primary_next_task": primary_next_task,
        "primary_next_task_command": primary_next_action_task.get("command", ""),
        "primary_next_task_command_source": primary_next_action_task.get("command_source", ""),
        "primary_next_task_command_missing": bool(primary_next_action_task.get("command_missing", False)),
        "primary_next_task_handoff": primary_next_action_task.get("handoff", ""),
        "primary_next_task_runbook": primary_runbook,
        "primary_next_task_runbook_first_step": str(
            primary_runbook_first_step.get("step") or ""
        ),
        "primary_next_task_runbook_first_command": primary_runbook_first_command,
        "primary_next_task_runbook_first_command_sha256": _sha256_text(
            primary_runbook_first_command
        ),
        "primary_next_task_acceptance_criteria": primary_next_action_task.get(
            "acceptance_criteria", ""
        ),
        "task_handoffs": [
            {
                "task": task["task"],
                "status": task["status"],
                "command": task["command"],
                "command_source": task["command_source"],
                "command_missing": task["command_missing"],
                "acceptance_criteria": task["acceptance_criteria"],
                "complete": task["complete"],
                "handoff": task["handoff"],
            }
            for task in tasks
        ],
        "complete_task_count": len(complete_tasks),
        "pending_task_count": len(pending_tasks),
        "blocked_task_count": len(blocked_tasks),
        "incomplete_task_count": len(incomplete_tasks),
        "ready_to_promote": not incomplete_tasks,
        "primary_next_action": primary_next_action_task.get("next_action", ""),
    }


def _candidate_evidence_bundle_markdown(bundle: dict[str, Any]) -> str:
    lines = [
        f"## Evidence bundle: `{bundle['case_id']}`",
        "",
        f"- Status: `{bundle['status']}`",
        f"- Target URL: {bundle['target_url']}",
        f"- Adapter domain: `{bundle['adapter_domain']}`",
        f"- Docs: {bundle['docs']}",
        f"- Example output: {bundle['example_output']}",
        f"- Ready to promote: `{str(bundle['ready_to_promote']).lower()}`",
        f"- Pending tasks: `{bundle['pending_task_count']}`",
        f"- Blocked tasks: `{bundle.get('blocked_task_count', 0)}`",
        f"- Complete tasks: `{bundle['complete_task_count']}`",
        f"- Incomplete tasks: `{bundle.get('incomplete_task_count', bundle['pending_task_count'])}`",
    ]
    primary_next_task = bundle.get("primary_next_task")
    if isinstance(primary_next_task, dict) and primary_next_task.get("task"):
        lines.append(f"- Primary next task: `{primary_next_task['task']}`")
        if primary_next_task.get("command"):
            lines.append(f"- Primary next command: `{primary_next_task['command']}`")
        if primary_next_task.get("handoff"):
            lines.append(f"- Primary next handoff: {primary_next_task['handoff']}")
        if primary_next_task.get("acceptance_criteria"):
            lines.append(
                f"- Primary next acceptance: {primary_next_task['acceptance_criteria']}"
            )
    primary_runbook = bundle.get("primary_next_task_runbook")
    if isinstance(primary_runbook, list) and primary_runbook:
        first_step = bundle.get("primary_next_task_runbook_first_step") or "-"
        first_command = bundle.get("primary_next_task_runbook_first_command") or "No command."
        lines.append(f"- Primary runbook first command: `{first_step}` -> `{first_command}`")
        lines.extend(["", "## Primary next runbook"])
        for step in primary_runbook:
            if not isinstance(step, dict):
                continue
            command = step.get("command") or "No command."
            lines.append(f"- `{step.get('step')}`: `{command}`")
            if step.get("handoff"):
                lines.append(f"  - handoff: {step['handoff']}")
    primary_incomplete_task = bundle.get("primary_incomplete_task")
    if isinstance(primary_incomplete_task, dict) and primary_incomplete_task.get("task"):
        lines.append(f"- Primary incomplete task: `{primary_incomplete_task['task']}`")
    blocked_tasks = bundle.get("blocked_tasks")
    if blocked_tasks:
        lines.append(f"- Blocked task names: {', '.join(f'`{task}`' for task in blocked_tasks)}")
    if bundle.get("primary_next_action"):
        lines.append(f"- Primary next action: {bundle['primary_next_action']}")

    lines.extend(["", "## Commands"])
    lines.extend(f"- `{command}`" for command in bundle.get("commands", []))
    lines.extend(["", "## Offline validation"])
    lines.extend(f"- `{command}`" for command in bundle.get("offline_commands", []))
    if bundle.get("llm_live_preflight_command"):
        lines.extend(
            [
                "",
                "## LLM live preflight",
                f"- `{bundle['llm_live_preflight_command']}`",
            ]
        )
        evidence_fields = bundle.get("llm_live_preflight_evidence_fields")
        if isinstance(evidence_fields, list) and evidence_fields:
            joined_fields = ", ".join(f"`{field}`" for field in evidence_fields)
            lines.append(f"- Evidence fields: {joined_fields}")
        if bundle.get("llm_live_preflight_blocker_note"):
            lines.append(f"- Blocker handling: {bundle['llm_live_preflight_blocker_note']}")
    if bundle.get("candidate_package_validation_command"):
        lines.extend(
            [
                "",
                "## Candidate package validation",
                f"- `{bundle['candidate_package_validation_command']}`",
            ]
        )
    lines.extend(["", "## Promotion command plan"])
    for item in bundle.get("promotion_command_plan", []):
        command = item.get("command") or "Not declared."
        lines.append(f"- `{item['task']}` ({item['source']}): `{command}`")
    lines.extend(["", "## Acceptance criteria"])
    for task, criteria in bundle.get("acceptance_criteria", {}).items():
        lines.append(f"- `{task}`: {criteria}")
    lines.extend(["", "## Promotion evidence"])

    for task in bundle.get("tasks", []):
        evidence_value = task.get("evidence") or "Not attached yet."
        next_action = task.get("next_action") or "No next action declared."
        command = task.get("command") or "Not declared."
        handoff = task.get("handoff") or "No handoff declared."
        lines.extend(
            [
                f"- `{task['task']}`: `{task['status']}`",
                f"  - complete: `{str(task['complete']).lower()}`",
                f"  - command: `{command}`",
                f"  - command_missing: `{str(task.get('command_missing', False)).lower()}`",
                f"  - evidence: {evidence_value}",
                f"  - next: {next_action}",
                f"  - acceptance: {task.get('acceptance_criteria')}",
                f"  - handoff: {handoff}",
            ]
        )

    return "\n".join(lines)


def _candidate_promotion_plan(cases: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_bundles = [
        _candidate_evidence_bundle(case)
        for case in cases
        if case.get("status") == "candidate"
    ]
    ranked_bundles = [
        bundle
        for _, bundle in sorted(
            enumerate(candidate_bundles),
            key=lambda item: _candidate_bundle_priority_key(item[1], item[0]),
        )
    ]
    candidates: list[dict[str, Any]] = []
    task_queue: list[dict[str, Any]] = []

    for priority_rank, bundle in enumerate(ranked_bundles, start=1):
        primary_next_task = bundle.get("primary_next_task")
        primary_next_task = primary_next_task if isinstance(primary_next_task, dict) else {}
        case_id = str(bundle.get("case_id") or "")
        evidence_bundle_command = f"cliany-site cases --case-id {case_id} --evidence-bundle"
        evidence_bundle_json_command = f"{evidence_bundle_command} --json"
        llm_live_preflight_command = str(bundle.get("llm_live_preflight_command") or "")
        llm_live_preflight_blocker_note = str(
            bundle.get("llm_live_preflight_blocker_note") or ""
        )
        priority_reason = _candidate_bundle_priority_reason(bundle, priority_rank)
        candidate_item = {
            "case_id": case_id,
            "title": bundle.get("title"),
            "status": bundle.get("status"),
            "target_url": bundle.get("target_url"),
            "adapter_domain": bundle.get("adapter_domain"),
            "ready_to_promote": bundle.get("ready_to_promote"),
            "pending_task_count": bundle.get("pending_task_count"),
            "blocked_task_count": bundle.get("blocked_task_count"),
            "complete_task_count": bundle.get("complete_task_count"),
            "incomplete_task_count": bundle.get("incomplete_task_count"),
            "primary_task": primary_next_task.get("task", ""),
            "primary_status": primary_next_task.get("status", ""),
            "primary_command": bundle.get("primary_next_task_command", ""),
            "primary_command_missing": bundle.get("primary_next_task_command_missing", False),
            "primary_handoff": bundle.get("primary_next_task_handoff", ""),
            "primary_runbook": bundle.get("primary_next_task_runbook", []),
            "primary_acceptance_criteria": bundle.get(
                "primary_next_task_acceptance_criteria", ""
            ),
            "promotion_command_plan_missing_tasks": bundle.get(
                "promotion_command_plan_missing_tasks", []
            ),
            "evidence_bundle_command": evidence_bundle_command,
            "evidence_bundle_json_command": evidence_bundle_json_command,
            "llm_live_preflight_command": llm_live_preflight_command,
            "llm_live_preflight_blocker_note": llm_live_preflight_blocker_note,
            "priority_rank": priority_rank,
            "priority_reason": priority_reason,
        }
        candidates.append(candidate_item)

        for task in bundle.get("tasks", []):
            if task.get("complete"):
                continue
            task_queue.append(
                {
                    "case_id": case_id,
                    "task": task.get("task", ""),
                    "status": task.get("status", ""),
                    "command": task.get("command", ""),
                    "command_source": task.get("command_source", ""),
                    "command_missing": task.get("command_missing", False),
                    "handoff": task.get("handoff", ""),
                    "acceptance_criteria": task.get("acceptance_criteria", ""),
                    "runbook": task.get("runbook", []),
                    "evidence_bundle_command": evidence_bundle_command,
                    "evidence_bundle_json_command": evidence_bundle_json_command,
                    "llm_live_preflight_command": llm_live_preflight_command,
                    "llm_live_preflight_blocker_note": llm_live_preflight_blocker_note,
                    "priority_rank": priority_rank,
                    "priority_reason": priority_reason,
                }
            )

    primary_next_item = task_queue[0] if task_queue else {}
    return {
        "candidate_count": len(candidates),
        "ready_to_promote_count": sum(1 for item in candidates if item["ready_to_promote"]),
        "pending_task_count": sum(int(item.get("pending_task_count") or 0) for item in candidates),
        "blocked_task_count": sum(int(item.get("blocked_task_count") or 0) for item in candidates),
        "complete_task_count": sum(int(item.get("complete_task_count") or 0) for item in candidates),
        "incomplete_task_count": len(task_queue),
        "primary_next_item": primary_next_item,
        "primary_case_id": primary_next_item.get("case_id", ""),
        "primary_task": primary_next_item.get("task", ""),
        "primary_command": primary_next_item.get("command", ""),
        "primary_handoff": primary_next_item.get("handoff", ""),
        "primary_acceptance_criteria": primary_next_item.get("acceptance_criteria", ""),
        "primary_runbook": primary_next_item.get("runbook", []),
        "primary_llm_live_preflight_command": primary_next_item.get(
            "llm_live_preflight_command", ""
        ),
        "primary_llm_live_preflight_blocker_note": primary_next_item.get(
            "llm_live_preflight_blocker_note", ""
        ),
        "llm_live_preflight_command": LLM_LIVE_PREFLIGHT_COMMAND,
        "llm_live_preflight_blocker_note": LLM_LIVE_PREFLIGHT_BLOCKER_NOTE,
        "candidates": candidates,
        "task_queue": task_queue,
    }


def _candidate_bundle_priority_key(bundle: dict[str, Any], index: int) -> tuple[int, int, int, int, int, int, int]:
    pending_count = int(bundle.get("pending_task_count") or 0)
    blocked_count = int(bundle.get("blocked_task_count") or 0)
    complete_count = int(bundle.get("complete_task_count") or 0)
    missing_command_count = len(bundle.get("promotion_command_plan_missing_tasks") or [])
    ready_to_promote = bool(bundle.get("ready_to_promote"))
    has_pending_work = pending_count > 0
    return (
        0 if ready_to_promote else 1,
        0 if has_pending_work else 1,
        -complete_count,
        blocked_count,
        missing_command_count,
        pending_count,
        index,
    )


def _candidate_bundle_priority_reason(bundle: dict[str, Any], rank: int) -> str:
    complete_count = int(bundle.get("complete_task_count") or 0)
    pending_count = int(bundle.get("pending_task_count") or 0)
    blocked_count = int(bundle.get("blocked_task_count") or 0)
    missing_command_count = len(bundle.get("promotion_command_plan_missing_tasks") or [])
    return (
        f"rank {rank}: complete {complete_count}/{len(PROMOTION_TASKS)}, "
        f"pending {pending_count}, blocked {blocked_count}, "
        f"missing commands {missing_command_count}"
    )


def _candidate_promotion_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "## Candidate promotion plan",
        "",
        f"- Candidate cases: `{plan['candidate_count']}`",
        f"- Ready to promote: `{plan['ready_to_promote_count']}`",
        f"- Pending tasks: `{plan['pending_task_count']}`",
        f"- Blocked tasks: `{plan['blocked_task_count']}`",
        f"- Complete tasks: `{plan['complete_task_count']}`",
        f"- Incomplete tasks: `{plan['incomplete_task_count']}`",
        f"- LLM live preflight: `{plan['llm_live_preflight_command']}`",
        f"- LLM blocker handling: {plan['llm_live_preflight_blocker_note']}",
    ]
    primary_next_item = plan.get("primary_next_item")
    if isinstance(primary_next_item, dict) and primary_next_item.get("case_id"):
        lines.extend(
            [
                "",
                "## Primary next item",
                f"- Case: `{primary_next_item['case_id']}`",
                f"- Task: `{primary_next_item['task']}`",
                f"- Status: `{primary_next_item['status']}`",
                f"- Priority: `{primary_next_item.get('priority_rank')}`",
                f"- Priority reason: {primary_next_item.get('priority_reason')}",
                f"- Command: `{primary_next_item.get('command') or 'Not declared.'}`",
                f"- Handoff: {primary_next_item.get('handoff') or 'No handoff declared.'}",
                (
                    "- Acceptance criteria: "
                    f"{primary_next_item.get('acceptance_criteria') or 'Not declared.'}"
                ),
                (
                    "- Evidence bundle JSON: "
                    f"`{primary_next_item['evidence_bundle_json_command']}`"
                ),
                (
                    "- LLM blocker handling: "
                    f"{primary_next_item.get('llm_live_preflight_blocker_note')}"
                ),
            ]
        )
        runbook = primary_next_item.get("runbook")
        if isinstance(runbook, list) and runbook:
            lines.extend(["", "## Primary runbook"])
            for step in runbook:
                if not isinstance(step, dict):
                    continue
                command = step.get("command") or "No command."
                lines.append(f"- `{step.get('step')}`: `{command}`")
                if step.get("handoff"):
                    lines.append(f"  - handoff: {step['handoff']}")
    elif not plan.get("candidate_count"):
        lines.extend(["", "No candidate cases matched the current filters."])
    else:
        lines.extend(["", "All matched candidate tasks are complete."])

    lines.extend(["", "## Candidate queue"])
    for candidate in plan.get("candidates", []):
        command = candidate.get("primary_command") or "Not declared."
        lines.extend(
            [
                f"- `{candidate['case_id']}`",
                f"  - target: {candidate.get('target_url')}",
                f"  - priority: `{candidate.get('priority_rank')}`",
                f"  - priority_reason: {candidate.get('priority_reason')}",
                f"  - ready_to_promote: `{str(candidate.get('ready_to_promote')).lower()}`",
                (
                    f"  - primary: `{candidate.get('primary_task') or '-'}` "
                    f"({candidate.get('primary_status') or '-'})"
                ),
                f"  - command: `{command}`",
                f"  - handoff: {candidate.get('primary_handoff') or 'No handoff declared.'}",
                (
                    "  - acceptance: "
                    f"{candidate.get('primary_acceptance_criteria') or 'Not declared.'}"
                ),
                (
                    "  - llm_blocker: "
                    f"{candidate.get('llm_live_preflight_blocker_note') or 'Not declared.'}"
                ),
                f"  - evidence_bundle_json: `{candidate['evidence_bundle_json_command']}`",
            ]
        )

    lines.extend(["", "## Incomplete task queue"])
    for item in plan.get("task_queue", []):
        command = item.get("command") or "Not declared."
        lines.extend(
            [
                f"- `{item['case_id']}/{item['task']}` ({item['status']})",
                f"  - priority: `{item.get('priority_rank')}`",
                f"  - priority_reason: {item.get('priority_reason')}",
                f"  - command: `{command}`",
                f"  - command_missing: `{str(item.get('command_missing', False)).lower()}`",
                f"  - handoff: {item.get('handoff') or 'No handoff declared.'}",
                f"  - acceptance: {item.get('acceptance_criteria') or 'Not declared.'}",
                (
                    "  - llm_blocker: "
                    f"{item.get('llm_live_preflight_blocker_note') or 'Not declared.'}"
                ),
            ]
        )
    return "\n".join(lines)


def _promotion_evidence_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    task_status_counts: dict[str, Counter[str]] = {task: Counter() for task in PROMOTION_TASKS}
    pending_tasks: list[dict[str, str]] = []
    task_count = 0
    candidate_bundles = [
        _candidate_evidence_bundle(case)
        for case in cases
        if case.get("status") == "candidate"
    ]
    ranked_bundles = [
        bundle
        for _, bundle in sorted(
            enumerate(candidate_bundles),
            key=lambda item: _candidate_bundle_priority_key(item[1], item[0]),
        )
    ]

    for bundle in ranked_bundles:
        evidence_by_task = {
            str(task.get("task") or ""): task
            for task in bundle.get("tasks", [])
            if isinstance(task, dict)
        }
        case_id = str(bundle.get("case_id") or "")
        for task in PROMOTION_TASKS:
            task_evidence = evidence_by_task.get(task)
            if not task_evidence:
                continue
            status = str(task_evidence.get("status") or "pending")
            evidence_value = str(task_evidence.get("evidence") or "")
            next_action = str(task_evidence.get("next_action") or "")
            acceptance_criteria = PROMOTION_ACCEPTANCE_CRITERIA[task]
            status_counts[status] += 1
            task_status_counts[task][status] += 1
            task_count += 1
            if status in {"pending", "blocked"}:
                pending_tasks.append(
                    {
                        "case_id": case_id,
                        "task": task,
                        "status": status,
                        "evidence": evidence_value,
                        "next_action": next_action,
                        "acceptance_criteria": acceptance_criteria,
                    }
                )

    primary = pending_tasks[0] if pending_tasks else {}
    primary_runbook: list[dict[str, Any]] = []
    primary_case_id = primary.get("case_id", "")
    primary_task = primary.get("task", "")
    if primary_case_id and primary_task:
        for bundle in ranked_bundles:
            if bundle.get("case_id") != primary_case_id:
                continue
            task = bundle.get("primary_next_task")
            if not isinstance(task, dict) or task.get("task") != primary_task:
                continue
            runbook = bundle.get("primary_next_task_runbook")
            if isinstance(runbook, list):
                primary_runbook = [step for step in runbook if isinstance(step, dict)]
            break
    primary_runbook_first_step = _runbook_first_step(primary_runbook)
    primary_runbook_first_command = str(primary_runbook_first_step.get("command") or "")
    return {
        "candidate_count": sum(1 for case in cases if case.get("status") == "candidate"),
        "task_count": task_count,
        "status_counts": {
            "pending": status_counts.get("pending", 0),
            "blocked": status_counts.get("blocked", 0),
            "complete": status_counts.get("complete", 0),
        },
        "task_status_counts": {
            task: {
                "pending": counts.get("pending", 0),
                "blocked": counts.get("blocked", 0),
                "complete": counts.get("complete", 0),
            }
            for task, counts in task_status_counts.items()
        },
        "pending_count": status_counts.get("pending", 0),
        "blocked_count": status_counts.get("blocked", 0),
        "complete_count": status_counts.get("complete", 0),
        "primary_task_detail": primary,
        "primary_next_task": primary,
        "primary_case_id": primary.get("case_id", ""),
        "primary_task": primary.get("task", ""),
        "primary_next_action": primary.get("next_action", ""),
        "primary_next_task_runbook_first_step": str(
            primary_runbook_first_step.get("step") or ""
        ),
        "primary_next_task_runbook_first_command": primary_runbook_first_command,
        "primary_next_task_runbook_first_command_sha256": _sha256_text(
            primary_runbook_first_command
        ),
        "primary_next_task_acceptance_criteria": primary.get("acceptance_criteria", ""),
    }


def _summary(cases: list[dict[str, Any]], *, catalog_total: int) -> dict[str, Any]:
    statuses = Counter(str(case.get("status") or "unknown") for case in cases)
    categories = Counter(str(case.get("category") or "unknown") for case in cases)
    return {
        "total": len(cases),
        "catalog_total": catalog_total,
        "status_counts": {status: statuses.get(status, 0) for status in ALLOWED_STATUSES},
        "category_counts": dict(sorted(categories.items())),
        "active_count": statuses.get("active", 0),
        "candidate_count": statuses.get("candidate", 0),
        "known_gap_count": statuses.get("known-gap", 0),
    }


def _print_single_case_detail(console: Any, case: dict[str, Any]) -> None:
    console.print("\n[bold]案例详情[/bold]")
    for label, key in (
        ("ID", "id"),
        ("Title", "title"),
        ("Status", "status"),
        ("Category", "category"),
        ("Target", "target_url"),
        ("Adapter", "adapter_domain"),
        ("Docs", "docs"),
        ("Example", "example_output"),
    ):
        value = case.get(key)
        if value:
            console.print(f"- {label}: {value}")

    validation = case.get("validation")
    if isinstance(validation, dict):
        console.print("\n[bold]Validation[/bold]")
        for key in ("offline", "online"):
            value = validation.get(key)
            if value:
                console.print(f"- {key}: {value}")

    evidence = case.get("promotion_evidence")
    if isinstance(evidence, dict):
        console.print("\n[bold]Promotion Tasks[/bold]")
        for task in PROMOTION_TASKS:
            task_evidence = evidence.get(task)
            if not isinstance(task_evidence, dict):
                continue
            status = task_evidence.get("status") or "unknown"
            evidence_value = task_evidence.get("evidence") or "Not attached yet."
            next_action = task_evidence.get("next_action") or "No next action declared."
            console.print(f"- {task}: {status}")
            console.print(f"  evidence: {evidence_value}")
            console.print(f"  next: {next_action}")
            console.print(f"  acceptance: {PROMOTION_ACCEPTANCE_CRITERIA[task]}")


def _print_human_cases(data: dict[str, Any], *, detail: bool) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    cases = data["cases"]
    summary = data["summary"]
    source = data.get("source_path") or "unknown"
    console.print("[bold]cliany-site cases[/bold]")
    case_counts = (
        f"active {summary['active_count']} / "
        f"candidate {summary['candidate_count']} / "
        f"known-gap {summary['known_gap_count']}"
    )
    console.print(f"共 {summary['total']} 个案例（{case_counts}）")
    console.print(f"索引: {source}")

    if not cases:
        console.print("[yellow]没有匹配的案例。[/yellow]")
        return

    if detail and len(cases) == 1:
        _print_single_case_detail(console, cases[0])

    table = Table(title="案例库")
    table.add_column("ID", style="cyan")
    table.add_column("Status")
    table.add_column("Category")
    table.add_column("Adapter")
    table.add_column("First command")
    for case in cases:
        commands = case.get("commands") if isinstance(case.get("commands"), list) else []
        table.add_row(
            str(case.get("id") or ""),
            str(case.get("status") or ""),
            str(case.get("category") or ""),
            str(case.get("adapter_domain") or "-"),
            str(commands[0]) if commands else "-",
        )
    console.print(table)

    console.print("\n[bold]快速命令[/bold]")
    for case in cases:
        commands = case.get("commands") if isinstance(case.get("commands"), list) else []
        if not commands:
            continue
        console.print(f"- {case.get('id')}:")
        command_lines = commands if detail else commands[:1]
        for command in command_lines:
            console.print(f"  {command}")

    promotion = data.get("promotion_evidence_summary")
    if isinstance(promotion, dict) and promotion.get("primary_next_action"):
        primary_task = promotion.get("primary_next_task") or promotion.get("primary_task_detail")
        primary_task = primary_task if isinstance(primary_task, dict) else {}
        primary_case_id = primary_task.get("case_id") or promotion.get("primary_case_id")
        primary_task_name = primary_task.get("task") or promotion.get("primary_task")
        primary_status = primary_task.get("status") or "unknown"
        primary_evidence = primary_task.get("evidence") or "Not attached yet."
        primary_next_action = primary_task.get("next_action") or promotion.get("primary_next_action")
        primary_acceptance = (
            primary_task.get("acceptance_criteria")
            or promotion.get("primary_next_task_acceptance_criteria")
        )
        console.print("\n[bold]Candidate 下一步[/bold]")
        console.print(
            f"- {primary_case_id}/{primary_task_name} ({primary_status}): "
            f"{primary_next_action}"
        )
        console.print(f"  evidence: {primary_evidence}")
        if primary_acceptance:
            console.print(f"  acceptance: {primary_acceptance}")
        first_runbook_command = promotion.get("primary_next_task_runbook_first_command")
        if first_runbook_command:
            first_runbook_step = promotion.get("primary_next_task_runbook_first_step")
            console.print(f"  runbook_first: {first_runbook_step} -> {first_runbook_command}")

    if detail:
        console.print("\n[bold]离线验证命令[/bold]")
        for case in cases:
            offline_commands = case.get("offline_commands")
            if not isinstance(offline_commands, list) or not offline_commands:
                continue
            console.print(f"- {case.get('id')}:")
            for command in offline_commands:
                console.print(f"  {command}")


@click.command("cases")
@click.option("--case-id", default=None, help="只显示指定案例 ID，并自动展开详情")
@click.option("--status", type=click.Choice(ALLOWED_STATUSES), default=None, help="只显示指定状态的案例")
@click.option("--detail", is_flag=True, default=False, help="显示 promotion 和 validation 详情")
@click.option("--issue-template", is_flag=True, default=False, help="为 candidate 案例输出 GitHub issue body")
@click.option("--evidence-bundle", is_flag=True, default=False, help="为 candidate 案例输出本地证据包")
@click.option("--promotion-plan", is_flag=True, default=False, help="输出 candidate 晋级队列和首要证据任务")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
def cases_cmd(
    ctx: click.Context,
    case_id: str | None,
    status: str | None,
    detail: bool,
    issue_template: bool,
    evidence_bundle: bool,
    promotion_plan: bool,
    json_mode: bool | None,
) -> None:
    """列出内置真实案例和候选工作流"""
    root_ctx = ctx.find_root()
    root_obj = root_ctx.obj if isinstance(root_ctx.obj, dict) else {}
    effective_json_mode = json_mode if json_mode is not None else bool(root_obj.get("json_mode", False))
    result: Envelope

    try:
        catalog_cases, source_path, checked_paths = _load_cases_manifest()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = err(
            "cases",
            ErrorCode.E_UNKNOWN,
            f"案例索引读取失败: {exc}",
            hint="请确认 cases/manifest.json 存在且是合法 JSON。",
            details={"checked_paths": [str(path) for path in _case_catalog_paths()]},
        )
        print_response(result, effective_json_mode)
        return

    if source_path is None:
        result = err(
            "cases",
            ErrorCode.E_UNKNOWN,
            "未找到案例索引 cases/manifest.json",
            hint="源码仓库请确认 cases/manifest.json 存在；安装包请重新安装包含案例资源的版本。",
            details={"checked_paths": [str(path) for path in checked_paths]},
        )
        print_response(result, effective_json_mode)
        return

    filtered_cases = [case for case in catalog_cases if status is None or case.get("status") == status]
    if sum(1 for flag in (issue_template, evidence_bundle, promotion_plan) if flag) > 1:
        result = err(
            "cases",
            ErrorCode.E_INVALID_PARAM,
            "--issue-template、--evidence-bundle 与 --promotion-plan 不能同时使用",
            hint="三选一：生成 issue body、生成 evidence bundle，或输出 candidate promotion plan。",
            details={"case_id": case_id, "status_filter": status},
        )
        print_response(result, effective_json_mode)
        return

    if (issue_template or evidence_bundle) and not case_id:
        result = err(
            "cases",
            ErrorCode.E_INVALID_PARAM,
            "--issue-template / --evidence-bundle 必须配合 --case-id 使用",
            hint="例如：cliany-site cases --case-id pypi-project-search --evidence-bundle",
            details={
                "status_filter": status,
                "available_case_ids": _case_ids(filtered_cases),
            },
        )
        print_response(result, effective_json_mode)
        return

    if case_id:
        exact_matches = [case for case in filtered_cases if case.get("id") == case_id]
        if not exact_matches:
            result = err(
                "cases",
                ErrorCode.E_INVALID_PARAM,
                f"未找到案例: {case_id}",
                hint="运行 cliany-site cases --json 查看可用案例，或检查 --status 筛选条件。",
                details={
                    "case_id": case_id,
                    "status_filter": status,
                    "available_case_ids": _case_ids(filtered_cases),
                },
            )
            print_response(result, effective_json_mode)
            return
        filtered_cases = exact_matches

    include_detail = detail or bool(case_id)
    rendered_issue_template = ""
    rendered_issue_template_primary_task: dict[str, Any] = {}
    rendered_evidence_bundle: dict[str, Any] = {}
    rendered_promotion_plan: dict[str, Any] = {}
    if issue_template or evidence_bundle:
        selected_case = filtered_cases[0]
        if selected_case.get("status") != "candidate":
            result = err(
                "cases",
                ErrorCode.E_INVALID_PARAM,
                f"案例 {case_id} 不是 candidate，不能生成 promotion 输出",
                hint=(
                    "仅 candidate 案例需要 promotion 输出；"
                    "运行 cliany-site cases --status candidate --json 查看候选项。"
                ),
                details={
                    "case_id": case_id,
                    "status": selected_case.get("status"),
                },
            )
            print_response(result, effective_json_mode)
            return
        if issue_template:
            rendered_issue_template = _candidate_issue_template(selected_case)
            raw_evidence = selected_case.get("promotion_evidence")
            evidence: dict[str, Any] = raw_evidence if isinstance(raw_evidence, dict) else {}
            rendered_issue_template_primary_task = _candidate_issue_primary_task(evidence)
        if evidence_bundle:
            rendered_evidence_bundle = _candidate_evidence_bundle(selected_case)
    if promotion_plan:
        rendered_promotion_plan = _candidate_promotion_plan(filtered_cases)

    data = {
        "source_path": str(source_path),
        "case_id": case_id,
        "status_filter": status,
        "summary": _summary(filtered_cases, catalog_total=len(catalog_cases)),
        "promotion_evidence_summary": _promotion_evidence_summary(filtered_cases),
        "cases": [_compact_case(case, detail=include_detail) for case in filtered_cases],
    }
    if rendered_issue_template:
        data["issue_template"] = rendered_issue_template
        data["issue_template_primary_task"] = rendered_issue_template_primary_task
    if rendered_evidence_bundle:
        data["evidence_bundle"] = rendered_evidence_bundle
    if rendered_promotion_plan:
        data["promotion_plan"] = rendered_promotion_plan
    result = ok(command="cases", data=data, source="builtin")

    if effective_json_mode:
        print_response(result, effective_json_mode)
        return
    if rendered_issue_template:
        click.echo(rendered_issue_template)
        return
    if rendered_evidence_bundle:
        click.echo(_candidate_evidence_bundle_markdown(rendered_evidence_bundle))
        return
    if rendered_promotion_plan:
        click.echo(_candidate_promotion_plan_markdown(rendered_promotion_plan))
        return
    _print_human_cases(data, detail=include_detail)
