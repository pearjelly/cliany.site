#!/usr/bin/env python3
"""Plan the next small cliany-site release slice from local project evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import sys
import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
ARTIFACT_MANIFEST_SCHEMA_VERSION = 1
CANDIDATE_PROMOTION_FIELDS = ("adapter_package", "metadata_validation", "online_smoke")
CANDIDATE_PROMOTION_COMMAND_PLAN_FIELDS = (
    "llm_live_preflight",
    "adapter_package",
    "metadata_validation",
    "online_smoke",
)
CANDIDATE_PACKAGE_VALIDATION_COMMAND = (
    "python scripts/validate_cases.py "
    "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict"
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
    "checks[llm_live].details.retryable",
    "checks[llm_live].details.status_code",
    "checks[llm_live].details.phase",
    "checks[llm_live].details.message",
)
WEBSITE_DEPLOY_COMMAND = "cd site && vercel link --yes --project cliany.site && vercel --prod --yes"
CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA = {
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
ARTIFACT_MANIFEST_KEYS = (
    "schema_version",
    "target_version",
    "artifact_bundle_summary",
    "candidate_count",
    "candidate_cases",
    "case_promotion_evidence_summary",
    "case_promotion_command_plan_summary",
    "standard_release_flow",
    "standard_release_flow_status",
    "standard_release_flow_primary_next_action",
    "standard_release_flow_command_count",
    "standard_release_flow_commands_sha256",
    "standard_release_flow_step_count",
    "standard_release_flow_step_names",
    "standard_release_flow_step_names_sha256",
    "standard_release_flow_steps_sha256",
    "standard_release_flow_first_step_name",
    "standard_release_flow_last_step_name",
    "standard_release_flow_step_boundary_sha256",
    "standard_release_flow_step_status_counts",
    "standard_release_flow_step_status_counts_sha256",
    "standard_release_flow_primary_blocked_step_name",
    "standard_release_flow_primary_pending_step_name",
    "standard_release_flow_has_website_deploy",
    "standard_release_flow_website_deploy_command",
    "standard_release_flow_website_deploy_command_sha256",
    "standard_release_flow_sha256",
    "blockers",
    "next_actions",
    "next_action_count",
    "next_actions_sha256",
    "primary_next_action",
    "commit_cadence",
    "candidate_issue_gate",
    "publication_ok",
    "publication_visibility",
    "publication_tag_publish_decision",
    "publication_blocker_count",
    "publication_blockers_sha256",
    "publication_primary_blocker",
    "publication_blockers",
    "publication_next_actions",
    "publication_publish_commands",
    "publication_ref_context",
    "publication_worktree_clean",
    "publication_worktree_status",
    "publication_publish_script_path",
    "publication_publish_script_path_sha256",
    "publication_publish_script_command",
    "publication_publish_script_command_sha256",
    "release_draft_path",
    "release_draft_issues",
    "issue_artifacts_command",
    "plan_report_command",
    "create_issues_dry_run_command",
    "create_issues_safety",
    "issue_body_inventory",
    "issue_body_summary",
    "issue_metadata_summary",
    "files",
    "review_order",
    "review_checklist",
    "validation_commands",
)
ARTIFACT_BUNDLE_SUMMARY_KEYS = (
    "artifact_bundle_summary_key_count",
    "artifact_bundle_summary_keys_sha256",
    "artifact_bundle_summary_key_preview_count",
    "artifact_bundle_summary_key_preview",
    "artifact_bundle_summary_key_preview_sha256",
    "artifact_bundle_summary_key_tail_count",
    "artifact_bundle_summary_key_tail",
    "artifact_bundle_summary_key_tail_sha256",
    "artifact_bundle_summary_first_key",
    "artifact_bundle_summary_last_key",
    "artifact_bundle_summary_key_boundary_sha256",
    "artifact_manifest_schema_version",
    "artifact_manifest_key_count",
    "artifact_manifest_keys_sha256",
    "artifact_manifest_first_key",
    "artifact_manifest_last_key",
    "artifact_manifest_key_boundary_sha256",
    "artifact_manifest_key_preview_count",
    "artifact_manifest_key_preview",
    "artifact_manifest_key_preview_sha256",
    "artifact_manifest_key_tail_count",
    "artifact_manifest_key_tail",
    "artifact_manifest_key_tail_sha256",
    "artifact_manifest_payload_key_count",
    "artifact_manifest_payload_first_key",
    "artifact_manifest_payload_last_key",
    "artifact_manifest_payload_key_boundary_sha256",
    "artifact_manifest_payload_key_preview_count",
    "artifact_manifest_payload_key_preview",
    "artifact_manifest_payload_key_preview_sha256",
    "artifact_manifest_payload_key_tail_count",
    "artifact_manifest_payload_key_tail",
    "artifact_manifest_payload_key_tail_sha256",
    "artifact_manifest_payload_sha256",
    "target_version",
    "candidate_count",
    "candidate_cases_first_case",
    "candidate_cases_last_case",
    "candidate_cases_boundary_sha256",
    "candidate_cases_preview_count",
    "candidate_cases_preview",
    "candidate_cases_preview_sha256",
    "candidate_cases_tail_count",
    "candidate_cases_tail",
    "candidate_cases_tail_sha256",
    "candidate_cases_sha256",
    "case_promotion_evidence_summary_key_count",
    "case_promotion_evidence_summary_keys_sha256",
    "case_promotion_evidence_summary_first_key",
    "case_promotion_evidence_summary_last_key",
    "case_promotion_evidence_summary_key_boundary_sha256",
    "case_promotion_evidence_summary_key_preview_count",
    "case_promotion_evidence_summary_key_preview",
    "case_promotion_evidence_summary_key_preview_sha256",
    "case_promotion_evidence_summary_key_tail_count",
    "case_promotion_evidence_summary_key_tail",
    "case_promotion_evidence_summary_key_tail_sha256",
    "case_promotion_evidence_summary_sha256",
    "case_promotion_evidence_candidate_count",
    "case_promotion_evidence_task_count",
    "case_promotion_evidence_pending_count",
    "case_promotion_evidence_blocked_count",
    "case_promotion_evidence_complete_count",
    "case_promotion_evidence_primary_next_action",
    "case_promotion_evidence_primary_case_id",
    "case_promotion_evidence_primary_task",
    "case_promotion_evidence_primary_status",
    "case_promotion_evidence_primary_evidence_sha256",
    "case_promotion_evidence_primary_detail_sha256",
    "case_promotion_evidence_primary_next_task_sha256",
    "case_promotion_evidence_primary_runbook_step_count",
    "case_promotion_evidence_primary_runbook_steps",
    "case_promotion_evidence_primary_runbook_steps_sha256",
    "case_promotion_evidence_primary_runbook_first_step",
    "case_promotion_evidence_primary_runbook_first_command",
    "case_promotion_evidence_primary_runbook_first_command_sha256",
    "case_promotion_evidence_primary_runbook_sha256",
    "case_promotion_command_plan_summary_sha256",
    "case_promotion_command_plan_candidate_count",
    "case_promotion_command_plan_command_count",
    "case_promotion_command_plan_missing_command_count",
    "case_promotion_command_plan_all_declared",
    "standard_release_flow_status",
    "standard_release_flow_target_tag",
    "standard_release_flow_primary_next_action",
    "standard_release_flow_command_count",
    "standard_release_flow_commands_sha256",
    "standard_release_flow_step_count",
    "standard_release_flow_step_names",
    "standard_release_flow_step_names_sha256",
    "standard_release_flow_steps_sha256",
    "standard_release_flow_first_step_name",
    "standard_release_flow_last_step_name",
    "standard_release_flow_step_boundary_sha256",
    "standard_release_flow_step_status_counts",
    "standard_release_flow_step_status_counts_sha256",
    "standard_release_flow_primary_blocked_step_name",
    "standard_release_flow_primary_pending_step_name",
    "standard_release_flow_has_website_deploy",
    "standard_release_flow_website_deploy_command",
    "standard_release_flow_website_deploy_command_sha256",
    "standard_release_flow_sha256",
    "body_count",
    "issue_body_inventory_preview_count",
    "issue_body_inventory_preview",
    "issue_body_inventory_preview_sha256",
    "issue_body_inventory_first_entry",
    "issue_body_inventory_last_entry",
    "issue_body_inventory_boundary_sha256",
    "issue_body_inventory_tail_count",
    "issue_body_inventory_tail",
    "issue_body_inventory_tail_sha256",
    "issue_body_summary_key_count",
    "issue_body_summary_keys_sha256",
    "issue_body_summary_first_key",
    "issue_body_summary_last_key",
    "issue_body_summary_key_boundary_sha256",
    "issue_body_summary_key_preview_count",
    "issue_body_summary_key_preview",
    "issue_body_summary_key_preview_sha256",
    "issue_body_summary_key_tail_count",
    "issue_body_summary_key_tail",
    "issue_body_summary_key_tail_sha256",
    "issue_body_summary_sha256",
    "review_item_count",
    "review_order_sha256",
    "review_order_first_item",
    "review_order_last_item",
    "review_order_boundary_sha256",
    "review_order_preview_count",
    "review_order_preview",
    "review_order_preview_sha256",
    "review_order_tail_count",
    "review_order_tail",
    "review_order_tail_sha256",
    "inventory_sha256",
    "issue_metadata_count",
    "issue_metadata_sha256",
    "issue_metadata_first_item",
    "issue_metadata_last_item",
    "issue_metadata_boundary_sha256",
    "issue_metadata_preview_count",
    "issue_metadata_preview",
    "issue_metadata_preview_sha256",
    "issue_metadata_tail_count",
    "issue_metadata_tail",
    "issue_metadata_tail_sha256",
    "artifact_files_key_count",
    "artifact_files_sha256",
    "artifact_files_first_key",
    "artifact_files_last_key",
    "artifact_files_key_boundary_sha256",
    "artifact_files_key_preview_count",
    "artifact_files_key_preview",
    "artifact_files_key_preview_sha256",
    "artifact_files_key_tail_count",
    "artifact_files_key_tail",
    "artifact_files_key_tail_sha256",
    "issue_artifacts_command_sha256",
    "plan_report_command_sha256",
    "publication_visibility_key_count",
    "publication_visibility_sha256",
    "publication_visibility_first_key",
    "publication_visibility_last_key",
    "publication_visibility_key_boundary_sha256",
    "publication_visibility_key_preview_count",
    "publication_visibility_key_preview",
    "publication_visibility_key_preview_sha256",
    "publication_visibility_key_tail_count",
    "publication_visibility_key_tail",
    "publication_visibility_key_tail_sha256",
    "publication_visibility_summary_sha256",
    "publication_tag_publish_decision_key_count",
    "publication_tag_publish_decision_sha256",
    "publication_tag_publish_decision_first_key",
    "publication_tag_publish_decision_last_key",
    "publication_tag_publish_decision_key_boundary_sha256",
    "publication_tag_publish_decision_key_preview_count",
    "publication_tag_publish_decision_key_preview",
    "publication_tag_publish_decision_key_preview_sha256",
    "publication_tag_publish_decision_key_tail_count",
    "publication_tag_publish_decision_key_tail",
    "publication_tag_publish_decision_key_tail_sha256",
    "publication_tag_publish_decision_status",
    "publication_tag_can_push",
    "publication_tag_required_action_sha256",
    "publication_target_tag",
    "publication_target_tag_status",
    "publication_target_tag_primary_command",
    "publication_target_tag_command_count",
    "publication_target_tag_commands_sha256",
    "publication_target_tag_required_action_sha256",
    "publication_target_tag_release_gate_status",
    "publication_target_tag_release_gate_blocker_count",
    "publication_target_tag_release_gate_primary_blocker",
    "publication_target_tag_release_gate_required_action_sha256",
    "publication_target_tag_release_gate_blockers_sha256",
    "publication_blocker_count",
    "publication_blockers_sha256",
    "publication_primary_blocker",
    "blocker_count",
    "blockers_sha256",
    "blocker_first_item",
    "blocker_last_item",
    "blocker_boundary_sha256",
    "blocker_preview_count",
    "blocker_preview",
    "blocker_preview_sha256",
    "blocker_tail_count",
    "blocker_tail",
    "blocker_tail_sha256",
    "next_action_count",
    "next_actions_sha256",
    "next_action_first_item",
    "next_action_last_item",
    "next_action_boundary_sha256",
    "next_action_preview_count",
    "next_action_preview",
    "next_action_preview_sha256",
    "next_action_tail_count",
    "next_action_tail",
    "next_action_tail_sha256",
    "publication_next_action_count",
    "publication_next_actions_sha256",
    "publication_next_action_first_item",
    "publication_next_action_last_item",
    "publication_next_action_boundary_sha256",
    "publication_next_action_preview_count",
    "publication_next_action_preview",
    "publication_next_action_preview_sha256",
    "publication_next_action_tail_count",
    "publication_next_action_tail",
    "publication_next_action_tail_sha256",
    "publication_primary_next_action",
    "publication_handoff_key_count",
    "publication_handoff_schema_version",
    "publication_handoff_first_key",
    "publication_handoff_last_key",
    "publication_handoff_key_boundary_sha256",
    "publication_handoff_key_preview_count",
    "publication_handoff_key_preview",
    "publication_handoff_key_preview_sha256",
    "publication_handoff_key_tail_count",
    "publication_handoff_key_tail",
    "publication_handoff_key_tail_sha256",
    "publication_handoff_sha256",
    "publication_handoff_candidate_issue_gate_primary_reason_code",
    "publication_handoff_candidate_issue_gate_primary_reason_description",
    "publication_handoff_candidate_issue_gate_primary_required_action",
    "commit_cadence_status",
    "commit_cadence_commit_day_count",
    "commit_cadence_min_commit_days",
    "commit_cadence_missing_commit_days",
    "commit_cadence_release_count_today",
    "commit_cadence_max_daily_releases",
    "commit_cadence_daily_release_limit_ok",
    "commit_cadence_next_action_count",
    "commit_cadence_primary_next_action",
    "commit_cadence_commit_days_sha256",
    "commit_cadence_release_tags_today_sha256",
    "commit_cadence_next_actions_sha256",
    "publication_ref_context_key_count",
    "publication_ref_context_sha256",
    "publication_ref_context_first_key",
    "publication_ref_context_last_key",
    "publication_ref_context_key_boundary_sha256",
    "publication_ref_context_key_preview_count",
    "publication_ref_context_key_preview",
    "publication_ref_context_key_preview_sha256",
    "publication_ref_context_key_tail_count",
    "publication_ref_context_key_tail",
    "publication_ref_context_key_tail_sha256",
    "publication_publish_command_count",
    "publication_publish_commands_sha256",
    "publication_publish_first_command",
    "publication_publish_last_command",
    "publication_publish_command_boundary_sha256",
    "publication_primary_publish_command",
    "publication_publish_script_path_sha256",
    "publication_publish_script_command_sha256",
    "publication_worktree_status_count",
    "publication_worktree_status_sha256",
    "publication_worktree_status_first_item",
    "publication_worktree_status_last_item",
    "publication_worktree_status_boundary_sha256",
    "release_draft_handoff_key_count",
    "release_draft_handoff_schema_version",
    "release_draft_handoff_primary_issue",
    "release_draft_handoff_primary_required_action",
    "release_draft_handoff_first_key",
    "release_draft_handoff_last_key",
    "release_draft_handoff_key_boundary_sha256",
    "release_draft_handoff_key_preview_count",
    "release_draft_handoff_key_preview",
    "release_draft_handoff_key_preview_sha256",
    "release_draft_handoff_key_tail_count",
    "release_draft_handoff_key_tail",
    "release_draft_handoff_key_tail_sha256",
    "release_draft_handoff_sha256",
    "release_draft_path",
    "release_draft_path_sha256",
    "release_draft_primary_issue",
    "release_draft_required_action_count",
    "release_draft_required_actions_sha256",
    "release_draft_first_required_action",
    "release_draft_last_required_action",
    "release_draft_required_action_boundary_sha256",
    "release_draft_required_action_preview_count",
    "release_draft_required_action_preview",
    "release_draft_required_action_preview_sha256",
    "release_draft_required_action_tail_count",
    "release_draft_required_action_tail",
    "release_draft_required_action_tail_sha256",
    "release_draft_primary_required_action",
    "release_draft_issues_sha256",
    "release_draft_first_issue",
    "release_draft_last_issue",
    "release_draft_issue_boundary_sha256",
    "release_draft_issue_preview_count",
    "release_draft_issue_preview",
    "release_draft_issue_preview_sha256",
    "release_draft_issue_tail_count",
    "release_draft_issue_tail",
    "release_draft_issue_tail_sha256",
    "validation_command_count",
    "validation_commands_sha256",
    "validation_first_command",
    "validation_last_command",
    "validation_command_boundary_sha256",
    "validation_command_preview_count",
    "validation_command_preview",
    "validation_command_preview_sha256",
    "validation_command_tail_count",
    "validation_command_tail",
    "validation_command_tail_sha256",
    "review_checklist_count",
    "review_checklist_sha256",
    "review_checklist_first_item",
    "review_checklist_last_item",
    "review_checklist_boundary_sha256",
    "review_checklist_preview_count",
    "review_checklist_preview",
    "review_checklist_preview_sha256",
    "review_checklist_tail_count",
    "review_checklist_tail",
    "review_checklist_tail_sha256",
    "create_issues_safety_contract_key_count",
    "create_issues_safety_contract_sha256",
    "create_issues_safety_contract_first_key",
    "create_issues_safety_contract_last_key",
    "create_issues_safety_contract_key_boundary_sha256",
    "create_issues_safety_contract_key_preview_count",
    "create_issues_safety_contract_key_preview",
    "create_issues_safety_contract_key_preview_sha256",
    "create_issues_safety_contract_key_tail_count",
    "create_issues_safety_contract_key_tail",
    "create_issues_safety_contract_key_tail_sha256",
    "publication_ok",
    "publication_visibility_status",
    "publication_branch",
    "publication_upstream",
    "publication_remote",
    "publication_latest_tag",
    "publication_tag_commit",
    "publication_local_head",
    "publication_upstream_head",
    "publication_tag_points_at_head",
    "publication_tag_commit_in_upstream",
    "publication_branch_published",
    "publication_tag_published",
    "publication_remote_branch_head",
    "publication_remote_tag_commit",
    "publication_remote_checked",
    "publication_ahead_count",
    "publication_behind_count",
    "release_draft_ok",
    "release_draft_issue_count",
    "candidate_issue_gate_key_count",
    "candidate_issue_gate_sha256",
    "candidate_issue_gate_status",
    "can_create_issues",
    "requires_maintainer_review",
    "candidate_issue_gate_summary_sha256",
    "candidate_issue_gate_evidence_key_count",
    "candidate_issue_gate_evidence_sha256",
    "candidate_issue_gate_evidence_first_key",
    "candidate_issue_gate_evidence_last_key",
    "candidate_issue_gate_evidence_key_boundary_sha256",
    "candidate_issue_gate_reason_description_count",
    "candidate_issue_gate_reason_descriptions_sha256",
    "candidate_issue_gate_reason_code_count",
    "candidate_issue_gate_reason_codes_sha256",
    "candidate_issue_gate_first_reason_code",
    "candidate_issue_gate_last_reason_code",
    "candidate_issue_gate_reason_code_boundary_sha256",
    "candidate_issue_gate_primary_reason_code",
    "candidate_issue_gate_primary_reason_description",
    "candidate_issue_gate_required_action_count",
    "candidate_issue_gate_required_actions_sha256",
    "candidate_issue_gate_first_required_action",
    "candidate_issue_gate_last_required_action",
    "candidate_issue_gate_required_action_boundary_sha256",
    "candidate_issue_gate_primary_required_action",
    "dry_run_supported",
    "preflight_required",
)
ARTIFACT_BUNDLE_SUMMARY_KEY_PREVIEW = ARTIFACT_BUNDLE_SUMMARY_KEYS[:8]
ARTIFACT_BUNDLE_SUMMARY_KEY_TAIL = ARTIFACT_BUNDLE_SUMMARY_KEYS[-8:]
ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY = {
    "first_key": ARTIFACT_BUNDLE_SUMMARY_KEYS[0],
    "last_key": ARTIFACT_BUNDLE_SUMMARY_KEYS[-1],
}
ARTIFACT_MANIFEST_KEY_BOUNDARY = {
    "first_key": ARTIFACT_MANIFEST_KEYS[0],
    "last_key": ARTIFACT_MANIFEST_KEYS[-1],
}
ARTIFACT_MANIFEST_KEY_PREVIEW = ARTIFACT_MANIFEST_KEYS[:8]
ARTIFACT_MANIFEST_KEY_TAIL = ARTIFACT_MANIFEST_KEYS[-8:]
ARTIFACT_MANIFEST_PAYLOAD_KEYS = tuple(
    key for key in ARTIFACT_MANIFEST_KEYS if key != "artifact_bundle_summary"
)
ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY = {
    "first_key": ARTIFACT_MANIFEST_PAYLOAD_KEYS[0],
    "last_key": ARTIFACT_MANIFEST_PAYLOAD_KEYS[-1],
}
ARTIFACT_MANIFEST_PAYLOAD_KEY_PREVIEW = ARTIFACT_MANIFEST_PAYLOAD_KEYS[:8]
ARTIFACT_MANIFEST_PAYLOAD_KEY_TAIL = ARTIFACT_MANIFEST_PAYLOAD_KEYS[-8:]
PUBLICATION_PUBLISH_SCRIPT_PATH = "/tmp/cliany-publish-release.sh"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_release_publication import build_report as build_publication_report  # noqa: E402
from release_readiness import build_report as build_readiness_report  # noqa: E402


@dataclass(frozen=True)
class CandidatePromotion:
    case_id: str
    issue_title: str
    issue_labels: list[str]
    target_url: str
    commands: list[str]
    offline_commands: list[str]
    adapter_package: str
    metadata_validation: str
    online_smoke: str
    priority_rank: int | None
    priority_reason: str
    promotion_evidence: dict[str, Any]
    promotion_evidence_primary_task: dict[str, Any]
    evidence_bundle_primary_next_task: dict[str, Any]
    evidence_bundle_primary_next_task_runbook: list[dict[str, Any]]
    candidate_package_validation_command: str
    promotion_command_plan: list[dict[str, Any]]
    llm_live_preflight_command: str
    llm_live_preflight_blocker_note: str
    llm_live_preflight_evidence_fields: list[str]
    evidence_bundle_command: str
    evidence_bundle_json_command: str
    issue_body: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "issue_title": self.issue_title,
            "issue_labels": self.issue_labels,
            "target_url": self.target_url,
            "commands": self.commands,
            "offline_commands": self.offline_commands,
            "adapter_package": self.adapter_package,
            "metadata_validation": self.metadata_validation,
            "online_smoke": self.online_smoke,
            "priority_rank": self.priority_rank,
            "priority_reason": self.priority_reason,
            "promotion_evidence": self.promotion_evidence,
            "promotion_evidence_primary_task": self.promotion_evidence_primary_task,
            "evidence_bundle_primary_next_task": self.evidence_bundle_primary_next_task,
            "evidence_bundle_primary_next_task_runbook": (
                self.evidence_bundle_primary_next_task_runbook
            ),
            "candidate_package_validation_command": self.candidate_package_validation_command,
            "promotion_command_plan": self.promotion_command_plan,
            "llm_live_preflight_command": self.llm_live_preflight_command,
            "llm_live_preflight_blocker_note": self.llm_live_preflight_blocker_note,
            "llm_live_preflight_evidence_fields": self.llm_live_preflight_evidence_fields,
            "evidence_bundle_command": self.evidence_bundle_command,
            "evidence_bundle_json_command": self.evidence_bundle_json_command,
            "issue_body": self.issue_body,
        }


@dataclass(frozen=True)
class IterationPlan:
    current_version: str
    target_version: str
    recommended_theme: str
    recommended_slice: str
    readiness_ok: bool
    publication_ok: bool
    commit_days: str
    commit_cadence: dict[str, Any]
    case_assets: str
    candidate_cases: list[str]
    candidate_promotions: list[CandidatePromotion]
    case_promotion_evidence_summary: dict[str, Any]
    case_promotion_command_plan_summary: dict[str, Any]
    standard_release_flow: dict[str, Any]
    blockers: list[str]
    next_actions: list[str]
    validation_commands: list[str]
    candidate_issue_gate: dict[str, Any]
    publication_visibility: dict[str, str]
    publication_tag_publish_decision: dict[str, Any]
    publication_blockers: list[str]
    publication_next_action_count: int
    publication_next_actions: list[str]
    publication_publish_command_count: int
    publication_publish_commands: list[str]
    publication_ref_context: dict[str, Any]
    publication_worktree_clean: bool
    publication_worktree_status: list[str]
    publication_publish_script_path: str
    publication_publish_script_path_sha256: str
    publication_publish_script_command: str
    publication_publish_script_command_sha256: str
    plan_report_command: str
    issue_artifacts_command: str
    release_draft_path: str
    release_draft_issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        primary_next_task = self.case_promotion_evidence_summary.get("primary_next_task")
        if not isinstance(primary_next_task, dict):
            primary_next_task = None
        primary_runbook = _primary_runbook_from_summary(self.case_promotion_evidence_summary)
        primary_runbook_steps = _runbook_steps(primary_runbook)
        primary_runbook_first_command = _runbook_first_command(primary_runbook)
        standard_release_flow_steps = _standard_release_flow_steps(self.standard_release_flow)
        standard_release_flow_step_names = _standard_release_flow_step_names(
            self.standard_release_flow
        )
        standard_release_flow_step_boundary = _standard_release_flow_step_boundary(
            self.standard_release_flow
        )
        standard_release_flow_step_status_counts = (
            _standard_release_flow_step_status_counts(self.standard_release_flow)
        )
        website_deploy_command = _standard_release_flow_website_deploy_command(
            self.standard_release_flow
        )
        return {
            "current_version": self.current_version,
            "target_version": self.target_version,
            "recommended_theme": self.recommended_theme,
            "recommended_slice": self.recommended_slice,
            "readiness_ok": self.readiness_ok,
            "publication_ok": self.publication_ok,
            "commit_days": self.commit_days,
            "commit_cadence": self.commit_cadence,
            "case_assets": self.case_assets,
            "candidate_cases": self.candidate_cases,
            "candidate_promotions": [promotion.to_dict() for promotion in self.candidate_promotions],
            "case_promotion_evidence_summary_sha256": _stable_json_sha256(
                self.case_promotion_evidence_summary
            ),
            "case_promotion_evidence_summary": self.case_promotion_evidence_summary,
            "case_promotion_command_plan_summary_sha256": _stable_json_sha256(
                self.case_promotion_command_plan_summary
            ),
            "case_promotion_command_plan_summary": self.case_promotion_command_plan_summary,
            "standard_release_flow_sha256": _stable_json_sha256(self.standard_release_flow),
            "standard_release_flow_status": self.standard_release_flow.get("status"),
            "standard_release_flow_primary_next_action": self.standard_release_flow.get(
                "primary_next_action"
            ),
            "standard_release_flow_command_count": self.standard_release_flow.get(
                "command_count"
            ),
            "standard_release_flow_commands_sha256": self.standard_release_flow.get(
                "commands_sha256"
            ),
            "standard_release_flow_step_count": len(standard_release_flow_steps),
            "standard_release_flow_step_names": standard_release_flow_step_names,
            "standard_release_flow_step_names_sha256": _stable_json_sha256(
                standard_release_flow_step_names
            ),
            "standard_release_flow_steps_sha256": _stable_json_sha256(
                standard_release_flow_steps
            ),
            "standard_release_flow_first_step_name": (
                standard_release_flow_step_boundary["first_step_name"]
            ),
            "standard_release_flow_last_step_name": (
                standard_release_flow_step_boundary["last_step_name"]
            ),
            "standard_release_flow_step_boundary_sha256": _stable_json_sha256(
                standard_release_flow_step_boundary
            ),
            "standard_release_flow_step_status_counts": (
                standard_release_flow_step_status_counts
            ),
            "standard_release_flow_step_status_counts_sha256": _stable_json_sha256(
                standard_release_flow_step_status_counts
            ),
            "standard_release_flow_primary_blocked_step_name": (
                _standard_release_flow_primary_step_name_with_status_prefix(
                    self.standard_release_flow, "blocked"
                )
            ),
            "standard_release_flow_primary_pending_step_name": (
                _standard_release_flow_primary_step_name_with_status_prefix(
                    self.standard_release_flow, "pending"
                )
            ),
            "standard_release_flow_has_website_deploy": website_deploy_command is not None,
            "standard_release_flow_website_deploy_command": website_deploy_command,
            "standard_release_flow_website_deploy_command_sha256": (
                _stable_json_sha256(website_deploy_command)
                if website_deploy_command
                else None
            ),
            "standard_release_flow": self.standard_release_flow,
            "case_promotion_evidence_primary_next_task": primary_next_task,
            "case_promotion_evidence_primary_next_action": (
                self.case_promotion_evidence_summary.get("primary_next_action")
            ),
            "case_promotion_evidence_primary_runbook": primary_runbook,
            "case_promotion_evidence_primary_runbook_step_count": len(primary_runbook_steps),
            "case_promotion_evidence_primary_runbook_steps": primary_runbook_steps,
            "case_promotion_evidence_primary_runbook_steps_sha256": _stable_json_sha256(
                primary_runbook_steps
            ),
            "case_promotion_evidence_primary_runbook_first_step": (
                _runbook_first_step_name(primary_runbook)
            ),
            "case_promotion_evidence_primary_runbook_first_command": (
                primary_runbook_first_command
            ),
            "case_promotion_evidence_primary_runbook_first_command_sha256": (
                _stable_json_sha256(primary_runbook_first_command)
                if primary_runbook_first_command
                else None
            ),
            "blockers": self.blockers,
            "next_action_count": len(self.next_actions),
            "next_actions_sha256": _stable_json_sha256(self.next_actions),
            "primary_next_action": self.next_actions[0] if self.next_actions else None,
            "next_actions": self.next_actions,
            "validation_commands": self.validation_commands,
            "candidate_issue_gate": self.candidate_issue_gate,
            "publication_visibility": self.publication_visibility,
            "publication_tag_publish_decision": self.publication_tag_publish_decision,
            "publication_blocker_count": len(self.publication_blockers),
            "publication_blockers_sha256": _stable_json_sha256(self.publication_blockers),
            "publication_primary_blocker": (
                self.publication_blockers[0] if self.publication_blockers else None
            ),
            "publication_blockers": self.publication_blockers,
            "publication_next_action_count": self.publication_next_action_count,
            "publication_next_actions_sha256": _stable_json_sha256(self.publication_next_actions),
            "publication_primary_next_action": (
                self.publication_next_actions[0] if self.publication_next_actions else None
            ),
            "publication_next_actions": self.publication_next_actions,
            "publication_publish_command_count": self.publication_publish_command_count,
            "publication_publish_commands_sha256": _stable_json_sha256(
                self.publication_publish_commands
            ),
            "publication_primary_publish_command": (
                self.publication_publish_commands[0] if self.publication_publish_commands else None
            ),
            "publication_publish_commands": self.publication_publish_commands,
            "publication_ref_context": self.publication_ref_context,
            "publication_worktree_clean": self.publication_worktree_clean,
            "publication_worktree_status": self.publication_worktree_status,
            "publication_publish_script_path": self.publication_publish_script_path,
            "publication_publish_script_path_sha256": self.publication_publish_script_path_sha256,
            "publication_publish_script_command": self.publication_publish_script_command,
            "publication_publish_script_command_sha256": (
                self.publication_publish_script_command_sha256
            ),
            "plan_report_command": self.plan_report_command,
            "issue_artifacts_command": self.issue_artifacts_command,
            "release_draft_path": self.release_draft_path,
            "release_draft_issues": self.release_draft_issues,
        }


def _project_version(root: Path) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _next_patch_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3:
        msg = f"Unsupported semantic version: {version}"
        raise ValueError(msg)
    major, minor, patch = parts
    return f"{major}.{minor}.{int(patch) + 1}"


def _publication_publish_commands(publication: Any) -> list[str]:
    commands = getattr(publication, "publish_commands", None)
    if commands is not None:
        return [str(command) for command in commands]
    to_dict = getattr(publication, "to_dict", None)
    if not callable(to_dict):
        return []
    payload = to_dict()
    return [str(command) for command in payload.get("publish_commands", [])]


def _publication_tag_publish_decision(
    publication: Any,
    target_version: str | None = None,
    *,
    readiness_blockers: list[str] | None = None,
) -> dict[str, Any]:
    decision = getattr(publication, "tag_publish_decision", None)
    if isinstance(decision, dict):
        return _with_target_tag_guidance(
            dict(decision),
            publication,
            target_version,
            readiness_blockers=readiness_blockers,
        )
    to_dict = getattr(publication, "to_dict", None)
    if callable(to_dict):
        payload = to_dict()
        decision = payload.get("tag_publish_decision")
        if isinstance(decision, dict):
            return _with_target_tag_guidance(
                dict(decision),
                publication,
                target_version,
                readiness_blockers=readiness_blockers,
            )

    latest_tag = getattr(publication, "latest_tag", None)
    tag_points_at_head = bool(getattr(publication, "tag_points_at_head", False))
    tag_published = getattr(publication, "tag_published", None)
    if not latest_tag:
        return _with_target_tag_guidance(
            {
                "status": "missing_tag",
                "can_push_tag": False,
                "latest_tag": None,
                "tag_points_at_head": tag_points_at_head,
                "tag_published": tag_published,
                "required_action": "Create a release tag before publishing a tag.",
            },
            publication,
            target_version,
            readiness_blockers=readiness_blockers,
        )
    if not tag_points_at_head:
        return _with_target_tag_guidance(
            {
                "status": "manual_decision_required",
                "can_push_tag": False,
                "latest_tag": str(latest_tag),
                "tag_points_at_head": False,
                "tag_published": tag_published,
                "required_action": (
                    "Move to the latest tag commit or create a new release tag at HEAD "
                    "before publishing a tag."
                ),
            },
            publication,
            target_version,
            readiness_blockers=readiness_blockers,
        )
    if tag_published is True:
        return _with_target_tag_guidance(
            {
                "status": "published",
                "can_push_tag": False,
                "latest_tag": str(latest_tag),
                "tag_points_at_head": True,
                "tag_published": True,
                "required_action": None,
            },
            publication,
            target_version,
            readiness_blockers=readiness_blockers,
        )
    if not _publication_worktree_clean(publication):
        return _with_target_tag_guidance(
            {
                "status": "blocked_by_worktree",
                "can_push_tag": False,
                "latest_tag": str(latest_tag),
                "tag_points_at_head": True,
                "tag_published": tag_published,
                "required_action": "Commit, stash, or discard local worktree changes before publishing release refs.",
            },
            publication,
            target_version,
            readiness_blockers=readiness_blockers,
        )
    if tag_published is False:
        return _with_target_tag_guidance(
            {
                "status": "ready_to_push",
                "can_push_tag": True,
                "latest_tag": str(latest_tag),
                "tag_points_at_head": True,
                "tag_published": False,
                "required_action": f"Push tag `{latest_tag}` after the branch is published.",
            },
            publication,
            target_version,
            readiness_blockers=readiness_blockers,
        )
    return _with_target_tag_guidance(
        {
            "status": "needs_remote_check",
            "can_push_tag": False,
            "latest_tag": str(latest_tag),
            "tag_points_at_head": True,
            "tag_published": tag_published,
            "required_action": "Rerun with `--remote` to verify the live remote tag.",
        },
        publication,
        target_version,
        readiness_blockers=readiness_blockers,
    )


def _target_tag_name(target_version: str | None) -> str | None:
    if not target_version:
        return None
    version = str(target_version).strip()
    if not version:
        return None
    return version if version.startswith("v") else f"v{version}"


def _has_target_daily_release_limit_blocker(blockers: list[str]) -> bool:
    return any(
        blocker.startswith("creating target tag ")
        and "today would exceed the daily release cap" in blocker
        for blocker in blockers
    )


def _mentions_create_new_release_tag(action: str) -> bool:
    return "create a new release tag at HEAD" in action


def _with_target_tag_guidance(
    decision: dict[str, Any],
    publication: Any,
    target_version: str | None,
    *,
    readiness_blockers: list[str] | None = None,
) -> dict[str, Any]:
    target_tag = _target_tag_name(target_version)
    if target_tag is None:
        return decision

    blockers = list(readiness_blockers or [])
    latest_tag = decision.get("latest_tag")
    tag_points_at_head = bool(decision.get("tag_points_at_head", False))
    target_tag_matches_latest = latest_tag == target_tag
    remote = str(getattr(publication, "remote", "") or "origin")
    create_command = f"git tag {shlex.quote(target_tag)}"
    push_command = f"git push {shlex.quote(remote)} {shlex.quote(target_tag)}"

    if _has_target_daily_release_limit_blocker(blockers):
        target_status = "blocked_by_daily_release_cap"
        required_action = f"Pause release tagging until the next day before creating target tag `{target_tag}`."
        commands = []
    elif target_tag_matches_latest and tag_points_at_head:
        target_status = "current_tag_at_head"
        required_action = decision.get("required_action")
        commands: list[str] = []
    elif not _publication_worktree_clean(publication):
        target_status = "blocked_by_worktree"
        required_action = (
            "Commit, stash, or discard local worktree changes before creating "
            f"target tag `{target_tag}`."
        )
        commands = [create_command, push_command]
    else:
        target_status = "create_target_tag_at_head"
        required_action = (
            f"After final release readiness is clean, create target tag `{target_tag}` at HEAD "
            "and push it after the branch is published."
        )
        commands = [create_command, push_command]

    return {
        **decision,
        "target_tag": target_tag,
        "target_tag_matches_latest": target_tag_matches_latest,
        "target_tag_status": target_status,
        "target_tag_required_action": required_action,
        "target_tag_command_count": len(commands),
        "target_tag_commands_sha256": _stable_json_sha256(commands),
        "target_tag_primary_command": commands[0] if commands else None,
        "target_tag_commands": commands,
        "target_tag_release_gate_status": (
            "blocked_by_readiness" if blockers else "ready_for_publication_review"
        ),
        "target_tag_release_gate_blocker_count": len(blockers),
        "target_tag_release_gate_blockers_sha256": _stable_json_sha256(blockers),
        "target_tag_release_gate_primary_blocker": blockers[0] if blockers else None,
        "target_tag_release_gate_required_action": (
            f"Clear release readiness blockers before creating target tag `{target_tag}`."
            if blockers
            else required_action
        ),
        "target_tag_release_gate_blockers": blockers,
    }


def _publication_next_actions(publication: Any) -> list[str]:
    actions = getattr(publication, "next_actions", None)
    if actions is not None:
        return [str(action).removeprefix("- ") for action in actions]
    to_dict = getattr(publication, "to_dict", None)
    if not callable(to_dict):
        return []
    payload = to_dict()
    return [str(action).removeprefix("- ") for action in payload.get("next_actions", [])]


def _publication_plan_next_actions(
    publication: Any,
    target_version: str | None,
    *,
    readiness_blockers: list[str] | None = None,
) -> list[str]:
    actions = _publication_next_actions(publication)
    decision = _publication_tag_publish_decision(
        publication,
        target_version,
        readiness_blockers=readiness_blockers,
    )
    if decision.get("status") != "manual_decision_required":
        return actions
    if decision.get("target_tag_status") not in {
        "blocked_by_worktree",
        "create_target_tag_at_head",
    }:
        return actions

    target_action = _target_tag_next_action(decision)
    if target_action is None:
        return actions

    latest_tag = str(decision.get("latest_tag") or "")
    normalized: list[str] = []
    inserted = False
    for action in actions:
        replaces_old_tag_action = "create a new release tag at HEAD" in action or (
            bool(latest_tag) and f"Push tag `{latest_tag}`" in action
        )
        if replaces_old_tag_action:
            if not inserted:
                normalized.append(target_action)
                inserted = True
            continue
        normalized.append(action)

    if not inserted:
        normalized.append(target_action)
    return normalized


def _target_tag_next_action(decision: dict[str, Any]) -> str | None:
    if decision.get("target_tag_status") not in {
        "blocked_by_worktree",
        "create_target_tag_at_head",
    }:
        return None
    action = decision.get("target_tag_required_action")
    if not action:
        return None

    commands = decision.get("target_tag_commands")
    if not isinstance(commands, list) or not commands:
        return str(action)
    command_text = " then ".join(f"`{command}`" for command in commands)
    return f"{action} Commands: {command_text}."


def _readiness_payload(readiness: Any) -> dict[str, Any]:
    to_dict = getattr(readiness, "to_dict", None)
    if not callable(to_dict):
        return {}
    payload = to_dict()
    return payload if isinstance(payload, dict) else {}


def _readiness_standard_release_flow(readiness: Any) -> dict[str, Any]:
    flow = getattr(readiness, "standard_release_flow", None)
    if isinstance(flow, dict):
        return dict(flow)
    flow = _readiness_payload(readiness).get("standard_release_flow")
    return dict(flow) if isinstance(flow, dict) else {}


def _standard_release_flow_primary_next_action(readiness: Any) -> str | None:
    action = _readiness_standard_release_flow(readiness).get("primary_next_action")
    return str(action) if action else None


def _standard_release_flow_website_deploy_command(flow: dict[str, Any]) -> str | None:
    commands = flow.get("commands")
    if not isinstance(commands, list):
        return None
    for command in commands:
        if str(command) == WEBSITE_DEPLOY_COMMAND:
            return str(command)
    return None


def _standard_release_flow_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for step in flow.get("steps") or [] if isinstance(step, dict)]


def _standard_release_flow_step_names(flow: dict[str, Any]) -> list[str]:
    return [
        str(step["name"])
        for step in _standard_release_flow_steps(flow)
        if step.get("name")
    ]


def _standard_release_flow_step_boundary(flow: dict[str, Any]) -> dict[str, str | None]:
    step_names = _standard_release_flow_step_names(flow)
    return {
        "first_step_name": step_names[0] if step_names else None,
        "last_step_name": step_names[-1] if step_names else None,
    }


def _standard_release_flow_step_status_counts(flow: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for step in _standard_release_flow_steps(flow):
        status = step.get("status")
        if status is None:
            continue
        status_key = str(status)
        counts[status_key] = counts.get(status_key, 0) + 1
    return counts


def _standard_release_flow_primary_step_name_with_status_prefix(
    flow: dict[str, Any],
    prefix: str,
) -> str | None:
    for step in _standard_release_flow_steps(flow):
        status = step.get("status")
        name = step.get("name")
        if status is not None and name is not None and str(status).startswith(prefix):
            return str(name)
    return None


def _readiness_next_actions(readiness: Any) -> list[str]:
    actions = getattr(readiness, "next_actions", None)
    if actions is None:
        actions = _readiness_payload(readiness).get("next_actions", [])
    if not isinstance(actions, list):
        return []
    return [str(action).removeprefix("- ") for action in actions]


def _standard_release_flow(
    readiness: Any,
    publication: Any,
    *,
    next_actions: list[str],
    publication_publish_commands: list[str],
    publication_tag_publish_decision: dict[str, Any],
    remote_check: bool,
    remote_name: str,
) -> dict[str, Any]:
    existing = _readiness_standard_release_flow(readiness)
    if existing:
        return existing

    target_version = str(getattr(readiness, "target_version", "") or "")
    target_tag = publication_tag_publish_decision.get("target_tag") or _target_tag_name(
        target_version
    )
    strict_command = _release_readiness_strict_command(
        target_version,
        remote_check=remote_check,
        remote_name=remote_name,
    )
    remote_audit_command = _remote_publication_audit_command(remote_name)
    validation_command = "CLIANY_QA_OFFLINE=1 pytest tests/ -q"
    case_validation_command = "python scripts/validate_cases.py --strict"
    target_tag_commands = [
        str(command)
        for command in publication_tag_publish_decision.get("target_tag_commands") or []
    ]
    release_notes_action = (
        f"Move CHANGELOG.md Unreleased entries into `## [{target_version}] - <date>`."
    )
    current_version = str(getattr(readiness, "current_version", "") or "")
    version_action = f"Update pyproject.toml project.version to `{target_version}`."
    validation_commands = [
        strict_command,
        validation_command,
        case_validation_command,
        *publication_publish_commands,
        *target_tag_commands,
        WEBSITE_DEPLOY_COMMAND,
        remote_audit_command,
    ]
    commands = list(dict.fromkeys(command for command in validation_commands if command))
    blockers = [
        *[str(blocker) for blocker in getattr(readiness, "blockers", [])],
        *_publication_blockers(publication),
    ]
    primary_next_action = (
        next_actions[0]
        if next_actions
        else f"Run `{strict_command}` before tagging `{target_tag}`."
    )
    return {
        "status": "blocked" if blockers else "ready",
        "target_version": target_version,
        "target_tag": target_tag,
        "blocker_count": len(blockers),
        "blockers_sha256": _stable_json_sha256(blockers),
        "blockers": blockers,
        "primary_next_action": primary_next_action,
        "command_count": len(commands),
        "commands_sha256": _stable_json_sha256(commands),
        "commands": commands,
        "steps": [
            {
                "name": "strict_release_readiness",
                "status": "blocked" if getattr(readiness, "blockers", []) else "ready",
                "command": strict_command,
            },
            {
                "name": "release_notes",
                "status": "pending",
                "action": release_notes_action,
            },
            {
                "name": "version_bump",
                "status": "pending" if current_version != target_version else "ready",
                "action": version_action,
            },
            {
                "name": "offline_validation",
                "status": "pending",
                "commands": [validation_command, case_validation_command],
            },
            {
                "name": "publish_branch",
                "status": "blocked" if not _publication_worktree_clean(publication) else "pending",
                "commands": list(publication_publish_commands),
            },
            {
                "name": "target_tag",
                "status": publication_tag_publish_decision.get("target_tag_status"),
                "commands": target_tag_commands,
            },
            {
                "name": "website_deploy",
                "status": "pending",
                "command": WEBSITE_DEPLOY_COMMAND,
            },
            {
                "name": "remote_publication_audit",
                "status": "pending",
                "command": remote_audit_command,
            },
        ],
    }


def _publication_blockers(publication: Any) -> list[str]:
    to_dict = getattr(publication, "to_dict", None)
    payload = to_dict() if callable(to_dict) else {}
    payload_blockers = payload.get("publication_blockers") or payload.get("blockers")
    if isinstance(payload_blockers, list):
        return [str(blocker) for blocker in payload_blockers]
    if bool(getattr(publication, "ok", payload.get("ok", False))):
        return []

    blockers: list[str] = []
    if not _publication_worktree_clean(publication):
        blockers.append("publication worktree is dirty")
    branch_published = getattr(publication, "branch_published", payload.get("branch_published"))
    if branch_published is not True:
        blockers.append("latest local release is not published")
    latest_tag = getattr(publication, "latest_tag", payload.get("latest_tag"))
    tag_points_at_head = bool(
        getattr(publication, "tag_points_at_head", payload.get("tag_points_at_head", False))
    )
    if latest_tag and not tag_points_at_head:
        blockers.append("latest release tag does not point at HEAD")
    tag_published = getattr(publication, "tag_published", payload.get("tag_published"))
    if tag_published is not True:
        blockers.append("latest local release tag is not published")
    if not latest_tag:
        blockers.append("release tag is missing")
    return blockers


def _package_gate_args(*, packages_dir: Path | None, require_packages: bool) -> str:
    args: list[str] = []
    if packages_dir is not None:
        args.extend(["--packages-dir", shlex.quote(str(packages_dir))])
    if require_packages:
        args.append("--require-packages")
    return f" {' '.join(args)}" if args else ""


def _remote_audit_args(*, remote_check: bool, remote_name: str) -> str:
    args: list[str] = []
    if remote_check:
        args.append("--remote")
    if remote_name != "origin":
        args.extend(["--remote-name", shlex.quote(remote_name)])
    return f" {' '.join(args)}" if args else ""


def _release_readiness_strict_command(
    target_version: str,
    *,
    remote_check: bool,
    remote_name: str,
) -> str:
    remote_args = _remote_audit_args(remote_check=remote_check, remote_name=remote_name)
    return (
        "python scripts/release_readiness.py --strict "
        f"--target-version {shlex.quote(target_version)}{remote_args}"
    )


def _remote_publication_audit_command(remote_name: str) -> str:
    remote_args = _remote_audit_args(remote_check=True, remote_name=remote_name)
    return f"python scripts/check_release_publication.py{remote_args} --json"


def _publication_audit_validation_command(*, remote_check: bool, remote_name: str) -> str:
    remote_args = _remote_audit_args(remote_check=remote_check, remote_name=remote_name)
    return f"python scripts/check_release_publication.py{remote_args} --json"


def _publication_publish_script_command(*, remote_check: bool, remote_name: str) -> str:
    remote_args = _remote_audit_args(remote_check=remote_check, remote_name=remote_name)
    return (
        f"python scripts/check_release_publication.py{remote_args} --json "
        f"--publish-script {PUBLICATION_PUBLISH_SCRIPT_PATH}"
    )


def _candidate_package_validation_command(packages_dir: Path | None) -> str | None:
    if packages_dir is None:
        return None
    quoted_packages_dir = shlex.quote(str(packages_dir))
    return (
        "python scripts/validate_cases.py "
        f"--packages-dir {quoted_packages_dir} --include-candidate-packages --strict"
    )


def _default_candidate_package_validation_command() -> str:
    return CANDIDATE_PACKAGE_VALIDATION_COMMAND


def _publication_worktree_clean(publication: Any) -> bool:
    clean = getattr(publication, "worktree_clean", None)
    if clean is not None:
        return bool(clean)
    to_dict = getattr(publication, "to_dict", None)
    if not callable(to_dict):
        return True
    payload = to_dict()
    return bool(payload.get("worktree_clean", True))


def _publication_ref_context(publication: Any) -> dict[str, Any]:
    fields = [
        "repo_root",
        "branch",
        "upstream",
        "remote",
        "local_head",
        "upstream_head",
        "ahead_count",
        "behind_count",
        "latest_tag",
        "tag_commit",
        "tag_points_at_head",
        "tag_commit_in_upstream",
        "branch_published",
        "tag_published",
        "remote_branch_head",
        "remote_tag_commit",
        "remote_checked",
    ]
    to_dict = getattr(publication, "to_dict", None)
    payload = to_dict() if callable(to_dict) else {}
    return {field: getattr(publication, field, payload.get(field, None)) for field in fields}


def _latest_release_visible(publication: Any) -> bool:
    if not _publication_worktree_clean(publication):
        return False
    if bool(getattr(publication, "ok", False)):
        return True
    latest_tag = str(getattr(publication, "latest_tag", "") or "")
    return bool(
        latest_tag
        and getattr(publication, "branch_published", None) is True
        and getattr(publication, "tag_published", None) is True
    )


def _publication_visibility(publication: Any) -> dict[str, str]:
    if not _publication_worktree_clean(publication):
        return {
            "status": "dirty_worktree",
            "summary": "Worktree has uncommitted changes; resolve them before publishing release refs.",
        }
    if bool(getattr(publication, "ok", False)):
        return {
            "status": "published",
            "summary": "Latest local release branch and tag are published.",
        }

    branch = str(getattr(publication, "branch", "") or "HEAD")
    remote = str(getattr(publication, "remote", "") or "upstream")
    latest_tag = str(getattr(publication, "latest_tag", "") or "(no tag)")
    ahead_count = getattr(publication, "ahead_count", None)
    tag_published = getattr(publication, "tag_published", None)
    tag_points_at_head = getattr(publication, "tag_points_at_head", None)
    remote_checked = bool(getattr(publication, "remote_checked", False))

    if _latest_release_visible(publication) and tag_points_at_head is False:
        return {
            "status": "published_with_unreleased_head",
            "summary": (
                f"Latest release `{latest_tag}` is visible on `{remote}`; HEAD contains "
                "unreleased changes that need a new target tag before the next release."
            ),
        }

    if isinstance(ahead_count, int) and ahead_count > 0:
        if latest_tag != "(no tag)" and tag_points_at_head is False:
            return {
                "status": "local_only",
                "summary": (
                    f"`{branch}` is ahead of `{remote}` by {ahead_count} commits; "
                    f"`{latest_tag}` does not point at HEAD, so publish `{branch}` first and "
                    "choose whether to move to that tag commit or create a new release tag at "
                    "HEAD before publishing a tag."
                ),
            }
        return {
            "status": "local_only",
            "summary": (
                f"`{branch}` is ahead of `{remote}` by {ahead_count} commits; "
                f"publish `{branch}` and `{latest_tag}` after maintainer approval."
            ),
        }
    if tag_published is False:
        check_note = (
            "remote check confirmed the tag is missing or stale"
            if remote_checked
            else "remote check has not run yet"
        )
        return {
            "status": "tag_not_visible",
            "summary": f"`{latest_tag}` is not visible on `{remote}`; {check_note}.",
        }
    return {
        "status": "needs_remote_check",
        "summary": "Publication visibility is inconclusive; rerun with `--remote` to verify live refs.",
    }


def _candidate_issue_gate(readiness: Any, publication: Any) -> dict[str, Any]:
    release_draft_issues = _release_draft_issues(readiness)
    release_readiness_blockers = _release_readiness_blockers(readiness)
    target_version = str(getattr(readiness, "target_version", "") or "") or None
    evidence = _candidate_issue_gate_evidence(readiness, publication, target_version)
    reason_codes = _candidate_issue_gate_reason_codes(release_draft_issues, publication)
    if release_readiness_blockers:
        reason_codes.append("release_readiness_blockers")
    reason_descriptions = _candidate_issue_gate_reason_descriptions(reason_codes)
    release_draft_actions = _release_draft_required_actions(release_draft_issues)
    release_readiness_actions = _release_readiness_required_actions(
        readiness,
        release_readiness_blockers,
    )
    if not _latest_release_visible(publication):
        publication_actions = _publication_next_actions(publication) or [
            "Run python scripts/check_release_publication.py --json and resolve publication blockers."
        ]
        actions = [*publication_actions, *release_draft_actions, *release_readiness_actions]
        return {
            "status": "blocked_by_publication",
            "can_create_issues": False,
            "requires_maintainer_review": True,
            "summary": "Do not create candidate issues until the latest local release is publicly visible.",
            **_candidate_issue_gate_reason_fields(reason_codes),
            "reason_descriptions": reason_descriptions,
            "primary_reason_description": _candidate_issue_gate_primary_reason_description(
                reason_codes, reason_descriptions
            ),
            **_candidate_issue_gate_action_fields(actions),
            "evidence": evidence,
        }
    if release_draft_issues:
        actions = [*release_draft_actions, *release_readiness_actions]
        return {
            "status": "review_required",
            "can_create_issues": True,
            "requires_maintainer_review": True,
            "summary": "Release draft issues must be resolved or intentionally deferred before tagging.",
            **_candidate_issue_gate_reason_fields(reason_codes),
            "reason_descriptions": reason_descriptions,
            "primary_reason_description": _candidate_issue_gate_primary_reason_description(
                reason_codes, reason_descriptions
            ),
            **_candidate_issue_gate_action_fields(actions),
            "evidence": evidence,
        }
    if release_readiness_blockers:
        return {
            "status": "review_required",
            "can_create_issues": True,
            "requires_maintainer_review": True,
            "summary": "Release readiness blockers must be resolved or intentionally deferred before tagging.",
            **_candidate_issue_gate_reason_fields(reason_codes),
            "reason_descriptions": reason_descriptions,
            "primary_reason_description": _candidate_issue_gate_primary_reason_description(
                reason_codes, reason_descriptions
            ),
            **_candidate_issue_gate_action_fields(release_readiness_actions),
            "evidence": evidence,
        }
    actions: list[str] = []
    return {
        "status": "ready",
        "can_create_issues": True,
        "requires_maintainer_review": False,
        "summary": "Candidate issues can be created after reviewing the generated artifacts.",
        **_candidate_issue_gate_reason_fields(reason_codes),
        "reason_descriptions": reason_descriptions,
        "primary_reason_description": _candidate_issue_gate_primary_reason_description(
            reason_codes, reason_descriptions
        ),
        **_candidate_issue_gate_action_fields(actions),
        "evidence": evidence,
    }


def _candidate_issue_gate_reason_fields(reason_codes: list[str]) -> dict[str, Any]:
    return {
        "reason_code_count": len(reason_codes),
        "reason_codes_sha256": _stable_json_sha256(reason_codes),
        "reason_codes": reason_codes,
        "primary_reason_code": reason_codes[0] if reason_codes else None,
    }


def _candidate_issue_gate_action_fields(actions: list[str]) -> dict[str, Any]:
    return {
        "required_action_count": len(actions),
        "required_actions_sha256": _stable_json_sha256(actions),
        "required_actions": actions,
        "primary_required_action": actions[0] if actions else None,
    }


def _release_draft_required_actions(release_draft_issues: list[str]) -> list[str]:
    return [f"Resolve release draft issue: {issue}" for issue in release_draft_issues]


def _release_readiness_blockers(readiness: Any) -> list[str]:
    blockers = [str(blocker) for blocker in getattr(readiness, "blockers", [])]
    return [blocker for blocker in blockers if blocker != "release draft validation failed"]


def _release_readiness_required_actions(readiness: Any, blockers: list[str]) -> list[str]:
    if not blockers:
        return []
    actions = _readiness_next_actions(readiness)
    if actions:
        return actions
    return [f"Resolve release readiness blocker: {blocker}" for blocker in blockers]


def _candidate_issue_gate_primary_reason_description(
    reason_codes: list[str], reason_descriptions: dict[str, str]
) -> str | None:
    if not reason_codes:
        return None
    return reason_descriptions.get(reason_codes[0])


def _stable_json_sha256(value: object) -> str:
    digest_source = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(digest_source).hexdigest()


def _candidate_issue_gate_reason_codes(release_draft_issues: list[str], publication: Any) -> list[str]:
    codes: list[str] = []
    if not _latest_release_visible(publication):
        codes.append("publication_not_published")
        visibility_status = _publication_visibility(publication).get("status")
        if visibility_status == "dirty_worktree":
            codes.append("dirty_worktree")
        elif visibility_status == "local_only":
            codes.append("local_release_only")
        elif visibility_status == "tag_not_visible":
            codes.append("tag_not_visible")
        elif visibility_status == "needs_remote_check":
            codes.append("needs_remote_check")
    if release_draft_issues:
        codes.append("release_draft_issues")
    return codes


def _candidate_issue_gate_reason_descriptions(reason_codes: list[str]) -> dict[str, str]:
    descriptions = {
        "publication_not_published": "The latest local release branch or tag is not visible upstream.",
        "dirty_worktree": "The working tree has uncommitted changes that must be resolved first.",
        "local_release_only": "The local branch is ahead of upstream and needs maintainer-approved publishing.",
        "tag_not_visible": "The latest local release tag is not visible on the configured remote.",
        "needs_remote_check": "Live remote refs have not been checked yet.",
        "release_draft_issues": "The target release draft still has validation issues.",
        "release_readiness_blockers": "The target release is still blocked by release readiness.",
    }
    return {code: descriptions[code] for code in reason_codes if code in descriptions}


def _candidate_issue_gate_evidence(
    readiness: Any, publication: Any, target_version: str | None = None
) -> dict[str, Any]:
    release_draft_issues = _release_draft_issues(readiness)
    release_readiness_blockers = _release_readiness_blockers(readiness)
    publication_visibility = _publication_visibility(publication)
    tag_decision = _publication_tag_publish_decision(
        publication,
        target_version,
        readiness_blockers=list(getattr(readiness, "blockers", []) or []),
    )
    draft = getattr(readiness, "draft", None)
    evidence = {
        "publication_ok": bool(getattr(publication, "ok", False)),
        "publication_visibility_status": publication_visibility.get("status") or "(unknown)",
        "publication_worktree_clean": _publication_worktree_clean(publication),
        "publication_remote_checked": bool(getattr(publication, "remote_checked", False)),
        "publication_branch": str(getattr(publication, "branch", "") or "HEAD"),
        "publication_latest_tag": str(getattr(publication, "latest_tag", "") or "(none)"),
        "publication_ahead_count": getattr(publication, "ahead_count", None),
        "publication_tag_decision_status": tag_decision.get("status"),
        "publication_tag_can_push": tag_decision.get("can_push_tag"),
        "publication_tag_required_action": tag_decision.get("required_action"),
        "publication_target_tag": tag_decision.get("target_tag"),
        "publication_target_tag_status": tag_decision.get("target_tag_status"),
        "publication_target_tag_primary_command": tag_decision.get(
            "target_tag_primary_command"
        ),
        "publication_target_tag_commands_sha256": tag_decision.get(
            "target_tag_commands_sha256"
        ),
        "publication_target_tag_required_action": tag_decision.get(
            "target_tag_required_action"
        ),
        "publication_target_tag_release_gate_status": tag_decision.get(
            "target_tag_release_gate_status"
        ),
        "publication_target_tag_release_gate_blocker_count": tag_decision.get(
            "target_tag_release_gate_blocker_count"
        ),
        "publication_target_tag_release_gate_primary_blocker": tag_decision.get(
            "target_tag_release_gate_primary_blocker"
        ),
        "publication_target_tag_release_gate_required_action": tag_decision.get(
            "target_tag_release_gate_required_action"
        ),
        "publication_target_tag_release_gate_blockers_sha256": tag_decision.get(
            "target_tag_release_gate_blockers_sha256"
        ),
        "release_draft_ok": bool(getattr(draft, "ok", False)),
        "release_draft_path": _release_draft_evidence_path(readiness),
        "release_draft_issue_count": len(release_draft_issues),
    }
    if release_readiness_blockers:
        evidence.update(
            {
                "release_readiness_blocker_count": len(release_readiness_blockers),
                "release_readiness_primary_blocker": release_readiness_blockers[0],
                "release_readiness_blockers_sha256": _stable_json_sha256(
                    release_readiness_blockers
                ),
            }
        )
    return evidence


def _release_draft_evidence_path(readiness: Any) -> str:
    target_version = str(getattr(readiness, "target_version", "") or "")
    if target_version:
        return f"docs/releases/v{target_version}-draft.md"
    draft = getattr(readiness, "draft", None)
    return str(getattr(draft, "path", "") or "")


def _publication_worktree_status(publication: Any) -> list[str]:
    status = getattr(publication, "worktree_status", None)
    if status is not None:
        return [str(line) for line in status]
    to_dict = getattr(publication, "to_dict", None)
    if not callable(to_dict):
        return []
    payload = to_dict()
    return [str(line) for line in payload.get("worktree_status", [])]


def _release_draft_issues(readiness: Any) -> list[str]:
    draft = getattr(readiness, "draft", None)
    issues = getattr(draft, "issues", []) if draft is not None else []
    if not isinstance(issues, list):
        return []
    return [str(issue) for issue in issues]


def _commit_cadence(readiness: Any) -> dict[str, Any]:
    cadence = getattr(readiness, "cadence", None)
    to_dict = getattr(cadence, "to_dict", None)
    payload = to_dict() if callable(to_dict) else {}
    commit_days_value = payload.get("commit_days", getattr(cadence, "commit_days", []))
    commit_days = (
        [str(day) for day in commit_days_value]
        if isinstance(commit_days_value, list)
        else []
    )
    commit_day_count = int(payload.get("commit_day_count", getattr(cadence, "commit_day_count", 0)) or 0)
    min_commit_days = int(payload.get("min_commit_days", getattr(cadence, "min_commit_days", 0)) or 0)
    missing_commit_days = max(min_commit_days - commit_day_count, 0)
    release_tags_today_value = payload.get("release_tags_today", getattr(cadence, "release_tags_today", []))
    release_tags_today = (
        [str(tag) for tag in release_tags_today_value]
        if isinstance(release_tags_today_value, list)
        else []
    )
    release_count_today = int(
        payload.get("release_count_today", getattr(cadence, "release_count_today", len(release_tags_today))) or 0
    )
    max_daily_releases = int(
        payload.get("max_daily_releases", getattr(cadence, "max_daily_releases", 3)) or 3
    )
    daily_release_limit_ok = bool(
        payload.get(
            "daily_release_limit_ok",
            getattr(cadence, "daily_release_limit_ok", release_count_today <= max_daily_releases),
        )
    )
    next_actions_value = payload.get("next_actions", getattr(cadence, "next_actions", []))
    next_actions = (
        [str(action).removeprefix("- ") for action in next_actions_value]
        if isinstance(next_actions_value, list)
        else []
    )
    if missing_commit_days and not next_actions:
        next_actions = [
            "Ship verified slices on "
            f"`{missing_commit_days}` more unique commit days this week."
        ]
    if not daily_release_limit_ok and not next_actions:
        next_actions = [
            "Pause release tagging until the next day; today's release cap has been exceeded."
        ]
    status = "ready"
    if missing_commit_days:
        status = "needs_more_commit_days"
    if not daily_release_limit_ok:
        status = "release_cap_exceeded"
    return {
        "status": status,
        "commit_days": commit_days,
        "commit_day_count": commit_day_count,
        "min_commit_days": min_commit_days,
        "missing_commit_days": missing_commit_days,
        "release_tags_today": release_tags_today,
        "release_count_today": release_count_today,
        "max_daily_releases": max_daily_releases,
        "daily_release_limit_ok": daily_release_limit_ok,
        "next_actions": next_actions,
        "summary": (
            f"{commit_day_count}/{min_commit_days} commit days; "
            f"{missing_commit_days} more unique day(s) needed."
            if missing_commit_days
            else (
                f"{commit_day_count}/{min_commit_days} commit days; "
                f"daily releases {release_count_today}/{max_daily_releases}; "
                "cadence satisfied."
                if daily_release_limit_ok
                else (
                    f"{commit_day_count}/{min_commit_days} commit days; "
                    f"daily releases {release_count_today}/{max_daily_releases}; "
                    "release cap exceeded."
                )
            )
        ),
    }


def _next_action_lines(readiness: Any, publication: Any) -> list[str]:
    actions: list[str] = []
    readiness_blockers = list(getattr(readiness, "blockers", []))
    daily_cap_blocked = _has_target_daily_release_limit_blocker(readiness_blockers)
    readiness_actions = _readiness_next_actions(readiness)
    if daily_cap_blocked:
        actions.extend(
            action for action in readiness_actions if action.startswith("Pause release tagging")
        )
    if not publication.ok:
        standard_primary_action = _standard_release_flow_primary_next_action(readiness)
        if standard_primary_action and not (
            daily_cap_blocked and _mentions_create_new_release_tag(standard_primary_action)
        ):
            actions.append(standard_primary_action)
            target_tag_action = _target_tag_next_action(
                _publication_tag_publish_decision(
                    publication,
                    str(getattr(readiness, "target_version", "") or ""),
                    readiness_blockers=readiness_blockers,
                )
            )
            if target_tag_action:
                actions.append(target_tag_action)
        publication_actions = _publication_plan_next_actions(
            publication,
            str(getattr(readiness, "target_version", "") or ""),
            readiness_blockers=readiness_blockers,
        )
        if daily_cap_blocked:
            publication_actions = [
                action
                for action in publication_actions
                if not _mentions_create_new_release_tag(action)
            ]
        if publication_actions:
            actions.extend(publication_actions)
        elif publication.ahead_count and publication.ahead_count > 0:
            actions.append(f"Push `{publication.branch or 'HEAD'}` after maintainer approval.")
        elif publication.latest_tag and publication.tag_published is False:
            actions.append(f"Publish tag `{publication.latest_tag}` after the branch is visible upstream.")
    if daily_cap_blocked:
        actions.extend(
            action
            for action in readiness_actions
            if not action.startswith("Pause release tagging")
        )
    else:
        actions.extend(readiness_actions)
    if readiness.blockers:
        actions.append("Clear release readiness blockers before tagging the target version.")
    if readiness.cadence.commit_day_count < readiness.cadence.min_commit_days:
        missing = readiness.cadence.min_commit_days - readiness.cadence.commit_day_count
        cadence_action_exists = any("more unique commit days" in action for action in actions)
        if not cadence_action_exists:
            actions.append(f"Ship verified slices on `{missing}` more unique commit days this week.")
    if readiness.cases.candidate:
        actions.append("Promote one candidate case by collecting adapter package, metadata, and online smoke evidence.")
    if _release_draft_issues(readiness):
        actions.append(f"Draft and verify `docs/releases/v{readiness.target_version}-draft.md` for the next release.")

    deduped: list[str] = []
    for action in actions:
        if action not in deduped:
            deduped.append(action)
    return deduped


def _recommended_slice(readiness: Any, publication: Any) -> tuple[str, str]:
    if not _latest_release_visible(publication):
        return (
            "发布可见性",
            "先让最新本地 tag 和分支在远端可见，再继续扩大下一版范围。",
        )
    if readiness.cases.candidate:
        return (
            "真实案例库",
            "选择一个 candidate 案例，补齐 adapter_package、metadata_validation 和 online_smoke 证据。",
        )
    if readiness.blockers:
        return (
            "发布门禁",
            "优先关闭 readiness blocker，让下个 patch 可以直接进入 release preflight。",
        )
    return (
        "新用户可用性",
        "围绕 quickstart、doctor 下一步提示或案例入口提交一个可离线验证的小切片。",
    )


def _promotion_value(promotion: Any, field_name: str) -> str:
    if isinstance(promotion, dict):
        return str(promotion.get(field_name) or "")
    return str(getattr(promotion, field_name, "") or "")


def _case_string_list(case: Any, field_name: str) -> list[str]:
    value = getattr(case, field_name, None)
    if value is None and isinstance(case, dict):
        value = case.get(field_name)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _case_string_value(case: Any, field_name: str) -> str:
    value = getattr(case, field_name, None)
    if value is None and isinstance(case, dict):
        value = case.get(field_name)
    return str(value or "")


def _case_dict_value(case: Any, field_name: str) -> dict[str, Any]:
    value = getattr(case, field_name, None)
    if value is None and isinstance(case, dict):
        value = case.get(field_name)
    return value if isinstance(value, dict) else {}


def _case_promotion_evidence_summary(cases_report: Any) -> dict[str, Any]:
    summary = getattr(cases_report, "promotion_evidence_summary", None)
    if isinstance(summary, dict):
        normalized = dict(summary)
        if "primary_next_task" not in normalized:
            if "primary_task_detail" in normalized:
                normalized["primary_next_task"] = normalized["primary_task_detail"]
            else:
                primary_task = normalized.get("primary_task")
                if isinstance(primary_task, dict):
                    normalized["primary_next_task"] = primary_task
        return normalized

    cases = getattr(cases_report, "cases", [])
    status_counts = {status: 0 for status in ("blocked", "complete", "pending")}
    task_status_counts = {
        field_name: {status: 0 for status in ("blocked", "complete", "pending")}
        for field_name in CANDIDATE_PROMOTION_FIELDS
    }
    pending_tasks: list[dict[str, Any]] = []
    blocked_tasks: list[dict[str, Any]] = []
    complete_tasks: list[dict[str, Any]] = []
    candidate_cases = [
        case for case in cases if _case_string_value(case, "status") == "candidate"
    ]
    ranked_candidate_cases = [
        case
        for _, case in sorted(
            enumerate(candidate_cases),
            key=lambda item: _case_promotion_priority_key(item[1], item[0]),
        )
    ]

    for priority_rank, case in enumerate(ranked_candidate_cases, start=1):
        evidence = _case_dict_value(case, "promotion_evidence")
        priority_reason = _case_promotion_priority_reason(case, priority_rank)
        for field_name in CANDIDATE_PROMOTION_FIELDS:
            task = evidence.get(field_name)
            if not isinstance(task, dict):
                continue
            status = str(task.get("status") or "unknown")
            if status in status_counts:
                status_counts[status] += 1
                task_status_counts[field_name][status] += 1
            entry = {
                "case_id": str(getattr(case, "id", "")),
                "task": field_name,
                "status": status,
                "evidence": str(task.get("evidence") or ""),
                "next_action": str(task.get("next_action") or ""),
                "priority_rank": priority_rank,
                "priority_reason": priority_reason,
            }
            if status == "pending":
                pending_tasks.append(entry)
            elif status == "blocked":
                blocked_tasks.append(entry)
            elif status == "complete":
                complete_tasks.append(entry)

    primary = pending_tasks[0] if pending_tasks else (blocked_tasks[0] if blocked_tasks else None)
    primary_case = None
    if primary:
        primary_case_id = str(primary.get("case_id") or "")
        primary_case = next(
            (case for case in ranked_candidate_cases if _case_string_value(case, "id") == primary_case_id),
            None,
        )
    primary_command_plan = (
        _candidate_promotion_command_plan(
            commands=_case_string_list(primary_case, "commands"),
            candidate_package_validation_command=CANDIDATE_PACKAGE_VALIDATION_COMMAND,
        )
        if primary_case is not None
        else []
    )
    primary_runbook = _candidate_primary_task_runbook(primary, primary_command_plan)
    return {
        "candidate_count": len(candidate_cases),
        "task_count": sum(status_counts.values()),
        "status_counts": status_counts,
        "task_status_counts": task_status_counts,
        "pending_count": len(pending_tasks),
        "blocked_count": len(blocked_tasks),
        "complete_count": len(complete_tasks),
        "pending_tasks": pending_tasks,
        "blocked_tasks": blocked_tasks,
        "complete_tasks": complete_tasks,
        "primary_task": primary,
        "primary_task_detail": primary,
        "primary_next_task": primary,
        "primary_next_task_runbook": primary_runbook,
        "primary_next_action": primary["next_action"] if primary else "",
    }


def _case_promotion_priority_reason(case: Any, rank: int) -> str:
    complete_count, pending_count, blocked_count = _case_promotion_task_counts(case)
    missing_command_count = _case_promotion_missing_command_count(case)
    return (
        f"rank {rank}: complete {complete_count}/{len(CANDIDATE_PROMOTION_FIELDS)}, "
        f"pending {pending_count}, blocked {blocked_count}, "
        f"missing commands {missing_command_count}"
    )


def _case_promotion_priority_key(case: Any, index: int) -> tuple[int, int, int, int, int, int, int]:
    complete_count, pending_count, blocked_count = _case_promotion_task_counts(case)
    missing_command_count = _case_promotion_missing_command_count(case)
    ready_to_promote = complete_count == len(CANDIDATE_PROMOTION_FIELDS)
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


def _case_promotion_task_counts(case: Any) -> tuple[int, int, int]:
    evidence = _case_dict_value(case, "promotion_evidence")
    complete_count = 0
    pending_count = 0
    blocked_count = 0
    for field_name in CANDIDATE_PROMOTION_FIELDS:
        task = evidence.get(field_name)
        if not isinstance(task, dict):
            continue
        status = str(task.get("status") or "pending")
        if status == "complete" and task.get("evidence"):
            complete_count += 1
        elif status == "blocked":
            blocked_count += 1
        else:
            pending_count += 1
    return complete_count, pending_count, blocked_count


def _case_promotion_missing_command_count(case: Any) -> int:
    value = getattr(case, "promotion_command_plan", None)
    if value is None and isinstance(case, dict):
        value = case.get("promotion_command_plan")
    command_plan = value if isinstance(value, list) else []
    return sum(
        1
        for item in command_plan
        if isinstance(item, dict) and item.get("missing")
    )


def _case_promotion_command_plan_summary(cases_report: Any) -> dict[str, Any]:
    summary = getattr(cases_report, "promotion_command_plan_summary", None)
    if isinstance(summary, dict):
        return dict(summary)

    cases = getattr(cases_report, "cases", [])
    candidate_count = 0
    command_count = 0
    missing_tasks: list[dict[str, str]] = []
    missing_cases: list[dict[str, Any]] = []
    task_missing_counts = {field_name: 0 for field_name in CANDIDATE_PROMOTION_COMMAND_PLAN_FIELDS}

    for case in cases:
        if getattr(case, "status", None) != "candidate":
            continue
        candidate_count += 1
        commands = _case_string_list(case, "commands")
        command_plan = getattr(case, "promotion_command_plan", None)
        if not isinstance(command_plan, list) or not command_plan:
            command_plan = _candidate_promotion_command_plan(
                commands=commands,
                candidate_package_validation_command=_default_candidate_package_validation_command(),
            )
        command_count += len(command_plan)
        case_missing_tasks: list[str] = []
        for item in command_plan:
            if not isinstance(item, dict) or not item.get("missing"):
                continue
            task = str(item.get("task") or "")
            source = str(item.get("source") or "")
            case_missing_tasks.append(task)
            if task in task_missing_counts:
                task_missing_counts[task] += 1
            missing_tasks.append({"case_id": str(getattr(case, "id", "")), "task": task, "source": source})
        if case_missing_tasks:
            missing_cases.append(
                {
                    "case_id": str(getattr(case, "id", "")),
                    "missing_task_count": len(case_missing_tasks),
                    "missing_tasks": case_missing_tasks,
                }
            )

    return {
        "candidate_count": candidate_count,
        "command_count": command_count,
        "expected_command_count": candidate_count * len(CANDIDATE_PROMOTION_COMMAND_PLAN_FIELDS),
        "missing_command_count": len(missing_tasks),
        "ready_candidate_count": candidate_count - len(missing_cases),
        "all_declared": not missing_tasks,
        "task_missing_counts": task_missing_counts,
        "missing_tasks": missing_tasks,
        "missing_cases": missing_cases,
        "primary_missing_task": missing_tasks[0] if missing_tasks else None,
    }


def _candidate_promotions(readiness: Any) -> list[CandidatePromotion]:
    promotions: list[CandidatePromotion] = []
    candidate_cases = [
        case
        for case in readiness.cases.cases
        if _case_string_value(case, "status") == "candidate"
    ]
    ranked_candidate_cases = [
        case
        for _, case in sorted(
            enumerate(candidate_cases),
            key=lambda item: _case_promotion_priority_key(item[1], item[0]),
        )
    ]
    for priority_rank, case in enumerate(ranked_candidate_cases, start=1):
        promotion = getattr(case, "promotion", None)
        if promotion is None:
            continue
        commands = _case_string_list(case, "commands")
        offline_commands = _case_string_list(case, "offline_commands")
        candidate_package_validation_command = _default_candidate_package_validation_command()
        promotion_command_plan = _candidate_promotion_command_plan(
            commands=commands,
            candidate_package_validation_command=candidate_package_validation_command,
        )
        promotion_evidence = _case_dict_value(case, "promotion_evidence")
        evidence_bundle_primary_next_task = _candidate_promotion_primary_task(promotion_evidence)
        priority_reason = _case_promotion_priority_reason(case, priority_rank)
        if evidence_bundle_primary_next_task:
            evidence_bundle_primary_next_task = {
                **evidence_bundle_primary_next_task,
                "priority_rank": priority_rank,
                "priority_reason": priority_reason,
            }
        evidence_bundle_primary_next_task_runbook = _candidate_primary_task_runbook(
            evidence_bundle_primary_next_task,
            promotion_command_plan,
        )
        promotions.append(
            CandidatePromotion(
                case_id=str(case.id),
                issue_title=_candidate_issue_title(str(case.id)),
                issue_labels=["case-proposal", "good first issue"],
                target_url=_case_string_value(case, "target_url"),
                commands=commands,
                offline_commands=offline_commands,
                adapter_package=_promotion_value(promotion, "adapter_package"),
                metadata_validation=_promotion_value(promotion, "metadata_validation"),
                online_smoke=_promotion_value(promotion, "online_smoke"),
                priority_rank=priority_rank,
                priority_reason=priority_reason,
                promotion_evidence=promotion_evidence,
                promotion_evidence_primary_task=evidence_bundle_primary_next_task,
                evidence_bundle_primary_next_task=evidence_bundle_primary_next_task,
                evidence_bundle_primary_next_task_runbook=(
                    evidence_bundle_primary_next_task_runbook
                ),
                candidate_package_validation_command=candidate_package_validation_command,
                promotion_command_plan=promotion_command_plan,
                llm_live_preflight_command=LLM_LIVE_PREFLIGHT_COMMAND,
                llm_live_preflight_blocker_note=LLM_LIVE_PREFLIGHT_BLOCKER_NOTE,
                llm_live_preflight_evidence_fields=list(
                    LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS
                ),
                evidence_bundle_command=_candidate_evidence_bundle_command(str(case.id)),
                evidence_bundle_json_command=_candidate_evidence_bundle_json_command(str(case.id)),
                issue_body=_candidate_issue_body(
                    case_id=str(case.id),
                    target_url=_case_string_value(case, "target_url"),
                    commands=commands,
                    offline_commands=offline_commands,
                    promotion_command_plan=promotion_command_plan,
                    adapter_package=_promotion_value(promotion, "adapter_package"),
                    metadata_validation=_promotion_value(promotion, "metadata_validation"),
                    online_smoke=_promotion_value(promotion, "online_smoke"),
                    promotion_evidence=promotion_evidence,
                    primary_task=evidence_bundle_primary_next_task,
                    primary_runbook=evidence_bundle_primary_next_task_runbook,
                ),
            )
        )
    return promotions


def _candidate_promotion_primary_task(evidence: dict[str, Any]) -> dict[str, Any]:
    incomplete_tasks: list[dict[str, Any]] = []
    for field_name in CANDIDATE_PROMOTION_FIELDS:
        task = evidence.get(field_name)
        task = task if isinstance(task, dict) else {}
        status = str(task.get("status") or "pending")
        evidence_value = task.get("evidence") or ""
        complete = status == "complete" and bool(evidence_value)
        if complete:
            continue
        incomplete_tasks.append(
            {
                "task": field_name,
                "status": status,
                "evidence": evidence_value,
                "next_action": str(task.get("next_action") or ""),
                "acceptance_criteria": CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA[field_name],
            }
        )

    pending = [task for task in incomplete_tasks if task["status"] == "pending"]
    blocked = [task for task in incomplete_tasks if task["status"] == "blocked"]
    primary = pending[0] if pending else (blocked[0] if blocked else (incomplete_tasks[0] if incomplete_tasks else {}))
    return dict(primary)


def _candidate_evidence_bundle_command(case_id: str) -> str:
    return f"cliany-site cases --case-id {case_id} --evidence-bundle"


def _candidate_evidence_bundle_json_command(case_id: str) -> str:
    return f"{_candidate_evidence_bundle_command(case_id)} --json"


def _candidate_issue_title(case_id: str) -> str:
    return f"Promote candidate case `{case_id}` toward active"


def _candidate_promotion_command_plan(
    *,
    commands: list[str],
    candidate_package_validation_command: str,
) -> list[dict[str, Any]]:
    explore_commands = [command for command in commands if command.startswith("cliany-site explore ")]
    adapter_commands = [
        command
        for command in commands
        if command.startswith("cliany-site ") and not command.startswith("cliany-site explore ")
    ]
    plan = [
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
            "command": candidate_package_validation_command,
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


def _candidate_primary_task_runbook(
    primary_task: dict[str, Any] | None,
    promotion_command_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    primary_task = primary_task if isinstance(primary_task, dict) else {}
    task_name = str(primary_task.get("task") or "")
    if not task_name:
        return []
    command_plan_item = next(
        (
            item
            for item in promotion_command_plan
            if isinstance(item, dict) and item.get("task") == task_name
        ),
        {},
    )
    command = str(command_plan_item.get("command") or "")
    command_missing = bool(command_plan_item.get("missing", not command))
    handoff = str(primary_task.get("next_action") or "")
    acceptance = CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA.get(task_name, "")
    runbook: list[dict[str, Any]] = []
    if task_name == "adapter_package":
        runbook.append(
            {
                "step": "llm_live_preflight",
                "command": LLM_LIVE_PREFLIGHT_COMMAND,
                "required": True,
                "handoff": LLM_LIVE_PREFLIGHT_BLOCKER_NOTE,
            }
        )
    runbook.append(
        {
            "step": task_name,
            "command": command,
            "required": not command_missing,
            "handoff": handoff,
        }
    )
    runbook.append(
        {
            "step": "acceptance",
            "command": "",
            "required": True,
            "handoff": acceptance,
        }
    )
    return runbook


def _primary_runbook_from_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    runbook = summary.get("primary_next_task_runbook")
    if not isinstance(runbook, list):
        return []
    return [dict(step) for step in runbook if isinstance(step, dict)]


def _runbook_steps(runbook: list[dict[str, Any]]) -> list[str]:
    return [str(step.get("step") or "") for step in runbook if step.get("step")]


def _runbook_first_step(runbook: list[dict[str, Any]]) -> dict[str, Any]:
    for step in runbook:
        if isinstance(step, dict):
            return step
    return {}


def _runbook_first_step_name(runbook: list[dict[str, Any]]) -> str | None:
    first_step = _runbook_first_step(runbook)
    step_name = first_step.get("step")
    return str(step_name) if step_name else None


def _runbook_first_command(runbook: list[dict[str, Any]]) -> str | None:
    first_step = _runbook_first_step(runbook)
    command = first_step.get("command")
    return str(command) if command else None


def _candidate_primary_runbook_markdown(runbook: list[dict[str, Any]]) -> list[str]:
    if not runbook:
        return []
    lines = ["## Primary Runbook"]
    for step in runbook:
        if not isinstance(step, dict):
            continue
        command = step.get("command") or "No command."
        lines.extend(
            [
                f"- `{step.get('step')}`: `{command}`",
                f"  - required: `{str(bool(step.get('required'))).lower()}`",
            ]
        )
        if step.get("handoff"):
            lines.append(f"  - handoff: {step['handoff']}")
    return lines


def _candidate_primary_runbook_summary(runbook: list[dict[str, Any]]) -> str:
    steps = [
        str(step.get("step") or "")
        for step in runbook
        if isinstance(step, dict) and step.get("step")
    ]
    return " -> ".join(steps) if steps else "Not declared."


def _candidate_issue_body(
    *,
    case_id: str,
    target_url: str,
    commands: list[str],
    offline_commands: list[str],
    promotion_command_plan: list[dict[str, Any]],
    adapter_package: str,
    metadata_validation: str,
    online_smoke: str,
    promotion_evidence: dict[str, Any],
    primary_task: dict[str, Any] | None = None,
    primary_runbook: list[dict[str, Any]] | None = None,
) -> str:
    command_lines = [f"  - `{command}`" for command in commands] or ["  - Not declared."]
    offline_command_lines = [f"  - `{command}`" for command in offline_commands] or ["  - Not declared."]
    promotion_command_lines = [
        f"- `{item['task']}`: `{item['command'] or 'Not declared.'}`"
        for item in promotion_command_plan
    ] or ["- No promotion command plan declared."]
    task_descriptions = {
        "adapter_package": adapter_package,
        "metadata_validation": metadata_validation,
        "online_smoke": online_smoke,
    }
    primary_task = dict(primary_task or _candidate_promotion_primary_task(promotion_evidence))
    if primary_task:
        primary_evidence = primary_task.get("evidence") or "Not attached yet."
        primary_next_action = primary_task.get("next_action") or "Not declared."
        primary_acceptance = CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA.get(
            str(primary_task.get("task") or ""), ""
        )
        primary_priority_lines: list[str] = []
        if primary_task.get("priority_rank") is not None:
            primary_priority_lines.append(f"- Priority rank: `{primary_task['priority_rank']}`")
        if primary_task.get("priority_reason"):
            primary_priority_lines.append(
                f"- Priority reason: {primary_task['priority_reason']}"
            )
        primary_task_lines = [
            f"- Task: `{primary_task['task']}`",
            f"- Status: `{primary_task['status']}`",
            *primary_priority_lines,
            f"- Current evidence: {primary_evidence}",
            f"- Next action: {primary_next_action}",
            f"- Acceptance criteria: {primary_acceptance}",
        ]
    else:
        primary_task_lines = ["- All promotion tasks already have complete evidence."]
    primary_runbook_lines = _candidate_primary_runbook_markdown(
        list(primary_runbook or _candidate_primary_task_runbook(primary_task, promotion_command_plan))
    )
    primary_runbook_section = [*primary_runbook_lines, ""] if primary_runbook_lines else []

    task_lines: list[str] = []
    for task_name in CANDIDATE_PROMOTION_FIELDS:
        task = promotion_evidence.get(task_name)
        task = task if isinstance(task, dict) else {}
        status = task.get("status") or "unknown"
        evidence_value = task.get("evidence")
        evidence = evidence_value or "Not attached yet."
        next_action = task.get("next_action") or "Not declared."
        checkbox = "x" if status == "complete" and bool(evidence_value) else " "
        task_lines.extend(
            [
                f"- [{checkbox}] `{task_name}`: {task_descriptions[task_name]}",
                f"  - Current status: `{status}`",
                f"  - Current evidence: {evidence}",
                f"  - Next action: {next_action}",
                f"  - Acceptance criteria: {CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA[task_name]}",
            ]
        )
    acceptance_lines = [
        f"- `{task_name}`: {CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA[task_name]}"
        for task_name in CANDIDATE_PROMOTION_FIELDS
    ]
    return "\n".join(
        [
            f"## Scope: promote candidate case `{case_id}`",
            "",
            "Move this candidate case one step closer to `active` without changing its status early.",
            "",
            "## Primary Evidence Task",
            *primary_task_lines,
            "",
            *primary_runbook_section,
            "## Reproduction Context",
            f"- Target URL: {target_url or 'Not declared.'}",
            "- Candidate commands:",
            *command_lines,
            "- Offline validation commands:",
            *offline_command_lines,
            "",
            "## Promotion Command Plan",
            *promotion_command_lines,
            "",
            "## LLM Preflight Gate",
            f"- Command: `{LLM_LIVE_PREFLIGHT_COMMAND}`",
            f"- Blocker handling: {LLM_LIVE_PREFLIGHT_BLOCKER_NOTE}",
            "",
            "## LLM Preflight Evidence Fields",
            *(f"- `{field}`" for field in LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS),
            "",
            "## Acceptance Criteria",
            *acceptance_lines,
            "",
            "## Tasks",
            *task_lines,
            "",
            "## Evidence Bundle",
            f"- Human: `{_candidate_evidence_bundle_command(case_id)}`",
            f"- JSON: `{_candidate_evidence_bundle_json_command(case_id)}`",
            "- Attach or paste the JSON output in the issue once evidence changes.",
            "",
            "## Validation Evidence",
            "- Attach the generated `.cliany-adapter.tar.gz` path or release asset name.",
            (
                "- Candidate package validation command: "
                f"`{_default_candidate_package_validation_command()}`"
            ),
            "- Paste the local `scripts/validate_cases.py --packages-dir` result.",
            "- Paste the read-only JSON envelope summary with `data.quality.ok=true` and `row_count>0`.",
            "",
            "## Non-goals",
            "- Do not mark the case `active` until all three promotion tasks are complete.",
            "- Do not require real LLM keys or write runtime state into the repository.",
        ]
    )


def build_plan(
    root: Path = ROOT,
    *,
    today: date | None = None,
    target_version: str | None = None,
    min_commit_days: int = 3,
    max_daily_releases: int = 3,
    remote_check: bool = False,
    remote_name: str = "origin",
    min_case_assets: int = 8,
    packages_dir: Path | None = None,
    require_packages: bool = False,
    readiness_report: Any | None = None,
    publication_report: Any | None = None,
) -> IterationPlan:
    current_version = _project_version(root)
    expected_target = target_version or _next_patch_version(current_version)
    readiness = readiness_report or build_readiness_report(
        root,
        today=today or date.today(),
        min_commit_days=min_commit_days,
        max_daily_releases=max_daily_releases,
        remote_check=remote_check,
        remote_name=remote_name,
        min_case_assets=min_case_assets,
        target_version=expected_target,
        packages_dir=packages_dir,
        require_packages=require_packages,
    )
    publication = publication_report or build_publication_report(
        root,
        remote_check=remote_check,
        remote=remote_name,
    )
    theme, release_slice = _recommended_slice(readiness, publication)
    candidate_promotions = _candidate_promotions(readiness)
    case_promotion_evidence_summary = _case_promotion_evidence_summary(readiness.cases)
    case_promotion_command_plan_summary = _case_promotion_command_plan_summary(readiness.cases)
    publication_blockers = _publication_blockers(publication)
    publication_next_actions = _publication_next_actions(publication)
    publication_publish_commands = _publication_publish_commands(publication)
    publication_tag_publish_decision = _publication_tag_publish_decision(
        publication,
        str(readiness.target_version),
        readiness_blockers=list(getattr(readiness, "blockers", []) or []),
    )
    next_actions = _next_action_lines(readiness, publication)
    standard_release_flow = _standard_release_flow(
        readiness,
        publication,
        next_actions=next_actions,
        publication_publish_commands=publication_publish_commands,
        publication_tag_publish_decision=publication_tag_publish_decision,
        remote_check=remote_check,
        remote_name=remote_name,
    )
    commit_cadence = _commit_cadence(readiness)
    candidate_cases = [
        str(case.id)
        for case in readiness.cases.cases
        if case.status == "candidate"
    ]
    blockers = [*readiness.blockers]
    if not _latest_release_visible(publication):
        blockers.append("latest local release is not published")

    package_args = _package_gate_args(packages_dir=packages_dir, require_packages=require_packages)
    remote_args = _remote_audit_args(remote_check=remote_check, remote_name=remote_name)
    validation_commands = [
        f"python scripts/plan_next_iteration.py --target-version {readiness.target_version}"
        f"{package_args}{remote_args} --json",
        f"python scripts/release_readiness.py --target-version {readiness.target_version}"
        f"{package_args}{remote_args} --json",
        _publication_audit_validation_command(remote_check=remote_check, remote_name=remote_name),
        "python scripts/validate_cases.py --strict",
    ]
    candidate_package_validation_command = _candidate_package_validation_command(packages_dir)
    if candidate_package_validation_command is not None:
        validation_commands.append(candidate_package_validation_command)
    plan_report_command = (
        f"python scripts/plan_next_iteration.py --target-version {readiness.target_version}"
        f"{package_args}{remote_args} --report /tmp/cliany-next-iteration.md"
    )
    issue_artifacts_command = (
        f"python scripts/plan_next_iteration.py --target-version {readiness.target_version}"
        f"{package_args}{remote_args} --issues-dir /tmp/cliany-candidate-issues"
    )
    publication_publish_script_command = _publication_publish_script_command(
        remote_check=remote_check,
        remote_name=remote_name,
    )
    return IterationPlan(
        current_version=current_version,
        target_version=str(readiness.target_version),
        recommended_theme=theme,
        recommended_slice=release_slice,
        readiness_ok=bool(readiness.ok),
        publication_ok=bool(publication.ok),
        commit_days=f"{readiness.cadence.commit_day_count}/{readiness.cadence.min_commit_days}",
        commit_cadence=commit_cadence,
        case_assets=(
            f"active {readiness.cases.active}, candidate {readiness.cases.candidate}, "
            f"known_gap {readiness.cases.known_gap}, total {readiness.cases.total}/{readiness.min_case_assets}"
        ),
        candidate_cases=candidate_cases,
        candidate_promotions=candidate_promotions,
        case_promotion_evidence_summary=case_promotion_evidence_summary,
        case_promotion_command_plan_summary=case_promotion_command_plan_summary,
        standard_release_flow=standard_release_flow,
        blockers=blockers,
        next_actions=next_actions,
        validation_commands=validation_commands,
        candidate_issue_gate=_candidate_issue_gate(readiness, publication),
        publication_visibility=_publication_visibility(publication),
        publication_tag_publish_decision=publication_tag_publish_decision,
        publication_blockers=publication_blockers,
        publication_next_action_count=len(publication_next_actions),
        publication_next_actions=publication_next_actions,
        publication_publish_command_count=len(publication_publish_commands),
        publication_publish_commands=publication_publish_commands,
        publication_ref_context=_publication_ref_context(publication),
        publication_worktree_clean=_publication_worktree_clean(publication),
        publication_worktree_status=_publication_worktree_status(publication),
        publication_publish_script_path=PUBLICATION_PUBLISH_SCRIPT_PATH,
        publication_publish_script_path_sha256=_stable_json_sha256(PUBLICATION_PUBLISH_SCRIPT_PATH),
        publication_publish_script_command=publication_publish_script_command,
        publication_publish_script_command_sha256=_stable_json_sha256(
            publication_publish_script_command
        ),
        plan_report_command=plan_report_command,
        issue_artifacts_command=issue_artifacts_command,
        release_draft_path=f"docs/releases/v{readiness.target_version}-draft.md",
        release_draft_issues=_release_draft_issues(readiness),
    )


def _print_text(plan: IterationPlan) -> None:
    standard_release_flow_steps = _standard_release_flow_steps(plan.standard_release_flow)
    standard_release_flow_step_names = _standard_release_flow_step_names(
        plan.standard_release_flow
    )
    standard_release_flow_step_boundary = _standard_release_flow_step_boundary(
        plan.standard_release_flow
    )
    standard_release_flow_step_status_counts = _standard_release_flow_step_status_counts(
        plan.standard_release_flow
    )
    website_deploy_command = _standard_release_flow_website_deploy_command(
        plan.standard_release_flow
    )
    print("=== cliany-site next iteration plan ===")
    print(f"current_version: {plan.current_version}")
    print(f"target_version: {plan.target_version}")
    print(f"recommended_theme: {plan.recommended_theme}")
    print(f"recommended_slice: {plan.recommended_slice}")
    print(f"readiness_ok: {plan.readiness_ok}")
    print(f"publication_ok: {plan.publication_ok}")
    print(f"commit_days: {plan.commit_days}")
    print("commit_cadence:")
    for key, value in plan.commit_cadence.items():
        _print_text_item(key, value)
    print(f"case_assets: {plan.case_assets}")
    print(f"release_draft_path: {plan.release_draft_path}")
    if plan.release_draft_issues:
        print("release_draft_issues:")
        for issue in plan.release_draft_issues:
            print(f"- {issue}")
    if plan.candidate_cases:
        print("candidate_cases:")
        for case_id in plan.candidate_cases:
            print(f"- {case_id}")
    print(
        "case_promotion_evidence_summary_sha256: "
        f"{_stable_json_sha256(plan.case_promotion_evidence_summary)}"
    )
    print("case_promotion_evidence_summary:")
    for key, value in plan.case_promotion_evidence_summary.items():
        _print_text_item(key, value)
    print(
        "case_promotion_command_plan_summary_sha256: "
        f"{_stable_json_sha256(plan.case_promotion_command_plan_summary)}"
    )
    print("case_promotion_command_plan_summary:")
    for key, value in plan.case_promotion_command_plan_summary.items():
        _print_text_item(key, value)
    print(
        "standard_release_flow: "
        f"status={plan.standard_release_flow.get('status')}, "
        f"target_tag={plan.standard_release_flow.get('target_tag')}, "
        f"commands={plan.standard_release_flow.get('command_count')}"
    )
    print(f"standard_release_flow_sha256: {_stable_json_sha256(plan.standard_release_flow)}")
    print(
        "standard_release_flow_primary_next_action: "
        f"{plan.standard_release_flow.get('primary_next_action')}"
    )
    print(
        "standard_release_flow_commands_sha256: "
        f"{plan.standard_release_flow.get('commands_sha256')}"
    )
    print(f"standard_release_flow_step_count: {len(standard_release_flow_steps)}")
    print(
        "standard_release_flow_step_names: "
        f"{', '.join(standard_release_flow_step_names)}"
    )
    print(
        "standard_release_flow_step_names_sha256: "
        f"{_stable_json_sha256(standard_release_flow_step_names)}"
    )
    print(
        "standard_release_flow_steps_sha256: "
        f"{_stable_json_sha256(standard_release_flow_steps)}"
    )
    print(
        "standard_release_flow_first_step_name: "
        f"{standard_release_flow_step_boundary['first_step_name']}"
    )
    print(
        "standard_release_flow_last_step_name: "
        f"{standard_release_flow_step_boundary['last_step_name']}"
    )
    print(
        "standard_release_flow_step_boundary_sha256: "
        f"{_stable_json_sha256(standard_release_flow_step_boundary)}"
    )
    print(
        "standard_release_flow_step_status_counts: "
        f"{json.dumps(standard_release_flow_step_status_counts, ensure_ascii=False)}"
    )
    print(
        "standard_release_flow_step_status_counts_sha256: "
        f"{_stable_json_sha256(standard_release_flow_step_status_counts)}"
    )
    print(
        "standard_release_flow_primary_blocked_step_name: "
        f"{_standard_release_flow_primary_step_name_with_status_prefix(plan.standard_release_flow, 'blocked')}"
    )
    print(
        "standard_release_flow_primary_pending_step_name: "
        f"{_standard_release_flow_primary_step_name_with_status_prefix(plan.standard_release_flow, 'pending')}"
    )
    print(f"standard_release_flow_has_website_deploy: {website_deploy_command is not None}")
    print(f"standard_release_flow_website_deploy_command: {website_deploy_command}")
    print(
        "standard_release_flow_website_deploy_command_sha256: "
        f"{_stable_json_sha256(website_deploy_command) if website_deploy_command else None}"
    )
    primary_next_task = plan.case_promotion_evidence_summary.get("primary_next_task")
    if isinstance(primary_next_task, dict) and primary_next_task:
        print("case_promotion_evidence_primary_next_task:")
        for key, value in primary_next_task.items():
            print(f"  {key}: {value}")
    primary_next_action = plan.case_promotion_evidence_summary.get("primary_next_action")
    if primary_next_action:
        print(f"case_promotion_evidence_primary_next_action: {primary_next_action}")
    primary_runbook = _primary_runbook_from_summary(plan.case_promotion_evidence_summary)
    primary_runbook_steps = _runbook_steps(primary_runbook)
    if primary_runbook_steps:
        print(
            "case_promotion_evidence_primary_runbook_steps: "
            f"{' -> '.join(primary_runbook_steps)}"
        )
        print(
            "case_promotion_evidence_primary_runbook_steps_sha256: "
            f"{_stable_json_sha256(primary_runbook_steps)}"
        )
        primary_runbook_first_command = _runbook_first_command(primary_runbook)
        primary_runbook_first_command_sha256 = (
            _stable_json_sha256(primary_runbook_first_command)
            if primary_runbook_first_command
            else None
        )
        print(
            "case_promotion_evidence_primary_runbook_first_step: "
            f"{_runbook_first_step_name(primary_runbook)}"
        )
        print(
            "case_promotion_evidence_primary_runbook_first_command: "
            f"{primary_runbook_first_command}"
        )
        print(
            "case_promotion_evidence_primary_runbook_first_command_sha256: "
            f"{primary_runbook_first_command_sha256}"
        )
    if plan.candidate_promotions:
        print("candidate_promotions:")
        for promotion in plan.candidate_promotions:
            print(f"- {promotion.case_id}")
            print(f"  issue_title: {promotion.issue_title}")
            print(f"  issue_labels: {', '.join(promotion.issue_labels)}")
            print(f"  adapter_package: {promotion.adapter_package}")
            print(f"  metadata_validation: {promotion.metadata_validation}")
            print(f"  online_smoke: {promotion.online_smoke}")
            print("  evidence_bundle_primary_next_task:")
            for key, value in promotion.evidence_bundle_primary_next_task.items():
                print(f"    {key}: {value}")
            print("  issue_body:")
            for line in promotion.issue_body.splitlines():
                print(f"    {line}")
    if plan.blockers:
        print("blockers:")
        for blocker in plan.blockers:
            print(f"- {blocker}")
    print(f"next_action_count: {len(plan.next_actions)}")
    print(f"next_actions_sha256: {_stable_json_sha256(plan.next_actions)}")
    if plan.next_actions:
        print(f"primary_next_action: {plan.next_actions[0]}")
    print("next_actions:")
    for action in plan.next_actions:
        print(f"- {action}")
    print("validation_commands:")
    for command in plan.validation_commands:
        print(f"- {command}")
    print("candidate_issue_gate:")
    for key, value in plan.candidate_issue_gate.items():
        _print_text_item(key, value)
    print("publication_visibility:")
    for key, value in plan.publication_visibility.items():
        print(f"- {key}: {value}")
    print("publication_tag_publish_decision:")
    for key, value in plan.publication_tag_publish_decision.items():
        print(f"- {key}: {value}")
    print(f"publication_blocker_count: {len(plan.publication_blockers)}")
    print(f"publication_blockers_sha256: {_stable_json_sha256(plan.publication_blockers)}")
    if plan.publication_blockers:
        print(f"publication_primary_blocker: {plan.publication_blockers[0]}")
        print("publication_blockers:")
        for blocker in plan.publication_blockers:
            print(f"- {blocker}")
    print(f"publication_next_action_count: {plan.publication_next_action_count}")
    print(f"publication_next_actions_sha256: {_stable_json_sha256(plan.publication_next_actions)}")
    if plan.publication_next_actions:
        print(f"publication_primary_next_action: {plan.publication_next_actions[0]}")
    if plan.publication_next_actions:
        print("publication_next_actions:")
        for action in plan.publication_next_actions:
            print(f"- {action}")
    print(f"publication_publish_command_count: {plan.publication_publish_command_count}")
    print(
        "publication_publish_commands_sha256: "
        f"{_stable_json_sha256(plan.publication_publish_commands)}"
    )
    if plan.publication_publish_commands:
        print(f"publication_primary_publish_command: {plan.publication_publish_commands[0]}")
    if plan.publication_publish_commands:
        print("publication_publish_commands:")
        for command in plan.publication_publish_commands:
            print(f"- {command}")
    print("publication_ref_context:")
    for key, value in plan.publication_ref_context.items():
        print(f"- {key}: {value}")
    print(f"publication_worktree_clean: {str(plan.publication_worktree_clean).lower()}")
    if plan.publication_worktree_status:
        print("publication_worktree_status:")
        for line in plan.publication_worktree_status:
            print(f"- {line}")
    print(f"publication_publish_script_path: {plan.publication_publish_script_path}")
    print(f"publication_publish_script_path_sha256: {plan.publication_publish_script_path_sha256}")
    print(f"publication_publish_script_command: {plan.publication_publish_script_command}")
    print(
        "publication_publish_script_command_sha256: "
        f"{plan.publication_publish_script_command_sha256}"
    )
    print(f"plan_report_command: {plan.plan_report_command}")
    print(f"issue_artifacts_command: {plan.issue_artifacts_command}")


def _print_text_item(key: str, value: object) -> None:
    if isinstance(value, list):
        print(f"- {key}:")
        for item in value:
            print(f"  - {item}")
        return
    if isinstance(value, dict):
        print(f"- {key}:")
        for nested_key, nested_value in value.items():
            print(f"  - {nested_key}: {_format_context_value(nested_value)}")
        return
    print(f"- {key}: {value}")


def _render_markdown(plan: IterationPlan) -> str:
    candidate_cases = ", ".join(f"`{case_id}`" for case_id in plan.candidate_cases) or "-"
    primary_candidate_task = plan.case_promotion_evidence_summary.get("primary_next_task")
    if isinstance(primary_candidate_task, dict) and primary_candidate_task:
        primary_candidate_task_value = json.dumps(
            primary_candidate_task,
            ensure_ascii=False,
            sort_keys=True,
        )
    else:
        primary_candidate_task_value = "(none)"
    primary_candidate_action = _format_context_value(
        plan.case_promotion_evidence_summary.get("primary_next_action")
    )
    primary_runbook = _primary_runbook_from_summary(plan.case_promotion_evidence_summary)
    primary_runbook_steps = _runbook_steps(primary_runbook)
    primary_runbook_first_step = _format_context_value(
        _runbook_first_step_name(primary_runbook)
    )
    primary_runbook_first_command = _runbook_first_command(primary_runbook)
    primary_runbook_first_command_sha256 = (
        _stable_json_sha256(primary_runbook_first_command)
        if primary_runbook_first_command
        else None
    )
    primary_runbook_first_command_text = _format_context_value(primary_runbook_first_command)
    primary_runbook_first_command_sha256_text = _format_context_value(
        primary_runbook_first_command_sha256
    )
    primary_publication_action = _format_context_value(
        plan.publication_next_actions[0] if plan.publication_next_actions else None
    )
    primary_publication_blocker = _format_context_value(
        plan.publication_blockers[0] if plan.publication_blockers else None
    )
    primary_publication_command = _format_context_value(
        plan.publication_publish_commands[0] if plan.publication_publish_commands else None
    )
    standard_release_flow_primary_action = _format_context_value(
        plan.standard_release_flow.get("primary_next_action")
    )
    standard_release_flow_steps = _standard_release_flow_steps(plan.standard_release_flow)
    standard_release_flow_step_names = _standard_release_flow_step_names(
        plan.standard_release_flow
    )
    standard_release_flow_step_boundary = _standard_release_flow_step_boundary(
        plan.standard_release_flow
    )
    standard_release_flow_step_status_counts = _standard_release_flow_step_status_counts(
        plan.standard_release_flow
    )
    standard_release_flow_step_status_counts_json = json.dumps(
        standard_release_flow_step_status_counts,
        ensure_ascii=False,
    )
    standard_release_flow_first_step_name = _format_context_value(
        standard_release_flow_step_boundary["first_step_name"]
    )
    standard_release_flow_last_step_name = _format_context_value(
        standard_release_flow_step_boundary["last_step_name"]
    )
    standard_release_flow_primary_blocked_step_name = _format_context_value(
        _standard_release_flow_primary_step_name_with_status_prefix(
            plan.standard_release_flow, "blocked"
        )
    )
    standard_release_flow_primary_pending_step_name = _format_context_value(
        _standard_release_flow_primary_step_name_with_status_prefix(
            plan.standard_release_flow, "pending"
        )
    )
    standard_release_flow_website_deploy_command = (
        _standard_release_flow_website_deploy_command(plan.standard_release_flow)
    )
    standard_release_flow_website_deploy_command_sha256 = (
        _stable_json_sha256(standard_release_flow_website_deploy_command)
        if standard_release_flow_website_deploy_command
        else None
    )
    standard_release_flow_website_deploy_command_text = _format_context_value(
        standard_release_flow_website_deploy_command
    )
    standard_release_flow_website_deploy_command_sha256_text = _format_context_value(
        standard_release_flow_website_deploy_command_sha256
    )
    command_plan_all_declared = str(
        bool(plan.case_promotion_command_plan_summary.get("all_declared"))
    ).lower()
    command_plan_missing_count = plan.case_promotion_command_plan_summary.get("missing_command_count")
    primary_next_action = _summary_inline_code(plan.next_actions[0] if plan.next_actions else None)
    blockers = "\n".join(f"- {blocker}" for blocker in plan.blockers) or "- None."
    next_actions = "\n".join(f"- {action}" for action in plan.next_actions)
    validation = "\n".join(f"- `{command}`" for command in plan.validation_commands)
    publication_visibility = _publication_visibility_markdown(plan.publication_visibility)
    tag_publish_decision = _publication_tag_publish_decision_markdown(
        plan.publication_tag_publish_decision
    )
    candidate_issue_gate = _candidate_issue_gate_markdown(plan.candidate_issue_gate)
    publication_blockers = _publication_blockers_markdown(plan.publication_blockers)
    publication_actions = _publication_next_actions_markdown(plan.publication_next_actions)
    publication_refs = _publication_ref_context_markdown(plan.publication_ref_context)
    publication_worktree = _publication_worktree_markdown(
        plan.publication_worktree_clean,
        plan.publication_worktree_status,
    )
    publication_commands = _publication_commands_markdown(plan.publication_publish_commands)
    publication_script = _publication_script_markdown(
        plan.publication_publish_script_path,
        plan.publication_publish_script_command,
    )
    standard_release_flow = _standard_release_flow_markdown(plan.standard_release_flow)
    case_promotion_evidence = _case_promotion_evidence_markdown(plan.case_promotion_evidence_summary)
    case_promotion_command_plan = _case_promotion_command_plan_markdown(
        plan.case_promotion_command_plan_summary
    )
    promotion_lines = _candidate_promotion_markdown(plan.candidate_promotions)
    release_draft_issues = _release_draft_issues_markdown(plan.release_draft_issues)
    return f"""# cliany-site Next Iteration Plan

