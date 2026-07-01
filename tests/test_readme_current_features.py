from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readmes_document_current_extract_quality_and_readiness():
    expected_partial_terms = {
        "README.md": "partially missing required fields",
        "README.zh.md": "关键字段部分缺失",
    }
    for filename in ("README.md", "README.zh.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")

        assert "v0.14.4" in text
        assert "data.quality" in text
        assert "--strict-quality" in text
        assert "E_EMPTY_RESULT" in text
        assert "scripts/release_readiness.py" in text
        assert "scripts/check_release_publication.py --json" in text
        assert "cliany-site cases --case-id pypi-project-search --json" in text
        assert "cliany-site cases --status candidate --promotion-plan" in text
        assert "promotion_plan.primary_next_item" in text
        assert "promotion_evidence_summary.primary_next_task" in text
        assert "promotion_evidence_summary.primary_next_task_acceptance_criteria" in text
        assert "python scripts/plan_next_iteration.py --issues-dir" in text
        assert "Primary Evidence Status" in text
        assert "Primary Acceptance Criteria" in text
        assert "promotion_evidence_summary.primary_task_detail" not in text
        assert "cliany-site cases --case-id pypi-project-search --issue-template" in text
        assert "issue_template_primary_task" in text
        assert "expected_adapter_package" in text
        assert "llm_live_preflight_required" in text
        assert "preflight_required" in text
        assert "preflight_blocker" in text
        assert "cliany-site cases --case-id pypi-project-search --evidence-bundle" in text
        assert "cliany-site cases --case-id pypi-project-search --evidence-bundle --json" in text
        assert "acceptance_criteria" in text
        assert "Real Demo Case Proposal" in text
        assert "weekly-maintainer-loop.md" in text
        assert (
            "one to three verified versions per day" in text
            or "每天 1~3 个可验证版本" in text
        )
        assert "release_count_today" in text
        assert "max_daily_releases" in text
        assert "daily_release_limit_ok" in text
        assert "daily_release_cap_blocked" in text
        assert "daily_release_resume_date" in text
        assert "next_actions" in text
        assert "primary_next_action" in text
        assert "next_actions_sha256" in text
        assert "publication_next_actions_sha256" in text
        assert "publication_publish_commands_sha256" in text
        assert "target_tag_commands_sha256" in text
        assert "github.com-1.0.0.cliany-adapter.tar.gz" in text
        assert "./github.com.cliany-adapter.tar.gz" not in text
        assert expected_partial_terms[filename] in text
