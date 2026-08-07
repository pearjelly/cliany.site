from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sdk_examples_include_an_async_entrypoint():
    for path in (ROOT / "README.md", ROOT / "README.zh.md", ROOT / "site" / "docs" / "index.html"):
        text = path.read_text(encoding="utf-8")
        assert "async def main():" in text
        assert "asyncio.run(main())" in text


def test_site_quickstart_matches_v0150_ten_minute_success_path():
    index = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    docs = (ROOT / "site" / "docs" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "site" / "script.js").read_text(encoding="utf-8")
    styles = (ROOT / "site" / "style.css").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh.md").read_text(encoding="utf-8")

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
    assert "Current baseline: v0.16.305" in index
    assert "当前基线：v0.16.305" in script
    assert "E_VERIFY_STATIC" in index
    assert "E_VERIFY_STATIC" in script
    assert "ADAPTER_NOT_FOUND" in index
    assert "ADAPTER_NOT_FOUND" in script
    assert "<code>404</code> 表示 adapter 或命令不存在" in docs
    assert "<code>503</code> 表示 Chrome 或 LLM 依赖暂不可用" in docs
    assert "params</code> 必须是对象" in docs
    assert 'cliany-site --headless serve --port 8080' in docs
    assert 'cliany-site --cdp-url "ws://chrome:9222" serve --port 8080' in docs
    assert "GET /health" in docs
    assert "GET /verify?domain=&lt;domain&gt;" in docs
    assert "await cs.verify(\"github.com\")" in docs
    assert "await cs.verify(\"github.com\")" in readme
    assert "await cs.verify(\"github.com\")" in readme_zh
    assert "GET /verify" in readme
    assert "GET /verify" in readme_zh
    assert "静态 adapter 检查，不会连接 Chrome 或 LLM" in docs
    assert '"service":"cliany-site"' in docs
    assert "liveness probe" in docs
    assert "marketplace dry run only preflights the package" in script
    assert "64 个字符小写十六进制 SHA-256 摘要" in script
    assert "lowercase 64-character hexadecimal SHA-256 of the completed archive" in script
    assert "market publish" in index
    assert "package_sha256" in index
    assert "lowercase 64-character hexadecimal SHA-256 of the completed archive" in index
    assert "v0.16.305 · Python" in docs
    assert "daily_release_capacity_remaining" in script
    assert "installed_version" in docs
    assert "installed_version=null" in docs
    assert "would_replace" in docs
    assert "audit_candidate_issues.py" in docs
    assert "unexpected" in docs
    assert "实际 title 和 URL" in docs
    assert "demo_adapter_quickstart.recommended_commands" in index
    assert "verify --strict" in index
    assert "verify --strict" in docs
    assert "固定 SHA-256 安装" in docs
    assert "不会替你安装、登录、执行或覆盖" in docs
    assert "cliany-site cases --status active" in docs
    human_step = "# 2. 复制上一步 human `doctor` 按顺序打印的命令"
    automation_step = "# 3. 自动化脚本才运行 JSON 路径"
    assert human_step in docs
    assert automation_step in docs
    assert docs.index(human_step) < docs.index(automation_step)
    assert "会把未来的 adapter 命令标为“当前不可运行”" in docs
    assert "不能当作 active demo 快速命令" in docs
    assert "修复 provider 配置或连接后重跑同一命令" in docs
    assert "cliany-site doctor --llm-live --require-capability generate_adapters --json" in docs
    assert "commands.py" in docs
    assert "click.Group" in index
    assert "click.Group" in script
    assert "POST /execute" in docs
    assert "E_VERIFY_STATIC" in docs
    assert "不会先启动浏览器" in docs
    assert "E_PARSE_FAILED" in index
    assert "E_PARSE_FAILED" in script
    assert "Generated adapter commands now preserve failed JSON envelopes and exit nonzero" in index
    assert "生成的 adapter 命令会保留失败 JSON envelope 并以非零状态退出" in script
    assert "cliany-site [ROOT OPTIONS] explore" in docs
    assert "--record / --no-record" in docs
    assert 'cliany-site --headless explore "https://github.com" "搜索仓库" --json' in docs
    assert 'cliany-site --cdp-url "ws://localhost:9222" explore "https://github.com" "搜索仓库" --json' in docs
    assert 'cliany-site explore "https://github.com" "搜索仓库" \\\n+  --headless' not in docs
    assert "--headless      无头模式（服务器/CI 环境）" not in docs
    assert "--cdp-url &lt;ws://host:port&gt;" not in docs
    assert "### Server and Docker Browser Setup" in readme
    assert 'cliany-site --headless explore "https://github.com" "Search repositories" --json' in readme
    assert (
        'cliany-site --cdp-url "ws://chrome:9222" explore '
        '"https://github.com" "Search repositories" --json' in readme
    )
    assert 'cliany-site --headless serve --port 8080' in readme
    assert 'cliany-site --cdp-url "ws://chrome:9222" serve --port 8080' in readme
    assert "curl -i http://localhost:8080/health" in readme
    assert '"service":"cliany-site"' in readme
    assert 'cliany-site --headless serve --port 8080' in readme_zh
    assert 'cliany-site --cdp-url "ws://chrome:9222" serve --port 8080' in readme_zh
    assert "curl -i http://localhost:8080/health" in readme_zh
    assert '"service":"cliany-site"' in readme_zh
    assert "ready_for_demo_adapters=true" in docs
    assert "exposes <code>recommended_commands</code>" in script
    assert "verify --strict" in script
    assert "commands.py" in script
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
    assert "data.quality.field_blank_rows" in index
    assert "data.quality.field_blank_rows" in docs
    assert "data.quality.field_blank_rows" in script
    assert "read-" in docs
    assert "extract-" in docs
    assert "E_EMPTY_RESULT" in docs
    assert "cliany-site market install &lt;package&gt; --dry-run --json" in index
    assert "--sha256 &lt;64-hex-sha256&gt;" in index
    assert "<code>requires_force=true</code> 的只读计划" in docs
    assert "website alias inspect" in index
    assert "PyPI version-specific publication audit" in index
    assert "10-Minute Success Path" in script
    assert "demo_adapter_quickstart.recommended_commands" in script
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