| Metric | Value |
|--------|-------|
| current_version | `{plan.current_version}` |
| target_version | `{plan.target_version}` |
| recommended_theme | {plan.recommended_theme} |
| readiness_ok | `{str(plan.readiness_ok).lower()}` |
| publication_ok | `{str(plan.publication_ok).lower()}` |
| publication_blocker_count | `{len(plan.publication_blockers)}` |
| publication_blockers_sha256 | `{_stable_json_sha256(plan.publication_blockers)}` |
| publication_primary_blocker | `{primary_publication_blocker}` |
| publication_next_action_count | `{plan.publication_next_action_count}` |
| publication_next_actions_sha256 | `{_stable_json_sha256(plan.publication_next_actions)}` |
| publication_primary_next_action | `{primary_publication_action}` |
| publication_publish_command_count | `{plan.publication_publish_command_count}` |
| publication_publish_commands_sha256 | `{_stable_json_sha256(plan.publication_publish_commands)}` |
| publication_primary_publish_command | `{primary_publication_command}` |
| publication_publish_script_path | `{plan.publication_publish_script_path}` |
| publication_publish_script_path_sha256 | `{plan.publication_publish_script_path_sha256}` |
| publication_publish_script_command_sha256 | `{plan.publication_publish_script_command_sha256}` |
| standard_release_flow_status | `{plan.standard_release_flow.get("status")}` |
| standard_release_flow_primary_next_action | `{standard_release_flow_primary_action}` |
| standard_release_flow_command_count | `{plan.standard_release_flow.get("command_count")}` |
| standard_release_flow_commands_sha256 | `{plan.standard_release_flow.get("commands_sha256")}` |
| standard_release_flow_step_count | `{len(standard_release_flow_steps)}` |
| standard_release_flow_step_names | `{json.dumps(standard_release_flow_step_names, ensure_ascii=False)}` |
| standard_release_flow_step_names_sha256 | `{_stable_json_sha256(standard_release_flow_step_names)}` |
| standard_release_flow_steps_sha256 | `{_stable_json_sha256(standard_release_flow_steps)}` |
| standard_release_flow_first_step_name | `{standard_release_flow_first_step_name}` |
| standard_release_flow_last_step_name | `{standard_release_flow_last_step_name}` |
| standard_release_flow_step_boundary_sha256 | `{_stable_json_sha256(standard_release_flow_step_boundary)}` |
| standard_release_flow_step_status_counts | `{standard_release_flow_step_status_counts_json}` |
| standard_release_flow_step_status_counts_sha256 | `{_stable_json_sha256(standard_release_flow_step_status_counts)}` |
| standard_release_flow_primary_blocked_step_name | `{standard_release_flow_primary_blocked_step_name}` |
| standard_release_flow_primary_pending_step_name | `{standard_release_flow_primary_pending_step_name}` |
| standard_release_flow_has_website_deploy | `{str(standard_release_flow_website_deploy_command is not None).lower()}` |
| standard_release_flow_website_deploy_command | `{standard_release_flow_website_deploy_command_text}` |
| standard_release_flow_website_deploy_command_sha256 | `{standard_release_flow_website_deploy_command_sha256_text}` |
| standard_release_flow_sha256 | `{_stable_json_sha256(plan.standard_release_flow)}` |
| next_action_count | `{len(plan.next_actions)}` |
| next_actions_sha256 | `{_stable_json_sha256(plan.next_actions)}` |
| primary_next_action | {primary_next_action} |
| commit_days | `{plan.commit_days}` |
| commit_cadence_status | `{plan.commit_cadence.get("status")}` |
| commit_cadence_missing_commit_days | `{plan.commit_cadence.get("missing_commit_days")}` |
| commit_cadence_summary | {plan.commit_cadence.get("summary")} |
| case_assets | {plan.case_assets} |
| candidate_cases | {candidate_cases} |
| case_promotion_evidence_summary_sha256 | `{_stable_json_sha256(plan.case_promotion_evidence_summary)}` |
| case_promotion_command_plan_summary_sha256 | `{_stable_json_sha256(plan.case_promotion_command_plan_summary)}` |
| case_promotion_evidence_primary_next_task | `{primary_candidate_task_value}` |
| case_promotion_evidence_primary_next_action | `{primary_candidate_action}` |
| case_promotion_evidence_primary_runbook_step_count | `{len(primary_runbook_steps)}` |
| case_promotion_evidence_primary_runbook_steps | `{json.dumps(primary_runbook_steps, ensure_ascii=False)}` |
| case_promotion_evidence_primary_runbook_steps_sha256 | `{_stable_json_sha256(primary_runbook_steps)}` |
| case_promotion_evidence_primary_runbook_first_step | `{primary_runbook_first_step}` |
| case_promotion_evidence_primary_runbook_first_command | `{primary_runbook_first_command_text}` |
| case_promotion_evidence_primary_runbook_first_command_sha256 | `{primary_runbook_first_command_sha256_text}` |
| case_promotion_command_plan_all_declared | `{command_plan_all_declared}` |
| case_promotion_command_plan_missing_command_count | `{command_plan_missing_count}` |
| plan_report_command | `{plan.plan_report_command}` |

