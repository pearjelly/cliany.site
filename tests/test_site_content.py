from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_site_quickstart_matches_v0150_ten_minute_success_path():
    index = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    docs = (ROOT / "site" / "docs" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "site" / "script.js").read_text(encoding="utf-8")
    styles = (ROOT / "site" / "style.css").read_text(encoding="utf-8")

    assert "cliany-site doctor" in index
    assert "10-Minute Success Path" in index
    assert "10 分钟成功路径" in docs
    assert "cliany-site cases" in index
    assert "cliany-site cases" in docs
    assert "issues.apache.org.cliany-adapter-v0.14.0.tar.gz" not in index
    assert "issues.apache.org.cliany-adapter-v0.14.0.tar.gz" not in docs
    assert "cliany-site verify issues.apache.org --json" not in index
    assert "cliany-site verify issues.apache.org --json" not in docs
    assert "cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json" not in docs
    assert "不需要先配置 LLM key" in docs
    assert "E_LLM_UNAVAILABLE" in docs
    assert "provider connection failure" in docs
    assert "generate_adapters.ready=false" in docs
    assert "Real Demo Case Proposal" in index
    assert "cliany-site cases --case-id pypi-project-search --issue-template" in index
    assert "Acceptance Criteria" in index
    assert "Primary Runbook" in index
    assert "Command SHA-256" in index
    assert "Promotion Command Plan Summary" in index
    assert "promotion_command_plan_summary" in index
    assert "issue_template_promotion_command_plan_summary" in index
    assert "candidate_promotions[*].promotion_command_plan_summary" in index
    assert "Promotion Command Plan</code> <code>command_sha256</code>" in index
    assert "<code>source</code> / <code>missing</code>" in index
    assert "Doctor Preflight Evidence Fields" in index
    assert "Doctor Preflight Evidence Template" in index
    assert "doctor_preflight_evidence_template" in index
    assert "doctor_preflight_evidence_template_field_count" in index
    assert "doctor_preflight_evidence_template_sha256" in index
    assert "doctor_preflight_state_fields" in index
    assert "doctor_preflight_state_statuses" in index
    assert "preflight_state.status" in index
    assert "preflight_state.ready_for_adapter_package" in index
    assert "preflight_state.primary_reason" in index
    assert "preflight_state.reason_codes" in index
    assert "preflight_state.next_action" in index
    assert "missing_fields" in index
    assert "--doctor-json /tmp/cliany-doctor-preflight.json --json" in index
    assert "doctor_preflight_evidence_values" in index
    assert "doctor_preflight_evidence_ok" in index
    assert "doctor_preflight_evidence_missing_count" in index
    assert "doctor_preflight_state" in index
    assert "cases/manifest.json" in index
    assert "python scripts/validate_cases.py --strict" in index
    assert "cliany-site cases --case-id &lt;id&gt; --evidence-bundle --json" in index
    assert "promotion_command_plan[*].command_sha256" in index
    assert "cliany-site cases --status candidate --promotion-plan" in index
    assert "primary_issue_template_command" in index
    assert "promotion_plan.primary_doctor_preflight_evidence_template_sha256" in index
    assert "promotion_plan.primary_llm_live_preflight_command_sha256" in index
    assert "primary_doctor_preflight_evidence_template_sha256" in index
    assert "task_queue[*].doctor_preflight_evidence_template_sha256" in index
    assert "task_queue[*].llm_live_preflight_command_sha256" in index
    assert "promotion_evidence_summary.primary_next_task.doctor_preflight_evidence_template_sha256" in index
    assert "scripts/validate_cases.py --report" in index
    assert "scripts/validate_cases.py --strict" in index
    assert "promotion_evidence_primary_doctor_preflight_evidence_template_sha256" in index
    assert "promotion_evidence_primary_llm_live_preflight_command_sha256" in index
    assert "Candidate Promotion Runbook" in index
    assert "docs/candidate-promotion-runbook.md" in index
    assert "pypi.org-&lt;version&gt;.cliany-adapter.tar.gz" in index
    assert "issue_template_json_command" in index
    assert "primary_next_task_acceptance_criteria" in index
    assert "preflight_required" in index
    assert "preflight_blocker" in index
    assert "python scripts/plan_next_iteration.py --issues-dir" in index
    assert "Primary Acceptance Criteria" in index
    assert "docs/good-first-issues.md" in index
    assert "docs/weekly-maintainer-loop.md" in index
    assert "python scripts/release_readiness.py --json" in index
    assert "python scripts/check_release_cadence.py --json" in index
    assert "next_actions" in index
    assert "weekly_commit_cadence_ok" in index
    assert "release_count_today" in index
    assert "max_daily_releases" in index
    assert "daily_release_limit_ok" in index
    assert "daily_release_cap_blocked" in index
    assert "daily_release_resume_date" in index
    assert "case_promotion_evidence_primary_llm_live_preflight_required" in index
    assert "case_promotion_evidence_primary_llm_live_preflight_command_sha256" in index
    assert "case_promotion_evidence_primary_llm_live_preflight_blocker_comment" in index
    assert "case_promotion_evidence_primary_doctor_preflight_blocker_comment" in index
    assert "case_promotion_evidence_primary_doctor_preflight_evidence_template_sha256" in index
    assert "case_promotion_doctor_preflight_evidence_template_sha256" in index
    assert "doctor_preflight_evidence_fields" in index
    assert "candidate_promotions[*].issue_template_command" in index
    assert "issue-metadata.json" in index
    assert "Candidate Promotion Runbook" in docs
    assert "docs/candidate-promotion-runbook.md" in docs
    assert "pypi.org-&lt;version&gt;.cliany-adapter.tar.gz" in docs
    assert "cliany-site pypi.org search-projects --query cliany-site --limit 5 --json" in docs
    assert "cliany-site cases --case-id &lt;id&gt; --evidence-bundle --json" in docs
    assert "1-3 releases/day loop" in index
    assert "Current baseline: v0.16.276" in index
    assert "当前基线：v0.16.276" in script
    assert "64 个字符小写十六进制 SHA-256 摘要" in script
    assert "lowercase 64-character hexadecimal SHA-256 of the completed archive" in script
    assert "market publish" in index
    assert "package_sha256" in index
    assert "lowercase 64-character hexadecimal SHA-256 of the completed archive" in index
    assert "v0.16.276 · Python" in docs
    assert "demo_adapter_quickstart.commands" in index
    assert "ready_for_demo_adapters=true" in docs
    assert "pinned GitHub Release URL, SHA-256 install, verify, and read-only command" in script
    assert "package_sha256" in docs
    assert "64 个字符小写十六进制 SHA-256 摘要" in docs
    assert "pypi-project-search" in index
    assert "E_LLM_UNAVAILABLE" in index
    assert "expects_nonempty" in index
    assert "list/search/read/extract" in index
    assert "extract action" in index
    assert "expects_nonempty=false" in script
    assert "list/search/read/extract" in script
    assert "extract action" in script
    assert "not silently rewritten" in script
    assert "expects_nonempty=false" in docs
    assert "data.quality" in docs
    assert "read-" in docs
    assert "extract-" in docs
    assert "E_EMPTY_RESULT" in docs
    assert "cliany-site market install &lt;package&gt; --dry-run --json" in index
    assert "--sha256 &lt;64-hex-sha256&gt;" in index
    assert "website alias inspect" in index
    assert "PyPI version-specific publication audit" in index
    assert "10-Minute Success Path" in script
    assert "demo_adapter_quickstart.commands" in script
    assert "cliany-site cases --case-id suitecrm-accounts" in docs
    assert "primary_next_task_acceptance_criteria" in script
    assert "cliany-site cases --case-id &lt;id&gt; --evidence-bundle --json" in script
    assert "promotion_command_plan[*].command_sha256" in script
    assert "cliany-site cases --status candidate --promotion-plan" in script
    assert "primary_issue_template_command" in script
    assert "promotion_plan.primary_doctor_preflight_evidence_template_sha256" in script
    assert "promotion_plan.primary_llm_live_preflight_command_sha256" in script
    assert "primary_doctor_preflight_evidence_template_sha256" in script
    assert "task_queue[*].doctor_preflight_evidence_template_sha256" in script
    assert "task_queue[*].llm_live_preflight_command_sha256" in script
    assert "promotion_evidence_summary.primary_next_task.doctor_preflight_evidence_template_sha256" in script
    assert "scripts/validate_cases.py --report" in script
    assert "scripts/validate_cases.py --strict" in script
    assert "promotion_evidence_primary_doctor_preflight_evidence_template_sha256" in script
    assert "promotion_evidence_primary_llm_live_preflight_command_sha256" in script
    assert "Candidate Promotion Runbook" in script
    assert "docs/candidate-promotion-runbook.md" in script
    assert "pypi.org-&lt;version&gt;.cliany-adapter.tar.gz" in script
    assert "issue_template_json_command" in script
    assert "python scripts/plan_next_iteration.py --issues-dir" in script
    assert "Primary Acceptance Criteria" in script
    assert "Generate Your Own" in script
    assert "After Your First Success" in script
    assert "cliany-site cases --case-id pypi-project-search --issue-template" in script
    assert "Acceptance Criteria" in script
    assert "Primary Runbook" in script
    assert "Command SHA-256" in script
    assert "Promotion Command Plan Summary" in script
    assert "promotion_command_plan_summary" in script
    assert "issue_template_promotion_command_plan_summary" in script
    assert "candidate_promotions[*].promotion_command_plan_summary" in script
    assert "Promotion Command Plan</code> <code>command_sha256</code>" in script
    assert "<code>source</code> / <code>missing</code>" in script
    assert "Doctor Preflight Evidence Fields" in script
    assert "Doctor Preflight Evidence Template" in script
    assert "doctor_preflight_evidence_template" in script
    assert "doctor_preflight_evidence_template_field_count" in script
    assert "doctor_preflight_evidence_template_sha256" in script
    assert "--doctor-json /tmp/cliany-doctor-preflight.json --json" in script
    assert "doctor_preflight_evidence_values" in script
    assert "doctor_preflight_evidence_ok" in script
    assert "doctor_preflight_evidence_missing_count" in script
    assert "doctor_preflight_state" in script
    assert "doctor_preflight_state_fields" in script
    assert "doctor_preflight_state_statuses" in script
    assert "preflight_state.status" in script
    assert "preflight_state.ready_for_adapter_package" in script
    assert "preflight_state.primary_reason" in script
    assert "preflight_state.reason_codes" in script
    assert "preflight_state.next_action" in script
    assert "missing_fields" in script
    assert "First-time contributors" in script
    assert "Maintainer Loop" in script
    assert "weekly_commit_cadence_ok" in script
    assert "release_count_today" in script
    assert "max_daily_releases" in script
    assert "daily_release_limit_ok" in script
    assert "daily_release_cap_blocked" in script
    assert "daily_release_resume_date" in script
    assert "case_promotion_evidence_primary_llm_live_preflight_command_sha256" in script
    assert "case_promotion_evidence_primary_llm_live_preflight_blocker_comment" in script
    assert "case_promotion_evidence_primary_doctor_preflight_blocker_comment" in script
    assert "case_promotion_evidence_primary_doctor_preflight_evidence_template_sha256" in script
    assert "case_promotion_doctor_preflight_evidence_template_sha256" in script
    assert "doctor_preflight_evidence_fields" in script
    assert "candidate_promotions[*].issue_template_command" in script
    assert "issue-metadata.json" in script
    assert "cliany-site market install &lt;package&gt; --dry-run --json" in script
    assert "--sha256 &lt;64-hex-sha256&gt;" in script
    assert "website alias inspect" in script
    assert "pypi_latest_version" in script
    assert ".first-success-card .code-block-container" in styles
    assert ".first-success-card .copy-btn" in styles
    assert "position: static;" in styles
    assert ".first-success-card .code-block" in styles
    assert "white-space: pre-wrap;" in styles