## Recommended Slice

{plan.recommended_slice}

## Blockers

{blockers}

## Next Actions

{next_actions}

{case_promotion_evidence}

{case_promotion_command_plan}

{promotion_lines}

## Validation Commands

{validation}

{publication_visibility}

{tag_publish_decision}

{candidate_issue_gate}

{publication_blockers}

{publication_actions}

{publication_refs}

{publication_worktree}

{publication_commands}

{publication_script}

{standard_release_flow}

## Release Draft

- `{plan.release_draft_path}`
{release_draft_issues}
"""


def _case_promotion_evidence_markdown(summary: dict[str, Any]) -> str:
    rows = [
        ("candidate_count", summary.get("candidate_count", 0)),
        ("task_count", summary.get("task_count", 0)),
        ("pending_count", summary.get("pending_count", 0)),
        ("blocked_count", summary.get("blocked_count", 0)),
        ("complete_count", summary.get("complete_count", 0)),
        ("primary_next_action", summary.get("primary_next_action") or "-"),
        (
            "primary_next_task_acceptance_criteria",
            summary.get("primary_next_task_acceptance_criteria") or "-",
        ),
    ]
    lines = [
        "## Candidate Promotion Evidence Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    lines.extend(f"| {key} | `{_format_context_value(value)}` |" for key, value in rows)
    lines.extend(
        [
            "",
            "| Case | Task | Status | Evidence | Next Action | Acceptance Criteria |",
            "|------|------|--------|----------|-------------|---------------------|",
        ]
    )
    tasks = [
        *list(summary.get("pending_tasks") or []),
        *list(summary.get("blocked_tasks") or []),
        *list(summary.get("complete_tasks") or []),
    ]
    if not tasks:
        lines.append("| - | - | - | - | - | - |")
        return "\n".join(lines)
    for task in tasks:
        lines.append(
            "| "
            f"`{_format_context_value(task.get('case_id'))}` | "
            f"`{_format_context_value(task.get('task'))}` | "
            f"`{_format_context_value(task.get('status'))}` | "
            f"{_format_context_value(task.get('evidence') or '-')} | "
            f"{_format_context_value(task.get('next_action') or '-')} | "
            f"{_format_context_value(task.get('acceptance_criteria') or '-')} |"
        )
    return "\n".join(lines)


def _case_promotion_command_plan_markdown(summary: dict[str, Any]) -> str:
    rows = [
        ("candidate_count", summary.get("candidate_count", 0)),
        ("command_count", summary.get("command_count", 0)),
        ("expected_command_count", summary.get("expected_command_count", 0)),
        ("missing_command_count", summary.get("missing_command_count", 0)),
        ("ready_candidate_count", summary.get("ready_candidate_count", 0)),
        ("all_declared", str(bool(summary.get("all_declared"))).lower()),
    ]
    lines = [
        "## Candidate Promotion Command Plan Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    lines.extend(f"| {key} | `{_format_context_value(value)}` |" for key, value in rows)
    lines.extend(["", "| Case | Missing Tasks |", "|------|---------------|"])
    missing_cases = list(summary.get("missing_cases") or [])
    if not missing_cases:
        lines.append("| - | - |")
        return "\n".join(lines)
    for case in missing_cases:
        missing_tasks = ", ".join(str(task) for task in case.get("missing_tasks") or [])
        lines.append(
            "| "
            f"`{_format_context_value(case.get('case_id'))}` | "
            f"`{_format_context_value(missing_tasks)}` |"
        )
    return "\n".join(lines)


def _release_draft_issues_markdown(issues: list[str]) -> str:
    if not issues:
        return ""
    issue_lines = "\n".join(f"- {issue}" for issue in issues)
    return f"\n\n### Release Draft Issues\n\n{issue_lines}"


def _publication_next_actions_markdown(actions: list[str]) -> str:
    if not actions:
        return "## Publication Next Actions\n\n- No publication next actions are needed."
    action_lines = "\n".join(f"- {action}" for action in actions)
    return f"""## Publication Next Actions

{action_lines}"""


def _publication_blockers_markdown(blockers: list[str]) -> str:
    if not blockers:
        return "## Publication Blockers\n\n- No publication blockers are present."
    blocker_lines = "\n".join(f"- {blocker}" for blocker in blockers)
    return f"""## Publication Blockers

{blocker_lines}"""


def _publication_tag_publish_decision_markdown(decision: dict[str, Any]) -> str:
    rows = [
        ("status", decision.get("status") or "(unknown)"),
        ("can_push_tag", str(bool(decision.get("can_push_tag", False))).lower()),
        ("latest_tag", _format_context_value(decision.get("latest_tag"))),
        ("tag_points_at_head", _format_context_value(decision.get("tag_points_at_head"))),
        ("tag_published", _format_context_value(decision.get("tag_published"))),
        ("required_action", _format_context_value(decision.get("required_action"))),
        (
            "target_tag_release_gate_status",
            _format_context_value(decision.get("target_tag_release_gate_status")),
        ),
        (
            "target_tag_release_gate_blocker_count",
            _format_context_value(decision.get("target_tag_release_gate_blocker_count")),
        ),
        (
            "target_tag_release_gate_primary_blocker",
            _format_context_value(decision.get("target_tag_release_gate_primary_blocker")),
        ),
        (
            "target_tag_release_gate_blockers_sha256",
            _format_context_value(decision.get("target_tag_release_gate_blockers_sha256")),
        ),
    ]
    lines = ["## Publication Tag Publish Decision", "", "| Field | Value |", "|-------|-------|"]
    lines.extend(f"| {field} | `{value}` |" for field, value in rows)
    return "\n".join(lines)


def _candidate_issue_gate_markdown(gate: dict[str, Any]) -> str:
    status = gate.get("status") or "(unknown)"
    can_create = str(bool(gate.get("can_create_issues", False))).lower()
    review_required = str(bool(gate.get("requires_maintainer_review", True))).lower()
    summary = gate.get("summary") or "Candidate issue gate has not been summarized."
    reason_count = gate.get("reason_code_count")
    reason_hash = gate.get("reason_codes_sha256") or "(unknown)"
    action_count = gate.get("required_action_count")
    action_hash = gate.get("required_actions_sha256") or "(unknown)"
    reason_codes = gate.get("reason_codes")
    reason_descriptions = gate.get("reason_descriptions")
    actions = gate.get("required_actions")
    evidence = gate.get("evidence")
    if not isinstance(reason_codes, list) or not reason_codes:
        reason_lines = "- No candidate issue gate reason codes are reported."
    else:
        reason_lines = "\n".join(f"- `{reason}`" for reason in reason_codes)
    description_lines = _candidate_issue_gate_reason_descriptions_markdown(reason_descriptions)
    if not isinstance(actions, list) or not actions:
        action_lines = "- No required actions are reported."
    else:
        action_lines = "\n".join(f"- {action}" for action in actions)
    evidence_lines = _candidate_issue_gate_evidence_markdown(evidence)
    return f"""## Candidate Issue Gate

- status: `{status}`
- can_create_issues: `{can_create}`
- requires_maintainer_review: `{review_required}`
- summary: {summary}
- reason_code_count: `{_format_context_value(reason_count)}`
- reason_codes_sha256: `{_format_context_value(reason_hash)}`
- required_action_count: `{_format_context_value(action_count)}`
- required_actions_sha256: `{_format_context_value(action_hash)}`

### Candidate Issue Gate Reason Codes

{reason_lines}

### Candidate Issue Gate Reason Descriptions

{description_lines}

### Candidate Issue Gate Evidence

{evidence_lines}

### Candidate Issue Gate Actions

{action_lines}"""


def _candidate_issue_gate_evidence_markdown(evidence: object) -> str:
    if not isinstance(evidence, dict) or not evidence:
        return "- No candidate issue gate evidence is reported."
    rows = [
        ("publication_ok", evidence.get("publication_ok")),
        ("publication_visibility_status", evidence.get("publication_visibility_status")),
        ("publication_worktree_clean", evidence.get("publication_worktree_clean")),
        ("publication_remote_checked", evidence.get("publication_remote_checked")),
        ("publication_branch", evidence.get("publication_branch")),
        ("publication_latest_tag", evidence.get("publication_latest_tag")),
        ("publication_ahead_count", evidence.get("publication_ahead_count")),
        ("publication_tag_decision_status", evidence.get("publication_tag_decision_status")),
        ("publication_tag_can_push", evidence.get("publication_tag_can_push")),
        ("publication_tag_required_action", evidence.get("publication_tag_required_action")),
        ("publication_target_tag", evidence.get("publication_target_tag")),
        ("publication_target_tag_status", evidence.get("publication_target_tag_status")),
        (
            "publication_target_tag_primary_command",
            evidence.get("publication_target_tag_primary_command"),
        ),
        (
            "publication_target_tag_commands_sha256",
            evidence.get("publication_target_tag_commands_sha256"),
        ),
        (
            "publication_target_tag_required_action",
            evidence.get("publication_target_tag_required_action"),
        ),
        (
            "publication_target_tag_release_gate_status",
            evidence.get("publication_target_tag_release_gate_status"),
        ),
        (
            "publication_target_tag_release_gate_blocker_count",
            evidence.get("publication_target_tag_release_gate_blocker_count"),
        ),
        (
            "publication_target_tag_release_gate_primary_blocker",
            evidence.get("publication_target_tag_release_gate_primary_blocker"),
        ),
        (
            "publication_target_tag_release_gate_required_action",
            evidence.get("publication_target_tag_release_gate_required_action"),
        ),
        (
            "publication_target_tag_release_gate_blockers_sha256",
            evidence.get("publication_target_tag_release_gate_blockers_sha256"),
        ),
        ("release_draft_ok", evidence.get("release_draft_ok")),
        ("release_draft_path", evidence.get("release_draft_path")),
        ("release_draft_issue_count", evidence.get("release_draft_issue_count")),
    ]
    lines = ["| Field | Value |", "|-------|-------|"]
    lines.extend(f"| {key} | `{_format_context_value(value)}` |" for key, value in rows)
    return "\n".join(lines)


def _publication_visibility_markdown(visibility: dict[str, str]) -> str:
    status = visibility.get("status") or "(unknown)"
    summary = visibility.get("summary") or "Publication visibility has not been summarized."
    return f"""## Publication Visibility

- status: `{status}`
- summary: {summary}"""


def _publication_script_markdown(path: str, command: str) -> str:
    return f"""## Publication Publish Script

- path: `{path}`

```bash
{command}
```"""


def _standard_release_flow_markdown(flow: dict[str, Any]) -> str:
    flow_steps = _standard_release_flow_steps(flow)
    flow_step_names = _standard_release_flow_step_names(flow)
    flow_step_boundary = _standard_release_flow_step_boundary(flow)
    flow_step_status_counts = _standard_release_flow_step_status_counts(flow)
    primary_blocked_step_name = _format_context_value(
        _standard_release_flow_primary_step_name_with_status_prefix(flow, "blocked")
    )
    primary_pending_step_name = _format_context_value(
        _standard_release_flow_primary_step_name_with_status_prefix(flow, "pending")
    )
    website_deploy_command = _standard_release_flow_website_deploy_command(flow)
    website_deploy_command_sha256 = (
        _stable_json_sha256(website_deploy_command) if website_deploy_command else None
    )
    commands = flow.get("commands")
    command_lines = (
        "\n".join(str(command) for command in commands)
        if isinstance(commands, list) and commands
        else "# No standard release flow commands are needed."
    )
    blockers = flow.get("blockers")
    blocker_lines = (
        "\n".join(f"- {blocker}" for blocker in blockers)
        if isinstance(blockers, list) and blockers
        else "- No standard release flow blockers are present."
    )
    return f"""## Standard Release Flow

- standard_release_flow_status: `{_format_context_value(flow.get("status"))}`
- standard_release_flow_target_version: `{_format_context_value(flow.get("target_version"))}`
- standard_release_flow_target_tag: `{_format_context_value(flow.get("target_tag"))}`
- standard_release_flow_blocker_count: `{_format_context_value(flow.get("blocker_count"))}`
- standard_release_flow_blockers_sha256: `{_format_context_value(flow.get("blockers_sha256"))}`
- standard_release_flow_primary_next_action: `{_format_context_value(flow.get("primary_next_action"))}`
- standard_release_flow_command_count: `{_format_context_value(flow.get("command_count"))}`
- standard_release_flow_commands_sha256: `{_format_context_value(flow.get("commands_sha256"))}`
- standard_release_flow_step_count: `{len(flow_steps)}`
- standard_release_flow_step_names: `{json.dumps(flow_step_names, ensure_ascii=False)}`
- standard_release_flow_step_names_sha256: `{_stable_json_sha256(flow_step_names)}`
- standard_release_flow_steps_sha256: `{_stable_json_sha256(flow_steps)}`
- standard_release_flow_first_step_name: `{_format_context_value(flow_step_boundary["first_step_name"])}`
- standard_release_flow_last_step_name: `{_format_context_value(flow_step_boundary["last_step_name"])}`
- standard_release_flow_step_boundary_sha256: `{_stable_json_sha256(flow_step_boundary)}`
- standard_release_flow_step_status_counts: `{json.dumps(flow_step_status_counts, ensure_ascii=False)}`
- standard_release_flow_step_status_counts_sha256: `{_stable_json_sha256(flow_step_status_counts)}`
- standard_release_flow_primary_blocked_step_name: `{primary_blocked_step_name}`
- standard_release_flow_primary_pending_step_name: `{primary_pending_step_name}`
- standard_release_flow_has_website_deploy: `{str(website_deploy_command is not None).lower()}`
- standard_release_flow_website_deploy_command: `{_format_context_value(website_deploy_command)}`
- standard_release_flow_website_deploy_command_sha256: `{_format_context_value(website_deploy_command_sha256)}`
- standard_release_flow_sha256: `{_stable_json_sha256(flow)}`

### Standard Release Flow Blockers

{blocker_lines}

### Standard Release Flow Commands

```bash
{command_lines}
```"""


def _publication_worktree_markdown(clean: bool, status: list[str]) -> str:
    if clean:
        return "## Publication Worktree\n\n- worktree_clean: `true`"
    status_lines = "\n".join(status) or "(no status lines)"
    return f"""## Publication Worktree

- worktree_clean: `false`

```text
{status_lines}
```"""


def _publication_ref_context_markdown(context: dict[str, Any]) -> str:
    rows = [
        ("repo_root", context.get("repo_root")),
        ("branch", context.get("branch")),
        ("upstream", context.get("upstream")),
        ("remote", context.get("remote")),
        ("latest_tag", context.get("latest_tag")),
        ("local_head", context.get("local_head")),
        ("tag_commit", context.get("tag_commit")),
        ("ahead_count", context.get("ahead_count")),
        ("behind_count", context.get("behind_count")),
        ("remote_checked", context.get("remote_checked")),
    ]
    lines = ["## Publication Ref Context", "", "| Field | Value |", "|-------|-------|"]
    lines.extend(f"| {key} | `{_format_context_value(value)}` |" for key, value in rows)
    return "\n".join(lines)


def _format_context_value(value: object) -> str:
    if value is None:
        return "(none)"
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _publication_commands_markdown(commands: list[str]) -> str:
    if not commands:
        return "## Publication Publish Commands\n\n- No publication publish commands are needed."
    command_lines = "\n".join(commands)
    return f"""## Publication Publish Commands

```bash
{command_lines}
```"""


def _candidate_promotion_markdown(promotions: list[CandidatePromotion]) -> str:
    if not promotions:
        return (
            "## Candidate Issue Metadata\n\n"
            "- No candidate issue metadata is available.\n\n"
            "## Candidate Promotion Tasks\n\n"
            "- No candidate promotion tasks are available."
        )

    lines = [
        "## Candidate Issue Metadata",
        "",
        (
            "| Case | Issue Title | Labels | Priority Rank | Priority Reason | "
            "Evidence Bundle Primary Next Task | LLM Live Preflight | LLM Blocker Handling |"
        ),
        (
            "|------|-------------|--------|---------------|-----------------|"
            "-----------------------------------|--------------------|----------------------|"
        ),
    ]
    for promotion in promotions:
        labels = ", ".join(f"`{label}`" for label in promotion.issue_labels)
        priority_rank = (
            f"`{promotion.priority_rank}`"
            if promotion.priority_rank is not None
            else "Not declared."
        )
        priority_reason = promotion.priority_reason or "Not declared."
        primary_task = promotion.evidence_bundle_primary_next_task.get("task") or "Not declared."
        lines.append(
            f"| `{promotion.case_id}` | {promotion.issue_title} | {labels} | {priority_rank} | "
            f"{priority_reason} | `{primary_task}` | `{promotion.llm_live_preflight_command}` | "
            f"{promotion.llm_live_preflight_blocker_note} |"
        )

    lines.extend(
        [
            "",
            "## Candidate Promotion Tasks",
            "",
            "| Case | Adapter Package | Metadata Validation | Online Smoke | Promotion Evidence |",
            "|------|-----------------|---------------------|--------------|--------------------|",
        ]
    )
    for promotion in promotions:
        evidence = _candidate_promotion_evidence_summary(promotion.promotion_evidence)
        lines.append(
            f"| `{promotion.case_id}` | {promotion.adapter_package} | "
            f"{promotion.metadata_validation} | {promotion.online_smoke} | {evidence} |"
        )
    lines.extend(["", "## Candidate Issue Body Templates"])
    for promotion in promotions:
        lines.extend(
            [
                "",
                f"### `{promotion.case_id}`",
                "",
                "```markdown",
                promotion.issue_body,
                "```",
            ]
        )
    return "\n".join(lines)


def _candidate_promotion_evidence_summary(evidence: dict[str, Any]) -> str:
    parts: list[str] = []
    for field_name in CANDIDATE_PROMOTION_FIELDS:
        task = evidence.get(field_name)
        if not isinstance(task, dict):
            continue
        status = task.get("status") or "unknown"
        next_action = task.get("next_action")
        evidence_value = task.get("evidence")
        details = [f"{field_name}: {status}"]
        if evidence_value:
            details.append(f"evidence: {evidence_value}")
        if next_action:
            details.append(f"next: {next_action}")
        parts.append("; ".join(details))
    return "<br>".join(parts) if parts else "-"


def _write_markdown_report(plan: IterationPlan, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown(plan), encoding="utf-8")


def _write_candidate_issue_files(plan: IterationPlan, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    metadata: list[dict[str, Any]] = []
    issue_commands: list[str] = []
    issue_body_inventory = _issue_body_inventory(plan.candidate_promotions)
    issue_body_summary = _issue_body_summary(issue_body_inventory)
    for promotion in plan.candidate_promotions:
        body_path = directory / f"{promotion.case_id}.md"
        body_path.write_text(promotion.issue_body + "\n", encoding="utf-8", newline="\n")
        labels = [*promotion.issue_labels]
        create_command = _gh_issue_create_command(promotion, body_path)
        metadata.append(
            {
                "case_id": promotion.case_id,
                "issue_title": promotion.issue_title,
                "issue_labels": labels,
                "target_url": promotion.target_url,
                "commands": promotion.commands,
                "offline_commands": promotion.offline_commands,
                "priority_rank": promotion.priority_rank,
                "priority_reason": promotion.priority_reason,
                "promotion_evidence": promotion.promotion_evidence,
                "promotion_evidence_primary_task": promotion.promotion_evidence_primary_task,
                "evidence_bundle_primary_next_task": promotion.evidence_bundle_primary_next_task,
                "evidence_bundle_primary_next_task_runbook": (
                    promotion.evidence_bundle_primary_next_task_runbook
                ),
                "candidate_package_validation_command": promotion.candidate_package_validation_command,
                "promotion_command_plan": promotion.promotion_command_plan,
                "llm_live_preflight_command": promotion.llm_live_preflight_command,
                "llm_live_preflight_blocker_note": promotion.llm_live_preflight_blocker_note,
                "llm_live_preflight_evidence_fields": list(
                    promotion.llm_live_preflight_evidence_fields
                ),
                "evidence_bundle_command": promotion.evidence_bundle_command,
                "evidence_bundle_json_command": promotion.evidence_bundle_json_command,
                "issue_body_name": body_path.name,
                "issue_body_file": str(body_path),
                "create_command": create_command,
            }
        )
        issue_commands.append(create_command)

    issue_body_names = [f"{promotion.case_id}.md" for promotion in plan.candidate_promotions]
    candidate_cases = [promotion.case_id for promotion in plan.candidate_promotions]
    script_path = directory / "create-issues.sh"
    create_issues_safety = _issue_artifact_create_issues_safety(script_path, plan)
    artifact_files = _issue_artifact_files(issue_body_names)
    review_order = [
        "README.md",
        "publication-handoff.json",
        "release-draft-handoff.json",
        "issue-metadata.json",
        *issue_body_names,
        "create-issues.sh",
    ]
    artifact_bundle_summary = _issue_artifact_bundle_summary(
        plan=plan,
        candidate_cases=candidate_cases,
        review_order=review_order,
        issue_body_inventory=issue_body_inventory,
        issue_body_summary=issue_body_summary,
        issue_metadata_summary=_issue_metadata_summary(metadata),
        create_issues_safety=create_issues_safety,
        artifact_files=artifact_files,
    )
    artifact_manifest_payload = _artifact_manifest_payload_without_summary(
        plan=plan,
        candidate_cases=candidate_cases,
        review_order=review_order,
        issue_body_inventory=issue_body_inventory,
        issue_body_summary=issue_body_summary,
        issue_metadata_summary=_issue_metadata_summary(metadata),
        create_issues_safety=create_issues_safety,
        artifact_files=artifact_files,
    )
    artifact_manifest = {
        "schema_version": artifact_manifest_payload["schema_version"],
        "target_version": artifact_manifest_payload["target_version"],
        "artifact_bundle_summary": artifact_bundle_summary,
        **{
            key: value
            for key, value in artifact_manifest_payload.items()
            if key not in {"schema_version", "target_version"}
        },
    }
    (directory / "artifact-manifest.json").write_text(
        json.dumps(artifact_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (directory / "issue-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    publication_handoff = _publication_handoff(plan)
    (directory / "publication-handoff.json").write_text(
        json.dumps(publication_handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    release_draft_handoff = _release_draft_handoff(plan)
    (directory / "release-draft-handoff.json").write_text(
        json.dumps(release_draft_handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    script_path.write_text(
        "\n".join(
            _candidate_issue_script_lines(
                issue_commands,
                preflight_command=str(create_issues_safety["preflight_command"]),
            )
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    script_path.chmod(0o755)
    (directory / "README.md").write_text(
        _render_issue_artifacts_readme(plan, artifact_bundle_summary=artifact_bundle_summary),
        encoding="utf-8",
        newline="\n",
    )


def _candidate_issue_script_lines(issue_commands: list[str], *, preflight_command: str) -> list[str]:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Review these commands before running; they create GitHub issues in the current repository.",
        "# Set CLIANY_CREATE_ISSUES_DRY_RUN=1 to print commands without running the preflight or gh.",
        "# Stop early if the candidate issue gate no longer allows issue creation.",
        'REPO_ROOT="$(git rev-parse --show-toplevel)"',
        'cd "$REPO_ROOT"',
        'if [[ "${CLIANY_CREATE_ISSUES_DRY_RUN:-0}" == "1" ]]; then',
        '  echo "Dry run: candidate issue gate preflight and gh issue create are not executed."',
        "  cat <<'CLIANY_ISSUE_COMMANDS'",
    ]
    lines.extend(issue_commands)
    lines.extend(
        [
            "CLIANY_ISSUE_COMMANDS",
            "  exit 0",
            "fi",
            'PREFLIGHT_JSON="/tmp/cliany-issue-gate-check.json"',
            f'if ! {preflight_command} >"$PREFLIGHT_JSON"; then',
            '  echo "Candidate issue gate preflight failed; review $PREFLIGHT_JSON '
            'before creating candidate issues." >&2',
            '  cat "$PREFLIGHT_JSON" >&2 || true',
            "  exit 1",
            "fi",
            'if ! python - "$PREFLIGHT_JSON" <<\'PY\'',
            "import json",
            "import sys",
            "",
            "path = sys.argv[1]",
            'with open(path, encoding="utf-8") as handle:',
            "    payload = json.load(handle)",
            'gate = payload.get("candidate_issue_gate") or {}',
            'if not gate.get("can_create_issues", False):',
            '    print("Candidate issue gate does not allow creating issues.", file=sys.stderr)',
            "    print(json.dumps(gate, ensure_ascii=False, indent=2), file=sys.stderr)",
            "    sys.exit(1)",
            'if gate.get("requires_maintainer_review", False):',
            '    print("Candidate issue gate requires maintainer review before creating issues.", file=sys.stderr)',
            '    primary_action = gate.get("primary_required_action")',
            "    if primary_action:",
            '        print(f"Primary required action: {primary_action}", file=sys.stderr)',
            "PY",
            "then",
            '  cat "$PREFLIGHT_JSON" >&2 || true',
            "  exit 1",
            "fi",
        ]
    )
    lines.extend(f"\n{command}" for command in issue_commands)
    return lines


def _render_issue_artifacts_readme(
    plan: IterationPlan,
    *,
    artifact_bundle_summary: dict[str, Any] | None = None,
) -> str:
    body_files = "\n".join(f"- `{promotion.case_id}.md`" for promotion in plan.candidate_promotions)
    body_files = body_files or "- No candidate issue body files were generated."
    candidate_summary = _issue_artifact_candidate_summary(plan.candidate_promotions)
    case_promotion_evidence_summary = _case_promotion_evidence_markdown(plan.case_promotion_evidence_summary)
    body_inventory = _issue_artifact_body_inventory_markdown(plan.candidate_promotions)
    body_summary = _issue_artifact_body_summary_markdown(plan.candidate_promotions)
    gate_quick_summary = _issue_artifact_gate_quick_summary(plan)
    commit_cadence_summary = _issue_artifact_commit_cadence_markdown(plan)
    bundle_summary = _issue_artifact_bundle_summary_markdown(plan, summary=artifact_bundle_summary)
    gate_reason_codes = _issue_artifact_gate_reason_codes(plan)
    gate_reason_descriptions = _issue_artifact_gate_reason_descriptions(plan)
    gate_latest_tag = _format_context_value(_candidate_issue_gate_evidence_value(plan, "publication_latest_tag"))
    gate_ahead_count = _format_context_value(_candidate_issue_gate_evidence_value(plan, "publication_ahead_count"))
    gate_worktree_clean = _format_context_value(
        _candidate_issue_gate_evidence_value(plan, "publication_worktree_clean")
    )
    gate_tag_decision = _format_context_value(
        _candidate_issue_gate_evidence_value(plan, "publication_tag_decision_status")
    )
    gate_tag_can_push = _format_context_value(
        _candidate_issue_gate_evidence_value(plan, "publication_tag_can_push")
    )
    gate_tag_required_action = _format_context_value(
        _candidate_issue_gate_evidence_value(plan, "publication_tag_required_action")
    )
    gate_target_tag = _format_context_value(
        _candidate_issue_gate_evidence_value(plan, "publication_target_tag")
    )
    gate_target_tag_status = _format_context_value(
        _candidate_issue_gate_evidence_value(plan, "publication_target_tag_status")
    )
    gate_target_tag_primary_command = _format_context_value(
        _candidate_issue_gate_evidence_value(plan, "publication_target_tag_primary_command")
    )
    gate_target_tag_commands_sha256 = _format_context_value(
        _candidate_issue_gate_evidence_value(plan, "publication_target_tag_commands_sha256")
    )
    gate_target_tag_release_gate_status = _format_context_value(
        _candidate_issue_gate_evidence_value(
            plan, "publication_target_tag_release_gate_status"
        )
    )
    gate_target_tag_release_gate_blocker_count = _format_context_value(
        _candidate_issue_gate_evidence_value(
            plan, "publication_target_tag_release_gate_blocker_count"
        )
    )
    gate_target_tag_release_gate_primary_blocker = _format_context_value(
        _candidate_issue_gate_evidence_value(
            plan, "publication_target_tag_release_gate_primary_blocker"
        )
    )
    gate_target_tag_release_gate_blockers_sha256 = _format_context_value(
        _candidate_issue_gate_evidence_value(
            plan, "publication_target_tag_release_gate_blockers_sha256"
        )
    )
    gate_draft_ok = _format_context_value(_candidate_issue_gate_evidence_value(plan, "release_draft_ok"))
    gate_draft_issues = _format_context_value(_candidate_issue_gate_evidence_value(plan, "release_draft_issue_count"))
    create_issues_safety = _issue_artifact_create_issues_safety(Path("create-issues.sh"), plan)
    release_draft_required_actions = _release_draft_required_actions(plan.release_draft_issues)
    standard_flow_status = _format_context_value(plan.standard_release_flow.get("status"))
    standard_flow_target_tag = _format_context_value(plan.standard_release_flow.get("target_tag"))
    standard_flow_primary_action = _format_context_value(
        plan.standard_release_flow.get("primary_next_action")
    )
    standard_flow_command_count = _format_context_value(
        plan.standard_release_flow.get("command_count")
    )
    standard_flow_commands_sha256 = _format_context_value(
        plan.standard_release_flow.get("commands_sha256")
    )
    standard_flow_steps = _standard_release_flow_steps(plan.standard_release_flow)
    standard_flow_step_names = _standard_release_flow_step_names(plan.standard_release_flow)
    standard_flow_step_boundary = _standard_release_flow_step_boundary(
        plan.standard_release_flow
    )
    standard_flow_step_names_sha256 = _stable_json_sha256(standard_flow_step_names)
    standard_flow_steps_sha256 = _stable_json_sha256(standard_flow_steps)
    standard_flow_step_boundary_sha256 = _stable_json_sha256(standard_flow_step_boundary)
    standard_flow_website_deploy_command = _standard_release_flow_website_deploy_command(
        plan.standard_release_flow
    )
    standard_flow_website_deploy_command_sha256 = (
        _stable_json_sha256(standard_flow_website_deploy_command)
        if standard_flow_website_deploy_command
        else None
    )
    standard_flow_website_deploy_command_text = _format_context_value(
        standard_flow_website_deploy_command
    )
    standard_flow_website_deploy_command_sha256_text = _format_context_value(
        standard_flow_website_deploy_command_sha256
    )
    return f"""# cliany-site Candidate Issue Artifacts

Generated for target version `{plan.target_version}`.

## Files

- `issue-metadata.json`: structured issue title, labels, reproduction context, body file name,
  body file path, and `gh issue create` command.
- `artifact-manifest.json`: schema version, candidate cases, promotion evidence summary, blockers,
  next actions, file names, review order, review checklist, candidate issue gate, publication status,
  publication ref context, worktree status, release draft handoff, reproduction command, plan report command,
  standard release flow, publish commands, and validation commands for this candidate issue artifact bundle.
- `publication-handoff.json`: publication status, candidate issue gate, visibility, next actions,
  standard release flow, publication next actions, ref context, worktree status, and publish commands to review first.
- `release-draft-handoff.json`: schema version, target version, release draft ok status, release draft path,
  release draft path hash, release draft issue count, primary release draft issue, primary required action,
  release draft required action count, release draft required actions hash, release draft required actions,
  release draft issues hash, and release draft issues
  to review before tagging the target version.
- `create-issues.sh`: reviewable shell script with a candidate issue gate preflight and
  one `gh issue create` command per candidate. Set `CLIANY_CREATE_ISSUES_DRY_RUN=1`
  to print the commands without running the preflight or creating issues.
{body_files}

{candidate_summary}

{case_promotion_evidence_summary}

{body_inventory}

{body_summary}

{gate_quick_summary}

{commit_cadence_summary}

{bundle_summary}

## Publication Handoff

- schema_version: `1`
- publication_ok: `{str(plan.publication_ok).lower()}`
- candidate_issue_gate: `{_format_context_value(plan.candidate_issue_gate.get("status"))}`
- can_create_issues: `{str(bool(plan.candidate_issue_gate.get("can_create_issues", False))).lower()}`
- gate_summary: {_format_context_value(plan.candidate_issue_gate.get("summary"))}
- gate_reason_code_count: `{_format_context_value(plan.candidate_issue_gate.get("reason_code_count"))}`
- gate_reason_codes_sha256: `{_format_context_value(plan.candidate_issue_gate.get("reason_codes_sha256"))}`
- gate_required_action_count: `{_format_context_value(plan.candidate_issue_gate.get("required_action_count"))}`
- gate_required_actions_sha256: `{_format_context_value(plan.candidate_issue_gate.get("required_actions_sha256"))}`
- gate_primary_reason_code: {_summary_inline_code(plan.candidate_issue_gate.get("primary_reason_code"))}
- gate_primary_reason_description: {_summary_inline_code(plan.candidate_issue_gate.get("primary_reason_description"))}
- gate_primary_required_action: {_summary_inline_code(plan.candidate_issue_gate.get("primary_required_action"))}
- gate_reason_codes: {gate_reason_codes}
- gate_reason_descriptions: {gate_reason_descriptions}
- gate_evidence_latest_tag: `{gate_latest_tag}`
- gate_evidence_ahead_count: `{gate_ahead_count}`
- gate_evidence_worktree_clean: `{gate_worktree_clean}`
- gate_evidence_tag_decision: `{gate_tag_decision}`
- gate_evidence_tag_can_push: `{gate_tag_can_push}`
- gate_evidence_tag_required_action: `{gate_tag_required_action}`
- gate_evidence_target_tag: `{gate_target_tag}`
- gate_evidence_target_tag_status: `{gate_target_tag_status}`
- gate_evidence_target_tag_primary_command: `{gate_target_tag_primary_command}`
- gate_evidence_target_tag_commands_sha256: `{gate_target_tag_commands_sha256}`
- gate_evidence_target_tag_release_gate_status: `{gate_target_tag_release_gate_status}`
- gate_evidence_target_tag_release_gate_blocker_count: `{gate_target_tag_release_gate_blocker_count}`
- gate_evidence_target_tag_release_gate_primary_blocker: `{gate_target_tag_release_gate_primary_blocker}`
- gate_evidence_target_tag_release_gate_blockers_sha256: `{gate_target_tag_release_gate_blockers_sha256}`
- gate_evidence_release_draft_ok: `{gate_draft_ok}`
- gate_evidence_release_draft_issues: `{gate_draft_issues}`
- visibility: `{_format_context_value(plan.publication_visibility.get("status"))}`
- visibility_summary: {_format_context_value(plan.publication_visibility.get("summary"))}
- tag_publish_decision: `{_format_context_value(plan.publication_tag_publish_decision.get("status"))}`
- tag_can_push: `{str(bool(plan.publication_tag_publish_decision.get("can_push_tag", False))).lower()}`
- tag_required_action: `{_format_context_value(plan.publication_tag_publish_decision.get("required_action"))}`
- publication_blocker_count: `{len(plan.publication_blockers)}`
- publication_blockers_sha256: `{_stable_json_sha256(plan.publication_blockers)}`
- publication_primary_blocker: `{_format_context_value(_publication_primary_blocker(plan))}`
- commit_cadence_status: `{_format_context_value(plan.commit_cadence.get("status"))}`
- commit_cadence_missing_commit_days: `{_format_context_value(plan.commit_cadence.get("missing_commit_days"))}`
- commit_cadence_primary_next_action: `{_format_context_value(_commit_cadence_primary_next_action(plan))}`
- standard_release_flow_status: `{standard_flow_status}`
- standard_release_flow_target_tag: `{standard_flow_target_tag}`
- standard_release_flow_primary_next_action: `{standard_flow_primary_action}`
- standard_release_flow_command_count: `{standard_flow_command_count}`
- standard_release_flow_commands_sha256: `{standard_flow_commands_sha256}`
- standard_release_flow_step_count: `{len(standard_flow_steps)}`
- standard_release_flow_step_names: `{json.dumps(standard_flow_step_names, ensure_ascii=False)}`
- standard_release_flow_step_names_sha256: `{standard_flow_step_names_sha256}`
- standard_release_flow_steps_sha256: `{standard_flow_steps_sha256}`
- standard_release_flow_first_step_name: `{_format_context_value(standard_flow_step_boundary["first_step_name"])}`
- standard_release_flow_last_step_name: `{_format_context_value(standard_flow_step_boundary["last_step_name"])}`
- standard_release_flow_step_boundary_sha256: `{standard_flow_step_boundary_sha256}`
- standard_release_flow_has_website_deploy: `{str(standard_flow_website_deploy_command is not None).lower()}`
- standard_release_flow_website_deploy_command: `{standard_flow_website_deploy_command_text}`
- standard_release_flow_website_deploy_command_sha256: `{standard_flow_website_deploy_command_sha256_text}`
- standard_release_flow_sha256: `{_stable_json_sha256(plan.standard_release_flow)}`
- plan_report_command: `{plan.plan_report_command}`
- plan_report_command_sha256: `{_stable_json_sha256(plan.plan_report_command)}`
- issue_artifacts_command: `{plan.issue_artifacts_command}`
- issue_artifacts_command_sha256: `{_stable_json_sha256(plan.issue_artifacts_command)}`
- latest_tag: `{_format_context_value(plan.publication_ref_context.get("latest_tag"))}`
- local_head: `{_format_context_value(plan.publication_ref_context.get("local_head"))}`
- worktree_clean: `{str(plan.publication_worktree_clean).lower()}`
- primary_next_action: `{_format_context_value(_publication_primary_next_action(plan))}`
- publish_command_count: `{plan.publication_publish_command_count}`
- primary_publish_command: `{_format_context_value(_publication_primary_publish_command(plan))}`
- publish_script_path: `{plan.publication_publish_script_path}`
- publish_script_path_sha256: `{plan.publication_publish_script_path_sha256}`
- publish_script_command_sha256: `{plan.publication_publish_script_command_sha256}`
- Review `publication-handoff.json` before running `create-issues.sh`.

### Publication Next Actions

{_issue_artifact_publication_next_actions(plan)}

### Publication Publish Script

- path: `{plan.publication_publish_script_path}`

```bash
{plan.publication_publish_script_command}
```

```bash
{_issue_artifact_publication_commands(plan)}
```

## Release Draft Handoff

- schema_version: `1`
- release_draft_ok: `{str(not plan.release_draft_issues).lower()}`
- release_draft_path: `{plan.release_draft_path}`
- release_draft_path_sha256: `{_stable_json_sha256(plan.release_draft_path)}`
- release_draft_issue_count: `{len(plan.release_draft_issues)}`
- release_draft_primary_issue: `{_format_context_value(_release_draft_primary_issue(plan))}`
- primary_issue: `{_format_context_value(_release_draft_primary_issue(plan))}`
- release_draft_primary_required_action: `{_format_context_value(_release_draft_primary_required_action(plan))}`
- primary_required_action: `{_format_context_value(_release_draft_primary_required_action(plan))}`
- release_draft_required_action_count: `{len(release_draft_required_actions)}`
- release_draft_required_actions_sha256: `{_stable_json_sha256(release_draft_required_actions)}`
- release_draft_required_actions:
{_issue_artifact_release_draft_required_actions(plan)}
- release_draft_issues_sha256: `{_stable_json_sha256(plan.release_draft_issues)}`
- release_draft_issues:
{_issue_artifact_release_draft_issues(plan)}
- plan_report_command: `{plan.plan_report_command}`
- plan_report_command_sha256: `{_stable_json_sha256(plan.plan_report_command)}`
- issue_artifacts_command: `{plan.issue_artifacts_command}`
- issue_artifacts_command_sha256: `{_stable_json_sha256(plan.issue_artifacts_command)}`

## Review Checklist

{_issue_artifact_review_checklist_markdown()}

## Validation Commands

```bash
{_issue_artifact_validation_commands_text(plan)}
```

## Create Issues

`create-issues.sh` is generated for review. It is not executed by `plan_next_iteration.py`.
Run it only after checking `issue-metadata.json` and the body files. The script runs
`{create_issues_safety["preflight_command"]}` before creating issues and checks
`candidate_issue_gate.can_create_issues`. It writes the preflight JSON to
`{create_issues_safety["preflight_json"]}`. If the planner preflight fails or the gate
rejects issue creation, it prints the preflight JSON before exiting. If the gate requires
maintainer review while still allowing issue creation, it prints the primary required action
before continuing.

### Create Issues Safety

- dry_run_supported: `{str(create_issues_safety["dry_run_supported"]).lower()}`
- dry_run_env: `{create_issues_safety["dry_run_env"]}`
- dry_run_command: `{create_issues_safety["dry_run_command"]}`
- preflight_required: `{str(create_issues_safety["preflight_required"]).lower()}`
- preflight_command: `{create_issues_safety["preflight_command"]}`
- preflight_json: `{create_issues_safety["preflight_json"]}`

Preview the issue commands without running the candidate issue gate preflight or creating issues:

```bash
CLIANY_CREATE_ISSUES_DRY_RUN=1 ./create-issues.sh
```
"""


def _issue_artifact_gate_quick_summary(plan: IterationPlan) -> str:
    primary_reason_code = plan.candidate_issue_gate.get("primary_reason_code")
    primary_reason_description = plan.candidate_issue_gate.get("primary_reason_description")
    primary_required_action = plan.candidate_issue_gate.get("primary_required_action")
    lines = [
        "## Candidate Issue Gate Quick Summary",
        "",
        f"- status: `{_format_context_value(plan.candidate_issue_gate.get('status'))}`",
        "- can_create_issues: "
        f"`{str(bool(plan.candidate_issue_gate.get('can_create_issues', False))).lower()}`",
        "- requires_maintainer_review: "
        f"`{str(bool(plan.candidate_issue_gate.get('requires_maintainer_review', False))).lower()}`",
        f"- publication_ok: `{str(plan.publication_ok).lower()}`",
        f"- release_draft_ok: `{str(not plan.release_draft_issues).lower()}`",
        f"- blocker_count: `{len(plan.blockers)}`",
    ]
    release_readiness_aliases = _release_readiness_handoff_aliases(plan)
    if release_readiness_aliases:
        lines.extend(
            [
                "- release_readiness_blocker_count: "
                f"`{_format_context_value(release_readiness_aliases.get('release_readiness_blocker_count'))}`",
                "- release_readiness_primary_blocker: "
                f"{_summary_inline_code(release_readiness_aliases.get('release_readiness_primary_blocker'))}",
                "- release_readiness_blockers_sha256: "
                f"`{_format_context_value(release_readiness_aliases.get('release_readiness_blockers_sha256'))}`",
            ]
        )
    lines.extend(
        [
            f"- next_action_count: `{len(plan.next_actions)}`",
            f"- publication_next_action_count: `{plan.publication_next_action_count}`",
            f"- publication_blocker_count: `{len(plan.publication_blockers)}`",
            "- publication_blockers_sha256: "
            f"`{_stable_json_sha256(plan.publication_blockers)}`",
            "- publication_primary_blocker: "
            f"{_summary_inline_code(_publication_primary_blocker(plan))}",
            f"- publication_publish_command_count: `{plan.publication_publish_command_count}`",
            "- publication_publish_script_path: "
            f"{_summary_inline_code(plan.publication_publish_script_path)}",
            "- publication_publish_script_path_sha256: "
            f"`{plan.publication_publish_script_path_sha256}`",
            "- publication_publish_script_command: "
            f"{_summary_inline_code(plan.publication_publish_script_command)}",
            "- publication_publish_script_command_sha256: "
            f"`{plan.publication_publish_script_command_sha256}`",
            "- reason_code_count: "
            f"`{_format_context_value(plan.candidate_issue_gate.get('reason_code_count'))}`",
            "- required_action_count: "
            f"`{_format_context_value(plan.candidate_issue_gate.get('required_action_count'))}`",
            f"- primary_reason_code: {_summary_inline_code(primary_reason_code)}",
            f"- primary_reason_description: {_summary_inline_code(primary_reason_description)}",
            f"- primary_required_action: {_summary_inline_code(primary_required_action)}",
            "- latest_tag: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_latest_tag'))}`",
            "- publication_branch: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_branch'))}`",
            "- publication_upstream: "
            f"`{_format_context_value(plan.publication_ref_context.get('upstream'))}`",
            "- publication_remote: "
            f"`{_format_context_value(plan.publication_ref_context.get('remote'))}`",
            "- publication_local_head: "
            f"`{_format_context_value(plan.publication_ref_context.get('local_head'))}`",
            "- publication_tag_commit: "
            f"`{_format_context_value(plan.publication_ref_context.get('tag_commit'))}`",
            "- publication_upstream_head: "
            f"`{_format_context_value(plan.publication_ref_context.get('upstream_head'))}`",
            "- publication_tag_points_at_head: "
            f"`{_format_context_value(plan.publication_ref_context.get('tag_points_at_head'))}`",
            "- publication_tag_commit_in_upstream: "
            f"`{_format_context_value(plan.publication_ref_context.get('tag_commit_in_upstream'))}`",
            "- publication_branch_published: "
            f"`{_format_context_value(plan.publication_ref_context.get('branch_published'))}`",
            "- publication_tag_published: "
            f"`{_format_context_value(plan.publication_ref_context.get('tag_published'))}`",
            "- publication_remote_branch_head: "
            f"`{_format_context_value(plan.publication_ref_context.get('remote_branch_head'))}`",
            "- publication_remote_tag_commit: "
            f"`{_format_context_value(plan.publication_ref_context.get('remote_tag_commit'))}`",
            "- publication_worktree_clean: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_worktree_clean'))}`",
            "- publication_ahead_count: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_ahead_count'))}`",
            "- publication_behind_count: "
            f"`{_format_context_value(plan.publication_ref_context.get('behind_count'))}`",
            "- publication_remote_checked: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_remote_checked'))}`",
            "- release_draft_issue_count: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'release_draft_issue_count'))}`",
            "- release_draft_path: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'release_draft_path'))}`",
            f"- visibility: `{_format_context_value(plan.publication_visibility.get('status'))}`",
            f"- visibility_summary: {_summary_inline_code(plan.publication_visibility.get('summary'))}",
        ]
    )
    return "\n".join(lines)


def _issue_artifact_commit_cadence_markdown(plan: IterationPlan) -> str:
    commit_days = plan.commit_cadence.get("commit_days")
    if not isinstance(commit_days, list) or not commit_days:
        commit_days_text = "`(none)`"
    else:
        commit_days_text = ", ".join(f"`{day}`" for day in commit_days)
    release_tags_today = plan.commit_cadence.get("release_tags_today")
    if not isinstance(release_tags_today, list) or not release_tags_today:
        release_tags_today_text = "`(none)`"
    else:
        release_tags_today_text = ", ".join(f"`{tag}`" for tag in release_tags_today)
    next_actions = plan.commit_cadence.get("next_actions")
    if isinstance(next_actions, list) and next_actions:
        next_actions_text = "\n".join(f"- {action}" for action in next_actions)
    else:
        next_actions_text = "- No commit cadence next actions are needed."
    return "\n".join(
        [
            "## Commit Cadence",
            "",
            f"- status: `{_format_context_value(plan.commit_cadence.get('status'))}`",
            f"- summary: {_summary_inline_code(plan.commit_cadence.get('summary'))}",
            f"- commit_day_count: `{_format_context_value(plan.commit_cadence.get('commit_day_count'))}`",
            f"- min_commit_days: `{_format_context_value(plan.commit_cadence.get('min_commit_days'))}`",
            f"- missing_commit_days: `{_format_context_value(plan.commit_cadence.get('missing_commit_days'))}`",
            f"- commit_days: {commit_days_text}",
            f"- release_count_today: `{_format_context_value(plan.commit_cadence.get('release_count_today'))}`",
            f"- max_daily_releases: `{_format_context_value(plan.commit_cadence.get('max_daily_releases'))}`",
            f"- daily_release_limit_ok: `{_format_context_value(plan.commit_cadence.get('daily_release_limit_ok'))}`",
            f"- release_tags_today: {release_tags_today_text}",
            "- primary_next_action: "
            f"{_summary_inline_code(_commit_cadence_primary_next_action(plan))}",
            "",
            "### Commit Cadence Next Actions",
            "",
            next_actions_text,
        ]
    )


def _candidate_issue_gate_evidence_value(plan: IterationPlan, key: str) -> object:
    evidence = plan.candidate_issue_gate.get("evidence")
    if not isinstance(evidence, dict):
        return None
    return evidence.get(key)


def _release_readiness_handoff_aliases(plan: IterationPlan) -> dict[str, object]:
    aliases = {
        key: _candidate_issue_gate_evidence_value(plan, key)
        for key in (
            "release_readiness_blocker_count",
            "release_readiness_primary_blocker",
            "release_readiness_blockers_sha256",
        )
    }
    return {key: value for key, value in aliases.items() if value is not None}


def _issue_artifact_gate_reason_codes(plan: IterationPlan) -> str:
    reason_codes = plan.candidate_issue_gate.get("reason_codes")
    if not isinstance(reason_codes, list) or not reason_codes:
        return "`(none)`"
    return ", ".join(f"`{reason}`" for reason in reason_codes)


def _candidate_issue_gate_reason_descriptions_markdown(descriptions: object) -> str:
    if not isinstance(descriptions, dict) or not descriptions:
        return "- No candidate issue gate reason descriptions are reported."
    lines = ["| Code | Description |", "|------|-------------|"]
    lines.extend(f"| `{code}` | {description} |" for code, description in descriptions.items())
    return "\n".join(lines)


def _issue_artifact_gate_reason_descriptions(plan: IterationPlan) -> str:
    descriptions = plan.candidate_issue_gate.get("reason_descriptions")
    if not isinstance(descriptions, dict) or not descriptions:
        return "`(none)`"
    return "; ".join(f"`{code}`: {description}" for code, description in descriptions.items())


def _issue_artifact_release_draft_issues(plan: IterationPlan) -> str:
    if not plan.release_draft_issues:
        return "  - No release draft issues are reported."
    return "\n".join(f"  - {issue}" for issue in plan.release_draft_issues)


def _issue_artifact_release_draft_required_actions(plan: IterationPlan) -> str:
    actions = _release_draft_required_actions(plan.release_draft_issues)
    if not actions:
        return "  - No release draft required actions are reported."
    return "\n".join(f"  - {action}" for action in actions)


def _issue_artifact_review_checklist() -> list[str]:
    return [
        "Confirm the latest local release has been published before creating new candidate work.",
        "Confirm release draft issues are resolved or intentionally deferred before tagging the target version.",
        "Confirm Publication Next Actions are resolved or intentionally deferred before running create-issues.sh.",
        (
            "Confirm issue-metadata.json has the expected target URL, candidate commands, "
            "offline validation commands, candidate_package_validation_command, "
            "promotion_command_plan, llm_live_preflight_command, and "
            "llm_live_preflight_blocker_note for each case."
        ),
        "Review each body file for scope, tasks, validation evidence, and non-goals.",
        (
            "Keep cases as candidate until adapter package, metadata validation, "
            "and online smoke evidence are complete."
        ),
        "Do not use real LLM keys or write runtime state into the repository.",
    ]


def _issue_artifact_review_checklist_markdown() -> str:
    return "\n".join(f"- {item}" for item in _issue_artifact_review_checklist())


def _issue_artifact_publication_commands(plan: IterationPlan) -> str:
    if plan.publication_publish_commands:
        return "\n".join(plan.publication_publish_commands)
    return "python scripts/check_release_publication.py --json"


def _issue_artifact_publication_next_actions(plan: IterationPlan) -> str:
    if not plan.publication_next_actions:
        return "- No publication next actions are needed."
    return "\n".join(f"- {action}" for action in plan.publication_next_actions)


def _issue_artifact_validation_commands(plan: IterationPlan) -> list[str]:
    return [
        plan.issue_artifacts_command,
        plan.plan_report_command,
        *plan.validation_commands,
    ]


def _issue_artifact_validation_commands_text(plan: IterationPlan) -> str:
    return "\n".join(_issue_artifact_validation_commands(plan))


def _issue_artifact_candidate_gate_preflight_command(plan: IterationPlan) -> str:
    if plan.validation_commands:
        command = plan.validation_commands[0]
        if command.startswith("python scripts/plan_next_iteration.py ") and command.endswith(" --json"):
            return command
    return f"python scripts/plan_next_iteration.py --target-version {plan.target_version} --json"


def _issue_artifact_create_issues_safety(script_path: Path, plan: IterationPlan) -> dict[str, Any]:
    return {
        "script": str(script_path),
        "dry_run_supported": True,
        "dry_run_env": "CLIANY_CREATE_ISSUES_DRY_RUN=1",
        "dry_run_command": f"CLIANY_CREATE_ISSUES_DRY_RUN=1 {script_path}",
        "preflight_required": True,
        "preflight_command": _issue_artifact_candidate_gate_preflight_command(plan),
        "preflight_json": "/tmp/cliany-issue-gate-check.json",
    }


def _issue_artifact_create_issues_safety_contract(create_issues_safety: dict[str, Any]) -> dict[str, Any]:
    return {
        "dry_run_supported": create_issues_safety["dry_run_supported"],
        "dry_run_env": create_issues_safety["dry_run_env"],
        "preflight_required": create_issues_safety["preflight_required"],
        "preflight_command": create_issues_safety["preflight_command"],
        "preflight_json": create_issues_safety["preflight_json"],
    }


def _issue_artifact_files(issue_body_names: list[str]) -> dict[str, Any]:
    return {
        "readme": "README.md",
        "issue_metadata": "issue-metadata.json",
        "publication_handoff": "publication-handoff.json",
        "release_draft_handoff": "release-draft-handoff.json",
        "create_issues_script": "create-issues.sh",
        "issue_bodies": issue_body_names,
    }


def _publication_handoff(plan: IterationPlan) -> dict[str, Any]:
    website_deploy_command = _standard_release_flow_website_deploy_command(
        plan.standard_release_flow
    )
    standard_release_flow_steps = _standard_release_flow_steps(plan.standard_release_flow)
    standard_release_flow_step_names = _standard_release_flow_step_names(
        plan.standard_release_flow
    )
    standard_release_flow_step_boundary = _standard_release_flow_step_boundary(
        plan.standard_release_flow
    )
    standard_release_flow_step_status_counts = _standard_release_flow_step_status_counts(
        plan.standard_release_flow
    )
    handoff = {
        "schema_version": 1,
        "publication_ok": plan.publication_ok,
        "candidate_issue_gate": plan.candidate_issue_gate,
        "candidate_issue_gate_primary_reason_code": plan.candidate_issue_gate.get(
            "primary_reason_code"
        ),
        "candidate_issue_gate_primary_reason_description": plan.candidate_issue_gate.get(
            "primary_reason_description"
        ),
        "candidate_issue_gate_primary_required_action": plan.candidate_issue_gate.get(
            "primary_required_action"
        ),
        "visibility": plan.publication_visibility,
        "tag_publish_decision": plan.publication_tag_publish_decision,
        "publication_blocker_count": len(plan.publication_blockers),
        "publication_blockers_sha256": _stable_json_sha256(plan.publication_blockers),
        "publication_primary_blocker": _publication_primary_blocker(plan),
        "publication_blockers": plan.publication_blockers,
        "next_actions": plan.next_actions,
        "commit_cadence": plan.commit_cadence,
        "commit_cadence_status": plan.commit_cadence.get("status"),
        "commit_cadence_missing_commit_days": plan.commit_cadence.get("missing_commit_days"),
        "commit_cadence_primary_next_action": _commit_cadence_primary_next_action(plan),
        "standard_release_flow": plan.standard_release_flow,
        "standard_release_flow_status": plan.standard_release_flow.get("status"),
        "standard_release_flow_primary_next_action": plan.standard_release_flow.get(
            "primary_next_action"
        ),
        "standard_release_flow_command_count": plan.standard_release_flow.get(
            "command_count"
        ),
        "standard_release_flow_commands_sha256": plan.standard_release_flow.get(
            "commands_sha256"
        ),
        "standard_release_flow_step_count": len(standard_release_flow_steps),
        "standard_release_flow_step_names": list(standard_release_flow_step_names),
        "standard_release_flow_step_names_sha256": _stable_json_sha256(
            standard_release_flow_step_names
        ),
        "standard_release_flow_steps_sha256": _stable_json_sha256(
            standard_release_flow_steps
        ),
        "standard_release_flow_first_step_name": (
            standard_release_flow_step_boundary["first_step_name"]
        ),
        "standard_release_flow_last_step_name": (
            standard_release_flow_step_boundary["last_step_name"]
        ),
        "standard_release_flow_step_boundary_sha256": _stable_json_sha256(
            standard_release_flow_step_boundary
        ),
        "standard_release_flow_step_status_counts": standard_release_flow_step_status_counts,
        "standard_release_flow_step_status_counts_sha256": _stable_json_sha256(
            standard_release_flow_step_status_counts
        ),
        "standard_release_flow_primary_blocked_step_name": (
            _standard_release_flow_primary_step_name_with_status_prefix(
                plan.standard_release_flow, "blocked"
            )
        ),
        "standard_release_flow_primary_pending_step_name": (
            _standard_release_flow_primary_step_name_with_status_prefix(
                plan.standard_release_flow, "pending"
            )
        ),
        "standard_release_flow_has_website_deploy": website_deploy_command is not None,
        "standard_release_flow_website_deploy_command": website_deploy_command,
        "standard_release_flow_website_deploy_command_sha256": (
            _stable_json_sha256(website_deploy_command) if website_deploy_command else None
        ),
        "standard_release_flow_sha256": _stable_json_sha256(plan.standard_release_flow),
        "publication_next_actions": plan.publication_next_actions,
        "primary_next_action": _publication_primary_next_action(plan),
        "plan_report_command": plan.plan_report_command,
        "plan_report_command_sha256": _stable_json_sha256(plan.plan_report_command),
        "issue_artifacts_command": plan.issue_artifacts_command,
        "issue_artifacts_command_sha256": _stable_json_sha256(plan.issue_artifacts_command),
        "ref_context": plan.publication_ref_context,
        "worktree_clean": plan.publication_worktree_clean,
        "worktree_status": plan.publication_worktree_status,
        "publish_command_count": plan.publication_publish_command_count,
        "primary_publish_command": _publication_primary_publish_command(plan),
        "publish_commands": plan.publication_publish_commands,
        "publish_script_path": plan.publication_publish_script_path,
        "publish_script_path_sha256": plan.publication_publish_script_path_sha256,
        "publish_script_command": plan.publication_publish_script_command,
        "publish_script_command_sha256": plan.publication_publish_script_command_sha256,
    }
    handoff.update(_release_readiness_handoff_aliases(plan))
    return handoff


def _commit_cadence_primary_next_action(plan: IterationPlan) -> str | None:
    actions = plan.commit_cadence.get("next_actions")
    if isinstance(actions, list) and actions:
        return str(actions[0])
    return None


def _publication_primary_next_action(plan: IterationPlan) -> str | None:
    return plan.publication_next_actions[0] if plan.publication_next_actions else None


def _publication_primary_blocker(plan: IterationPlan) -> str | None:
    return plan.publication_blockers[0] if plan.publication_blockers else None


def _publication_primary_publish_command(plan: IterationPlan) -> str | None:
    return plan.publication_publish_commands[0] if plan.publication_publish_commands else None


def _release_draft_primary_issue(plan: IterationPlan) -> str | None:
    return plan.release_draft_issues[0] if plan.release_draft_issues else None


def _release_draft_primary_required_action(plan: IterationPlan) -> str | None:
    primary_issue = _release_draft_primary_issue(plan)
    if primary_issue is None:
        return None
    return f"Resolve release draft issue: {primary_issue}"


def _release_draft_handoff(plan: IterationPlan) -> dict[str, Any]:
    required_actions = _release_draft_required_actions(plan.release_draft_issues)
    return {
        "schema_version": 1,
        "release_draft_ok": not plan.release_draft_issues,
        "release_draft_issue_count": len(plan.release_draft_issues),
        "release_draft_path": plan.release_draft_path,
        "release_draft_path_sha256": _stable_json_sha256(plan.release_draft_path),
        "release_draft_primary_issue": _release_draft_primary_issue(plan),
        "primary_issue": _release_draft_primary_issue(plan),
        "release_draft_primary_required_action": _release_draft_primary_required_action(plan),
        "primary_required_action": _release_draft_primary_required_action(plan),
        "release_draft_required_action_count": len(required_actions),
        "release_draft_required_actions_sha256": _stable_json_sha256(required_actions),
        "release_draft_required_actions": required_actions,
        "release_draft_issues_sha256": _stable_json_sha256(plan.release_draft_issues),
        "release_draft_issues": plan.release_draft_issues,
        "plan_report_command": plan.plan_report_command,
        "plan_report_command_sha256": _stable_json_sha256(plan.plan_report_command),
        "issue_artifacts_command": plan.issue_artifacts_command,
        "issue_artifacts_command_sha256": _stable_json_sha256(plan.issue_artifacts_command),
        "target_version": plan.target_version,
    }


def _issue_body_inventory(promotions: list[CandidatePromotion]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for promotion in promotions:
        body_name = f"{promotion.case_id}.md"
        body_bytes = f"{promotion.issue_body}\n".encode()
        inventory.append(
            {
                "case_id": promotion.case_id,
                "issue_body_name": body_name,
                "byte_count": len(body_bytes),
                "sha256": hashlib.sha256(body_bytes).hexdigest(),
            }
        )
    return inventory


def _issue_body_summary(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    digest_source = json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {
        "body_count": len(inventory),
        "total_byte_count": sum(int(item["byte_count"]) for item in inventory),
        "inventory_sha256": hashlib.sha256(digest_source).hexdigest(),
    }


def _issue_metadata_summary(metadata: list[dict[str, Any]]) -> dict[str, Any]:
    stable_metadata = [
        {
            "case_id": item["case_id"],
            "issue_title": item["issue_title"],
            "issue_labels": item["issue_labels"],
            "target_url": item["target_url"],
            "commands": item["commands"],
            "offline_commands": item["offline_commands"],
            "priority_rank": item["priority_rank"],
            "priority_reason": item["priority_reason"],
            "promotion_evidence": item["promotion_evidence"],
            "promotion_evidence_primary_task": item["promotion_evidence_primary_task"],
            "evidence_bundle_primary_next_task": item["evidence_bundle_primary_next_task"],
            "evidence_bundle_primary_next_task_runbook": item[
                "evidence_bundle_primary_next_task_runbook"
            ],
            "candidate_package_validation_command": item["candidate_package_validation_command"],
            "promotion_command_plan": item["promotion_command_plan"],
            "llm_live_preflight_command": item["llm_live_preflight_command"],
            "llm_live_preflight_blocker_note": item["llm_live_preflight_blocker_note"],
            "llm_live_preflight_evidence_fields": item[
                "llm_live_preflight_evidence_fields"
            ],
            "evidence_bundle_command": item["evidence_bundle_command"],
            "evidence_bundle_json_command": item["evidence_bundle_json_command"],
            "issue_body_name": item["issue_body_name"],
        }
        for item in metadata
    ]
    metadata_boundary = {
        "first_item": stable_metadata[0] if stable_metadata else None,
        "last_item": stable_metadata[-1] if stable_metadata else None,
    }
    metadata_preview = stable_metadata[:8]
    metadata_tail = stable_metadata[-8:]
    digest_source = json.dumps(stable_metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {
        "metadata_count": len(stable_metadata),
        "metadata_sha256": hashlib.sha256(digest_source).hexdigest(),
        "metadata_first_item": metadata_boundary["first_item"],
        "metadata_last_item": metadata_boundary["last_item"],
        "metadata_boundary_sha256": _stable_json_sha256(metadata_boundary),
        "metadata_preview_count": len(metadata_preview),
        "metadata_preview": list(metadata_preview),
        "metadata_preview_sha256": _stable_json_sha256(metadata_preview),
        "metadata_tail_count": len(metadata_tail),
        "metadata_tail": list(metadata_tail),
        "metadata_tail_sha256": _stable_json_sha256(metadata_tail),
    }


def _issue_metadata_for_summary(promotions: list[CandidatePromotion]) -> list[dict[str, Any]]:
    return [
        {
            "case_id": promotion.case_id,
            "issue_title": promotion.issue_title,
            "issue_labels": [*promotion.issue_labels],
            "target_url": promotion.target_url,
            "commands": promotion.commands,
            "offline_commands": promotion.offline_commands,
            "priority_rank": promotion.priority_rank,
            "priority_reason": promotion.priority_reason,
            "promotion_evidence": promotion.promotion_evidence,
            "promotion_evidence_primary_task": promotion.promotion_evidence_primary_task,
            "evidence_bundle_primary_next_task": promotion.evidence_bundle_primary_next_task,
            "evidence_bundle_primary_next_task_runbook": (
                promotion.evidence_bundle_primary_next_task_runbook
            ),
            "candidate_package_validation_command": promotion.candidate_package_validation_command,
            "promotion_command_plan": promotion.promotion_command_plan,
            "llm_live_preflight_command": promotion.llm_live_preflight_command,
            "llm_live_preflight_blocker_note": promotion.llm_live_preflight_blocker_note,
            "llm_live_preflight_evidence_fields": list(
                promotion.llm_live_preflight_evidence_fields
            ),
            "evidence_bundle_command": promotion.evidence_bundle_command,
            "evidence_bundle_json_command": promotion.evidence_bundle_json_command,
            "issue_body_name": f"{promotion.case_id}.md",
        }
        for promotion in promotions
    ]


def _issue_artifact_body_inventory_markdown(promotions: list[CandidatePromotion]) -> str:
    inventory = _issue_body_inventory(promotions)
    if not inventory:
        return "## Issue Body Inventory\n\n- No issue body inventory is available."
    lines = [
        "## Issue Body Inventory",
        "",
        "| Case | Issue Body | Bytes | SHA-256 |",
        "|------|------------|-------|---------|",
    ]
    for item in inventory:
        lines.append(
            f"| `{item['case_id']}` | `{item['issue_body_name']}` | "
            f"{item['byte_count']} | `{item['sha256']}` |"
        )
    return "\n".join(lines)


def _issue_artifact_body_summary_markdown(promotions: list[CandidatePromotion]) -> str:
    summary = _issue_body_summary(_issue_body_inventory(promotions))
    return "\n".join(
        [
            "## Issue Body Summary",
            "",
            f"- body_count: `{summary['body_count']}`",
            f"- total_byte_count: `{summary['total_byte_count']}`",
            f"- inventory_sha256: `{summary['inventory_sha256']}`",
        ]
    )


def _artifact_manifest_payload_without_summary(
    *,
    plan: IterationPlan,
    candidate_cases: list[str],
    review_order: list[str],
    issue_body_inventory: list[dict[str, Any]],
    issue_body_summary: dict[str, Any],
    issue_metadata_summary: dict[str, Any],
    create_issues_safety: dict[str, Any],
    artifact_files: dict[str, Any],
) -> dict[str, Any]:
    website_deploy_command = _standard_release_flow_website_deploy_command(
        plan.standard_release_flow
    )
    standard_release_flow_steps = _standard_release_flow_steps(plan.standard_release_flow)
    standard_release_flow_step_names = _standard_release_flow_step_names(
        plan.standard_release_flow
    )
    standard_release_flow_step_boundary = _standard_release_flow_step_boundary(
        plan.standard_release_flow
    )
    standard_release_flow_step_status_counts = _standard_release_flow_step_status_counts(
        plan.standard_release_flow
    )
    return {
        "schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "target_version": plan.target_version,
        "candidate_count": len(candidate_cases),
        "candidate_cases": candidate_cases,
        "case_promotion_evidence_summary": plan.case_promotion_evidence_summary,
        "case_promotion_command_plan_summary": plan.case_promotion_command_plan_summary,
        "standard_release_flow": plan.standard_release_flow,
        "standard_release_flow_status": plan.standard_release_flow.get("status"),
        "standard_release_flow_primary_next_action": plan.standard_release_flow.get(
            "primary_next_action"
        ),
        "standard_release_flow_command_count": plan.standard_release_flow.get(
            "command_count"
        ),
        "standard_release_flow_commands_sha256": plan.standard_release_flow.get(
            "commands_sha256"
        ),
        "standard_release_flow_step_count": len(standard_release_flow_steps),
        "standard_release_flow_step_names": list(standard_release_flow_step_names),
        "standard_release_flow_step_names_sha256": _stable_json_sha256(
            standard_release_flow_step_names
        ),
        "standard_release_flow_steps_sha256": _stable_json_sha256(
            standard_release_flow_steps
        ),
        "standard_release_flow_first_step_name": (
            standard_release_flow_step_boundary["first_step_name"]
        ),
        "standard_release_flow_last_step_name": (
            standard_release_flow_step_boundary["last_step_name"]
        ),
        "standard_release_flow_step_boundary_sha256": _stable_json_sha256(
            standard_release_flow_step_boundary
        ),
        "standard_release_flow_step_status_counts": standard_release_flow_step_status_counts,
        "standard_release_flow_step_status_counts_sha256": _stable_json_sha256(
            standard_release_flow_step_status_counts
        ),
        "standard_release_flow_primary_blocked_step_name": (
            _standard_release_flow_primary_step_name_with_status_prefix(
                plan.standard_release_flow, "blocked"
            )
        ),
        "standard_release_flow_primary_pending_step_name": (
            _standard_release_flow_primary_step_name_with_status_prefix(
                plan.standard_release_flow, "pending"
            )
        ),
        "standard_release_flow_has_website_deploy": website_deploy_command is not None,
        "standard_release_flow_website_deploy_command": website_deploy_command,
        "standard_release_flow_website_deploy_command_sha256": (
            _stable_json_sha256(website_deploy_command) if website_deploy_command else None
        ),
        "standard_release_flow_sha256": _stable_json_sha256(plan.standard_release_flow),
        "blockers": plan.blockers,
        "next_actions": plan.next_actions,
        "next_action_count": len(plan.next_actions),
        "next_actions_sha256": _stable_json_sha256(plan.next_actions),
        "primary_next_action": plan.next_actions[0] if plan.next_actions else None,
        "commit_cadence": plan.commit_cadence,
        "candidate_issue_gate": plan.candidate_issue_gate,
        "publication_ok": plan.publication_ok,
        "publication_visibility": plan.publication_visibility,
        "publication_tag_publish_decision": plan.publication_tag_publish_decision,
        "publication_blocker_count": len(plan.publication_blockers),
        "publication_blockers_sha256": _stable_json_sha256(plan.publication_blockers),
        "publication_primary_blocker": _publication_primary_blocker(plan),
        "publication_blockers": plan.publication_blockers,
        "publication_next_actions": plan.publication_next_actions,
        "publication_publish_commands": plan.publication_publish_commands,
        "publication_ref_context": plan.publication_ref_context,
        "publication_worktree_clean": plan.publication_worktree_clean,
        "publication_worktree_status": plan.publication_worktree_status,
        "publication_publish_script_path": plan.publication_publish_script_path,
        "publication_publish_script_path_sha256": plan.publication_publish_script_path_sha256,
        "publication_publish_script_command": plan.publication_publish_script_command,
        "publication_publish_script_command_sha256": (
            plan.publication_publish_script_command_sha256
        ),
        "release_draft_path": plan.release_draft_path,
        "release_draft_issues": plan.release_draft_issues,
        "issue_artifacts_command": plan.issue_artifacts_command,
        "plan_report_command": plan.plan_report_command,
        "create_issues_dry_run_command": create_issues_safety["dry_run_command"],
        "create_issues_safety": create_issues_safety,
        "issue_body_inventory": issue_body_inventory,
        "issue_body_summary": issue_body_summary,
        "issue_metadata_summary": issue_metadata_summary,
        "files": artifact_files,
        "review_order": review_order,
        "review_checklist": _issue_artifact_review_checklist(),
        "validation_commands": _issue_artifact_validation_commands(plan),
    }


def _issue_artifact_bundle_summary(
    *,
    plan: IterationPlan,
    candidate_cases: list[str],
    review_order: list[str],
    issue_body_inventory: list[dict[str, Any]],
    issue_body_summary: dict[str, Any],
    issue_metadata_summary: dict[str, Any],
    create_issues_safety: dict[str, Any],
    artifact_files: dict[str, Any],
) -> dict[str, Any]:
    review_order_digest_source = json.dumps(
        review_order,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    review_order_boundary = {
        "first_item": review_order[0] if review_order else None,
        "last_item": review_order[-1] if review_order else None,
    }
    review_order_preview = review_order[:8]
    review_order_tail = review_order[-8:]
    create_issues_safety_contract = _issue_artifact_create_issues_safety_contract(create_issues_safety)
    publication_handoff = _publication_handoff(plan)
    release_draft_handoff = _release_draft_handoff(plan)
    publication_handoff_keys = list(publication_handoff)
    publication_handoff_key_boundary = {
        "first_key": publication_handoff_keys[0] if publication_handoff_keys else None,
        "last_key": publication_handoff_keys[-1] if publication_handoff_keys else None,
    }
    publication_handoff_key_preview = publication_handoff_keys[:8]
    publication_handoff_key_tail = publication_handoff_keys[-8:]
    candidate_issue_gate_evidence = plan.candidate_issue_gate.get("evidence")
    if not isinstance(candidate_issue_gate_evidence, dict):
        candidate_issue_gate_evidence = {}
    candidate_issue_gate_reason_descriptions = plan.candidate_issue_gate.get("reason_descriptions")
    if not isinstance(candidate_issue_gate_reason_descriptions, dict):
        candidate_issue_gate_reason_descriptions = {}
    candidate_issue_gate_reason_codes = plan.candidate_issue_gate.get("reason_codes")
    if not isinstance(candidate_issue_gate_reason_codes, list):
        candidate_issue_gate_reason_codes = []
    candidate_issue_gate_required_actions = plan.candidate_issue_gate.get("required_actions")
    if not isinstance(candidate_issue_gate_required_actions, list):
        candidate_issue_gate_required_actions = []
    candidate_issue_gate_primary_reason_code = (
        candidate_issue_gate_reason_codes[0] if candidate_issue_gate_reason_codes else None
    )
    candidate_issue_gate_reason_code_boundary = {
        "first_code": candidate_issue_gate_reason_codes[0]
        if candidate_issue_gate_reason_codes
        else None,
        "last_code": candidate_issue_gate_reason_codes[-1]
        if candidate_issue_gate_reason_codes
        else None,
    }
    candidate_issue_gate_required_action_boundary = {
        "first_action": candidate_issue_gate_required_actions[0]
        if candidate_issue_gate_required_actions
        else None,
        "last_action": candidate_issue_gate_required_actions[-1]
        if candidate_issue_gate_required_actions
        else None,
    }
    candidate_issue_gate_primary_reason_description = None
    if candidate_issue_gate_primary_reason_code is not None:
        candidate_issue_gate_primary_reason_description = candidate_issue_gate_reason_descriptions.get(
            candidate_issue_gate_primary_reason_code
        )
    candidate_issue_gate_summary = plan.candidate_issue_gate.get("summary")
    candidate_issue_gate_evidence_keys = list(candidate_issue_gate_evidence)
    candidate_issue_gate_evidence_key_boundary = {
        "first_key": candidate_issue_gate_evidence_keys[0]
        if candidate_issue_gate_evidence_keys
        else None,
        "last_key": candidate_issue_gate_evidence_keys[-1]
        if candidate_issue_gate_evidence_keys
        else None,
    }
    release_draft_required_actions = _release_draft_required_actions(plan.release_draft_issues)
    release_draft_required_action_boundary = {
        "first_action": release_draft_required_actions[0]
        if release_draft_required_actions
        else None,
        "last_action": release_draft_required_actions[-1]
        if release_draft_required_actions
        else None,
    }
    release_draft_required_action_preview = release_draft_required_actions[:8]
    release_draft_required_action_tail = release_draft_required_actions[-8:]
    release_draft_issue_boundary = {
        "first_issue": plan.release_draft_issues[0]
        if plan.release_draft_issues
        else None,
        "last_issue": plan.release_draft_issues[-1]
        if plan.release_draft_issues
        else None,
    }
    release_draft_issue_preview = plan.release_draft_issues[:8]
    release_draft_issue_tail = plan.release_draft_issues[-8:]
    validation_commands = _issue_artifact_validation_commands(plan)
    validation_command_boundary = {
        "first_command": validation_commands[0] if validation_commands else None,
        "last_command": validation_commands[-1] if validation_commands else None,
    }
    validation_command_preview = validation_commands[:8]
    validation_command_tail = validation_commands[-8:]
    review_checklist = _issue_artifact_review_checklist()
    review_checklist_boundary = {
        "first_item": review_checklist[0] if review_checklist else None,
        "last_item": review_checklist[-1] if review_checklist else None,
    }
    review_checklist_preview = review_checklist[:8]
    review_checklist_tail = review_checklist[-8:]
    create_issues_safety_contract_keys = list(create_issues_safety_contract)
    create_issues_safety_contract_key_boundary = {
        "first_key": create_issues_safety_contract_keys[0]
        if create_issues_safety_contract_keys
        else None,
        "last_key": create_issues_safety_contract_keys[-1]
        if create_issues_safety_contract_keys
        else None,
    }
    create_issues_safety_contract_key_preview = create_issues_safety_contract_keys[:8]
    create_issues_safety_contract_key_tail = create_issues_safety_contract_keys[-8:]
    publication_ref_context_keys = list(plan.publication_ref_context)
    publication_ref_context_key_boundary = {
        "first_key": publication_ref_context_keys[0]
        if publication_ref_context_keys
        else None,
        "last_key": publication_ref_context_keys[-1]
        if publication_ref_context_keys
        else None,
    }
    publication_ref_context_key_preview = publication_ref_context_keys[:8]
    publication_ref_context_key_tail = publication_ref_context_keys[-8:]
    publication_publish_command_boundary = {
        "first_command": plan.publication_publish_commands[0]
        if plan.publication_publish_commands
        else None,
        "last_command": plan.publication_publish_commands[-1]
        if plan.publication_publish_commands
        else None,
    }
    publication_worktree_status_boundary = {
        "first_item": plan.publication_worktree_status[0]
        if plan.publication_worktree_status
        else None,
        "last_item": plan.publication_worktree_status[-1]
        if plan.publication_worktree_status
        else None,
    }
    release_draft_handoff_keys = list(release_draft_handoff)
    release_draft_handoff_key_boundary = {
        "first_key": release_draft_handoff_keys[0]
        if release_draft_handoff_keys
        else None,
        "last_key": release_draft_handoff_keys[-1]
        if release_draft_handoff_keys
        else None,
    }
    release_draft_handoff_key_preview = release_draft_handoff_keys[:8]
    release_draft_handoff_key_tail = release_draft_handoff_keys[-8:]
    artifact_file_keys = list(artifact_files)
    artifact_files_key_boundary = {
        "first_key": artifact_file_keys[0] if artifact_file_keys else None,
        "last_key": artifact_file_keys[-1] if artifact_file_keys else None,
    }
    artifact_files_key_preview = artifact_file_keys[:8]
    artifact_files_key_tail = artifact_file_keys[-8:]
    publication_visibility_keys = list(plan.publication_visibility)
    publication_visibility_key_boundary = {
        "first_key": publication_visibility_keys[0]
        if publication_visibility_keys
        else None,
        "last_key": publication_visibility_keys[-1]
        if publication_visibility_keys
        else None,
    }
    publication_visibility_key_preview = publication_visibility_keys[:8]
    publication_visibility_key_tail = publication_visibility_keys[-8:]
    tag_publish_decision_keys = list(plan.publication_tag_publish_decision)
    tag_publish_decision_key_boundary = {
        "first_key": tag_publish_decision_keys[0]
        if tag_publish_decision_keys
        else None,
        "last_key": tag_publish_decision_keys[-1]
        if tag_publish_decision_keys
        else None,
    }
    tag_publish_decision_key_preview = tag_publish_decision_keys[:8]
    tag_publish_decision_key_tail = tag_publish_decision_keys[-8:]
    case_promotion_evidence_summary_keys = list(plan.case_promotion_evidence_summary)
    case_promotion_evidence_summary_key_boundary = {
        "first_key": case_promotion_evidence_summary_keys[0]
        if case_promotion_evidence_summary_keys
        else None,
        "last_key": case_promotion_evidence_summary_keys[-1]
        if case_promotion_evidence_summary_keys
        else None,
    }
    case_promotion_evidence_summary_key_preview = case_promotion_evidence_summary_keys[:8]
    case_promotion_evidence_summary_key_tail = case_promotion_evidence_summary_keys[-8:]
    case_promotion_evidence_primary_task = plan.case_promotion_evidence_summary.get("primary_task")
    if not isinstance(case_promotion_evidence_primary_task, dict):
        case_promotion_evidence_primary_task = {}
    case_promotion_evidence_primary_next_task = plan.case_promotion_evidence_summary.get(
        "primary_next_task"
    )
    if not isinstance(case_promotion_evidence_primary_next_task, dict):
        case_promotion_evidence_primary_next_task = {}
    case_promotion_evidence_primary_runbook = _primary_runbook_from_summary(
        plan.case_promotion_evidence_summary
    )
    case_promotion_evidence_primary_runbook_steps = _runbook_steps(
        case_promotion_evidence_primary_runbook
    )
    case_promotion_evidence_primary_runbook_first_command = _runbook_first_command(
        case_promotion_evidence_primary_runbook
    )
    command_plan_summary = plan.case_promotion_command_plan_summary
    blocker_boundary = {
        "first_item": plan.blockers[0] if plan.blockers else None,
        "last_item": plan.blockers[-1] if plan.blockers else None,
    }
    blocker_preview = plan.blockers[:8]
    blocker_tail = plan.blockers[-8:]
    next_action_boundary = {
        "first_item": plan.next_actions[0] if plan.next_actions else None,
        "last_item": plan.next_actions[-1] if plan.next_actions else None,
    }
    next_action_preview = plan.next_actions[:8]
    next_action_tail = plan.next_actions[-8:]
    publication_next_action_boundary = {
        "first_item": plan.publication_next_actions[0]
        if plan.publication_next_actions
        else None,
        "last_item": plan.publication_next_actions[-1]
        if plan.publication_next_actions
        else None,
    }
    publication_next_action_preview = plan.publication_next_actions[:8]
    publication_next_action_tail = plan.publication_next_actions[-8:]
    artifact_manifest_payload = _artifact_manifest_payload_without_summary(
        plan=plan,
        candidate_cases=candidate_cases,
        review_order=review_order,
        issue_body_inventory=issue_body_inventory,
        issue_body_summary=issue_body_summary,
        issue_metadata_summary=issue_metadata_summary,
        create_issues_safety=create_issues_safety,
        artifact_files=artifact_files,
    )
    issue_body_inventory_preview = issue_body_inventory[:8]
    issue_body_inventory_tail = issue_body_inventory[-8:]
    issue_body_inventory_boundary = {
        "first_entry": issue_body_inventory[0] if issue_body_inventory else None,
        "last_entry": issue_body_inventory[-1] if issue_body_inventory else None,
    }
    issue_body_summary_keys = list(issue_body_summary)
    issue_body_summary_key_boundary = {
        "first_key": issue_body_summary_keys[0] if issue_body_summary_keys else None,
        "last_key": issue_body_summary_keys[-1] if issue_body_summary_keys else None,
    }
    issue_body_summary_key_preview = issue_body_summary_keys[:8]
    issue_body_summary_key_tail = issue_body_summary_keys[-8:]
    website_deploy_command = _standard_release_flow_website_deploy_command(
        plan.standard_release_flow
    )
    standard_release_flow_steps = _standard_release_flow_steps(plan.standard_release_flow)
    standard_release_flow_step_names = _standard_release_flow_step_names(
        plan.standard_release_flow
    )
    standard_release_flow_step_boundary = _standard_release_flow_step_boundary(
        plan.standard_release_flow
    )
    standard_release_flow_step_status_counts = _standard_release_flow_step_status_counts(
        plan.standard_release_flow
    )
    return {
        "artifact_bundle_summary_key_count": len(ARTIFACT_BUNDLE_SUMMARY_KEYS),
        "artifact_bundle_summary_keys_sha256": _stable_json_sha256(ARTIFACT_BUNDLE_SUMMARY_KEYS),
        "artifact_bundle_summary_key_preview_count": len(ARTIFACT_BUNDLE_SUMMARY_KEY_PREVIEW),
        "artifact_bundle_summary_key_preview": list(ARTIFACT_BUNDLE_SUMMARY_KEY_PREVIEW),
        "artifact_bundle_summary_key_preview_sha256": _stable_json_sha256(
            ARTIFACT_BUNDLE_SUMMARY_KEY_PREVIEW
        ),
        "artifact_bundle_summary_key_tail_count": len(ARTIFACT_BUNDLE_SUMMARY_KEY_TAIL),
        "artifact_bundle_summary_key_tail": list(ARTIFACT_BUNDLE_SUMMARY_KEY_TAIL),
        "artifact_bundle_summary_key_tail_sha256": _stable_json_sha256(
            ARTIFACT_BUNDLE_SUMMARY_KEY_TAIL
        ),
        "artifact_bundle_summary_first_key": ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY["first_key"],
        "artifact_bundle_summary_last_key": ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY["last_key"],
        "artifact_bundle_summary_key_boundary_sha256": _stable_json_sha256(
            ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY
        ),
        "artifact_manifest_schema_version": ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "artifact_manifest_key_count": len(ARTIFACT_MANIFEST_KEYS),
        "artifact_manifest_keys_sha256": _stable_json_sha256(ARTIFACT_MANIFEST_KEYS),
        "artifact_manifest_first_key": ARTIFACT_MANIFEST_KEY_BOUNDARY["first_key"],
        "artifact_manifest_last_key": ARTIFACT_MANIFEST_KEY_BOUNDARY["last_key"],
        "artifact_manifest_key_boundary_sha256": _stable_json_sha256(
            ARTIFACT_MANIFEST_KEY_BOUNDARY
        ),
        "artifact_manifest_key_preview_count": len(ARTIFACT_MANIFEST_KEY_PREVIEW),
        "artifact_manifest_key_preview": list(ARTIFACT_MANIFEST_KEY_PREVIEW),
        "artifact_manifest_key_preview_sha256": _stable_json_sha256(
            ARTIFACT_MANIFEST_KEY_PREVIEW
        ),
        "artifact_manifest_key_tail_count": len(ARTIFACT_MANIFEST_KEY_TAIL),
        "artifact_manifest_key_tail": list(ARTIFACT_MANIFEST_KEY_TAIL),
        "artifact_manifest_key_tail_sha256": _stable_json_sha256(
            ARTIFACT_MANIFEST_KEY_TAIL
        ),
        "artifact_manifest_payload_key_count": len(artifact_manifest_payload),
        "artifact_manifest_payload_first_key": ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY[
            "first_key"
        ],
        "artifact_manifest_payload_last_key": ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY[
            "last_key"
        ],
        "artifact_manifest_payload_key_boundary_sha256": _stable_json_sha256(
            ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY
        ),
        "artifact_manifest_payload_key_preview_count": len(
            ARTIFACT_MANIFEST_PAYLOAD_KEY_PREVIEW
        ),
        "artifact_manifest_payload_key_preview": list(
            ARTIFACT_MANIFEST_PAYLOAD_KEY_PREVIEW
        ),
        "artifact_manifest_payload_key_preview_sha256": _stable_json_sha256(
            ARTIFACT_MANIFEST_PAYLOAD_KEY_PREVIEW
        ),
        "artifact_manifest_payload_key_tail_count": len(
            ARTIFACT_MANIFEST_PAYLOAD_KEY_TAIL
        ),
        "artifact_manifest_payload_key_tail": list(
            ARTIFACT_MANIFEST_PAYLOAD_KEY_TAIL
        ),
        "artifact_manifest_payload_key_tail_sha256": _stable_json_sha256(
            ARTIFACT_MANIFEST_PAYLOAD_KEY_TAIL
        ),
        "artifact_manifest_payload_sha256": _stable_json_sha256(artifact_manifest_payload),
        "target_version": plan.target_version,
        "candidate_count": len(candidate_cases),
        "candidate_cases_first_case": candidate_cases[0] if candidate_cases else None,
        "candidate_cases_last_case": candidate_cases[-1] if candidate_cases else None,
        "candidate_cases_boundary_sha256": _stable_json_sha256(
            {
                "first_case": candidate_cases[0] if candidate_cases else None,
                "last_case": candidate_cases[-1] if candidate_cases else None,
            }
        ),
        "candidate_cases_preview_count": len(candidate_cases[:8]),
        "candidate_cases_preview": list(candidate_cases[:8]),
        "candidate_cases_preview_sha256": _stable_json_sha256(candidate_cases[:8]),
        "candidate_cases_tail_count": len(candidate_cases[-8:]),
        "candidate_cases_tail": list(candidate_cases[-8:]),
        "candidate_cases_tail_sha256": _stable_json_sha256(candidate_cases[-8:]),
        "candidate_cases_sha256": _stable_json_sha256(candidate_cases),
        "case_promotion_evidence_summary_key_count": len(plan.case_promotion_evidence_summary),
        "case_promotion_evidence_summary_keys_sha256": _stable_json_sha256(
            case_promotion_evidence_summary_keys
        ),
        "case_promotion_evidence_summary_first_key": (
            case_promotion_evidence_summary_key_boundary["first_key"]
        ),
        "case_promotion_evidence_summary_last_key": (
            case_promotion_evidence_summary_key_boundary["last_key"]
        ),
        "case_promotion_evidence_summary_key_boundary_sha256": _stable_json_sha256(
            case_promotion_evidence_summary_key_boundary
        ),
        "case_promotion_evidence_summary_key_preview_count": len(
            case_promotion_evidence_summary_key_preview
        ),
        "case_promotion_evidence_summary_key_preview": list(
            case_promotion_evidence_summary_key_preview
        ),
        "case_promotion_evidence_summary_key_preview_sha256": _stable_json_sha256(
            case_promotion_evidence_summary_key_preview
        ),
        "case_promotion_evidence_summary_key_tail_count": len(
            case_promotion_evidence_summary_key_tail
        ),
        "case_promotion_evidence_summary_key_tail": list(
            case_promotion_evidence_summary_key_tail
        ),
        "case_promotion_evidence_summary_key_tail_sha256": _stable_json_sha256(
            case_promotion_evidence_summary_key_tail
        ),
        "case_promotion_evidence_summary_sha256": _stable_json_sha256(
            plan.case_promotion_evidence_summary
        ),
        "case_promotion_evidence_candidate_count": plan.case_promotion_evidence_summary.get(
            "candidate_count"
        ),
        "case_promotion_evidence_task_count": plan.case_promotion_evidence_summary.get(
            "task_count"
        ),
        "case_promotion_evidence_pending_count": plan.case_promotion_evidence_summary.get(
            "pending_count"
        ),
        "case_promotion_evidence_blocked_count": plan.case_promotion_evidence_summary.get(
            "blocked_count"
        ),
        "case_promotion_evidence_complete_count": plan.case_promotion_evidence_summary.get(
            "complete_count"
        ),
        "case_promotion_evidence_primary_next_action": (
            plan.case_promotion_evidence_summary.get("primary_next_action")
        ),
        "case_promotion_evidence_primary_case_id": (
            case_promotion_evidence_primary_task.get("case_id")
        ),
        "case_promotion_evidence_primary_task": (
            case_promotion_evidence_primary_task.get("task")
        ),
        "case_promotion_evidence_primary_status": (
            case_promotion_evidence_primary_task.get("status")
        ),
        "case_promotion_evidence_primary_evidence_sha256": _stable_json_sha256(
            case_promotion_evidence_primary_task.get("evidence")
        ),
        "case_promotion_evidence_primary_detail_sha256": _stable_json_sha256(
            case_promotion_evidence_primary_task
        ),
        "case_promotion_evidence_primary_next_task_sha256": _stable_json_sha256(
            case_promotion_evidence_primary_next_task
        ),
        "case_promotion_evidence_primary_runbook_step_count": len(
            case_promotion_evidence_primary_runbook_steps
        ),
        "case_promotion_evidence_primary_runbook_steps": list(
            case_promotion_evidence_primary_runbook_steps
        ),
        "case_promotion_evidence_primary_runbook_steps_sha256": _stable_json_sha256(
            case_promotion_evidence_primary_runbook_steps
        ),
        "case_promotion_evidence_primary_runbook_first_step": _runbook_first_step_name(
            case_promotion_evidence_primary_runbook
        ),
        "case_promotion_evidence_primary_runbook_first_command": (
            case_promotion_evidence_primary_runbook_first_command
        ),
        "case_promotion_evidence_primary_runbook_first_command_sha256": (
            _stable_json_sha256(case_promotion_evidence_primary_runbook_first_command)
            if case_promotion_evidence_primary_runbook_first_command
            else None
        ),
        "case_promotion_evidence_primary_runbook_sha256": _stable_json_sha256(
            case_promotion_evidence_primary_runbook
        ),
        "case_promotion_command_plan_summary_sha256": _stable_json_sha256(
            command_plan_summary
        ),
        "case_promotion_command_plan_candidate_count": command_plan_summary.get(
            "candidate_count"
        ),
        "case_promotion_command_plan_command_count": command_plan_summary.get("command_count"),
        "case_promotion_command_plan_missing_command_count": command_plan_summary.get(
            "missing_command_count"
        ),
        "case_promotion_command_plan_all_declared": command_plan_summary.get("all_declared"),
        "standard_release_flow_status": plan.standard_release_flow.get("status"),
        "standard_release_flow_target_tag": plan.standard_release_flow.get("target_tag"),
        "standard_release_flow_primary_next_action": plan.standard_release_flow.get(
            "primary_next_action"
        ),
        "standard_release_flow_command_count": plan.standard_release_flow.get(
            "command_count"
        ),
        "standard_release_flow_commands_sha256": plan.standard_release_flow.get(
            "commands_sha256"
        ),
        "standard_release_flow_step_count": len(standard_release_flow_steps),
        "standard_release_flow_step_names": list(standard_release_flow_step_names),
        "standard_release_flow_step_names_sha256": _stable_json_sha256(
            standard_release_flow_step_names
        ),
        "standard_release_flow_steps_sha256": _stable_json_sha256(
            standard_release_flow_steps
        ),
        "standard_release_flow_first_step_name": (
            standard_release_flow_step_boundary["first_step_name"]
        ),
        "standard_release_flow_last_step_name": (
            standard_release_flow_step_boundary["last_step_name"]
        ),
        "standard_release_flow_step_boundary_sha256": _stable_json_sha256(
            standard_release_flow_step_boundary
        ),
        "standard_release_flow_step_status_counts": standard_release_flow_step_status_counts,
        "standard_release_flow_step_status_counts_sha256": _stable_json_sha256(
            standard_release_flow_step_status_counts
        ),
        "standard_release_flow_primary_blocked_step_name": (
            _standard_release_flow_primary_step_name_with_status_prefix(
                plan.standard_release_flow, "blocked"
            )
        ),
        "standard_release_flow_primary_pending_step_name": (
            _standard_release_flow_primary_step_name_with_status_prefix(
                plan.standard_release_flow, "pending"
            )
        ),
        "standard_release_flow_has_website_deploy": website_deploy_command is not None,
        "standard_release_flow_website_deploy_command": website_deploy_command,
        "standard_release_flow_website_deploy_command_sha256": (
            _stable_json_sha256(website_deploy_command) if website_deploy_command else None
        ),
        "standard_release_flow_sha256": _stable_json_sha256(plan.standard_release_flow),
        "body_count": issue_body_summary["body_count"],
        "issue_body_inventory_preview_count": len(issue_body_inventory_preview),
        "issue_body_inventory_preview": list(issue_body_inventory_preview),
        "issue_body_inventory_preview_sha256": _stable_json_sha256(
            issue_body_inventory_preview
        ),
        "issue_body_inventory_first_entry": issue_body_inventory_boundary[
            "first_entry"
        ],
        "issue_body_inventory_last_entry": issue_body_inventory_boundary["last_entry"],
        "issue_body_inventory_boundary_sha256": _stable_json_sha256(
            issue_body_inventory_boundary
        ),
        "issue_body_inventory_tail_count": len(issue_body_inventory_tail),
        "issue_body_inventory_tail": list(issue_body_inventory_tail),
        "issue_body_inventory_tail_sha256": _stable_json_sha256(
            issue_body_inventory_tail
        ),
        "issue_body_summary_key_count": len(issue_body_summary),
        "issue_body_summary_keys_sha256": _stable_json_sha256(
            issue_body_summary_keys
        ),
        "issue_body_summary_first_key": issue_body_summary_key_boundary[
            "first_key"
        ],
        "issue_body_summary_last_key": issue_body_summary_key_boundary["last_key"],
        "issue_body_summary_key_boundary_sha256": _stable_json_sha256(
            issue_body_summary_key_boundary
        ),
        "issue_body_summary_key_preview_count": len(issue_body_summary_key_preview),
        "issue_body_summary_key_preview": list(issue_body_summary_key_preview),
        "issue_body_summary_key_preview_sha256": _stable_json_sha256(
            issue_body_summary_key_preview
        ),
        "issue_body_summary_key_tail_count": len(issue_body_summary_key_tail),
        "issue_body_summary_key_tail": list(issue_body_summary_key_tail),
        "issue_body_summary_key_tail_sha256": _stable_json_sha256(
            issue_body_summary_key_tail
        ),
        "issue_body_summary_sha256": _stable_json_sha256(issue_body_summary),
        "review_item_count": len(review_order),
        "review_order_sha256": hashlib.sha256(review_order_digest_source).hexdigest(),
        "review_order_first_item": review_order_boundary["first_item"],
        "review_order_last_item": review_order_boundary["last_item"],
        "review_order_boundary_sha256": _stable_json_sha256(review_order_boundary),
        "review_order_preview_count": len(review_order_preview),
        "review_order_preview": list(review_order_preview),
        "review_order_preview_sha256": _stable_json_sha256(review_order_preview),
        "review_order_tail_count": len(review_order_tail),
        "review_order_tail": list(review_order_tail),
        "review_order_tail_sha256": _stable_json_sha256(review_order_tail),
        "inventory_sha256": issue_body_summary["inventory_sha256"],
        "issue_metadata_count": issue_metadata_summary["metadata_count"],
        "issue_metadata_sha256": issue_metadata_summary["metadata_sha256"],
        "issue_metadata_first_item": issue_metadata_summary["metadata_first_item"],
        "issue_metadata_last_item": issue_metadata_summary["metadata_last_item"],
        "issue_metadata_boundary_sha256": issue_metadata_summary[
            "metadata_boundary_sha256"
        ],
        "issue_metadata_preview_count": issue_metadata_summary[
            "metadata_preview_count"
        ],
        "issue_metadata_preview": list(issue_metadata_summary["metadata_preview"]),
        "issue_metadata_preview_sha256": issue_metadata_summary[
            "metadata_preview_sha256"
        ],
        "issue_metadata_tail_count": issue_metadata_summary[
            "metadata_tail_count"
        ],
        "issue_metadata_tail": list(issue_metadata_summary["metadata_tail"]),
        "issue_metadata_tail_sha256": issue_metadata_summary[
            "metadata_tail_sha256"
        ],
        "artifact_files_key_count": len(artifact_files),
        "artifact_files_sha256": _stable_json_sha256(artifact_files),
        "artifact_files_first_key": artifact_files_key_boundary["first_key"],
        "artifact_files_last_key": artifact_files_key_boundary["last_key"],
        "artifact_files_key_boundary_sha256": _stable_json_sha256(
            artifact_files_key_boundary
        ),
        "artifact_files_key_preview_count": len(artifact_files_key_preview),
        "artifact_files_key_preview": list(artifact_files_key_preview),
        "artifact_files_key_preview_sha256": _stable_json_sha256(
            artifact_files_key_preview
        ),
        "artifact_files_key_tail_count": len(artifact_files_key_tail),
        "artifact_files_key_tail": list(artifact_files_key_tail),
        "artifact_files_key_tail_sha256": _stable_json_sha256(
            artifact_files_key_tail
        ),
        "issue_artifacts_command_sha256": _stable_json_sha256(plan.issue_artifacts_command),
        "plan_report_command_sha256": _stable_json_sha256(plan.plan_report_command),
        "publication_visibility_key_count": len(plan.publication_visibility),
        "publication_visibility_sha256": _stable_json_sha256(plan.publication_visibility),
        "publication_visibility_first_key": publication_visibility_key_boundary[
            "first_key"
        ],
        "publication_visibility_last_key": publication_visibility_key_boundary[
            "last_key"
        ],
        "publication_visibility_key_boundary_sha256": _stable_json_sha256(
            publication_visibility_key_boundary
        ),
        "publication_visibility_key_preview_count": len(
            publication_visibility_key_preview
        ),
        "publication_visibility_key_preview": list(publication_visibility_key_preview),
        "publication_visibility_key_preview_sha256": _stable_json_sha256(
            publication_visibility_key_preview
        ),
        "publication_visibility_key_tail_count": len(
            publication_visibility_key_tail
        ),
        "publication_visibility_key_tail": list(publication_visibility_key_tail),
        "publication_visibility_key_tail_sha256": _stable_json_sha256(
            publication_visibility_key_tail
        ),
        "publication_visibility_summary_sha256": _stable_json_sha256(
            plan.publication_visibility.get("summary")
        ),
        "publication_tag_publish_decision_key_count": len(
            plan.publication_tag_publish_decision
        ),
        "publication_tag_publish_decision_sha256": _stable_json_sha256(
            plan.publication_tag_publish_decision
        ),
        "publication_tag_publish_decision_first_key": tag_publish_decision_key_boundary[
            "first_key"
        ],
        "publication_tag_publish_decision_last_key": tag_publish_decision_key_boundary[
            "last_key"
        ],
        "publication_tag_publish_decision_key_boundary_sha256": _stable_json_sha256(
            tag_publish_decision_key_boundary
        ),
        "publication_tag_publish_decision_key_preview_count": len(
            tag_publish_decision_key_preview
        ),
        "publication_tag_publish_decision_key_preview": list(
            tag_publish_decision_key_preview
        ),
        "publication_tag_publish_decision_key_preview_sha256": _stable_json_sha256(
            tag_publish_decision_key_preview
        ),
        "publication_tag_publish_decision_key_tail_count": len(
            tag_publish_decision_key_tail
        ),
        "publication_tag_publish_decision_key_tail": list(
            tag_publish_decision_key_tail
        ),
        "publication_tag_publish_decision_key_tail_sha256": _stable_json_sha256(
            tag_publish_decision_key_tail
        ),
        "publication_tag_publish_decision_status": (
            plan.publication_tag_publish_decision.get("status")
        ),
        "publication_tag_can_push": plan.publication_tag_publish_decision.get(
            "can_push_tag"
        ),
        "publication_tag_required_action_sha256": _stable_json_sha256(
            plan.publication_tag_publish_decision.get("required_action")
        ),
        "publication_target_tag": plan.publication_tag_publish_decision.get("target_tag"),
        "publication_target_tag_status": plan.publication_tag_publish_decision.get(
            "target_tag_status"
        ),
        "publication_target_tag_primary_command": (
            plan.publication_tag_publish_decision.get("target_tag_primary_command")
        ),
        "publication_target_tag_command_count": plan.publication_tag_publish_decision.get(
            "target_tag_command_count"
        ),
        "publication_target_tag_commands_sha256": (
            plan.publication_tag_publish_decision.get("target_tag_commands_sha256")
        ),
        "publication_target_tag_required_action_sha256": _stable_json_sha256(
            plan.publication_tag_publish_decision.get("target_tag_required_action")
        ),
        "publication_target_tag_release_gate_status": (
            plan.publication_tag_publish_decision.get("target_tag_release_gate_status")
        ),
        "publication_target_tag_release_gate_blocker_count": (
            plan.publication_tag_publish_decision.get(
                "target_tag_release_gate_blocker_count"
            )
        ),
        "publication_target_tag_release_gate_primary_blocker": (
            plan.publication_tag_publish_decision.get(
                "target_tag_release_gate_primary_blocker"
            )
        ),
        "publication_target_tag_release_gate_required_action_sha256": _stable_json_sha256(
            plan.publication_tag_publish_decision.get(
                "target_tag_release_gate_required_action"
            )
        ),
        "publication_target_tag_release_gate_blockers_sha256": (
            plan.publication_tag_publish_decision.get(
                "target_tag_release_gate_blockers_sha256"
            )
        ),
        "publication_blocker_count": len(plan.publication_blockers),
        "publication_blockers_sha256": _stable_json_sha256(plan.publication_blockers),
        "publication_primary_blocker": _publication_primary_blocker(plan),
        "blocker_count": len(plan.blockers),
        "blockers_sha256": _stable_json_sha256(plan.blockers),
        "blocker_first_item": blocker_boundary["first_item"],
        "blocker_last_item": blocker_boundary["last_item"],
        "blocker_boundary_sha256": _stable_json_sha256(blocker_boundary),
        "blocker_preview_count": len(blocker_preview),
        "blocker_preview": list(blocker_preview),
        "blocker_preview_sha256": _stable_json_sha256(blocker_preview),
        "blocker_tail_count": len(blocker_tail),
        "blocker_tail": list(blocker_tail),
        "blocker_tail_sha256": _stable_json_sha256(blocker_tail),
        "next_action_count": len(plan.next_actions),
        "next_actions_sha256": _stable_json_sha256(plan.next_actions),
        "next_action_first_item": next_action_boundary["first_item"],
        "next_action_last_item": next_action_boundary["last_item"],
        "next_action_boundary_sha256": _stable_json_sha256(next_action_boundary),
        "next_action_preview_count": len(next_action_preview),
        "next_action_preview": list(next_action_preview),
        "next_action_preview_sha256": _stable_json_sha256(next_action_preview),
        "next_action_tail_count": len(next_action_tail),
        "next_action_tail": list(next_action_tail),
        "next_action_tail_sha256": _stable_json_sha256(next_action_tail),
        "publication_next_action_count": len(plan.publication_next_actions),
        "publication_next_actions_sha256": _stable_json_sha256(plan.publication_next_actions),
        "publication_next_action_first_item": publication_next_action_boundary[
            "first_item"
        ],
        "publication_next_action_last_item": publication_next_action_boundary[
            "last_item"
        ],
        "publication_next_action_boundary_sha256": _stable_json_sha256(
            publication_next_action_boundary
        ),
        "publication_next_action_preview_count": len(publication_next_action_preview),
        "publication_next_action_preview": list(publication_next_action_preview),
        "publication_next_action_preview_sha256": _stable_json_sha256(
            publication_next_action_preview
        ),
        "publication_next_action_tail_count": len(publication_next_action_tail),
        "publication_next_action_tail": list(publication_next_action_tail),
        "publication_next_action_tail_sha256": _stable_json_sha256(
            publication_next_action_tail
        ),
        "publication_primary_next_action": (
            plan.publication_next_actions[0] if plan.publication_next_actions else None
        ),
        "publication_handoff_key_count": len(publication_handoff),
        "publication_handoff_schema_version": publication_handoff.get("schema_version"),
        "publication_handoff_first_key": publication_handoff_key_boundary["first_key"],
        "publication_handoff_last_key": publication_handoff_key_boundary["last_key"],
        "publication_handoff_key_boundary_sha256": _stable_json_sha256(
            publication_handoff_key_boundary
        ),
        "publication_handoff_key_preview_count": len(publication_handoff_key_preview),
        "publication_handoff_key_preview": list(publication_handoff_key_preview),
        "publication_handoff_key_preview_sha256": _stable_json_sha256(
            publication_handoff_key_preview
        ),
        "publication_handoff_key_tail_count": len(publication_handoff_key_tail),
        "publication_handoff_key_tail": list(publication_handoff_key_tail),
        "publication_handoff_key_tail_sha256": _stable_json_sha256(
            publication_handoff_key_tail
        ),
        "publication_handoff_sha256": _stable_json_sha256(publication_handoff),
        "publication_handoff_candidate_issue_gate_primary_reason_code": publication_handoff.get(
            "candidate_issue_gate_primary_reason_code"
        ),
        "publication_handoff_candidate_issue_gate_primary_reason_description": publication_handoff.get(
            "candidate_issue_gate_primary_reason_description"
        ),
        "publication_handoff_candidate_issue_gate_primary_required_action": publication_handoff.get(
            "candidate_issue_gate_primary_required_action"
        ),
        "commit_cadence_status": plan.commit_cadence.get("status"),
        "commit_cadence_commit_day_count": plan.commit_cadence.get("commit_day_count"),
        "commit_cadence_min_commit_days": plan.commit_cadence.get("min_commit_days"),
        "commit_cadence_missing_commit_days": plan.commit_cadence.get("missing_commit_days"),
        "commit_cadence_release_count_today": plan.commit_cadence.get("release_count_today"),
        "commit_cadence_max_daily_releases": plan.commit_cadence.get("max_daily_releases"),
        "commit_cadence_daily_release_limit_ok": plan.commit_cadence.get("daily_release_limit_ok"),
        "commit_cadence_next_action_count": len(
            plan.commit_cadence.get("next_actions", [])
            if isinstance(plan.commit_cadence.get("next_actions"), list)
            else []
        ),
        "commit_cadence_primary_next_action": _commit_cadence_primary_next_action(plan),
        "commit_cadence_commit_days_sha256": _stable_json_sha256(
            plan.commit_cadence.get("commit_days", [])
        ),
        "commit_cadence_release_tags_today_sha256": _stable_json_sha256(
            plan.commit_cadence.get("release_tags_today", [])
        ),
        "commit_cadence_next_actions_sha256": _stable_json_sha256(
            plan.commit_cadence.get("next_actions", [])
        ),
        "publication_ref_context_key_count": len(plan.publication_ref_context),
        "publication_ref_context_sha256": _stable_json_sha256(plan.publication_ref_context),
        "publication_ref_context_first_key": publication_ref_context_key_boundary[
            "first_key"
        ],
        "publication_ref_context_last_key": publication_ref_context_key_boundary[
            "last_key"
        ],
        "publication_ref_context_key_boundary_sha256": _stable_json_sha256(
            publication_ref_context_key_boundary
        ),
        "publication_ref_context_key_preview_count": len(
            publication_ref_context_key_preview
        ),
        "publication_ref_context_key_preview": list(
            publication_ref_context_key_preview
        ),
        "publication_ref_context_key_preview_sha256": _stable_json_sha256(
            publication_ref_context_key_preview
        ),
        "publication_ref_context_key_tail_count": len(
            publication_ref_context_key_tail
        ),
        "publication_ref_context_key_tail": list(publication_ref_context_key_tail),
        "publication_ref_context_key_tail_sha256": _stable_json_sha256(
            publication_ref_context_key_tail
        ),
        "publication_publish_command_count": plan.publication_publish_command_count,
        "publication_publish_commands_sha256": _stable_json_sha256(plan.publication_publish_commands),
        "publication_publish_first_command": publication_publish_command_boundary[
            "first_command"
        ],
        "publication_publish_last_command": publication_publish_command_boundary[
            "last_command"
        ],
        "publication_publish_command_boundary_sha256": _stable_json_sha256(
            publication_publish_command_boundary
        ),
        "publication_primary_publish_command": (
            plan.publication_publish_commands[0] if plan.publication_publish_commands else None
        ),
        "publication_publish_script_path_sha256": _stable_json_sha256(
            plan.publication_publish_script_path
        ),
        "publication_publish_script_command_sha256": _stable_json_sha256(
            plan.publication_publish_script_command
        ),
        "publication_worktree_status_count": len(plan.publication_worktree_status),
        "publication_worktree_status_sha256": _stable_json_sha256(plan.publication_worktree_status),
        "publication_worktree_status_first_item": publication_worktree_status_boundary[
            "first_item"
        ],
        "publication_worktree_status_last_item": publication_worktree_status_boundary[
            "last_item"
        ],
        "publication_worktree_status_boundary_sha256": _stable_json_sha256(
            publication_worktree_status_boundary
        ),
        "release_draft_handoff_key_count": len(release_draft_handoff),
        "release_draft_handoff_schema_version": release_draft_handoff.get("schema_version"),
        "release_draft_handoff_primary_issue": release_draft_handoff.get("primary_issue"),
        "release_draft_handoff_primary_required_action": release_draft_handoff.get(
            "primary_required_action"
        ),
        "release_draft_handoff_first_key": release_draft_handoff_key_boundary[
            "first_key"
        ],
        "release_draft_handoff_last_key": release_draft_handoff_key_boundary[
            "last_key"
        ],
        "release_draft_handoff_key_boundary_sha256": _stable_json_sha256(
            release_draft_handoff_key_boundary
        ),
        "release_draft_handoff_key_preview_count": len(
            release_draft_handoff_key_preview
        ),
        "release_draft_handoff_key_preview": list(
            release_draft_handoff_key_preview
        ),
        "release_draft_handoff_key_preview_sha256": _stable_json_sha256(
            release_draft_handoff_key_preview
        ),
        "release_draft_handoff_key_tail_count": len(
            release_draft_handoff_key_tail
        ),
        "release_draft_handoff_key_tail": list(release_draft_handoff_key_tail),
        "release_draft_handoff_key_tail_sha256": _stable_json_sha256(
            release_draft_handoff_key_tail
        ),
        "release_draft_handoff_sha256": _stable_json_sha256(release_draft_handoff),
        "release_draft_path": plan.release_draft_path,
        "release_draft_path_sha256": _stable_json_sha256(plan.release_draft_path),
        "release_draft_primary_issue": _release_draft_primary_issue(plan),
        "release_draft_required_action_count": len(release_draft_required_actions),
        "release_draft_required_actions_sha256": _stable_json_sha256(release_draft_required_actions),
        "release_draft_first_required_action": release_draft_required_action_boundary[
            "first_action"
        ],
        "release_draft_last_required_action": release_draft_required_action_boundary[
            "last_action"
        ],
        "release_draft_required_action_boundary_sha256": _stable_json_sha256(
            release_draft_required_action_boundary
        ),
        "release_draft_required_action_preview_count": len(
            release_draft_required_action_preview
        ),
        "release_draft_required_action_preview": list(
            release_draft_required_action_preview
        ),
        "release_draft_required_action_preview_sha256": _stable_json_sha256(
            release_draft_required_action_preview
        ),
        "release_draft_required_action_tail_count": len(
            release_draft_required_action_tail
        ),
        "release_draft_required_action_tail": list(
            release_draft_required_action_tail
        ),
        "release_draft_required_action_tail_sha256": _stable_json_sha256(
            release_draft_required_action_tail
        ),
        "release_draft_primary_required_action": (
            release_draft_required_actions[0] if release_draft_required_actions else None
        ),
        "release_draft_issues_sha256": _stable_json_sha256(plan.release_draft_issues),
        "release_draft_first_issue": release_draft_issue_boundary["first_issue"],
        "release_draft_last_issue": release_draft_issue_boundary["last_issue"],
        "release_draft_issue_boundary_sha256": _stable_json_sha256(
            release_draft_issue_boundary
        ),
        "release_draft_issue_preview_count": len(release_draft_issue_preview),
        "release_draft_issue_preview": list(release_draft_issue_preview),
        "release_draft_issue_preview_sha256": _stable_json_sha256(
            release_draft_issue_preview
        ),
        "release_draft_issue_tail_count": len(release_draft_issue_tail),
        "release_draft_issue_tail": list(release_draft_issue_tail),
        "release_draft_issue_tail_sha256": _stable_json_sha256(
            release_draft_issue_tail
        ),
        "validation_command_count": len(validation_commands),
        "validation_commands_sha256": _stable_json_sha256(validation_commands),
        "validation_first_command": validation_command_boundary["first_command"],
        "validation_last_command": validation_command_boundary["last_command"],
        "validation_command_boundary_sha256": _stable_json_sha256(
            validation_command_boundary
        ),
        "validation_command_preview_count": len(validation_command_preview),
        "validation_command_preview": list(validation_command_preview),
        "validation_command_preview_sha256": _stable_json_sha256(
            validation_command_preview
        ),
        "validation_command_tail_count": len(validation_command_tail),
        "validation_command_tail": list(validation_command_tail),
        "validation_command_tail_sha256": _stable_json_sha256(
            validation_command_tail
        ),
        "review_checklist_count": len(review_checklist),
        "review_checklist_sha256": _stable_json_sha256(review_checklist),
        "review_checklist_first_item": review_checklist_boundary["first_item"],
        "review_checklist_last_item": review_checklist_boundary["last_item"],
        "review_checklist_boundary_sha256": _stable_json_sha256(review_checklist_boundary),
        "review_checklist_preview_count": len(review_checklist_preview),
        "review_checklist_preview": list(review_checklist_preview),
        "review_checklist_preview_sha256": _stable_json_sha256(
            review_checklist_preview
        ),
        "review_checklist_tail_count": len(review_checklist_tail),
        "review_checklist_tail": list(review_checklist_tail),
        "review_checklist_tail_sha256": _stable_json_sha256(review_checklist_tail),
        "create_issues_safety_contract_key_count": len(create_issues_safety_contract),
        "create_issues_safety_contract_sha256": _stable_json_sha256(create_issues_safety_contract),
        "create_issues_safety_contract_first_key": create_issues_safety_contract_key_boundary[
            "first_key"
        ],
        "create_issues_safety_contract_last_key": create_issues_safety_contract_key_boundary[
            "last_key"
        ],
        "create_issues_safety_contract_key_boundary_sha256": _stable_json_sha256(
            create_issues_safety_contract_key_boundary
        ),
        "create_issues_safety_contract_key_preview_count": len(
            create_issues_safety_contract_key_preview
        ),
        "create_issues_safety_contract_key_preview": list(
            create_issues_safety_contract_key_preview
        ),
        "create_issues_safety_contract_key_preview_sha256": _stable_json_sha256(
            create_issues_safety_contract_key_preview
        ),
        "create_issues_safety_contract_key_tail_count": len(
            create_issues_safety_contract_key_tail
        ),
        "create_issues_safety_contract_key_tail": list(
            create_issues_safety_contract_key_tail
        ),
        "create_issues_safety_contract_key_tail_sha256": _stable_json_sha256(
            create_issues_safety_contract_key_tail
        ),
        "publication_ok": plan.publication_ok,
        "publication_visibility_status": plan.publication_visibility.get("status"),
        "publication_branch": plan.publication_ref_context.get("branch"),
        "publication_upstream": plan.publication_ref_context.get("upstream"),
        "publication_remote": plan.publication_ref_context.get("remote"),
        "publication_latest_tag": plan.publication_ref_context.get("latest_tag"),
        "publication_tag_commit": plan.publication_ref_context.get("tag_commit"),
        "publication_local_head": plan.publication_ref_context.get("local_head"),
        "publication_upstream_head": plan.publication_ref_context.get("upstream_head"),
        "publication_tag_points_at_head": plan.publication_ref_context.get("tag_points_at_head"),
        "publication_tag_commit_in_upstream": plan.publication_ref_context.get("tag_commit_in_upstream"),
        "publication_branch_published": plan.publication_ref_context.get("branch_published"),
        "publication_tag_published": plan.publication_ref_context.get("tag_published"),
        "publication_remote_branch_head": plan.publication_ref_context.get("remote_branch_head"),
        "publication_remote_tag_commit": plan.publication_ref_context.get("remote_tag_commit"),
        "publication_remote_checked": bool(plan.publication_ref_context.get("remote_checked", False)),
        "publication_ahead_count": plan.publication_ref_context.get("ahead_count"),
        "publication_behind_count": plan.publication_ref_context.get("behind_count"),
        "release_draft_ok": not plan.release_draft_issues,
        "release_draft_issue_count": len(plan.release_draft_issues),
        "candidate_issue_gate_key_count": len(plan.candidate_issue_gate),
        "candidate_issue_gate_sha256": _stable_json_sha256(plan.candidate_issue_gate),
        "candidate_issue_gate_status": plan.candidate_issue_gate.get("status"),
        "can_create_issues": bool(plan.candidate_issue_gate.get("can_create_issues", False)),
        "requires_maintainer_review": bool(plan.candidate_issue_gate.get("requires_maintainer_review", False)),
        "candidate_issue_gate_summary_sha256": _stable_json_sha256(candidate_issue_gate_summary),
        "candidate_issue_gate_evidence_key_count": len(candidate_issue_gate_evidence),
        "candidate_issue_gate_evidence_sha256": _stable_json_sha256(candidate_issue_gate_evidence),
        "candidate_issue_gate_evidence_first_key": candidate_issue_gate_evidence_key_boundary[
            "first_key"
        ],
        "candidate_issue_gate_evidence_last_key": candidate_issue_gate_evidence_key_boundary[
            "last_key"
        ],
        "candidate_issue_gate_evidence_key_boundary_sha256": _stable_json_sha256(
            candidate_issue_gate_evidence_key_boundary
        ),
        "candidate_issue_gate_reason_description_count": len(candidate_issue_gate_reason_descriptions),
        "candidate_issue_gate_reason_descriptions_sha256": _stable_json_sha256(
            candidate_issue_gate_reason_descriptions
        ),
        "candidate_issue_gate_reason_code_count": plan.candidate_issue_gate.get("reason_code_count"),
        "candidate_issue_gate_reason_codes_sha256": plan.candidate_issue_gate.get("reason_codes_sha256"),
        "candidate_issue_gate_first_reason_code": candidate_issue_gate_reason_code_boundary[
            "first_code"
        ],
        "candidate_issue_gate_last_reason_code": candidate_issue_gate_reason_code_boundary[
            "last_code"
        ],
        "candidate_issue_gate_reason_code_boundary_sha256": _stable_json_sha256(
            candidate_issue_gate_reason_code_boundary
        ),
        "candidate_issue_gate_primary_reason_code": candidate_issue_gate_primary_reason_code,
        "candidate_issue_gate_primary_reason_description": candidate_issue_gate_primary_reason_description,
        "candidate_issue_gate_required_action_count": plan.candidate_issue_gate.get("required_action_count"),
        "candidate_issue_gate_required_actions_sha256": plan.candidate_issue_gate.get("required_actions_sha256"),
        "candidate_issue_gate_first_required_action": candidate_issue_gate_required_action_boundary[
            "first_action"
        ],
        "candidate_issue_gate_last_required_action": candidate_issue_gate_required_action_boundary[
            "last_action"
        ],
        "candidate_issue_gate_required_action_boundary_sha256": _stable_json_sha256(
            candidate_issue_gate_required_action_boundary
        ),
        "candidate_issue_gate_primary_required_action": (
            candidate_issue_gate_required_actions[0] if candidate_issue_gate_required_actions else None
        ),
        "dry_run_supported": bool(create_issues_safety["dry_run_supported"]),
        "preflight_required": bool(create_issues_safety["preflight_required"]),
    }


def _summary_inline_code(value: Any) -> str:
    if value is None:
        return "`(none)`"
    text = str(value)
    if "`" in text:
        return f"`` {text} ``"
    return f"`{text}`"


def _issue_artifact_bundle_summary_markdown(
    plan: IterationPlan,
    *,
    summary: dict[str, Any] | None = None,
) -> str:
    candidate_cases = [promotion.case_id for promotion in plan.candidate_promotions]
    issue_body_names = [f"{promotion.case_id}.md" for promotion in plan.candidate_promotions]
    issue_body_inventory = _issue_body_inventory(plan.candidate_promotions)
    review_order = [
        "README.md",
        "publication-handoff.json",
        "release-draft-handoff.json",
        "issue-metadata.json",
        *issue_body_names,
        "create-issues.sh",
    ]
    if summary is None:
        summary = _issue_artifact_bundle_summary(
            plan=plan,
            candidate_cases=candidate_cases,
            review_order=review_order,
            issue_body_inventory=issue_body_inventory,
            issue_body_summary=_issue_body_summary(issue_body_inventory),
            issue_metadata_summary=_issue_metadata_summary(_issue_metadata_for_summary(plan.candidate_promotions)),
            create_issues_safety=_issue_artifact_create_issues_safety(Path("create-issues.sh"), plan),
            artifact_files=_issue_artifact_files(issue_body_names),
        )
    return "\n".join(
        [
            "## Artifact Bundle Summary",
            "",
            f"- artifact_bundle_summary_key_count: `{summary['artifact_bundle_summary_key_count']}`",
            f"- artifact_bundle_summary_keys_sha256: `{summary['artifact_bundle_summary_keys_sha256']}`",
            "- artifact_bundle_summary_key_preview_count: "
            f"`{summary['artifact_bundle_summary_key_preview_count']}`",
            "- artifact_bundle_summary_key_preview: "
            f"`{json.dumps(summary['artifact_bundle_summary_key_preview'], ensure_ascii=False)}`",
            "- artifact_bundle_summary_key_preview_sha256: "
            f"`{summary['artifact_bundle_summary_key_preview_sha256']}`",
            "- artifact_bundle_summary_key_tail_count: "
            f"`{summary['artifact_bundle_summary_key_tail_count']}`",
            "- artifact_bundle_summary_key_tail: "
            f"`{json.dumps(summary['artifact_bundle_summary_key_tail'], ensure_ascii=False)}`",
            "- artifact_bundle_summary_key_tail_sha256: "
            f"`{summary['artifact_bundle_summary_key_tail_sha256']}`",
            "- artifact_bundle_summary_first_key: "
            f"`{summary['artifact_bundle_summary_first_key']}`",
            "- artifact_bundle_summary_last_key: "
            f"`{summary['artifact_bundle_summary_last_key']}`",
            "- artifact_bundle_summary_key_boundary_sha256: "
            f"`{summary['artifact_bundle_summary_key_boundary_sha256']}`",
            "- artifact_manifest_schema_version: "
            f"`{summary['artifact_manifest_schema_version']}`",
            f"- artifact_manifest_key_count: `{summary['artifact_manifest_key_count']}`",
            f"- artifact_manifest_keys_sha256: `{summary['artifact_manifest_keys_sha256']}`",
            f"- artifact_manifest_first_key: `{summary['artifact_manifest_first_key']}`",
            f"- artifact_manifest_last_key: `{summary['artifact_manifest_last_key']}`",
            "- artifact_manifest_key_boundary_sha256: "
            f"`{summary['artifact_manifest_key_boundary_sha256']}`",
            f"- artifact_manifest_key_preview_count: `{summary['artifact_manifest_key_preview_count']}`",
            "- artifact_manifest_key_preview: "
            f"`{json.dumps(summary['artifact_manifest_key_preview'], ensure_ascii=False)}`",
            "- artifact_manifest_key_preview_sha256: "
            f"`{summary['artifact_manifest_key_preview_sha256']}`",
            f"- artifact_manifest_key_tail_count: `{summary['artifact_manifest_key_tail_count']}`",
            "- artifact_manifest_key_tail: "
            f"`{json.dumps(summary['artifact_manifest_key_tail'], ensure_ascii=False)}`",
            "- artifact_manifest_key_tail_sha256: "
            f"`{summary['artifact_manifest_key_tail_sha256']}`",
            f"- artifact_manifest_payload_key_count: `{summary['artifact_manifest_payload_key_count']}`",
            "- artifact_manifest_payload_first_key: "
            f"`{summary['artifact_manifest_payload_first_key']}`",
            "- artifact_manifest_payload_last_key: "
            f"`{summary['artifact_manifest_payload_last_key']}`",
            "- artifact_manifest_payload_key_boundary_sha256: "
            f"`{summary['artifact_manifest_payload_key_boundary_sha256']}`",
            "- artifact_manifest_payload_key_preview_count: "
            f"`{summary['artifact_manifest_payload_key_preview_count']}`",
            "- artifact_manifest_payload_key_preview: "
            f"`{json.dumps(summary['artifact_manifest_payload_key_preview'], ensure_ascii=False)}`",
            "- artifact_manifest_payload_key_preview_sha256: "
            f"`{summary['artifact_manifest_payload_key_preview_sha256']}`",
            "- artifact_manifest_payload_key_tail_count: "
            f"`{summary['artifact_manifest_payload_key_tail_count']}`",
            "- artifact_manifest_payload_key_tail: "
            f"`{json.dumps(summary['artifact_manifest_payload_key_tail'], ensure_ascii=False)}`",
            "- artifact_manifest_payload_key_tail_sha256: "
            f"`{summary['artifact_manifest_payload_key_tail_sha256']}`",
            f"- artifact_manifest_payload_sha256: `{summary['artifact_manifest_payload_sha256']}`",
            f"- target_version: `{summary['target_version']}`",
            f"- candidate_count: `{summary['candidate_count']}`",
            f"- candidate_cases_first_case: `{summary['candidate_cases_first_case']}`",
            f"- candidate_cases_last_case: `{summary['candidate_cases_last_case']}`",
            f"- candidate_cases_boundary_sha256: `{summary['candidate_cases_boundary_sha256']}`",
            f"- candidate_cases_preview_count: `{summary['candidate_cases_preview_count']}`",
            "- candidate_cases_preview: "
            f"`{json.dumps(summary['candidate_cases_preview'], ensure_ascii=False)}`",
            f"- candidate_cases_preview_sha256: `{summary['candidate_cases_preview_sha256']}`",
            f"- candidate_cases_tail_count: `{summary['candidate_cases_tail_count']}`",
            "- candidate_cases_tail: "
            f"`{json.dumps(summary['candidate_cases_tail'], ensure_ascii=False)}`",
            f"- candidate_cases_tail_sha256: `{summary['candidate_cases_tail_sha256']}`",
            f"- candidate_cases_sha256: `{summary['candidate_cases_sha256']}`",
            "- case_promotion_evidence_summary_key_count: "
            f"`{summary['case_promotion_evidence_summary_key_count']}`",
            "- case_promotion_evidence_summary_keys_sha256: "
            f"`{summary['case_promotion_evidence_summary_keys_sha256']}`",
            "- case_promotion_evidence_summary_first_key: "
            f"`{summary['case_promotion_evidence_summary_first_key']}`",
            "- case_promotion_evidence_summary_last_key: "
            f"`{summary['case_promotion_evidence_summary_last_key']}`",
            "- case_promotion_evidence_summary_key_boundary_sha256: "
            f"`{summary['case_promotion_evidence_summary_key_boundary_sha256']}`",
            "- case_promotion_evidence_summary_key_preview_count: "
            f"`{summary['case_promotion_evidence_summary_key_preview_count']}`",
            "- case_promotion_evidence_summary_key_preview: "
            f"`{json.dumps(summary['case_promotion_evidence_summary_key_preview'], ensure_ascii=False)}`",
            "- case_promotion_evidence_summary_key_preview_sha256: "
            f"`{summary['case_promotion_evidence_summary_key_preview_sha256']}`",
            "- case_promotion_evidence_summary_key_tail_count: "
            f"`{summary['case_promotion_evidence_summary_key_tail_count']}`",
            "- case_promotion_evidence_summary_key_tail: "
            f"`{json.dumps(summary['case_promotion_evidence_summary_key_tail'], ensure_ascii=False)}`",
            "- case_promotion_evidence_summary_key_tail_sha256: "
            f"`{summary['case_promotion_evidence_summary_key_tail_sha256']}`",
            "- case_promotion_evidence_summary_sha256: "
            f"`{summary['case_promotion_evidence_summary_sha256']}`",
            "- case_promotion_evidence_candidate_count: "
            f"`{summary['case_promotion_evidence_candidate_count']}`",
            "- case_promotion_evidence_task_count: "
            f"`{summary['case_promotion_evidence_task_count']}`",
            "- case_promotion_evidence_pending_count: "
            f"`{summary['case_promotion_evidence_pending_count']}`",
            "- case_promotion_evidence_blocked_count: "
            f"`{summary['case_promotion_evidence_blocked_count']}`",
            "- case_promotion_evidence_complete_count: "
            f"`{summary['case_promotion_evidence_complete_count']}`",
            "- case_promotion_evidence_primary_next_action: "
            f"{_summary_inline_code(summary['case_promotion_evidence_primary_next_action'])}",
            "- case_promotion_evidence_primary_case_id: "
            f"{_summary_inline_code(summary['case_promotion_evidence_primary_case_id'])}",
            "- case_promotion_evidence_primary_task: "
            f"{_summary_inline_code(summary['case_promotion_evidence_primary_task'])}",
            "- case_promotion_evidence_primary_status: "
            f"{_summary_inline_code(summary['case_promotion_evidence_primary_status'])}",
            "- case_promotion_evidence_primary_evidence_sha256: "
            f"`{summary['case_promotion_evidence_primary_evidence_sha256']}`",
            "- case_promotion_evidence_primary_detail_sha256: "
            f"`{summary['case_promotion_evidence_primary_detail_sha256']}`",
            "- case_promotion_evidence_primary_next_task_sha256: "
            f"`{summary['case_promotion_evidence_primary_next_task_sha256']}`",
            "- case_promotion_evidence_primary_runbook_step_count: "
            f"`{summary['case_promotion_evidence_primary_runbook_step_count']}`",
            "- case_promotion_evidence_primary_runbook_steps: "
            f"`{json.dumps(summary['case_promotion_evidence_primary_runbook_steps'], ensure_ascii=False)}`",
            "- case_promotion_evidence_primary_runbook_steps_sha256: "
            f"`{summary['case_promotion_evidence_primary_runbook_steps_sha256']}`",
            "- case_promotion_evidence_primary_runbook_first_step: "
            f"{_summary_inline_code(summary['case_promotion_evidence_primary_runbook_first_step'])}",
            "- case_promotion_evidence_primary_runbook_first_command: "
            f"{_summary_inline_code(summary['case_promotion_evidence_primary_runbook_first_command'])}",
            "- case_promotion_evidence_primary_runbook_first_command_sha256: "
            f"`{summary['case_promotion_evidence_primary_runbook_first_command_sha256']}`",
            "- case_promotion_evidence_primary_runbook_sha256: "
            f"`{summary['case_promotion_evidence_primary_runbook_sha256']}`",
            "- case_promotion_command_plan_summary_sha256: "
            f"`{summary['case_promotion_command_plan_summary_sha256']}`",
            "- case_promotion_command_plan_candidate_count: "
            f"`{summary['case_promotion_command_plan_candidate_count']}`",
            "- case_promotion_command_plan_command_count: "
            f"`{summary['case_promotion_command_plan_command_count']}`",
            "- case_promotion_command_plan_missing_command_count: "
            f"`{summary['case_promotion_command_plan_missing_command_count']}`",
            "- case_promotion_command_plan_all_declared: "
            f"`{str(bool(summary['case_promotion_command_plan_all_declared'])).lower()}`",
            "- standard_release_flow_status: "
            f"{_summary_inline_code(summary['standard_release_flow_status'])}",
            "- standard_release_flow_target_tag: "
            f"{_summary_inline_code(summary['standard_release_flow_target_tag'])}",
            "- standard_release_flow_primary_next_action: "
            f"{_summary_inline_code(summary['standard_release_flow_primary_next_action'])}",
            "- standard_release_flow_command_count: "
            f"`{summary['standard_release_flow_command_count']}`",
            "- standard_release_flow_commands_sha256: "
            f"`{summary['standard_release_flow_commands_sha256']}`",
            "- standard_release_flow_step_count: "
            f"`{summary['standard_release_flow_step_count']}`",
            "- standard_release_flow_step_names: "
            f"`{json.dumps(summary['standard_release_flow_step_names'], ensure_ascii=False)}`",
            "- standard_release_flow_step_names_sha256: "
            f"`{summary['standard_release_flow_step_names_sha256']}`",
            "- standard_release_flow_steps_sha256: "
            f"`{summary['standard_release_flow_steps_sha256']}`",
            "- standard_release_flow_first_step_name: "
            f"{_summary_inline_code(summary['standard_release_flow_first_step_name'])}",
            "- standard_release_flow_last_step_name: "
            f"{_summary_inline_code(summary['standard_release_flow_last_step_name'])}",
            "- standard_release_flow_step_boundary_sha256: "
            f"`{summary['standard_release_flow_step_boundary_sha256']}`",
            "- standard_release_flow_step_status_counts: "
            f"`{json.dumps(summary['standard_release_flow_step_status_counts'], ensure_ascii=False)}`",
            "- standard_release_flow_step_status_counts_sha256: "
            f"`{summary['standard_release_flow_step_status_counts_sha256']}`",
            "- standard_release_flow_primary_blocked_step_name: "
            f"{_summary_inline_code(summary['standard_release_flow_primary_blocked_step_name'])}",
            "- standard_release_flow_primary_pending_step_name: "
            f"{_summary_inline_code(summary['standard_release_flow_primary_pending_step_name'])}",
            "- standard_release_flow_has_website_deploy: "
            f"`{str(bool(summary['standard_release_flow_has_website_deploy'])).lower()}`",
            "- standard_release_flow_website_deploy_command: "
            f"{_summary_inline_code(summary['standard_release_flow_website_deploy_command'])}",
            "- standard_release_flow_website_deploy_command_sha256: "
            f"`{summary['standard_release_flow_website_deploy_command_sha256']}`",
            "- standard_release_flow_sha256: "
            f"`{summary['standard_release_flow_sha256']}`",
            f"- body_count: `{summary['body_count']}`",
            f"- issue_body_inventory_preview_count: `{summary['issue_body_inventory_preview_count']}`",
            "- issue_body_inventory_preview: "
            f"`{json.dumps(summary['issue_body_inventory_preview'], ensure_ascii=False)}`",
            "- issue_body_inventory_preview_sha256: "
            f"`{summary['issue_body_inventory_preview_sha256']}`",
            "- issue_body_inventory_first_entry: "
            f"`{json.dumps(summary['issue_body_inventory_first_entry'], ensure_ascii=False)}`",
            "- issue_body_inventory_last_entry: "
            f"`{json.dumps(summary['issue_body_inventory_last_entry'], ensure_ascii=False)}`",
            "- issue_body_inventory_boundary_sha256: "
            f"`{summary['issue_body_inventory_boundary_sha256']}`",
            f"- issue_body_inventory_tail_count: `{summary['issue_body_inventory_tail_count']}`",
            "- issue_body_inventory_tail: "
            f"`{json.dumps(summary['issue_body_inventory_tail'], ensure_ascii=False)}`",
            "- issue_body_inventory_tail_sha256: "
            f"`{summary['issue_body_inventory_tail_sha256']}`",
            f"- issue_body_summary_key_count: `{summary['issue_body_summary_key_count']}`",
            f"- issue_body_summary_keys_sha256: `{summary['issue_body_summary_keys_sha256']}`",
            f"- issue_body_summary_first_key: `{summary['issue_body_summary_first_key']}`",
            f"- issue_body_summary_last_key: `{summary['issue_body_summary_last_key']}`",
            "- issue_body_summary_key_boundary_sha256: "
            f"`{summary['issue_body_summary_key_boundary_sha256']}`",
            f"- issue_body_summary_key_preview_count: `{summary['issue_body_summary_key_preview_count']}`",
            "- issue_body_summary_key_preview: "
            f"`{json.dumps(summary['issue_body_summary_key_preview'], ensure_ascii=False)}`",
            "- issue_body_summary_key_preview_sha256: "
            f"`{summary['issue_body_summary_key_preview_sha256']}`",
            f"- issue_body_summary_key_tail_count: `{summary['issue_body_summary_key_tail_count']}`",
            "- issue_body_summary_key_tail: "
            f"`{json.dumps(summary['issue_body_summary_key_tail'], ensure_ascii=False)}`",
            "- issue_body_summary_key_tail_sha256: "
            f"`{summary['issue_body_summary_key_tail_sha256']}`",
            f"- issue_body_summary_sha256: `{summary['issue_body_summary_sha256']}`",
            f"- review_item_count: `{summary['review_item_count']}`",
            f"- review_order_sha256: `{summary['review_order_sha256']}`",
            f"- review_order_first_item: `{summary['review_order_first_item']}`",
            f"- review_order_last_item: `{summary['review_order_last_item']}`",
            f"- review_order_boundary_sha256: `{summary['review_order_boundary_sha256']}`",
            f"- review_order_preview_count: `{summary['review_order_preview_count']}`",
            "- review_order_preview: "
            f"`{json.dumps(summary['review_order_preview'], ensure_ascii=False)}`",
            f"- review_order_preview_sha256: `{summary['review_order_preview_sha256']}`",
            f"- review_order_tail_count: `{summary['review_order_tail_count']}`",
            "- review_order_tail: "
            f"`{json.dumps(summary['review_order_tail'], ensure_ascii=False)}`",
            f"- review_order_tail_sha256: `{summary['review_order_tail_sha256']}`",
            f"- inventory_sha256: `{summary['inventory_sha256']}`",
            f"- issue_metadata_count: `{summary['issue_metadata_count']}`",
            f"- issue_metadata_sha256: `{summary['issue_metadata_sha256']}`",
            "- issue_metadata_first_item: "
            f"`{json.dumps(summary['issue_metadata_first_item'], ensure_ascii=False)}`",
            "- issue_metadata_last_item: "
            f"`{json.dumps(summary['issue_metadata_last_item'], ensure_ascii=False)}`",
            f"- issue_metadata_boundary_sha256: `{summary['issue_metadata_boundary_sha256']}`",
            f"- issue_metadata_preview_count: `{summary['issue_metadata_preview_count']}`",
            "- issue_metadata_preview: "
            f"`{json.dumps(summary['issue_metadata_preview'], ensure_ascii=False)}`",
            f"- issue_metadata_preview_sha256: `{summary['issue_metadata_preview_sha256']}`",
            f"- issue_metadata_tail_count: `{summary['issue_metadata_tail_count']}`",
            "- issue_metadata_tail: "
            f"`{json.dumps(summary['issue_metadata_tail'], ensure_ascii=False)}`",
            f"- issue_metadata_tail_sha256: `{summary['issue_metadata_tail_sha256']}`",
            f"- artifact_files_key_count: `{summary['artifact_files_key_count']}`",
            f"- artifact_files_sha256: `{summary['artifact_files_sha256']}`",
            f"- artifact_files_first_key: `{summary['artifact_files_first_key']}`",
            f"- artifact_files_last_key: `{summary['artifact_files_last_key']}`",
            f"- artifact_files_key_boundary_sha256: `{summary['artifact_files_key_boundary_sha256']}`",
            f"- artifact_files_key_preview_count: `{summary['artifact_files_key_preview_count']}`",
            "- artifact_files_key_preview: "
            f"`{json.dumps(summary['artifact_files_key_preview'], ensure_ascii=False)}`",
            f"- artifact_files_key_preview_sha256: `{summary['artifact_files_key_preview_sha256']}`",
            f"- artifact_files_key_tail_count: `{summary['artifact_files_key_tail_count']}`",
            "- artifact_files_key_tail: "
            f"`{json.dumps(summary['artifact_files_key_tail'], ensure_ascii=False)}`",
            f"- artifact_files_key_tail_sha256: `{summary['artifact_files_key_tail_sha256']}`",
            f"- issue_artifacts_command_sha256: `{summary['issue_artifacts_command_sha256']}`",
            f"- plan_report_command_sha256: `{summary['plan_report_command_sha256']}`",
            f"- publication_visibility_key_count: `{summary['publication_visibility_key_count']}`",
            f"- publication_visibility_sha256: `{summary['publication_visibility_sha256']}`",
            f"- publication_visibility_first_key: `{summary['publication_visibility_first_key']}`",
            f"- publication_visibility_last_key: `{summary['publication_visibility_last_key']}`",
            "- publication_visibility_key_boundary_sha256: "
            f"`{summary['publication_visibility_key_boundary_sha256']}`",
            "- publication_visibility_key_preview_count: "
            f"`{summary['publication_visibility_key_preview_count']}`",
            "- publication_visibility_key_preview: "
            f"`{json.dumps(summary['publication_visibility_key_preview'], ensure_ascii=False)}`",
            "- publication_visibility_key_preview_sha256: "
            f"`{summary['publication_visibility_key_preview_sha256']}`",
            "- publication_visibility_key_tail_count: "
            f"`{summary['publication_visibility_key_tail_count']}`",
            "- publication_visibility_key_tail: "
            f"`{json.dumps(summary['publication_visibility_key_tail'], ensure_ascii=False)}`",
            "- publication_visibility_key_tail_sha256: "
            f"`{summary['publication_visibility_key_tail_sha256']}`",
            "- publication_visibility_summary_sha256: "
            f"`{summary['publication_visibility_summary_sha256']}`",
            "- publication_tag_publish_decision_key_count: "
            f"`{summary['publication_tag_publish_decision_key_count']}`",
            "- publication_tag_publish_decision_sha256: "
            f"`{summary['publication_tag_publish_decision_sha256']}`",
            "- publication_tag_publish_decision_first_key: "
            f"`{summary['publication_tag_publish_decision_first_key']}`",
            "- publication_tag_publish_decision_last_key: "
            f"`{summary['publication_tag_publish_decision_last_key']}`",
            "- publication_tag_publish_decision_key_boundary_sha256: "
            f"`{summary['publication_tag_publish_decision_key_boundary_sha256']}`",
            "- publication_tag_publish_decision_key_preview_count: "
            f"`{summary['publication_tag_publish_decision_key_preview_count']}`",
            "- publication_tag_publish_decision_key_preview: "
            f"`{json.dumps(summary['publication_tag_publish_decision_key_preview'], ensure_ascii=False)}`",
            "- publication_tag_publish_decision_key_preview_sha256: "
            f"`{summary['publication_tag_publish_decision_key_preview_sha256']}`",
            "- publication_tag_publish_decision_key_tail_count: "
            f"`{summary['publication_tag_publish_decision_key_tail_count']}`",
            "- publication_tag_publish_decision_key_tail: "
            f"`{json.dumps(summary['publication_tag_publish_decision_key_tail'], ensure_ascii=False)}`",
            "- publication_tag_publish_decision_key_tail_sha256: "
            f"`{summary['publication_tag_publish_decision_key_tail_sha256']}`",
            "- publication_tag_publish_decision_status: "
            f"{_summary_inline_code(summary['publication_tag_publish_decision_status'])}",
            "- publication_tag_can_push: "
            f"`{str(bool(summary['publication_tag_can_push'])).lower()}`",
            "- publication_tag_required_action_sha256: "
            f"`{summary['publication_tag_required_action_sha256']}`",
            "- publication_target_tag: "
            f"{_summary_inline_code(summary['publication_target_tag'])}",
            "- publication_target_tag_status: "
            f"{_summary_inline_code(summary['publication_target_tag_status'])}",
            "- publication_target_tag_primary_command: "
            f"{_summary_inline_code(summary['publication_target_tag_primary_command'])}",
            "- publication_target_tag_command_count: "
            f"`{summary['publication_target_tag_command_count']}`",
            "- publication_target_tag_commands_sha256: "
            f"`{summary['publication_target_tag_commands_sha256']}`",
            "- publication_target_tag_required_action_sha256: "
            f"`{summary['publication_target_tag_required_action_sha256']}`",
            "- publication_target_tag_release_gate_status: "
            f"{_summary_inline_code(summary['publication_target_tag_release_gate_status'])}",
            "- publication_target_tag_release_gate_blocker_count: "
            f"`{summary['publication_target_tag_release_gate_blocker_count']}`",
            "- publication_target_tag_release_gate_primary_blocker: "
            f"{_summary_inline_code(summary['publication_target_tag_release_gate_primary_blocker'])}",
            "- publication_target_tag_release_gate_required_action_sha256: "
            f"`{summary['publication_target_tag_release_gate_required_action_sha256']}`",
            "- publication_target_tag_release_gate_blockers_sha256: "
            f"`{summary['publication_target_tag_release_gate_blockers_sha256']}`",
            f"- blocker_count: `{summary['blocker_count']}`",
            f"- blockers_sha256: `{summary['blockers_sha256']}`",
            "- blocker_first_item: "
            f"{_summary_inline_code(summary['blocker_first_item'])}",
            "- blocker_last_item: "
            f"{_summary_inline_code(summary['blocker_last_item'])}",
            f"- blocker_boundary_sha256: `{summary['blocker_boundary_sha256']}`",
            f"- blocker_preview_count: `{summary['blocker_preview_count']}`",
            "- blocker_preview: "
            f"`{json.dumps(summary['blocker_preview'], ensure_ascii=False)}`",
            f"- blocker_preview_sha256: `{summary['blocker_preview_sha256']}`",
            f"- blocker_tail_count: `{summary['blocker_tail_count']}`",
            "- blocker_tail: "
            f"`{json.dumps(summary['blocker_tail'], ensure_ascii=False)}`",
            f"- blocker_tail_sha256: `{summary['blocker_tail_sha256']}`",
            f"- next_action_count: `{summary['next_action_count']}`",
            f"- next_actions_sha256: `{summary['next_actions_sha256']}`",
            "- next_action_first_item: "
            f"{_summary_inline_code(summary['next_action_first_item'])}",
            "- next_action_last_item: "
            f"{_summary_inline_code(summary['next_action_last_item'])}",
            f"- next_action_boundary_sha256: `{summary['next_action_boundary_sha256']}`",
            f"- next_action_preview_count: `{summary['next_action_preview_count']}`",
            "- next_action_preview: "
            f"`{json.dumps(summary['next_action_preview'], ensure_ascii=False)}`",
            f"- next_action_preview_sha256: `{summary['next_action_preview_sha256']}`",
            f"- next_action_tail_count: `{summary['next_action_tail_count']}`",
            "- next_action_tail: "
            f"`{json.dumps(summary['next_action_tail'], ensure_ascii=False)}`",
            f"- next_action_tail_sha256: `{summary['next_action_tail_sha256']}`",
            f"- publication_next_action_count: `{summary['publication_next_action_count']}`",
            f"- publication_next_actions_sha256: `{summary['publication_next_actions_sha256']}`",
            "- publication_next_action_first_item: "
            f"{_summary_inline_code(summary['publication_next_action_first_item'])}",
            "- publication_next_action_last_item: "
            f"{_summary_inline_code(summary['publication_next_action_last_item'])}",
            "- publication_next_action_boundary_sha256: "
            f"`{summary['publication_next_action_boundary_sha256']}`",
            "- publication_next_action_preview_count: "
            f"`{summary['publication_next_action_preview_count']}`",
            "- publication_next_action_preview: "
            f"`{json.dumps(summary['publication_next_action_preview'], ensure_ascii=False)}`",
            "- publication_next_action_preview_sha256: "
            f"`{summary['publication_next_action_preview_sha256']}`",
            "- publication_next_action_tail_count: "
            f"`{summary['publication_next_action_tail_count']}`",
            "- publication_next_action_tail: "
            f"`{json.dumps(summary['publication_next_action_tail'], ensure_ascii=False)}`",
            "- publication_next_action_tail_sha256: "
            f"`{summary['publication_next_action_tail_sha256']}`",
            "- publication_primary_next_action: "
            f"{_summary_inline_code(summary['publication_primary_next_action'])}",
            f"- publication_handoff_key_count: `{summary['publication_handoff_key_count']}`",
            "- publication_handoff_schema_version: "
            f"{_summary_inline_code(summary['publication_handoff_schema_version'])}",
            "- publication_handoff_first_key: "
            f"`{summary['publication_handoff_first_key']}`",
            "- publication_handoff_last_key: "
            f"`{summary['publication_handoff_last_key']}`",
            "- publication_handoff_key_boundary_sha256: "
            f"`{summary['publication_handoff_key_boundary_sha256']}`",
            "- publication_handoff_key_preview_count: "
            f"`{summary['publication_handoff_key_preview_count']}`",
            "- publication_handoff_key_preview: "
            f"`{json.dumps(summary['publication_handoff_key_preview'], ensure_ascii=False)}`",
            "- publication_handoff_key_preview_sha256: "
            f"`{summary['publication_handoff_key_preview_sha256']}`",
            "- publication_handoff_key_tail_count: "
            f"`{summary['publication_handoff_key_tail_count']}`",
            "- publication_handoff_key_tail: "
            f"`{json.dumps(summary['publication_handoff_key_tail'], ensure_ascii=False)}`",
            "- publication_handoff_key_tail_sha256: "
            f"`{summary['publication_handoff_key_tail_sha256']}`",
            f"- publication_handoff_sha256: `{summary['publication_handoff_sha256']}`",
            "- publication_handoff_candidate_issue_gate_primary_reason_code: "
            f"{_summary_inline_code(summary['publication_handoff_candidate_issue_gate_primary_reason_code'])}",
            "- publication_handoff_candidate_issue_gate_primary_reason_description: "
            f"{_summary_inline_code(summary['publication_handoff_candidate_issue_gate_primary_reason_description'])}",
            "- publication_handoff_candidate_issue_gate_primary_required_action: "
            f"{_summary_inline_code(summary['publication_handoff_candidate_issue_gate_primary_required_action'])}",
            "- commit_cadence_status: "
            f"{_summary_inline_code(summary['commit_cadence_status'])}",
            f"- commit_cadence_commit_day_count: `{summary['commit_cadence_commit_day_count']}`",
            f"- commit_cadence_min_commit_days: `{summary['commit_cadence_min_commit_days']}`",
            f"- commit_cadence_missing_commit_days: `{summary['commit_cadence_missing_commit_days']}`",
            f"- commit_cadence_release_count_today: `{summary['commit_cadence_release_count_today']}`",
            f"- commit_cadence_max_daily_releases: `{summary['commit_cadence_max_daily_releases']}`",
            f"- commit_cadence_daily_release_limit_ok: `{summary['commit_cadence_daily_release_limit_ok']}`",
            f"- commit_cadence_next_action_count: `{summary['commit_cadence_next_action_count']}`",
            "- commit_cadence_primary_next_action: "
            f"{_summary_inline_code(summary['commit_cadence_primary_next_action'])}",
            "- commit_cadence_commit_days_sha256: "
            f"`{summary['commit_cadence_commit_days_sha256']}`",
            "- commit_cadence_release_tags_today_sha256: "
            f"`{summary['commit_cadence_release_tags_today_sha256']}`",
            "- commit_cadence_next_actions_sha256: "
            f"`{summary['commit_cadence_next_actions_sha256']}`",
            f"- publication_ref_context_key_count: `{summary['publication_ref_context_key_count']}`",
            f"- publication_ref_context_sha256: `{summary['publication_ref_context_sha256']}`",
            "- publication_ref_context_first_key: "
            f"`{summary['publication_ref_context_first_key']}`",
            "- publication_ref_context_last_key: "
            f"`{summary['publication_ref_context_last_key']}`",
            "- publication_ref_context_key_boundary_sha256: "
            f"`{summary['publication_ref_context_key_boundary_sha256']}`",
            "- publication_ref_context_key_preview_count: "
            f"`{summary['publication_ref_context_key_preview_count']}`",
            "- publication_ref_context_key_preview: "
            f"`{json.dumps(summary['publication_ref_context_key_preview'], ensure_ascii=False)}`",
            "- publication_ref_context_key_preview_sha256: "
            f"`{summary['publication_ref_context_key_preview_sha256']}`",
            "- publication_ref_context_key_tail_count: "
            f"`{summary['publication_ref_context_key_tail_count']}`",
            "- publication_ref_context_key_tail: "
            f"`{json.dumps(summary['publication_ref_context_key_tail'], ensure_ascii=False)}`",
            "- publication_ref_context_key_tail_sha256: "
            f"`{summary['publication_ref_context_key_tail_sha256']}`",
            f"- publication_publish_command_count: `{summary['publication_publish_command_count']}`",
            f"- publication_publish_commands_sha256: `{summary['publication_publish_commands_sha256']}`",
            "- publication_publish_first_command: "
            f"{_summary_inline_code(summary['publication_publish_first_command'])}",
            "- publication_publish_last_command: "
            f"{_summary_inline_code(summary['publication_publish_last_command'])}",
            "- publication_publish_command_boundary_sha256: "
            f"`{summary['publication_publish_command_boundary_sha256']}`",
            "- publication_primary_publish_command: "
            f"{_summary_inline_code(summary['publication_primary_publish_command'])}",
            "- publication_publish_script_path_sha256: "
            f"`{summary['publication_publish_script_path_sha256']}`",
            "- publication_publish_script_command_sha256: "
            f"`{summary['publication_publish_script_command_sha256']}`",
            f"- publication_worktree_status_count: `{summary['publication_worktree_status_count']}`",
            f"- publication_worktree_status_sha256: `{summary['publication_worktree_status_sha256']}`",
            "- publication_worktree_status_first_item: "
            f"{_summary_inline_code(summary['publication_worktree_status_first_item'])}",
            "- publication_worktree_status_last_item: "
            f"{_summary_inline_code(summary['publication_worktree_status_last_item'])}",
            "- publication_worktree_status_boundary_sha256: "
            f"`{summary['publication_worktree_status_boundary_sha256']}`",
            f"- release_draft_handoff_key_count: `{summary['release_draft_handoff_key_count']}`",
            "- release_draft_handoff_schema_version: "
            f"{_summary_inline_code(summary['release_draft_handoff_schema_version'])}",
            "- release_draft_handoff_primary_issue: "
            f"{_summary_inline_code(summary['release_draft_handoff_primary_issue'])}",
            "- release_draft_handoff_primary_required_action: "
            f"{_summary_inline_code(summary['release_draft_handoff_primary_required_action'])}",
            "- release_draft_handoff_first_key: "
            f"`{summary['release_draft_handoff_first_key']}`",
            "- release_draft_handoff_last_key: "
            f"`{summary['release_draft_handoff_last_key']}`",
            "- release_draft_handoff_key_boundary_sha256: "
            f"`{summary['release_draft_handoff_key_boundary_sha256']}`",
            "- release_draft_handoff_key_preview_count: "
            f"`{summary['release_draft_handoff_key_preview_count']}`",
            "- release_draft_handoff_key_preview: "
            f"`{json.dumps(summary['release_draft_handoff_key_preview'], ensure_ascii=False)}`",
            "- release_draft_handoff_key_preview_sha256: "
            f"`{summary['release_draft_handoff_key_preview_sha256']}`",
            "- release_draft_handoff_key_tail_count: "
            f"`{summary['release_draft_handoff_key_tail_count']}`",
            "- release_draft_handoff_key_tail: "
            f"`{json.dumps(summary['release_draft_handoff_key_tail'], ensure_ascii=False)}`",
            "- release_draft_handoff_key_tail_sha256: "
            f"`{summary['release_draft_handoff_key_tail_sha256']}`",
            f"- release_draft_handoff_sha256: `{summary['release_draft_handoff_sha256']}`",
            f"- release_draft_path: `{summary['release_draft_path']}`",
            f"- release_draft_path_sha256: `{summary['release_draft_path_sha256']}`",
            f"- release_draft_primary_issue: {_summary_inline_code(summary['release_draft_primary_issue'])}",
            f"- release_draft_required_action_count: `{summary['release_draft_required_action_count']}`",
            "- release_draft_required_actions_sha256: "
            f"`{summary['release_draft_required_actions_sha256']}`",
            "- release_draft_first_required_action: "
            f"{_summary_inline_code(summary['release_draft_first_required_action'])}",
            "- release_draft_last_required_action: "
            f"{_summary_inline_code(summary['release_draft_last_required_action'])}",
            "- release_draft_required_action_boundary_sha256: "
            f"`{summary['release_draft_required_action_boundary_sha256']}`",
            "- release_draft_required_action_preview_count: "
            f"`{summary['release_draft_required_action_preview_count']}`",
            "- release_draft_required_action_preview: "
            f"`{json.dumps(summary['release_draft_required_action_preview'], ensure_ascii=False)}`",
            "- release_draft_required_action_preview_sha256: "
            f"`{summary['release_draft_required_action_preview_sha256']}`",
            "- release_draft_required_action_tail_count: "
            f"`{summary['release_draft_required_action_tail_count']}`",
            "- release_draft_required_action_tail: "
            f"`{json.dumps(summary['release_draft_required_action_tail'], ensure_ascii=False)}`",
            "- release_draft_required_action_tail_sha256: "
            f"`{summary['release_draft_required_action_tail_sha256']}`",
            "- release_draft_primary_required_action: "
            f"{_summary_inline_code(summary['release_draft_primary_required_action'])}",
            f"- release_draft_issues_sha256: `{summary['release_draft_issues_sha256']}`",
            "- release_draft_first_issue: "
            f"{_summary_inline_code(summary['release_draft_first_issue'])}",
            "- release_draft_last_issue: "
            f"{_summary_inline_code(summary['release_draft_last_issue'])}",
            "- release_draft_issue_boundary_sha256: "
            f"`{summary['release_draft_issue_boundary_sha256']}`",
            "- release_draft_issue_preview_count: "
            f"`{summary['release_draft_issue_preview_count']}`",
            "- release_draft_issue_preview: "
            f"`{json.dumps(summary['release_draft_issue_preview'], ensure_ascii=False)}`",
            "- release_draft_issue_preview_sha256: "
            f"`{summary['release_draft_issue_preview_sha256']}`",
            "- release_draft_issue_tail_count: "
            f"`{summary['release_draft_issue_tail_count']}`",
            "- release_draft_issue_tail: "
            f"`{json.dumps(summary['release_draft_issue_tail'], ensure_ascii=False)}`",
            "- release_draft_issue_tail_sha256: "
            f"`{summary['release_draft_issue_tail_sha256']}`",
            f"- validation_command_count: `{summary['validation_command_count']}`",
            f"- validation_commands_sha256: `{summary['validation_commands_sha256']}`",
            "- validation_first_command: "
            f"{_summary_inline_code(summary['validation_first_command'])}",
            "- validation_last_command: "
            f"{_summary_inline_code(summary['validation_last_command'])}",
            "- validation_command_boundary_sha256: "
            f"`{summary['validation_command_boundary_sha256']}`",
            "- validation_command_preview_count: "
            f"`{summary['validation_command_preview_count']}`",
            "- validation_command_preview: "
            f"`{json.dumps(summary['validation_command_preview'], ensure_ascii=False)}`",
            "- validation_command_preview_sha256: "
            f"`{summary['validation_command_preview_sha256']}`",
            "- validation_command_tail_count: "
            f"`{summary['validation_command_tail_count']}`",
            "- validation_command_tail: "
            f"`{json.dumps(summary['validation_command_tail'], ensure_ascii=False)}`",
            "- validation_command_tail_sha256: "
            f"`{summary['validation_command_tail_sha256']}`",
            f"- review_checklist_count: `{summary['review_checklist_count']}`",
            f"- review_checklist_sha256: `{summary['review_checklist_sha256']}`",
            "- review_checklist_first_item: "
            f"{_summary_inline_code(summary['review_checklist_first_item'])}",
            "- review_checklist_last_item: "
            f"{_summary_inline_code(summary['review_checklist_last_item'])}",
            "- review_checklist_boundary_sha256: "
            f"`{summary['review_checklist_boundary_sha256']}`",
            "- review_checklist_preview_count: "
            f"`{summary['review_checklist_preview_count']}`",
            "- review_checklist_preview: "
            f"`{json.dumps(summary['review_checklist_preview'], ensure_ascii=False)}`",
            "- review_checklist_preview_sha256: "
            f"`{summary['review_checklist_preview_sha256']}`",
            "- review_checklist_tail_count: "
            f"`{summary['review_checklist_tail_count']}`",
            "- review_checklist_tail: "
            f"`{json.dumps(summary['review_checklist_tail'], ensure_ascii=False)}`",
            "- review_checklist_tail_sha256: "
            f"`{summary['review_checklist_tail_sha256']}`",
            f"- create_issues_safety_contract_key_count: `{summary['create_issues_safety_contract_key_count']}`",
            f"- create_issues_safety_contract_sha256: `{summary['create_issues_safety_contract_sha256']}`",
            "- create_issues_safety_contract_first_key: "
            f"`{summary['create_issues_safety_contract_first_key']}`",
            "- create_issues_safety_contract_last_key: "
            f"`{summary['create_issues_safety_contract_last_key']}`",
            "- create_issues_safety_contract_key_boundary_sha256: "
            f"`{summary['create_issues_safety_contract_key_boundary_sha256']}`",
            "- create_issues_safety_contract_key_preview_count: "
            f"`{summary['create_issues_safety_contract_key_preview_count']}`",
            "- create_issues_safety_contract_key_preview: "
            f"`{json.dumps(summary['create_issues_safety_contract_key_preview'], ensure_ascii=False)}`",
            "- create_issues_safety_contract_key_preview_sha256: "
            f"`{summary['create_issues_safety_contract_key_preview_sha256']}`",
            "- create_issues_safety_contract_key_tail_count: "
            f"`{summary['create_issues_safety_contract_key_tail_count']}`",
            "- create_issues_safety_contract_key_tail: "
            f"`{json.dumps(summary['create_issues_safety_contract_key_tail'], ensure_ascii=False)}`",
            "- create_issues_safety_contract_key_tail_sha256: "
            f"`{summary['create_issues_safety_contract_key_tail_sha256']}`",
            f"- publication_ok: `{str(summary['publication_ok']).lower()}`",
            f"- publication_visibility_status: `{summary['publication_visibility_status']}`",
            f"- publication_branch: `{summary['publication_branch']}`",
            f"- publication_upstream: `{summary['publication_upstream']}`",
            f"- publication_remote: `{summary['publication_remote']}`",
            f"- publication_latest_tag: `{summary['publication_latest_tag']}`",
            f"- publication_tag_commit: `{summary['publication_tag_commit']}`",
            f"- publication_local_head: `{summary['publication_local_head']}`",
            f"- publication_upstream_head: `{summary['publication_upstream_head']}`",
            "- publication_tag_points_at_head: "
            f"`{str(summary['publication_tag_points_at_head']).lower()}`",
            "- publication_tag_commit_in_upstream: "
            f"`{str(summary['publication_tag_commit_in_upstream']).lower()}`",
            f"- publication_branch_published: `{str(summary['publication_branch_published']).lower()}`",
            f"- publication_tag_published: `{str(summary['publication_tag_published']).lower()}`",
            f"- publication_remote_branch_head: `{summary['publication_remote_branch_head']}`",
            f"- publication_remote_tag_commit: `{summary['publication_remote_tag_commit']}`",
            f"- publication_remote_checked: `{str(summary['publication_remote_checked']).lower()}`",
            f"- publication_ahead_count: `{summary['publication_ahead_count']}`",
            f"- publication_behind_count: `{summary['publication_behind_count']}`",
            f"- release_draft_ok: `{str(summary['release_draft_ok']).lower()}`",
            f"- release_draft_issue_count: `{summary['release_draft_issue_count']}`",
            f"- candidate_issue_gate_key_count: `{summary['candidate_issue_gate_key_count']}`",
            f"- candidate_issue_gate_sha256: `{summary['candidate_issue_gate_sha256']}`",
            f"- candidate_issue_gate_status: `{summary['candidate_issue_gate_status']}`",
            f"- can_create_issues: `{str(summary['can_create_issues']).lower()}`",
            f"- requires_maintainer_review: `{str(summary['requires_maintainer_review']).lower()}`",
            f"- candidate_issue_gate_summary_sha256: `{summary['candidate_issue_gate_summary_sha256']}`",
            f"- candidate_issue_gate_evidence_key_count: `{summary['candidate_issue_gate_evidence_key_count']}`",
            f"- candidate_issue_gate_evidence_sha256: `{summary['candidate_issue_gate_evidence_sha256']}`",
            "- candidate_issue_gate_evidence_first_key: "
            f"`{summary['candidate_issue_gate_evidence_first_key']}`",
            "- candidate_issue_gate_evidence_last_key: "
            f"`{summary['candidate_issue_gate_evidence_last_key']}`",
            "- candidate_issue_gate_evidence_key_boundary_sha256: "
            f"`{summary['candidate_issue_gate_evidence_key_boundary_sha256']}`",
            "- candidate_issue_gate_reason_description_count: "
            f"`{summary['candidate_issue_gate_reason_description_count']}`",
            "- candidate_issue_gate_reason_descriptions_sha256: "
            f"`{summary['candidate_issue_gate_reason_descriptions_sha256']}`",
            f"- candidate_issue_gate_reason_code_count: `{summary['candidate_issue_gate_reason_code_count']}`",
            f"- candidate_issue_gate_reason_codes_sha256: `{summary['candidate_issue_gate_reason_codes_sha256']}`",
            "- candidate_issue_gate_first_reason_code: "
            f"{_summary_inline_code(summary['candidate_issue_gate_first_reason_code'])}",
            "- candidate_issue_gate_last_reason_code: "
            f"{_summary_inline_code(summary['candidate_issue_gate_last_reason_code'])}",
            "- candidate_issue_gate_reason_code_boundary_sha256: "
            f"`{summary['candidate_issue_gate_reason_code_boundary_sha256']}`",
            "- candidate_issue_gate_primary_reason_code: "
            f"{_summary_inline_code(summary['candidate_issue_gate_primary_reason_code'])}",
            "- candidate_issue_gate_primary_reason_description: "
            f"{_summary_inline_code(summary['candidate_issue_gate_primary_reason_description'])}",
            f"- candidate_issue_gate_required_action_count: `{summary['candidate_issue_gate_required_action_count']}`",
            "- candidate_issue_gate_required_actions_sha256: "
            f"`{summary['candidate_issue_gate_required_actions_sha256']}`",
            "- candidate_issue_gate_first_required_action: "
            f"{_summary_inline_code(summary['candidate_issue_gate_first_required_action'])}",
            "- candidate_issue_gate_last_required_action: "
            f"{_summary_inline_code(summary['candidate_issue_gate_last_required_action'])}",
            "- candidate_issue_gate_required_action_boundary_sha256: "
            f"`{summary['candidate_issue_gate_required_action_boundary_sha256']}`",
            "- candidate_issue_gate_primary_required_action: "
            f"{_summary_inline_code(summary['candidate_issue_gate_primary_required_action'])}",
            f"- dry_run_supported: `{str(summary['dry_run_supported']).lower()}`",
            f"- preflight_required: `{str(summary['preflight_required']).lower()}`",
        ]
    )


def _issue_artifact_candidate_summary(promotions: list[CandidatePromotion]) -> str:
    if not promotions:
        return "## Candidate Summary\n\n- No candidate issue metadata is available."
    lines = [
        "## Candidate Summary",
        "",
        (
            "| Case | Issue Body | Target URL | Candidate Commands | Offline Validation Commands | "
            "Priority Rank | Priority Reason | Primary Evidence Task | Primary Evidence Status | "
            "Primary Acceptance Criteria | Evidence Bundle Primary Next Task | "
            "Evidence Bundle Primary Runbook | LLM Preflight Evidence Fields | "
            "Candidate Package Validation | Evidence Bundle | Evidence Bundle JSON |"
        ),
        "|------|------------|------------|--------------------|-----------------------------|---------------|-----------------|-----------------------|-------------------------|-----------------------------|-----------------------------------|---------------------------------|-------------------------------|------------------------------|-----------------|----------------------|",
    ]
    for promotion in promotions:
        primary_task = promotion.promotion_evidence_primary_task.get("task") or "Not declared."
        primary_status = promotion.promotion_evidence_primary_task.get("status") or "unknown"
        primary_acceptance = (
            promotion.promotion_evidence_primary_task.get("acceptance_criteria")
            or "Not declared."
        )
        evidence_bundle_primary_task = promotion.evidence_bundle_primary_next_task.get("task") or "Not declared."
        primary_runbook = _candidate_primary_runbook_summary(
            promotion.evidence_bundle_primary_next_task_runbook
        )
        evidence_fields = ", ".join(
            f"`{field}`" for field in promotion.llm_live_preflight_evidence_fields
        )
        lines.append(
            f"| `{promotion.case_id}` | `{promotion.case_id}.md` | {promotion.target_url or 'Not declared.'} | "
            f"{len(promotion.commands)} | {len(promotion.offline_commands)} | "
            f"`{promotion.priority_rank}` | {promotion.priority_reason or 'Not declared.'} | "
            f"`{primary_task}` | `{primary_status}` | {primary_acceptance} | "
            f"`{evidence_bundle_primary_task}` | "
            f"`{primary_runbook}` | "
            f"{evidence_fields or 'Not declared.'} | "
            f"`{promotion.candidate_package_validation_command}` | "
            f"`{promotion.evidence_bundle_command}` | `{promotion.evidence_bundle_json_command}` |"
        )
    return "\n".join(lines)


def _gh_issue_create_command(promotion: CandidatePromotion, body_path: Path) -> str:
    parts = [
        "gh",
        "issue",
        "create",
        "--title",
        promotion.issue_title,
        "--body-file",
        str(body_path),
    ]
    for label in promotion.issue_labels:
        parts.extend(["--label", label])
    return " ".join(shlex.quote(part) for part in parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan the next verified cliany-site release slice.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--target-version", help="Target release version. Defaults to next patch version.")
    parser.add_argument("--min-days", type=int, default=3, help="Minimum unique commit days expected this week.")
    parser.add_argument("--max-daily-releases", type=int, default=3, help="Maximum release tags allowed per day.")
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Check live remote branch and tag refs in publication inputs.",
    )
    parser.add_argument("--remote-name", default="origin", help="Fallback remote name when no upstream is configured.")
    parser.add_argument("--min-case-assets", type=int, default=8, help="Minimum tracked case assets expected.")
    parser.add_argument("--today", help="Override current date as YYYY-MM-DD, for audits.")
    parser.add_argument("--report", type=Path, help="Optional Markdown plan report path.")
    parser.add_argument("--packages-dir", type=Path, help="Optional directory containing demo adapter packages.")
    parser.add_argument(
        "--require-packages",
        action="store_true",
        help="Require --packages-dir package validation in the release readiness input.",
    )
    parser.add_argument(
        "--issues-dir",
        type=Path,
        help="Optional directory for candidate issue body files, metadata JSON, and a reviewable gh script.",
    )
    args = parser.parse_args(argv)

    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else None
    plan = build_plan(
        ROOT,
        today=today,
        target_version=args.target_version,
        min_commit_days=args.min_days,
        max_daily_releases=args.max_daily_releases,
        remote_check=args.remote,
        remote_name=args.remote_name,
        min_case_assets=args.min_case_assets,
        packages_dir=args.packages_dir,
        require_packages=args.require_packages,
    )
    if args.report:
        _write_markdown_report(plan, args.report)
    if args.issues_dir:
        _write_candidate_issue_files(plan, args.issues_dir)
    if args.json:
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_text(plan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
