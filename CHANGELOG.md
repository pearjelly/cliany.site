# 更新日志

本项目的所有显著更改都将记录在此文件中。

本文件的格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
并且本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 新增 `docs/releases/v0.16.227-draft.md`，把下一版 patch release 聚焦到 `v0.16.226` 本地 release 的发布可见性交接。
- `v0.16.227` 草案明确记录 `publication_visibility`、`candidate_issue_gate`、`publication-handoff.json` 和 `release-draft-handoff.json` 在本地 release 未公开时的审阅路径。

### Fixed
- `plan_next_iteration.py` 现在把 `tag_points_at_head=false` 的发布审计动作透传到顶层 `next_actions` 和 `publication_visibility.summary`，避免把 tag mismatch 误写成“直接推 tag”。
- `check_release_publication.py --publish-script` 现在在最新 tag 不指向 HEAD 时写入审阅注释，明确脚本不会自动推送旧 tag。
- `check_release_publication.py --json` / `--report` 现在输出 `tag_publish_decision`，用稳定字段标记 `manual_decision_required`、`ready_to_push`、`published` 等 tag 发布状态。
- `plan_next_iteration.py` 现在把 `tag_publish_decision` 透传为 `publication_tag_publish_decision`，并写入 Markdown report、`artifact-manifest.json`、`publication-handoff.json` 和 artifacts `README.md`。
- `artifact_bundle_summary` 现在输出 `publication_tag_publish_decision_*` 摘要字段，让只读整包摘要的维护工具也能判断 tag 是否可推，并检测该对象字段漂移。
- `candidate_issue_gate.evidence` 现在包含 tag 发布决策状态、是否可推和 required action，artifacts `README.md` 的 `Publication Handoff` 也会展示同一组 gate evidence。
- `candidate_issue_gate` 现在直接输出 `primary_reason_code`、`primary_reason_description` 和 `primary_required_action`，artifacts `README.md` 的 `Publication Handoff` 也会展示这组首要 gate 字段。
- `publication-handoff.json` 现在把 `candidate_issue_gate_primary_reason_code`、`candidate_issue_gate_primary_reason_description` 和 `candidate_issue_gate_primary_required_action` 提升为顶层别名，方便只读 handoff 的工具展示首要 gate 状态。
- `artifact_bundle_summary` 现在输出 `publication_handoff_candidate_issue_gate_primary_*` 字段，让只读整包摘要的工具也能确认 publication handoff 顶层 gate primary 别名。
- `plan_next_iteration.py` 现在输出结构化 `commit_cadence`，并在 Markdown report、`artifact-manifest.json` 和 `artifact_bundle_summary` 中展示提交天数状态、缺口和摘要 hash。
- `publication-handoff.json` 和 artifacts `README.md` 的 `Publication Handoff` 现在展示 `commit_cadence` 状态、缺口和首要 cadence next action，帮助维护者先看到本周提交天数阻塞。
- Candidate issue artifacts `README.md` 现在新增 `Commit Cadence` 小节，集中展示本周提交天数、缺口、已有提交日期和 cadence next actions。
- `artifact_bundle_summary` 现在输出 `commit_cadence_next_action_count` 和 `commit_cadence_primary_next_action`，让只读整包摘要的工具能直接展示提交节奏下一步。

## [0.16.226] - 2026-06-15

### Added
- 新增 `docs/releases/v0.16.226-draft.md`，把下一版 patch release 聚焦到 `v0.16.225` 本地 release 的发布可见性交接。
- `v0.16.226` 草案明确记录 `publication_visibility`、`candidate_issue_gate`、`publication-handoff.json` 和 `release-draft-handoff.json` 在本地 release 未公开时的审阅路径。

## [0.16.225] - 2026-06-15

### Added
- 新增 `docs/releases/v0.16.225-draft.md`，把下一版 patch release 聚焦到发布可见性优先的维护路径。
- `v0.16.225` 草案明确记录 `publication_visibility`、`candidate_issue_gate`、`publication-handoff.json` 和 `release-draft-handoff.json` 的交接关系，让下一轮计划不再被缺失草案阻塞。

### Fixed
- `plan_next_iteration.py` 现在只在 release draft 真的存在校验问题时提示 `Draft and verify`，避免草案已通过后仍重复提示已完成动作。

## [0.16.224] - 2026-06-15

### Added
- `artifact_bundle_summary` 现在输出 `case_promotion_evidence_primary_case_id`、`case_promotion_evidence_primary_task` 和 `case_promotion_evidence_primary_status`，让只读整包摘要的工具能直接定位首要 candidate 晋级任务。
- `artifact_bundle_summary` 现在输出 `case_promotion_evidence_primary_evidence_sha256`，让维护工具能检测首要任务当前 evidence 是否漂移。
- 新增 `docs/releases/v0.16.224-draft.md`，把下一版 patch release 聚焦到 candidate promotion primary task 的 bundle-level 可定位性。

## [0.16.223] - 2026-06-15

### Added
- `artifact_bundle_summary` 现在输出 `case_promotion_evidence_summary_*` key count/hash/preview/tail/boundary 字段，让只读整包摘要的工具能检测 candidate 晋级证据摘要字段漂移。
- `artifact_bundle_summary` 现在输出 `case_promotion_evidence_candidate_count`、`case_promotion_evidence_task_count`、pending/blocked/complete 计数和 `case_promotion_evidence_primary_next_action`，方便维护工具不展开完整 manifest 也能展示首要晋级动作。
- 新增 `docs/releases/v0.16.223-draft.md`，把下一版 patch release 聚焦到 candidate promotion evidence summary 的 bundle-level 可审计性。

## [0.16.222] - 2026-06-15

### Added
- Candidate issue artifacts 的 `artifact-manifest.json` 现在带顶层 `case_promotion_evidence_summary`，让只读 manifest 的维护工具能直接看到 candidate 晋级证据摘要。
- Candidate issue artifacts `README.md` 现在展示 `Candidate Promotion Evidence Summary` 小节，把 pending/blocked/complete 数量、primary next action 和任务明细放进人工审阅入口。
- 新增 `docs/releases/v0.16.222-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的证据摘要可见性。

## [0.16.221] - 2026-06-13

### Added
- `scripts/plan_next_iteration.py` 的 JSON、默认文本输出和 Markdown report 现在输出 `case_promotion_evidence_summary`，让周初计划直接展示 candidate 晋级任务的状态汇总。
- Next iteration Markdown report 新增 `Candidate Promotion Evidence Summary` 小节，展示 candidate/task 数量、pending/blocked/complete 数量、primary next action 和任务明细。
- 新增 `docs/releases/v0.16.221-draft.md`，把下一版 patch release 聚焦到周初计划中的 candidate promotion evidence summary。

## [0.16.220] - 2026-06-13

### Added
- `scripts/validate_cases.py` 的 JSON 现在输出 `promotion_evidence_summary`，汇总 candidate 数量、任务数量、pending/blocked/complete 状态计数和 primary next action。
- `scripts/validate_cases.py --report` 新增 `Candidate Promotion Evidence Summary` 小节，让维护者不用展开每个 candidate 也能看到下一项该推进的晋级证据。
- `scripts/validate_cases.py` 默认文本输出现在展示 `promotion_evidence_pending`、`promotion_evidence_blocked`、`promotion_evidence_complete` 和 `promotion_evidence_next`。
- 新增 `docs/releases/v0.16.220-draft.md`，把下一版 patch release 聚焦到 candidate promotion evidence summary。

## [0.16.219] - 2026-06-13

### Added
- Candidate 案例现在声明 `promotion_evidence`，为 `adapter_package`、`metadata_validation` 和 `online_smoke` 记录 `pending` / `complete` / `blocked` 状态、证据和下一步动作。
- `scripts/validate_cases.py` 现在校验 candidate `promotion_evidence`，并在文本、JSON 和 Markdown report 中输出结构化晋级证据。
- `scripts/plan_next_iteration.py` 现在把 `promotion_evidence` 透传到 candidate promotion JSON、issue body、`issue-metadata.json` 和 issue metadata summary，方便维护者按证据状态拆分任务。
- 新增 `docs/releases/v0.16.219-draft.md`，把下一版 patch release 聚焦到 candidate promotion evidence 的可交接性。

## [0.16.218] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_next_action_preview_count`、`publication_next_action_preview` 和 `publication_next_action_preview_sha256`，让只读取整包摘要的维护工具能检查 publication next actions 前窗口。
- `artifact_bundle_summary` 现在输出 `publication_next_action_tail_count`、`publication_next_action_tail` 和 `publication_next_action_tail_sha256`，让 publication next actions 尾部窗口也可审计。
- 新增 `docs/releases/v0.16.218-draft.md`，把下一版 patch release 聚焦到 publication next action preview/tail 可见性。

## [0.16.217] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_handoff_key_preview_count`、`publication_handoff_key_preview` 和 `publication_handoff_key_preview_sha256`，让只读取整包摘要的维护工具能检查 `publication-handoff.json` 字段清单前窗口。
- `artifact_bundle_summary` 现在输出 `publication_handoff_key_tail_count`、`publication_handoff_key_tail` 和 `publication_handoff_key_tail_sha256`，让 publication handoff 字段清单尾部窗口也可审计。
- 新增 `docs/releases/v0.16.217-draft.md`，把下一版 patch release 聚焦到 publication handoff key preview/tail 可见性。

## [0.16.216] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_ref_context_key_preview_count`、`publication_ref_context_key_preview` 和 `publication_ref_context_key_preview_sha256`，让只读取整包摘要的维护工具能检查 publication ref context 字段清单前窗口。
- `artifact_bundle_summary` 现在输出 `publication_ref_context_key_tail_count`、`publication_ref_context_key_tail` 和 `publication_ref_context_key_tail_sha256`，让 publication ref context 字段清单尾部窗口也可审计。
- 新增 `docs/releases/v0.16.216-draft.md`，把下一版 patch release 聚焦到 publication ref context key preview/tail 可见性。

## [0.16.215] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_key_preview_count`、`release_draft_handoff_key_preview` 和 `release_draft_handoff_key_preview_sha256`，让只读取整包摘要的维护工具能检查 `release-draft-handoff.json` 字段清单前窗口。
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_key_tail_count`、`release_draft_handoff_key_tail` 和 `release_draft_handoff_key_tail_sha256`，让 release draft handoff 字段清单尾部窗口也可审计。
- 新增 `docs/releases/v0.16.215-draft.md`，把下一版 patch release 聚焦到 release draft handoff key preview/tail 可见性。

## [0.16.214] - 2026-06-13

### Added
- `release_readiness.py` 的 JSON 和 Markdown report 现在输出 `release_mode` 与 `release_tag`，让维护者和自动化能区分普通 target-version readiness 与 tagged release preflight。
- `Weekly Review` 的发布已验证 tag 文案现在只在显式 `--release-tag` 模式通过时出现；普通 `--target-version` readiness 继续提示准备打 tag。
- 新增 `docs/releases/v0.16.214-draft.md`，把下一版 patch release 聚焦到 release readiness mode 可见性。

## [0.16.213] - 2026-06-13

### Added
- `release_readiness.py --report` 的 `Weekly Review` 在 tagged release preflight 通过且 tag 已指向 HEAD 时，现在把下一步显示为发布已验证 tag。
- 新增测试覆盖 tagged release mode 的 Weekly Review 文案，避免 tag 已存在时继续提示维护者“Ready to tag”。
- 新增 `docs/releases/v0.16.213-draft.md`，把下一版 patch release 聚焦到 tagged release preflight 的下一步可读性。

## [0.16.212] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_issue_gate_evidence_first_key`、`candidate_issue_gate_evidence_last_key` 和 `candidate_issue_gate_evidence_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue gate evidence key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 gate evidence key boundary，并继续展示 evidence key count 和 evidence hash。
- 新增 `docs/releases/v0.16.212-draft.md`，把下一版 patch release 聚焦到 candidate issue gate evidence key boundary 可见性。

## [0.16.211] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `create_issues_safety_contract_key_preview_count`、`create_issues_safety_contract_key_preview` 和 `create_issues_safety_contract_key_preview_sha256`，让只读取整包摘要的维护工具能检查 create issues safety contract key 前窗口。
- `artifact_bundle_summary` 现在输出 `create_issues_safety_contract_key_tail_count`、`create_issues_safety_contract_key_tail` 和 `create_issues_safety_contract_key_tail_sha256`，让 create issues safety contract keys 的尾部窗口与 review checklist、validation commands 和 blockers 的可见性保持一致。
- 新增 `docs/releases/v0.16.211-draft.md`，把下一版 patch release 聚焦到 create issues safety contract key preview/tail 可见性。

## [0.16.210] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_checklist_preview_count`、`review_checklist_preview` 和 `review_checklist_preview_sha256`，让只读取整包摘要的维护工具能检查 review checklist 前窗口。
- `artifact_bundle_summary` 现在输出 `review_checklist_tail_count`、`review_checklist_tail` 和 `review_checklist_tail_sha256`，让 review checklist 的尾部窗口与 validation commands、blockers 和 next actions 的可见性保持一致。
- 新增 `docs/releases/v0.16.210-draft.md`，把下一版 patch release 聚焦到 review checklist preview/tail 可见性。

## [0.16.209] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `validation_command_preview_count`、`validation_command_preview` 和 `validation_command_preview_sha256`，让只读取整包摘要的维护工具能检查 validation commands 前窗口。
- `artifact_bundle_summary` 现在输出 `validation_command_tail_count`、`validation_command_tail` 和 `validation_command_tail_sha256`，让 validation commands 的尾部窗口与 blockers、next actions 和 release draft windows 的可见性保持一致。
- 新增 `docs/releases/v0.16.209-draft.md`，把下一版 patch release 聚焦到 validation command preview/tail 可见性。

## [0.16.208] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_required_action_preview_count`、`release_draft_required_action_preview`、`release_draft_required_action_preview_sha256`、`release_draft_required_action_tail_count`、`release_draft_required_action_tail` 和 `release_draft_required_action_tail_sha256`，让只读取整包摘要的维护工具能检查 release draft required actions 前后窗口。
- `artifact_bundle_summary` 现在输出 `release_draft_issue_preview_count`、`release_draft_issue_preview`、`release_draft_issue_preview_sha256`、`release_draft_issue_tail_count`、`release_draft_issue_tail` 和 `release_draft_issue_tail_sha256`，让 release draft issues 的窗口摘要与 blockers/next actions 的可见性保持一致。
- 新增 `docs/releases/v0.16.208-draft.md`，把下一版 patch release 聚焦到 release draft issue/action preview 与 tail 可见性。

## [0.16.207] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_next_action_first_item`、`publication_next_action_last_item` 和 `publication_next_action_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication next actions 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication next action first/last item 与 boundary hash，并继续展示 next action count、完整 hash 和 primary action。
- 新增 `docs/releases/v0.16.207-draft.md`，把下一版 patch release 聚焦到 publication next action boundary 可见性。

## [0.16.206] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_handoff_first_key`、`publication_handoff_last_key` 和 `publication_handoff_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication handoff key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication handoff first/last key 与 boundary hash，并继续展示 handoff key count、schema version 和完整 hash。
- 新增 `docs/releases/v0.16.206-draft.md`，把下一版 patch release 聚焦到 publication handoff boundary 可见性。

## [0.16.205] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_first_key`、`release_draft_handoff_last_key` 和 `release_draft_handoff_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 release draft handoff key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft handoff first/last key 与 boundary hash，并继续展示 handoff key count、schema version、primary issue/action 和完整 hash。
- 新增 `docs/releases/v0.16.205-draft.md`，把下一版 patch release 聚焦到 release draft handoff boundary 可见性。

## [0.16.204] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_worktree_status_first_item`、`publication_worktree_status_last_item` 和 `publication_worktree_status_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication worktree status 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication worktree status first/last item 与 boundary hash，并继续展示 status count 和完整 hash。
- 新增 `docs/releases/v0.16.204-draft.md`，把下一版 patch release 聚焦到 publication worktree status boundary 可见性。

## [0.16.203] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_publish_first_command`、`publication_publish_last_command` 和 `publication_publish_command_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication publish commands 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication publish command first/last command 与 boundary hash，并继续展示 publish command count、完整 hash 和 primary command。
- 新增 `docs/releases/v0.16.203-draft.md`，把下一版 patch release 聚焦到 publication publish command boundary 可见性。

## [0.16.202] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_ref_context_first_key`、`publication_ref_context_last_key` 和 `publication_ref_context_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication ref context 的 key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication ref context first/last key 与 boundary hash，并继续展示 ref context key count 和完整 hash。
- 新增 `docs/releases/v0.16.202-draft.md`，把下一版 patch release 聚焦到 publication ref context boundary 可见性。

## [0.16.201] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `create_issues_safety_contract_first_key`、`create_issues_safety_contract_last_key` 和 `create_issues_safety_contract_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 create issues safety contract 的 key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 create issues safety contract first/last key 与 boundary hash，并继续展示 contract key count 和完整 hash。
- 新增 `docs/releases/v0.16.201-draft.md`，把下一版 patch release 聚焦到 create issues safety contract boundary 可见性。

## [0.16.200] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_checklist_first_item`、`review_checklist_last_item` 和 `review_checklist_boundary_sha256`，让只读取整包摘要的维护工具能检查 review checklist 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 review checklist first/last item 与 boundary hash，并继续展示 checklist count 和完整 hash。
- 新增 `docs/releases/v0.16.200-draft.md`，把下一版 patch release 聚焦到 review checklist boundary 可见性。

## [0.16.199] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `validation_first_command`、`validation_last_command` 和 `validation_command_boundary_sha256`，让只读取整包摘要的维护工具能检查 validation commands 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 validation command first/last command 与 boundary hash，并继续展示 validation command count 和完整 hash。
- 新增 `docs/releases/v0.16.199-draft.md`，把下一版 patch release 聚焦到 validation command boundary 可见性。

## [0.16.198] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_first_required_action`、`release_draft_last_required_action` 和 `release_draft_required_action_boundary_sha256`，让只读取整包摘要的维护工具能检查 release draft required actions 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft required action first/last action 与 boundary hash，并继续展示 required action count、完整 hash 和 primary action。
- 新增 `docs/releases/v0.16.198-draft.md`，把下一版 patch release 聚焦到 release draft required action boundary 可见性。

## [0.16.197] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_first_issue`、`release_draft_last_issue` 和 `release_draft_issue_boundary_sha256`，让只读取整包摘要的维护工具能检查 release draft issues 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft issue first/last item 与 boundary hash，并继续展示 issue count、primary issue 和完整 hash。
- 新增 `docs/releases/v0.16.197-draft.md`，把下一版 patch release 聚焦到 release draft issue boundary 可见性。

## [0.16.196] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_issue_gate_first_required_action`、`candidate_issue_gate_last_required_action` 和 `candidate_issue_gate_required_action_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue gate required action 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate issue gate required action first/last action 与 boundary hash，并继续展示 required action count、完整 hash 和 primary action。
- 新增 `docs/releases/v0.16.196-draft.md`，把下一版 patch release 聚焦到 candidate issue gate required action boundary 可见性。

## [0.16.195] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_issue_gate_first_reason_code`、`candidate_issue_gate_last_reason_code` 和 `candidate_issue_gate_reason_code_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue gate reason code 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate issue gate reason code first/last code 与 boundary hash，并继续展示 reason code count、完整 hash 和 primary reason。
- 新增 `docs/releases/v0.16.195-draft.md`，把下一版 patch release 聚焦到 candidate issue gate reason code boundary 可见性。

## [0.16.194] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `next_action_first_item`、`next_action_last_item` 和 `next_action_boundary_sha256`，让只读取整包摘要的维护工具能检查 next actions 列表首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 next action first/last item 与 boundary hash，并继续展示 next action preview、next action tail、next action count 与完整 hash。
- 新增 `docs/releases/v0.16.194-draft.md`，把下一版 patch release 聚焦到 next action boundary 可见性。

## [0.16.193] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `next_action_tail_count`、`next_action_tail` 和 `next_action_tail_sha256`，让只读取整包摘要的维护工具能看到 next actions 列表末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 next action tail count/list/hash，并继续展示 next action preview、next action count 与完整 hash。
- 新增 `docs/releases/v0.16.193-draft.md`，把下一版 patch release 聚焦到 next action tail 可见性。

## [0.16.192] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `next_action_preview_count`、`next_action_preview` 和 `next_action_preview_sha256`，让只读取整包摘要的维护工具能看到 next actions 列表入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 next action preview count/list/hash，并继续展示 next action count 与完整 hash。
- 新增 `docs/releases/v0.16.192-draft.md`，把下一版 patch release 聚焦到 next action preview 可见性。

## [0.16.191] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `blocker_first_item`、`blocker_last_item` 和 `blocker_boundary_sha256`，让只读取整包摘要的维护工具能检查 blockers 列表首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 blocker first/last item 与 boundary hash，并继续展示 blocker preview、blocker tail、blocker count 与完整 hash。
- 新增 `docs/releases/v0.16.191-draft.md`，把下一版 patch release 聚焦到 blocker boundary 可见性。

## [0.16.190] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `blocker_tail_count`、`blocker_tail` 和 `blocker_tail_sha256`，让只读取整包摘要的维护工具能看到 blockers 列表末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 blocker tail count/list/hash，并继续展示 blocker preview、blocker count 与完整 hash。
- 新增 `docs/releases/v0.16.190-draft.md`，把下一版 patch release 聚焦到 blocker tail 可见性。

## [0.16.189] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `blocker_preview_count`、`blocker_preview` 和 `blocker_preview_sha256`，让只读取整包摘要的维护工具能看到 blockers 列表入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 blocker preview count/list/hash，并继续展示 blocker count 与完整 hash。
- 新增 `docs/releases/v0.16.189-draft.md`，把下一版 patch release 聚焦到 blocker preview 可见性。

## [0.16.188] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_visibility_key_tail_count`、`publication_visibility_key_tail` 和 `publication_visibility_key_tail_sha256`，让只读取整包摘要的维护工具能看到发布可见性对象末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication visibility key tail count/list/hash，并继续展示 preview、first/last key、boundary hash、key count、visibility hash 与 summary hash。
- 新增 `docs/releases/v0.16.188-draft.md`，把下一版 patch release 聚焦到 publication visibility key tail 可见性。

## [0.16.187] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_visibility_key_preview_count`、`publication_visibility_key_preview` 和 `publication_visibility_key_preview_sha256`，让只读取整包摘要的维护工具能看到发布可见性对象字段入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication visibility key preview count/list/hash，并继续展示 first/last key、boundary hash、key count、visibility hash 与 summary hash。
- 新增 `docs/releases/v0.16.187-draft.md`，把下一版 patch release 聚焦到 publication visibility key preview 可见性。

## [0.16.186] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_visibility_first_key`、`publication_visibility_last_key` 和 `publication_visibility_key_boundary_sha256`，让只读取整包摘要的维护工具能检查发布可见性对象首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication visibility first/last key 与 boundary hash，并继续展示 key count、visibility hash 与 summary hash。
- 新增 `docs/releases/v0.16.186-draft.md`，把下一版 patch release 聚焦到 publication visibility key boundary 可见性。

## [0.16.185] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_files_first_key`、`artifact_files_last_key` 和 `artifact_files_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue artifacts 文件映射首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact files first/last key 与 boundary hash，并继续展示 artifact files key preview、tail、key count 与完整 hash。
- 新增 `docs/releases/v0.16.185-draft.md`，把下一版 patch release 聚焦到 artifact files key boundary 可见性。

## [0.16.184] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_files_key_tail_count`、`artifact_files_key_tail` 和 `artifact_files_key_tail_sha256`，让只读取整包摘要的维护工具能看到 candidate issue artifacts 文件映射末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact files key tail count/list/hash，并继续展示 artifact files key preview、key count 与完整 hash。
- 新增 `docs/releases/v0.16.184-draft.md`，把下一版 patch release 聚焦到 artifact files key tail 可见性。

## [0.16.183] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_files_key_preview_count`、`artifact_files_key_preview` 和 `artifact_files_key_preview_sha256`，让只读取整包摘要的维护工具能看到 candidate issue artifacts 文件映射入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact files key preview count/list/hash，并继续展示 artifact files key count 与完整 hash。
- 新增 `docs/releases/v0.16.183-draft.md`，把下一版 patch release 聚焦到 artifact files key preview 可见性。

## [0.16.182] - 2026-06-13

### Added
- `issue_metadata_summary` 现在输出 `metadata_first_item`、`metadata_last_item` 和 `metadata_boundary_sha256`，让候选 issue metadata 的首尾边界可被机器审阅。
- `artifact_bundle_summary` 现在输出 `issue_metadata_first_item`、`issue_metadata_last_item` 和 `issue_metadata_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue metadata 首尾边界。
- 新增 `docs/releases/v0.16.182-draft.md`，把下一版 patch release 聚焦到 issue metadata boundary 可见性。

## [0.16.181] - 2026-06-13

### Added
- `issue_metadata_summary` 现在输出 `metadata_tail_count`、`metadata_tail` 和 `metadata_tail_sha256`，让候选 issue metadata 的稳定末尾入口可被机器审阅。
- `artifact_bundle_summary` 现在输出 `issue_metadata_tail_count`、`issue_metadata_tail` 和 `issue_metadata_tail_sha256`，让只读取整包摘要的维护工具能检查 candidate issue metadata 末尾入口。
- 新增 `docs/releases/v0.16.181-draft.md`，把下一版 patch release 聚焦到 issue metadata tail 可见性。

## [0.16.180] - 2026-06-13

### Added
- `issue_metadata_summary` 现在输出 `metadata_preview_count`、`metadata_preview` 和 `metadata_preview_sha256`，让候选 issue metadata 的稳定入口可被机器审阅。
- `artifact_bundle_summary` 现在输出 `issue_metadata_preview_count`、`issue_metadata_preview` 和 `issue_metadata_preview_sha256`，让只读取整包摘要的维护工具能检查 candidate issue metadata 入口。
- 新增 `docs/releases/v0.16.180-draft.md`，把下一版 patch release 聚焦到 issue metadata preview 可见性。

## [0.16.179] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_order_first_item`、`review_order_last_item` 和 `review_order_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue artifacts 审阅顺序首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 review order first/last item 与 boundary hash，并继续展示 review order preview、tail 和完整 hash。
- 新增 `docs/releases/v0.16.179-draft.md`，把下一版 patch release 聚焦到 review order boundary 可见性。

## [0.16.178] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_order_tail_count`、`review_order_tail` 和 `review_order_tail_sha256`，让只读取整包摘要的维护工具能检查 candidate issue artifacts 审阅顺序末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 review order tail count/list/hash，并继续展示 review order preview 与完整 hash。
- 新增 `docs/releases/v0.16.178-draft.md`，把下一版 patch release 聚焦到 review order tail 可见性。

## [0.16.177] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_order_preview_count`、`review_order_preview` 和 `review_order_preview_sha256`，让只读取整包摘要的维护工具能看到 candidate issue artifacts 审阅顺序入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 review order preview count/list/hash，并继续展示 review order hash。
- 新增 `docs/releases/v0.16.177-draft.md`，把下一版 patch release 聚焦到 review order preview 可见性。

## [0.16.176] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_summary_key_tail_count`、`issue_body_summary_key_tail` 和 `issue_body_summary_key_tail_sha256`，让只读取整包摘要的维护工具能检查 issue body summary 字段集合末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body summary key tail count/list/hash，并继续展示 key preview 与完整 summary hash。
- 新增 `docs/releases/v0.16.176-draft.md`，把下一版 patch release 聚焦到 issue body summary key tail 可见性。

## [0.16.175] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_summary_key_preview_count`、`issue_body_summary_key_preview` 和 `issue_body_summary_key_preview_sha256`，让只读取整包摘要的维护工具能看到 issue body summary 字段集合入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body summary key preview count/list/hash，并继续展示 key boundary 与完整 summary hash。
- 新增 `docs/releases/v0.16.175-draft.md`，把下一版 patch release 聚焦到 issue body summary key preview 可见性。

## [0.16.174] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_summary_first_key`、`issue_body_summary_last_key` 和 `issue_body_summary_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 issue body summary 字段集合首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body summary first/last key 和 boundary hash，并继续展示 issue body summary key count/hash。
- 新增 `docs/releases/v0.16.174-draft.md`，把下一版 patch release 聚焦到 issue body summary key boundary 可见性。

## [0.16.173] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_summary_key_count` 和 `issue_body_summary_keys_sha256`，让只读取整包摘要的维护工具能检查 issue body summary 字段集合。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body summary key count/hash，并继续展示 issue body summary hash。
- 新增 `docs/releases/v0.16.173-draft.md`，把下一版 patch release 聚焦到 issue body summary schema 可见性。

## [0.16.172] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_inventory_first_entry`、`issue_body_inventory_last_entry` 和 `issue_body_inventory_boundary_sha256`，让只读取整包摘要的维护工具能检查 issue body inventory 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body inventory first/last entry 和 boundary hash，并继续展示 preview/tail 与完整 inventory hash。
- 新增 `docs/releases/v0.16.172-draft.md`，把下一版 patch release 聚焦到 issue body inventory 首尾边界可见性。

## [0.16.171] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_inventory_tail_count`、`issue_body_inventory_tail` 和 `issue_body_inventory_tail_sha256`，让只读取整包摘要的维护工具能检查 issue body inventory 末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body inventory tail count/list/hash，并继续展示 preview 与完整 inventory hash。
- 新增 `docs/releases/v0.16.171-draft.md`，把下一版 patch release 聚焦到 issue body inventory 末尾预览可见性。

## [0.16.170] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_inventory_preview_count`、`issue_body_inventory_preview` 和 `issue_body_inventory_preview_sha256`，让只读取整包摘要的维护工具能看到 issue body inventory 入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body inventory preview count/list/hash，并继续展示完整 inventory hash。
- 新增 `docs/releases/v0.16.170-draft.md`，把下一版 patch release 聚焦到 issue body inventory 预览可见性。

## [0.16.169] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_cases_first_case`、`candidate_cases_last_case` 和 `candidate_cases_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate case 列表首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate cases first/last case 和 boundary hash，并继续展示 candidate cases preview/tail。
- 新增 `docs/releases/v0.16.169-draft.md`，把下一版 patch release 聚焦到 candidate case 列表边界可见性。

## [0.16.168] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_cases_tail_count`、`candidate_cases_tail` 和 `candidate_cases_tail_sha256`，让只读取整包摘要的维护工具能检查 candidate case 列表尾部入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate cases tail count/list/hash，并继续展示 candidate cases preview。
- 新增 `docs/releases/v0.16.168-draft.md`，把下一版 patch release 聚焦到 candidate case 列表尾部预览可见性。

## [0.16.167] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_cases_preview_count`、`candidate_cases_preview` 和 `candidate_cases_preview_sha256`，让只读取整包摘要的维护工具能直接看到 candidate case 列表入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate cases preview count/list/hash，并继续展示完整 candidate cases hash。
- 新增 `docs/releases/v0.16.167-draft.md`，把下一版 patch release 聚焦到 candidate case 列表预览可见性。

## [0.16.166] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_payload_first_key`、`artifact_manifest_payload_last_key` 和 `artifact_manifest_payload_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` payload 字段首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest payload first/last key 和 boundary hash，并继续展示 payload key preview/tail。
- 新增 `docs/releases/v0.16.166-draft.md`，把下一版 patch release 聚焦到 artifact manifest payload 字段边界可见性。

## [0.16.165] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_payload_key_tail_count`、`artifact_manifest_payload_key_tail` 和 `artifact_manifest_payload_key_tail_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` payload 字段后缀。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest payload key tail count/list/hash，并继续展示 payload key preview。
- 新增 `docs/releases/v0.16.165-draft.md`，把下一版 patch release 聚焦到 artifact manifest payload 字段尾部预览可见性。

## [0.16.164] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_payload_key_preview_count`、`artifact_manifest_payload_key_preview` 和 `artifact_manifest_payload_key_preview_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` payload 字段前缀。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest payload key preview count/list/hash，并继续展示 payload hash。
- 新增 `docs/releases/v0.16.164-draft.md`，把下一版 patch release 聚焦到 artifact manifest payload 字段预览可见性。

## [0.16.163] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_key_tail_count`、`artifact_manifest_key_tail` 和 `artifact_manifest_key_tail_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` 顶层字段后缀。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest key tail count/list/hash，并继续展示 manifest key preview。
- 新增 `docs/releases/v0.16.163-draft.md`，把下一版 patch release 聚焦到 artifact manifest 顶层字段尾部预览可见性。

## [0.16.162] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_key_preview_count`、`artifact_manifest_key_preview` 和 `artifact_manifest_key_preview_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` 顶层字段前缀。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest key preview count/list/hash，并继续展示 manifest key boundary。
- 新增 `docs/releases/v0.16.162-draft.md`，把下一版 patch release 聚焦到 artifact manifest 顶层字段预览可见性。

## [0.16.161] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_first_key`、`artifact_manifest_last_key` 和 `artifact_manifest_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` 顶层字段首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest first/last key 和 boundary hash，并继续展示 manifest key count/hash。
- 新增 `docs/releases/v0.16.161-draft.md`，把下一版 patch release 聚焦到 artifact manifest 顶层字段边界可见性。

## [0.16.160] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_bundle_summary_first_key`、`artifact_bundle_summary_last_key` 和 `artifact_bundle_summary_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 summary 首尾字段边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact bundle summary first/last key 和 boundary hash，并继续展示 key preview/tail。
- 新增 `docs/releases/v0.16.160-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 自身字段边界可见性。

## [0.16.159] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_bundle_summary_key_tail_count`、`artifact_bundle_summary_key_tail` 和 `artifact_bundle_summary_key_tail_sha256`，让只读取整包摘要的维护工具能检查 summary 末尾字段。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact bundle summary key tail count/list/hash，并继续展示 key preview。
- 新增 `docs/releases/v0.16.159-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 自身字段尾部预览可见性。

## [0.16.158] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_bundle_summary_key_preview_count`、`artifact_bundle_summary_key_preview` 和 `artifact_bundle_summary_key_preview_sha256`，让只读取整包摘要的维护工具能先检查 summary 前几个关键字段。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact bundle summary key preview count/list/hash，并继续展示完整 key count/hash。
- 新增 `docs/releases/v0.16.158-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 自身字段预览可见性。

## [0.16.157] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_bundle_summary_key_count` 和 `artifact_bundle_summary_keys_sha256`，让只读取整包摘要的维护工具能判断 summary 自身字段规模和字段清单是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact bundle summary key count/hash，并继续展示 manifest payload hash。
- 新增 `docs/releases/v0.16.157-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 自身字段清单摘要可见性。

## [0.16.156] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_payload_key_count` 和 `artifact_manifest_payload_sha256`，让只读取整包摘要的维护工具能判断除 summary 自身之外的 manifest payload 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在复用 manifest 中预先计算的 bundle summary，确保 README 与 `artifact-manifest.json` 的 payload hash 同源。
- 新增 `docs/releases/v0.16.156-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifact manifest payload summary 可见性。

## [0.16.155] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_key_count` 和 `artifact_manifest_keys_sha256`，让只读取整包摘要的维护工具能判断 `artifact-manifest.json` 顶层字段规模和字段清单是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest key count/hash，并继续展示 manifest schema version。
- 新增 `docs/releases/v0.16.155-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifact manifest key summary 可见性。

## [0.16.154] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_schema_version`，让只读取整包摘要的维护工具能先判断 `artifact-manifest.json` 字段语义版本。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `artifact_manifest_schema_version`，并与 manifest 顶层 `schema_version` 保持同源。
- 新增 `docs/releases/v0.16.154-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifact manifest schema version 可见性。

## [0.16.153] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_primary_issue` 和 `release_draft_handoff_primary_required_action`，让只读取整包摘要的维护工具能用 handoff primary alias 展示首要草案问题和处理动作。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft handoff primary alias，并继续展示 schema version、key count 与 hash。
- 新增 `docs/releases/v0.16.153-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft handoff primary alias 可见性。

## [0.16.152] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_schema_version`，让只读取整包摘要的维护工具能先判断 release draft handoff 字段语义版本。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `release_draft_handoff_schema_version`，并继续展示 handoff key count 与 hash。
- 新增 `docs/releases/v0.16.152-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft handoff schema version 可见性。

## [0.16.151] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_handoff_schema_version`，让只读取整包摘要的维护工具能先判断 publication handoff 字段语义版本。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `publication_handoff_schema_version`，并继续展示 handoff key count 与 hash。
- 新增 `docs/releases/v0.16.151-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication handoff schema version 可见性。

## [0.16.150] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `schema_version: 1`，让只读取 publication handoff 的维护工具能先判断字段语义版本。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示 `schema_version`，并让 `publication_handoff_key_count` 与 hash 反映该字段变化。
- 新增 `docs/releases/v0.16.150-draft.md`，把下一版 patch release 聚焦到 publication handoff schema version 可见性。

## [0.16.149] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `primary_issue` 和 `primary_required_action`，让工具能用和 publication handoff 一致的 primary 字段模型读取首要草案问题。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `primary_issue` 和 `primary_required_action`，并在无 release draft issue 时使用 `(none)`。
- 新增 `docs/releases/v0.16.149-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 primary 字段别名可见性。

## [0.16.148] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `primary_next_action`，让只读取 publication handoff 的维护工具也能直接展示第一条发布同步待办。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示 `primary_next_action`，并在无 publication next action 时使用 `(none)`。
- 新增 `docs/releases/v0.16.148-draft.md`，把下一版 patch release 聚焦到 publication handoff 的 primary next action 可见性。

## [0.16.147] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `primary_publish_command`，让只读取 publication handoff 的维护工具也能直接展示第一条发布同步命令。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示 `primary_publish_command`，并在无 publish command 时使用 `(none)`。
- 新增 `docs/releases/v0.16.147-draft.md`，把下一版 patch release 聚焦到 publication handoff 的 primary publish command 可见性。

## [0.16.146] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_primary_publish_command`，让只读取整包摘要的维护工具也能直接展示第一条发布同步命令。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `publication_primary_publish_command`，并在无 publish command 时使用 `(none)`。
- 新增 `docs/releases/v0.16.146-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication primary publish command 可见性。

## [0.16.145] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_primary_next_action`，让只读取整包摘要的维护工具也能直接展示第一条发布同步待办。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `publication_primary_next_action`，并在无 publication next action 时使用 `(none)`。
- 新增 `docs/releases/v0.16.145-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication primary next action 可见性。

## [0.16.144] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_primary_issue`，让只读取整包摘要的维护工具也能直接展示第一条 release draft 阻塞原因。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `release_draft_primary_issue`，并在无阻塞原因时使用 `(none)`。
- 新增 `docs/releases/v0.16.144-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft primary issue 可见性。

## [0.16.143] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_primary_required_action`，让只读取整包摘要的维护工具也能直接展示第一条 release draft 修复动作。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `release_draft_primary_required_action`，并在无动作时使用 `(none)`。
- 新增 `docs/releases/v0.16.143-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft primary required action 可见性。

## [0.16.142] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_required_action_count` 和 `release_draft_required_actions_sha256`，让只读取整包摘要的维护工具也能判断 release draft required actions 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft required actions 的数量和 hash。
- 新增 `docs/releases/v0.16.142-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft required actions 可见性。

## [0.16.141] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_required_action_count`、`release_draft_required_actions_sha256` 和 `release_draft_required_actions`，让只读取 handoff 的维护工具也能直接拿到完整草案处理动作列表。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 release draft required actions 的数量、hash 和列表。
- 新增 `docs/releases/v0.16.141-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的完整 required actions 可见性。

## [0.16.140] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_primary_required_action`，让只读取 handoff 的维护工具也能直接拿到第一条草案处理动作。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_primary_required_action`。
- 新增 `docs/releases/v0.16.140-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 primary required action 可见性。

## [0.16.139] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `schema_version`，让只读取 handoff 的维护工具也能先判断字段语义版本。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `schema_version`。
- 新增 `docs/releases/v0.16.139-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 schema version 可见性。

## [0.16.138] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_primary_issue`，让只读取 handoff 的维护工具也能直接看到第一条草案阻塞原因。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_primary_issue`。
- 新增 `docs/releases/v0.16.138-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 primary issue 可见性。

## [0.16.137] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_issues_sha256`，让只读取 handoff 的维护工具也能检测草案问题列表漂移。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_issues_sha256`。
- 新增 `docs/releases/v0.16.137-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的问题列表摘要可见性。

## [0.16.136] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_path_sha256`，让只读取 handoff 的维护工具也能检测草案路径漂移。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_path_sha256`。
- 新增 `docs/releases/v0.16.136-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的路径摘要可见性。

## [0.16.135] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_ok`，让只读取 handoff 的维护工具也能直接判断草案门禁是否通过。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_ok`。
- 新增 `docs/releases/v0.16.135-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 ok 状态可见性。

## [0.16.134] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_issue_count`，让只读取 handoff 的维护工具也能先判断草案门禁规模。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_issue_count`。
- 新增 `docs/releases/v0.16.134-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 issue 数量可见性。

## [0.16.133] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `publish_command_count`，让只读取 handoff 的维护工具也能先判断发布命令规模。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示 `publish_command_count`。
- 新增 `docs/releases/v0.16.133-draft.md`，把下一版 patch release 聚焦到 publication handoff 的发布命令数量可见性。

## [0.16.132] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `publish_script_path_sha256` 和 `publish_script_command_sha256`，让只读取 handoff 的维护工具也能检测发布脚本路径或命令漂移。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示同一组发布脚本摘要字段。
- 新增 `docs/releases/v0.16.132-draft.md`，把下一版 patch release 聚焦到 publication handoff 的发布脚本摘要可见性。

## [0.16.131] - 2026-06-13

### Added
- `scripts/plan_next_iteration.py` 现在输出 `publication_publish_script_command_sha256`，让计划 JSON、文本输出和 Markdown report 不生成 artifacts 也能检测发布脚本生成命令漂移。
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 和 `artifact-manifest.json` 现在展示 `publication_publish_script_command_sha256`。
- 新增 `docs/releases/v0.16.131-draft.md`，把下一版 patch release 聚焦到 publication publish script command hash 的 plan 级可见性。

## [0.16.130] - 2026-06-13

### Added
- `scripts/plan_next_iteration.py` 现在输出 `publication_publish_script_path_sha256`，让计划 JSON、文本输出和 Markdown report 不生成 artifacts 也能检测发布脚本路径漂移。
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 和 `artifact-manifest.json` 现在展示 `publication_publish_script_path_sha256`。
- 新增 `docs/releases/v0.16.130-draft.md`，把下一版 patch release 聚焦到 publication publish script path hash 的 plan 级可见性。

## [0.16.129] - 2026-06-13

### Added
- `scripts/plan_next_iteration.py` 现在输出 `publication_publish_script_path`，让计划 JSON、文本输出和 Markdown report 直接展示可审阅发布脚本的默认路径。
- Candidate issue artifacts `README.md`、`artifact-manifest.json` 和 `publication-handoff.json` 现在保留发布脚本路径；`artifact_bundle_summary` 新增 `publication_publish_script_path_sha256` 便于检测路径漂移。
- 新增 `docs/releases/v0.16.129-draft.md`，把下一版 patch release 聚焦到 publication publish script path 的结构化可见性。

## [0.16.128] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_publish_script_command`，方便维护者第一屏就能看到生成可审阅发布脚本的命令。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication publish script command。
- 新增 `docs/releases/v0.16.128-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布脚本生成命令可见性。

## [0.16.127] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_publish_command_count`，方便维护者先判断发布命令规模。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication publish command 数量。
- 新增 `docs/releases/v0.16.127-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布命令数量可见性。

## [0.16.126] - 2026-06-12

### Fixed
- `Candidate Issue Gate Quick Summary` 的 inline code helper 现在会用带空格的双反引号包裹包含反引号的 summary，避免 `visibility_summary` 以反引号开头时生成含混的 Markdown。
- `tests/test_plan_next_iteration.py` 覆盖 summary 以反引号开头的格式化边界。
- 新增 `docs/releases/v0.16.126-draft.md`，把下一版 patch release 聚焦到 quick summary inline code fence 稳定性。

## [0.16.125] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `visibility_summary`，方便维护者先读到发布可见性的可读解释。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 visibility summary。
- 新增 `docs/releases/v0.16.125-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的 visibility summary 可见性。

## [0.16.124] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `blocker_count`、`next_action_count` 和 `publication_next_action_count`，方便维护者先判断本轮待办规模。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 blocker/next action 数量。
- 新增 `docs/releases/v0.16.124-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的待办规模可见性。

## [0.16.123] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_ok` 和 `release_draft_ok`，方便维护者先区分发布阻塞和草案阻塞。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication/release draft ok。
- 新增 `docs/releases/v0.16.123-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的 ok 布尔值可见性。

## [0.16.122] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_upstream_head`、`publication_tag_points_at_head`、`publication_tag_commit_in_upstream`、`publication_branch_published`、`publication_tag_published`、`publication_remote_branch_head` 和 `publication_remote_tag_commit`。
- `tests/test_plan_next_iteration.py` 覆盖 quick summary 的 upstream HEAD、tag state、published state 和 remote refs。
- 新增 `docs/releases/v0.16.122-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布状态字段落地。

## [0.16.121] - 2026-06-12

### Added
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 现在明确说明 `Candidate Issue Gate Quick Summary` 会展示 publication upstream HEAD、tag state、published state 和 remote refs。
- `tests/test_weekly_maintainer_loop_docs.py` 固定 quick summary 文档契约，避免维护者循环说明遗漏现有发布状态字段。
- 新增 `docs/releases/v0.16.121-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的文档契约完整性。

## [0.16.120] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_tag_commit`，方便维护者先核对最新 tag 指向的提交。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication local HEAD/tag commit。
- 新增 `docs/releases/v0.16.120-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的 tag commit 可见性。

## [0.16.119] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_local_head`，方便维护者先核对本地发布提交。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication local HEAD。
- 新增 `docs/releases/v0.16.119-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的本地 HEAD 可见性。

## [0.16.118] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_remote`，方便维护者先确认发布命令对应的远端名称。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication branch/upstream/remote。
- 新增 `docs/releases/v0.16.118-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的远端名称可见性。

## [0.16.117] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_upstream`，方便维护者先确认本地分支对应的上游引用。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication branch/upstream。
- 新增 `docs/releases/v0.16.117-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的上游引用可见性。

## [0.16.116] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_branch`，方便维护者先确认待发布分支。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication branch。
- 新增 `docs/releases/v0.16.116-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布分支可见性。

## [0.16.115] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_worktree_clean`，方便维护者先判断是否需要清理本地改动再发布。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication worktree clean。
- 新增 `docs/releases/v0.16.115-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的工作区清洁状态可见性。

## [0.16.114] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_behind_count`，方便维护者先判断本地分支是否落后远端。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication ahead/behind 数。
- 新增 `docs/releases/v0.16.114-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的 behind 同步风险可见性。

## [0.16.113] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_remote_checked`，方便维护者先判断发布可见性结论是否做过远端复核。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication remote checked。
- 新增 `docs/releases/v0.16.113-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的远端复核状态可见性。

## [0.16.112] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `release_draft_path`，方便维护者直接定位需要审阅的草案文件。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 release draft path。
- 新增 `docs/releases/v0.16.112-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的草案路径可见性。

## [0.16.111] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_ahead_count` 和 `release_draft_issue_count`，方便维护者先判断本地 release 发布规模和草案剩余问题数量。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication ahead 数和 release draft issue 数。
- 新增 `docs/releases/v0.16.111-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布/草案规模可见性。

## [0.16.110] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `reason_code_count` 和 `required_action_count`，方便维护者先判断 gate 是否还有更多细节需要展开。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 reason/action 数量。
- 新增 `docs/releases/v0.16.110-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 数量可见性。

## [0.16.109] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 现在会在 `Artifact Bundle Summary` 前展示 `Candidate Issue Gate Quick Summary`，让维护者先看到 gate status、首要 reason/action、latest tag 和 visibility。
- README quick summary 会复用已有 primary reason code、reason description 和 required action，让人工审阅不必先展开完整 artifact bundle summary。
- 新增 `docs/releases/v0.16.109-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 可读性。

## [0.16.108] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_primary_reason_description`，方便工具只读整包摘要就展示首要 gate reason 的可读说明。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 会展示 gate primary reason description，并保持 primary reason code/action 字段不变。
- 新增 `docs/releases/v0.16.108-draft.md`，把下一版 patch release 聚焦到 candidate issue gate primary reason description 可见性。

## [0.16.107] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_primary_reason_code` 和 `candidate_issue_gate_primary_required_action`，方便工具只读整包摘要就展示首要 gate 阻塞原因和首个维护动作。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 会展示 gate primary reason/action，并对包含反引号的动作文本使用更宽的 Markdown code span。
- 新增 `docs/releases/v0.16.107-draft.md`，把下一版 patch release 聚焦到 candidate issue gate primary summary 可见性。

## [0.16.106] - 2026-06-12

### Added
- `publication_ref_context` 现在包含 `remote_branch_head` 和 `remote_tag_commit`，方便候选 issue artifacts 保留远端 ref 实际指向。
- `artifact_bundle_summary` 现在包含 `publication_remote_branch_head` 和 `publication_remote_tag_commit`，方便工具只读整包摘要就判断 remote check 看到的远端分支和 tag commit。
- 新增 `docs/releases/v0.16.106-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication remote ref 可见性。

## [0.16.105] - 2026-06-12

### Added
- `publication_ref_context` 现在包含 `branch_published` 和 `tag_published`，方便候选 issue artifacts 保留分支/tag 是否公开可见的判断。
- `artifact_bundle_summary` 现在包含 `publication_branch_published` 和 `publication_tag_published`，方便工具只读整包摘要就判断发布 refs 是否公开。
- 新增 `docs/releases/v0.16.105-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication published state 可见性。

## [0.16.104] - 2026-06-12

### Added
- `publication_ref_context` 现在包含 `tag_points_at_head` 和 `tag_commit_in_upstream`，方便候选 issue artifacts 保留 tag 状态判断。
- `artifact_bundle_summary` 现在包含 `publication_tag_points_at_head` 和 `publication_tag_commit_in_upstream`，方便工具只读整包摘要就判断最新本地 tag 是否指向 HEAD 以及 tag commit 是否在上游。
- 新增 `docs/releases/v0.16.104-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication tag state 可见性。

## [0.16.103] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_local_head` 和 `publication_upstream_head`，方便工具只读候选 issue artifacts 整包摘要就定位本地 HEAD 与上游 HEAD。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication local/upstream HEAD。
- 新增 `docs/releases/v0.16.103-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication head 可见性。

## [0.16.102] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_latest_tag` 和 `publication_tag_commit`，方便工具只读候选 issue artifacts 整包摘要就定位最新本地 tag 及其提交。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication latest tag/tag commit。
- 新增 `docs/releases/v0.16.102-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication tag 可见性。

## [0.16.101] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_branch`、`publication_upstream` 和 `publication_remote`，方便工具只读候选 issue artifacts 整包摘要就定位发布分支、上游和远端。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication branch/upstream/remote。
- 新增 `docs/releases/v0.16.101-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication ref names 可见性。

## [0.16.100] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_behind_count`，方便工具只读候选 issue artifacts 整包摘要就判断本地分支是否落后远端。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication behind count。
- 新增 `docs/releases/v0.16.100-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication behind 可见性。

## [0.16.99] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_remote_checked` 和 `publication_ahead_count`，方便工具只读候选 issue artifacts 整包摘要就判断 publication audit 是否做过远端复核及本地领先规模。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication remote checked 与 ahead count。
- 新增 `docs/releases/v0.16.99-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication remote 可见性。

## [0.16.98] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `release_draft_ok`，方便工具只读候选 issue artifacts 整包摘要就判断 release draft gate 是否通过。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 release draft ok 布尔值。
- 新增 `docs/releases/v0.16.98-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft gate 可见性。

## [0.16.97] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `release_draft_path` 和 `release_draft_path_sha256`，方便工具只读候选 issue artifacts 整包摘要就判断目标 release draft 路径是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 release draft path 与 path hash。
- 新增 `docs/releases/v0.16.97-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft path 可见性。

## [0.16.96] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `release_draft_issues_sha256`，方便工具只读候选 issue artifacts 整包摘要就判断 release draft issues 列表是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 release draft issues hash。
- 新增 `docs/releases/v0.16.96-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft issues 可见性。

## [0.16.95] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_visibility_key_count`，方便工具只读候选 issue artifacts 整包摘要就判断 publication visibility 结构规模。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication visibility key count。
- 新增 `docs/releases/v0.16.95-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication visibility 结构可见性。

## [0.16.94] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_ref_context_key_count`，方便工具只读候选 issue artifacts 整包摘要就判断 publication ref context 结构规模。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication ref context key count。
- 新增 `docs/releases/v0.16.94-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication ref context 结构可见性。

## [0.16.93] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_publish_command_count`，方便工具只读候选 issue artifacts 整包摘要就判断发布命令数量。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication publish command count。
- 新增 `docs/releases/v0.16.93-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的发布命令数量可见性。

## [0.16.92] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 JSON、默认文本输出和 Markdown report 现在包含 `publication_next_action_count` 与 `publication_publish_command_count`，方便维护者在周初计划里先判断发布待办规模。
- 新增 `docs/releases/v0.16.92-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的发布待办数量可见性。

## [0.16.91] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 的 JSON、默认文本输出和 Markdown report 现在包含 `next_action_count` 与 `publish_command_count`，方便维护者先判断发布待办规模再展开具体列表。
- 新增 `docs/releases/v0.16.91-draft.md`，把下一版 patch release 聚焦到 publication audit 的待办数量可见性。

## [0.16.90] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_publish_script_command_sha256`，方便工具只读整包摘要就检测发布脚本生成命令是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication publish script command hash。
- 新增 `docs/releases/v0.16.90-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的发布脚本生成入口漂移检测。

## [0.16.89] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_visibility_sha256` 和 `publication_visibility_summary_sha256`，方便工具只读整包摘要就检测发布可见性对象或 summary 文本是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication visibility hash 和 summary hash。
- 新增 `docs/releases/v0.16.89-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的发布可见性漂移检测。

## [0.16.88] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `issue_artifacts_command_sha256`，方便工具只读整包摘要就检测 candidate issue artifacts 复现命令是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 issue artifacts command hash。
- 新增 `docs/releases/v0.16.88-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifacts 复现命令漂移检测。

## [0.16.87] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `artifact_files_key_count` 和 `artifact_files_sha256`，方便工具只读整包摘要就检测 candidate issue artifacts 文件映射是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 artifact files key count 和 hash。
- 新增 `docs/releases/v0.16.87-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifacts 文件映射漂移检测。

## [0.16.86] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_key_count` 和 `candidate_issue_gate_sha256`，方便工具只读整包摘要就检测整个 candidate issue gate 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate issue gate key count 和 hash。
- 新增 `docs/releases/v0.16.86-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 candidate issue gate 整体漂移检测。

## [0.16.85] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `requires_maintainer_review`，方便工具只读整包摘要就判断候选 issue gate 是否仍需人工审阅。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 maintainer review flag。
- 新增 `docs/releases/v0.16.85-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的人工审阅标记。

## [0.16.84] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_summary_sha256`，方便工具只读整包摘要就检测 gate summary 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate issue gate summary hash。
- 新增 `docs/releases/v0.16.84-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 gate summary 漂移检测。

## [0.16.83] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_reason_description_count` 和 `candidate_issue_gate_reason_descriptions_sha256`，方便工具只读整包摘要就检测 gate reason descriptions 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate issue gate reason descriptions count 和 hash。
- 新增 `docs/releases/v0.16.83-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 gate reason descriptions 漂移检测。

## [0.16.82] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_evidence_key_count` 和 `candidate_issue_gate_evidence_sha256`，方便工具只读整包摘要就检测 gate evidence 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate issue gate evidence key count 和 hash。
- 新增 `docs/releases/v0.16.82-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 gate evidence 漂移检测。

## [0.16.81] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_handoff_key_count` 和 `publication_handoff_sha256`，方便工具只读整包摘要就检测 publication handoff 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication handoff key count 和 hash。
- 新增 `docs/releases/v0.16.81-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication handoff 漂移检测。

## [0.16.80] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `release_draft_handoff_key_count` 和 `release_draft_handoff_sha256`，方便工具只读整包摘要就检测 release draft handoff 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 release draft handoff key count 和 hash。
- 新增 `docs/releases/v0.16.80-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft handoff 漂移检测。

## [0.16.79] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `issue_body_summary_sha256`，方便工具只读整包摘要就检测 issue body summary 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 issue body summary hash。
- 新增 `docs/releases/v0.16.79-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 issue body summary 漂移检测。

## [0.16.78] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_cases_sha256`，方便工具只读整包摘要就检测候选 case 列表是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate cases hash。
- 新增 `docs/releases/v0.16.78-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 candidate cases 漂移检测。

## [0.16.77] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `issue_metadata_count` 和 `issue_metadata_sha256`，方便工具只读整包摘要就检测候选 issue metadata 是否漂移。
- `artifact-manifest.json` 新增 `issue_metadata_summary`，记录稳定 issue metadata 字段的数量和 SHA-256。
- 新增 `docs/releases/v0.16.77-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 issue metadata 漂移检测。

## [0.16.76] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `create_issues_safety_contract_key_count` 和 `create_issues_safety_contract_sha256`，方便工具只读整包摘要就检测候选 issue 创建安全契约是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 create issues safety contract 摘要字段。
- 新增 `docs/releases/v0.16.76-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 create issues safety contract 漂移检测。

## [0.16.75] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `review_checklist_count` 和 `review_checklist_sha256`，方便工具只读整包摘要就检测候选 issue 审阅清单是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 review checklist 摘要字段。
- 新增 `docs/releases/v0.16.75-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 review checklist 漂移检测。

## [0.16.74] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `validation_command_count` 和 `validation_commands_sha256`，方便工具只读整包摘要就检测验证命令集合是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 validation commands 摘要字段。
- 新增 `docs/releases/v0.16.74-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 validation commands 漂移检测。

## [0.16.73] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_worktree_status_count` 和 `publication_worktree_status_sha256`，方便工具只读整包摘要就检测发布前工作树证据是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 publication worktree status 摘要字段。
- 新增 `docs/releases/v0.16.73-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 worktree status 漂移检测。

## [0.16.72] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_ref_context_sha256` 和 `publication_publish_commands_sha256`，方便工具只读整包摘要就检测发布可见性证据是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 publication ref context / publish commands hash 字段。
- 新增 `docs/releases/v0.16.72-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的发布可见性漂移检测。

## [0.16.71] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `blockers_sha256`、`next_actions_sha256` 和 `publication_next_actions_sha256`，方便工具只读整包摘要就检测 blockers/action lists 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 blocker/action hash 字段。
- 新增 `docs/releases/v0.16.71-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的待办内容漂移检测。

## [0.16.70] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `blocker_count`、`next_action_count` 和 `publication_next_action_count`，方便工具只读整包摘要就判断本轮待办规模。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 blocker/action 计数字段。
- 新增 `docs/releases/v0.16.70-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的待办规模预筛。

## [0.16.69] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_ok`、`publication_visibility_status` 和 `release_draft_issue_count`，方便工具只读整包摘要就区分 publication/release draft 阻塞来源。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 publication/release draft 预筛字段。
- 新增 `docs/releases/v0.16.69-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的阻塞来源预筛。

## [0.16.68] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 candidate issue gate reason/action 的 count/hash，方便工具只读整包摘要就判断 gate 是否需要展开。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 gate reason/action 摘要字段。
- 新增 `docs/releases/v0.16.68-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 gate 摘要。

## [0.16.67] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `reason_code_count` 和 `reason_codes_sha256`，方便工具快速检测 gate reason set 是否变化。
- Next iteration Markdown report 与 candidate issue artifacts `README.md` 现在展示 reason code count/hash。
- 新增 `docs/releases/v0.16.67-draft.md`，把下一版 patch release 聚焦到 candidate issue gate reason codes 摘要。

## [0.16.66] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `required_action_count` 和 `required_actions_sha256`，方便工具快速检测 gate action set 是否变化。
- Next iteration Markdown report 与 candidate issue artifacts `README.md` 现在展示 required actions count/hash。
- 新增 `docs/releases/v0.16.66-draft.md`，把下一版 patch release 聚焦到 candidate issue gate required actions 摘要。

## [0.16.65] - 2026-06-12

### Changed
- `candidate_issue_gate.required_actions` 现在会在 publication 阻塞之外追加 release draft 修复动作，避免 `release_draft_issues` 只有原因码、没有可执行待办。
- Release draft 修复动作统一使用 `Resolve release draft issue: ...` 文案，方便维护者和自动化从 gate payload 直接执行下一步。
- 新增 `docs/releases/v0.16.65-draft.md`，把下一版 patch release 聚焦到 candidate issue gate required actions 的完整性。

## [0.16.64] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `review_order_sha256`，让工具能快速检测 candidate issue artifacts 审阅顺序是否变化。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 review order hash。
- 新增 `docs/releases/v0.16.64-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 审阅顺序摘要。

## [0.16.63] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `artifact_bundle_summary`，汇总 candidate/body/review item 数量、inventory hash、gate 状态和创建脚本安全布尔值。
- Candidate issue artifacts `README.md` 现在展示 `Artifact Bundle Summary` 小节，方便维护者先快速审阅整包状态。
- 新增 `docs/releases/v0.16.63-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 整包摘要。

## [0.16.62] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `issue_body_summary`，记录 candidate issue body 总数、总字节数和 inventory SHA-256。
- Candidate issue artifacts `README.md` 现在展示 `Issue Body Summary` 小节，方便维护者快速判断整批 body 文件是否变化。
- 新增 `docs/releases/v0.16.62-draft.md`，把下一版 patch release 聚焦到 candidate issue body 汇总的机器可读审计。

## [0.16.61] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `issue_body_inventory`，记录每个 candidate issue body 的文件名、字节数和 SHA-256。
- Candidate issue artifacts `README.md` 现在展示 `Issue Body Inventory` 表，方便维护者核对 body 文件完整性。
- 新增 `docs/releases/v0.16.61-draft.md`，把下一版 patch release 聚焦到 candidate issue body 清单的机器可读审计。

## [0.16.60] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `create_issues_safety`，结构化说明候选 issue 创建脚本的 dry-run 和 publication preflight 行为。
- Candidate issue artifacts `README.md` 现在展示 `Create Issues Safety` 小节，让维护者直接看到 dry-run、preflight command 和 preflight JSON 路径。
- 新增 `docs/releases/v0.16.60-draft.md`，把下一版 patch release 聚焦到 candidate issue 创建脚本安全语义的机器可读交接。

## [0.16.59] - 2026-06-12

### Added
- 生成的 candidate issue `create-issues.sh` 现在支持 `CLIANY_CREATE_ISSUES_DRY_RUN=1` 预览模式，只打印 `gh issue create` 命令，不运行 preflight 或创建 issue。
- `artifact-manifest.json` 现在包含 `create_issues_dry_run_command`，方便工具和维护者展示安全预览入口。
- 新增 `docs/releases/v0.16.59-draft.md`，把下一版 patch release 聚焦到 candidate issue 创建脚本的 dry-run 预览能力。

## [0.16.58] - 2026-06-12

### Changed
- Candidate issue artifacts `README.md` 的 `Validation Commands` 现在复用 `artifact-manifest.json.validation_commands` 的完整命令列表。
- Artifacts README 现在直接展示 release readiness 与 publication audit 复核命令，减少维护者只照 README 操作时漏跑门禁的风险。
- 新增 `docs/releases/v0.16.58-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 与 manifest 的验证命令对齐。

## [0.16.57] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `reason_descriptions`，为 `reason_codes` 提供同源可读说明。
- Next iteration Markdown report 和 candidate issue artifacts README 现在展示 gate reason descriptions，方便维护者无需查文档也能理解原因码。
- 新增 `docs/releases/v0.16.57-draft.md`，把下一版 patch release 聚焦到 candidate issue gate reason code descriptions。

## [0.16.56] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `reason_codes`，用 `publication_not_published`、`local_release_only`、`release_draft_issues` 等稳定原因码解释 gate 结论。
- Next iteration Markdown report 和 candidate issue artifacts README 现在展示 gate reason codes，方便维护者和自动化无需解析 summary。
- 新增 `docs/releases/v0.16.56-draft.md`，把下一版 patch release 聚焦到 candidate issue gate 的机器可读原因码。

## [0.16.55] - 2026-06-12

### Added
- `candidate_issue_gate.evidence` 现在包含 `publication_worktree_clean` 和 `release_draft_ok`，让维护者和自动化能直接审计 worktree 与 release draft 门禁状态。
- Next iteration Markdown report 和 candidate issue artifacts README 现在展示这两个布尔 gate evidence 字段。
- 新增 `docs/releases/v0.16.55-draft.md`，把下一版 patch release 聚焦到 candidate issue gate 的布尔判定证据。

## [0.16.54] - 2026-06-12

### Changed
- `candidate_issue_gate.evidence.release_draft_path` 现在使用 `docs/releases/v<version>-draft.md` 形式的仓库相对路径，避免 candidate issue artifacts 泄漏维护者本机绝对路径。
- 新增 `docs/releases/v0.16.54-draft.md`，把下一版 patch release 聚焦到 candidate issue gate evidence 的相对路径交接。

## [0.16.53] - 2026-06-12

### Added
- `plan_next_iteration.py` 的默认文本输出现在会把 `candidate_issue_gate.evidence` 展开为缩进列表，方便维护者在终端直接审阅 gate 判定依据。
- 新增 `docs/releases/v0.16.53-draft.md`，把下一版 patch release 聚焦到 candidate issue gate evidence 的文本输出可读性。

## [0.16.52] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `evidence`，记录 publication visibility、latest tag、ahead count 和 release draft issue count 等判定输入。
- Next iteration Markdown report 和 candidate issue artifacts README 现在展示 candidate issue gate evidence，方便维护者审计为什么候选 issue 创建被阻塞或需要人工审阅。
- 新增 `docs/releases/v0.16.52-draft.md`，把下一版 patch release 聚焦到 candidate issue gate 的机器可读判定证据。

## [0.16.51] - 2026-06-12

### Added
- `plan_next_iteration.py` 现在输出 `candidate_issue_gate`，用 `blocked_by_publication`、`review_required` 和 `ready` 区分候选 issue 创建前的硬性发布门控与人工审阅门控。
- Candidate issue artifacts 的 `artifact-manifest.json`、`publication-handoff.json` 和 `README.md` 现在同步展示 `candidate_issue_gate`、`can_create_issues` 和 required actions。
- 新增 `docs/releases/v0.16.51-draft.md`，把下一版 patch release 聚焦到 candidate issue 创建门控的机器可读交接。

## [0.16.50] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `review_checklist`，让候选任务产物包的放行审阅步骤也能被工具读取。
- 新增 `docs/releases/v0.16.50-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的机器可读审阅清单。

## [0.16.49] - 2026-06-12

### Added
- `artifact-manifest.json` 的 `validation_commands` 现在包含 `python scripts/release_readiness.py --target-version <version> --json`，让候选任务产物包直接给出 release gate 复核命令。
- 新增 `docs/releases/v0.16.49-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 release readiness 验证命令。

## [0.16.48] - 2026-06-12

### Added
- `artifact-manifest.json` 的 `validation_commands` 现在包含 `python scripts/check_release_publication.py --json`，让候选任务产物包直接给出发布可见性复核命令。
- 新增 `docs/releases/v0.16.48-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 publication audit 验证命令。

## [0.16.47] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `schema_version: 1`，让维护脚本能先识别 candidate issue artifacts manifest 的字段语义。
- 新增 `docs/releases/v0.16.47-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 schema version。

## [0.16.46] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `issue_artifacts_command`，让候选任务产物包的机器可读入口也能直接展示重新生成同一批 artifacts 的命令。
- 新增 `docs/releases/v0.16.46-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的复现命令。

## [0.16.45] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `release_draft_path` 和 `release_draft_issues`，让候选任务产物包的机器可读入口也能直接展示下一版 release draft handoff。
- 新增 `docs/releases/v0.16.45-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 release draft handoff 摘要。

## [0.16.44] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `publication_ref_context`、`publication_worktree_clean`、`publication_worktree_status` 和 `publication_publish_script_command`，让候选任务产物包的机器可读入口也能直接展示发布 refs、worktree 和发布脚本生成命令。
- 新增 `docs/releases/v0.16.44-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 publication context 摘要。

## [0.16.43] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `publication_ok`、`publication_visibility`、`publication_next_actions` 和 `publication_publish_commands`，让候选任务产物包的机器可读入口也能直接展示发布可见性与推送命令。
- 新增 `docs/releases/v0.16.43-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 publication 摘要。

## [0.16.42] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `blockers` 和 `next_actions`，让候选任务产物包有单文件可读的交接摘要。
- 新增 `docs/releases/v0.16.42-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 blocker/next action 摘要。

## [0.16.41] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `candidate_count` 和 `candidate_cases`，让维护者和工具无需读取 issue metadata 也能快速识别本批 candidate artifacts 覆盖范围。
- 新增 `docs/releases/v0.16.41-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的候选案例摘要。

## [0.16.40] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 现在会写出 `artifact-manifest.json`，列出 candidate issue artifacts 的文件名、review order 和 validation commands。
- 新增 `docs/releases/v0.16.40-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的结构化 manifest。

## [0.16.39] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 现在会写出 `release-draft-handoff.json`，把 target version、release draft path 和 release draft issues 作为结构化 artifact 交给维护者和工具读取。
- 新增 `docs/releases/v0.16.39-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的结构化 release draft handoff。

## [0.16.38] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会展示 `Release Draft Handoff`，包含下一版草案路径和 release draft issues。
- 新增 `docs/releases/v0.16.38-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 release draft handoff。

## [0.16.37] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会在 `Publication Handoff` 中展示 `visibility_summary`，维护者不用打开 `publication-handoff.json` 也能看到发布可见性原因。
- 新增 `docs/releases/v0.16.37-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 publication visibility summary。

## [0.16.36] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在会输出 `publication_visibility`，并在 Markdown plan、`publication-handoff.json` 和 candidate artifacts `README.md` 中展示发布可见性状态与 summary。
- 新增 `docs/releases/v0.16.36-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publication visibility 结论字段。

## [0.16.35] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在会输出 `publication_ref_context`，并在 Markdown plan、`publication-handoff.json` 和 artifacts `README.md` 中展示 publication latest tag、local HEAD 和 tag commit 等上下文。
- 新增 `docs/releases/v0.16.35-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publication ref context 交接。

## [0.16.34] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在会输出 `publication_worktree_clean` / `publication_worktree_status`，并在 Markdown plan、`publication-handoff.json` 和 artifacts `README.md` 中展示 publication worktree 状态。
- 新增 `docs/releases/v0.16.34-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publication worktree 状态交接。

## [0.16.33] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 的 JSON、文本和 Markdown report 现在会展示 `worktree_clean` / `worktree_status`，dirty worktree 时优先提示清理本地改动并收敛 `publish_commands`。
- 新增 `docs/releases/v0.16.33-draft.md`，把下一版 patch release 聚焦到 publication audit 的 worktree 状态可见性。

## [0.16.32] - 2026-06-12

### Added
- `scripts/check_release_publication.py --publish-script` 生成的发布脚本现在会在 push 前运行 `git status --porcelain`，当 worktree 有未提交改动时拒绝执行。
- 新增 `docs/releases/v0.16.32-draft.md`，把下一版 patch release 聚焦到 publish script 的 dirty worktree 保护。

## [0.16.31] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 的 publication report 现在包含 `repo_root`，生成的 publish script 会先进入该仓库根目录并校验 `git rev-parse --show-toplevel`，避免从错误目录执行时作用到错误工作区。
- 新增 `docs/releases/v0.16.31-draft.md`，把下一版 patch release 聚焦到 publish script 的 repo root 固定。

## [0.16.30] - 2026-06-12

### Added
- `scripts/check_release_publication.py --publish-script` 生成的发布脚本现在会在 push 前执行本地 stale preflight，确认 HEAD、latest tag 和 tag commit 仍与脚本生成时一致。
- 新增 `docs/releases/v0.16.30-draft.md`，把下一版 patch release 聚焦到 publish script 的过期脚本保护。

## [0.16.29] - 2026-06-12

### Added
- `scripts/check_release_publication.py --publish-script` 生成的发布脚本现在会带 `Publication context` 注释，展示 branch、tag、HEAD、ahead/behind 和 remote check 状态，方便维护者审阅脚本是否对应当前本地 release。
- 新增 `docs/releases/v0.16.29-draft.md`，把下一版 patch release 聚焦到 publish script 的发布上下文注释。

## [0.16.28] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 `issue-metadata.json` 现在为每个 candidate 增加 `issue_body_name`，方便下游工具不解析绝对路径也能定位 body 文件。
- 新增 `docs/releases/v0.16.28-draft.md`，把下一版 patch release 聚焦到 candidate issue metadata 的 body 文件名字段。

## [0.16.27] - 2026-06-12

### Changed
- `scripts/plan_next_iteration.py` 生成的 candidate issue body 现在会把 candidate commands 和 offline validation commands 渲染为 `Reproduction Context` 下的子列表，提升 GitHub issue 可读性。
- 新增 `docs/releases/v0.16.27-draft.md`，把下一版 patch release 聚焦到 candidate issue body 的复现命令层级。

## [0.16.26] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会在 `Publication Handoff` 中展示 `Publication Publish Script` 命令，方便维护者先生成并审阅发布脚本。
- 新增 `docs/releases/v0.16.26-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 publish script 入口。

## [0.16.25] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 审阅清单现在要求先确认 `Publication Next Actions` 已处理或明确延后，再运行 `create-issues.sh`。
- 新增 `docs/releases/v0.16.25-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 publication next actions 审阅门禁。

## [0.16.24] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会在 `Publication Handoff` 中展示 `Publication Next Actions`，让维护者不用打开 JSON 也能看到具体发布阻塞。
- 新增 `docs/releases/v0.16.24-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 publication next actions 可见性。

## [0.16.23] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 JSON、文本和 Markdown report 现在会输出 `publication_next_actions`，直接透传 publication audit 的具体发布待办。
- `scripts/plan_next_iteration.py --issues-dir` 写出的 `publication-handoff.json` 现在包含 `publication_next_actions`，方便候选 issue 派发前审阅发布阻塞。
- 新增 `docs/releases/v0.16.23-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publication audit 待办交接。

## [0.16.22] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 JSON、文本和 Markdown report 现在会输出 `release_draft_issues`，把下一版 release draft 缺失或 snippet 校验失败的具体原因直接带到周初计划里。
- 新增 `docs/releases/v0.16.22-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 release draft 诊断细节。

## [0.16.21] - 2026-06-12

### Changed
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 中，`Candidate Summary` 表现在包含每个 candidate 对应的 issue body 文件名。
- 新增 `docs/releases/v0.16.21-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 摘要表的 body 文件入口。

## [0.16.20] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在包含 `Candidate Summary` 表，展示每个 candidate 的 target URL、candidate commands 数量和 offline validation commands 数量。
- 新增 `docs/releases/v0.16.20-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的 README 候选摘要表。

## [0.16.19] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会要求维护者审阅 `issue-metadata.json` 中的 target URL、candidate commands 和 offline validation commands。
- 新增 `docs/releases/v0.16.19-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的 metadata 复现字段审阅清单。

## [0.16.18] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 `issue-metadata.json` 现在包含 `target_url`、`commands` 和 `offline_commands`，方便维护者机器可读地审阅候选 issue 复现上下文。
- 新增 `docs/releases/v0.16.18-draft.md`，把下一版 patch release 聚焦到 candidate issue metadata 的结构化复现上下文。

## [0.16.17] - 2026-06-12

### Changed
- `scripts/plan_next_iteration.py --issues-dir` 生成的 `create-issues.sh` 在 publication preflight 失败时会把 `/tmp/cliany-issue-publication-check.json` 打印到 stderr 后退出。
- 新增 `docs/releases/v0.16.17-draft.md`，把下一版 patch release 聚焦到 candidate issue script 的 publication preflight 失败可读性。

## [0.16.16] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 现在写出 `publication-handoff.json`，把 publication 状态、next actions 和 publish commands 放进候选 issue artifacts。
- 新增 `docs/releases/v0.16.16-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的 publication handoff。

## [0.16.15] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 `create-issues.sh` 现在会先运行 `python scripts/check_release_publication.py --strict --json`，在最新本地 release 尚未公开可见时阻止继续创建候选 issue。
- 新增 `docs/releases/v0.16.15-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的 publication preflight。

## [0.16.14] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 生成的 candidate issue body 现在包含 `Reproduction Context`，带上 target URL、candidate commands 和 offline validation commands。
- 新增 `docs/releases/v0.16.14-draft.md`，把下一版 patch release 聚焦到 candidate issue body 的复现上下文。

## [0.16.13] - 2026-06-12

### Added
- `scripts/validate_cases.py --report` 现在输出 `Candidate Handoff Matrix`，把 candidate 的 target URL、推荐命令和离线验证命令集中成贡献者交接表。
- 新增 `docs/releases/v0.16.13-draft.md`，把下一版 patch release 聚焦到 candidate 案例 handoff matrix。

## [0.16.12] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在输出 `publication_publish_script_command`，周初计划可直接给出生成 `/tmp/cliany-publish-release.sh` 的命令。
- 新增 `docs/releases/v0.16.12-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publish script 生成命令。

## [0.16.11] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 新增 `--publish-script`，可把 `publish_commands` 写成可审阅的可执行 shell 脚本，便于维护者手动发布 branch/tag 后复核远端 refs。
- 新增 `docs/releases/v0.16.11-draft.md`，把下一版 patch release 聚焦到 release publication publish script artifact。

## [0.16.10] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在会把 publication audit 的 `publish_commands` 带入 `publication_publish_commands`，周初计划可直接展示 branch/tag push 和远端复核命令。
- 新增 `docs/releases/v0.16.10-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的发布交接命令。

## [0.16.9] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 现在输出 `publish_commands`，把需要维护者审阅执行的 branch/tag push 和远端复核命令集中到 JSON、文本和 Markdown report。
- 新增 `docs/releases/v0.16.9-draft.md`，把下一版 patch release 聚焦到 release publication handoff 命令。

## [0.16.8] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --json` 现在输出 `issue_artifacts_command`，`--issues-dir` 生成的 `README.md` 也会展示同一条候选 issue artifacts 复现命令。
- 新增 `docs/releases/v0.16.8-draft.md`，把下一版 patch release 聚焦到候选 issue artifacts 可复现生成命令。

## [0.16.7] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 现在会写出 `README.md`，说明 candidate issue artifacts 的文件用途、审阅清单、验证命令和 `create-issues.sh` 不会自动执行的边界。
- 新增 `docs/releases/v0.16.7-draft.md`，把下一版 patch release 聚焦到候选案例 issue artifact README。

## [0.16.6] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 新增 `--issues-dir`，可离线写出 candidate issue body 文件、`issue-metadata.json` 和可审阅的 `create-issues.sh`，帮助维护者批量创建候选案例晋级 issue。
- 新增 `docs/releases/v0.16.6-draft.md`，把下一版 patch release 聚焦到候选案例 issue artifacts 输出。

## [0.16.5] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 `candidate_promotions` 现在包含 `issue_title` 和 `issue_labels`，Markdown report 新增 `Candidate Issue Metadata` 表，便于维护者直接创建候选案例晋级 issue。
- 新增 `docs/releases/v0.16.5-draft.md`，把下一版 patch release 聚焦到计划器生成候选案例 issue 标题和标签。

## [0.16.4] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 `candidate_promotions` 现在包含可复制 `issue_body`，Markdown report 新增 `Candidate Issue Body Templates` 小节，帮助维护者把候选案例晋级拆成 GitHub issue。
- 新增 `docs/releases/v0.16.4-draft.md`，把下一版 patch release 聚焦到计划器生成候选案例 issue 模板。

## [0.16.3] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --json` 和 `--report` 现在输出 `candidate_promotions` / `Candidate Promotion Tasks`，直接列出 candidate 案例晋级所需的 `adapter_package`、`metadata_validation` 和 `online_smoke` 证据。
- 新增 `docs/releases/v0.16.3-draft.md`，把下一版 patch release 聚焦到计划器中的 candidate 晋级任务表。

## [0.16.2] - 2026-06-12

### Added
- 新增 `scripts/plan_next_iteration.py`，聚合 release readiness、publication audit、commit cadence 和 candidate cases，为下个版本输出可执行推荐切片、JSON 和 Markdown 报告。
- 新增 `docs/releases/v0.16.2-draft.md`，把下一版 patch release 聚焦到维护者下个迭代计划入口。

## [0.16.1] - 2026-06-12

### Changed
- `scripts/validate_cases.py --packages-dir ... --report` 的包校验失败现在会输出 `next_actions`，帮助维护者定位 domain、metadata schema、hash 或缺失文件问题。

## [0.16.0] - 2026-06-12

### Changed
- 案例库新增结构化 `validation.offline_commands`，`scripts/validate_cases.py --report` 会汇总每个案例的离线验证命令，便于 PR 和 release 复盘直接复制。

## [0.15.9] - 2026-06-12

### Changed
- `Real Demo Case Proposal` issue 模板现在包含 candidate 晋级证据字段，并指向 `Candidate Promotion Tasks` / `Issue Body Template`，让外部案例提案沿用后续 active 晋级结构。

## [0.15.8] - 2026-06-12

### Changed
- `scripts/validate_cases.py --report` 的 `Candidate Promotion Tasks` 现在会为每个 candidate 输出可复制的 `Issue Body Template`，包含任务、验收证据和非目标边界。

## [0.15.7] - 2026-06-12

### Changed
- `scripts/validate_cases.py --report` 现在会输出 `Candidate Promotion Tasks` 小节，把 candidate 案例的 `promotion` 清单转成可复制的 GitHub issue 任务。

## [0.15.6] - 2026-06-12

### Changed
- 候选案例文档和 Good First Issues 现在把 `adapter_package`、`metadata_validation`、`online_smoke` 拆成独立可验收子任务，帮助贡献者推进 candidate 案例晋级 active。

## [0.15.5] - 2026-06-12

### Changed
- `docs/module-ownership.md` 的 Release operations 行现在纳入 `scripts/check_release_publication.py` 和 `tests/test_release_publication.py`，让贡献者能从模块地图找到发布可见性检查。

## [0.15.4] - 2026-06-12

### Changed
- README 双语路线图入口现在会提示 `scripts/check_release_publication.py --json`，让维护者在选择下一块发布切片时同时确认最新本地 tag 是否公开可见。

## [0.15.3] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 新增 `--report`，可生成 release publication Markdown 报告，保存 branch/tag 发布可见性、refs 和 next actions。
- 新增 `docs/releases/v0.15.3-draft.md`，把下一版 patch release 聚焦到发布可见性报告 artifact。

## [0.15.2] - 2026-06-12

### Added
- 新增 `scripts/check_release_publication.py`，用于检查最新本地 release commit/tag 是否已经被 upstream 或远端 refs 看见，并输出可执行 `next_actions`。
- 新增 `docs/releases/v0.15.2-draft.md`，把下一版 patch release 聚焦到发布可见性检查，避免本地 tag 与公开 GitHub/PyPI 发布状态脱节。

## [0.15.1] - 2026-06-12

### Added
- 新增 `docs/releases/v0.15.1-draft.md`，把下一版 patch release 聚焦到 candidate 案例晋级路径和包名提示去版本漂移。

### Changed
- candidate 案例的 `promotion.adapter_package` 现在要求使用 `<domain>-<version>.cliany-adapter.tar.gz` 占位格式，避免发布后继续保留上一轮固定版本提示。
- `cases/manifest.json` 中 PyPI、npm 和 crates.io 候选案例的晋级包名提示改为 `<version>` 占位，便于后续任意 release train 复用。

## [0.15.0] - 2026-06-12

### Added
- 新增 `docs/releases/v0.15.0-draft.md`，把下一版 minor release 聚焦到 10 分钟成功路径、doctor 下一步提示和 demo adapter 静态验证闭环。

### Changed
- `doctor --json` 的 `data.summary` 现在包含 `demo_adapter_quickstart` 命令清单，human 输出也会展示 demo adapter 安装、list、verify 和只读执行路径。
- 官网首页和文档页的 quickstart 现在明确展示 `10 分钟成功路径`，优先引导用户安装、验证并执行真实 demo adapter，而不是先配置 LLM 后 explore。
- `release_readiness.py` 的项目元数据 gate 现在会检查官网首页和官网 docs 是否保留 10 分钟成功路径，防止网站入口退回旧 quickstart。
- `release_readiness.py` 的项目元数据 gate 现在会检查 `docs/quickstart-10min.md` 是否保留 doctor、demo adapter install/verify/只读命令和无 LLM key 分叉提示。
- `docs/release-cadence.md` 现在说明 minor release 应使用 `release_readiness.py --target-version 0.15.0` 跟踪目标版本，避免默认下一 patch 草案与路线图目标脱节。
- `release_readiness.py --release-tag` 现在要求目标 tag 指向当前 HEAD，避免在 tag 后继续提交时误把后续工作区当作已打 tag 的发布状态。

## [0.14.4] - 2026-06-12

### Added
- 案例库新增 `candidate` 状态和 `pypi-project-search` 候选案例，用离线 JSON 样例承接真实公开只读工作流，待 adapter 包准备好后再晋级 active。
- 案例库新增 `npm-package-search` 候选案例，用离线 JSON 样例覆盖 JavaScript 包注册表搜索场景。
- 案例库新增 `crates-io-crate-search` 候选案例，用离线 JSON 样例覆盖 Rust 包注册表搜索场景，并把真实案例资产推进到 8 个。
- 新增 `docs/module-ownership.md`，把 owner area、主要路径、典型改动和最小验证命令整理成贡献者模块地图。
- 新增 `docs/weekly-maintainer-loop.md`，把路线图、release readiness、案例库验证和发布节奏串成每周选题、实现、复盘的维护者循环。
- 新增 `docs/good-first-issues.md`，把首次贡献任务整理成默认离线、带验证命令的候选池。
- 新增 GitHub `Real Demo Case Proposal` issue 模板，引导外部用户提交可验证、只读、带离线样例输出的真实案例候选。
- `scripts/release_readiness.py` 新增 `--report`，可生成下一版发布 readiness Markdown 摘要，便于发版复盘和 release notes 准备。
- `scripts/validate_cases.py` 新增 `--report`，可生成案例库离线验收 Markdown 报告；CI 会上传 `case-catalog-report` artifact。
- 新增 `cases/examples/*.json` 离线样例输出，让 active 真实案例在不访问第三方站点时也能展示 JSON envelope 形状和典型字段。
- 新增 `tests/fixtures/search_extraction_gap.html` 和离线回归测试，用最小 HTML 页面固定搜索结果抽取字段缺失应判为 `partial` 的 known-gap 语义。
- 新增 `docs/adapter-lifecycle.md`，固化 adapter 从生成、验证、打包、安装到回滚的生命周期，以及 `.cliany-adapter.tar.gz` 包格式和安全边界。
- 新增 `scripts/validate_cases.py`，为 `cases/manifest.json` 提供离线验收报告，并可选检查本地 demo adapter 包 manifest、声明文件哈希和 metadata schema v3 是否与案例声明匹配。
- 新增 `scripts/release_readiness.py`，聚合发布节奏、真实案例库和下一版发布草案检查，作为发版前统一本地门禁。
- 新增抽取结果质量评估，保存的 Markdown 报告会标记空结果、全空字段和部分缺字段，推进搜索/列表抽取 known-gap 的任务级验收。
- 新增 `docs/releases/v0.14.4-draft.md`，提前整理下一版 patch release 的用户价值、风险、验证命令和发版阻塞项。

### Changed
- `doctor` 的 summary 现在包含 `recommended_next_step`，human 输出会直接显示 `下一步`，帮助首次运行用户判断先跑 demo adapter、配置 LLM key 还是修复环境。
- `doctor` 的 summary 现在包含 `capabilities`，按管理已有 adapter、运行浏览器 workflow、生成新 adapter 三条路径展示 ready 状态和 blockers。
- `docs/adapter-lifecycle.md` 新增临时 HOME 的离线 roundtrip 验证流程，帮助维护者在不污染真实 `~/.cliany-site/` 的情况下检查 publish/install/verify/rollback。
- README 双语 marketplace 示例现在使用 `market publish` 实际生成的 `<domain>-<version>.cliany-adapter.tar.gz` 包名，避免复制旧包名失败。
- 案例库 candidate 状态现在要求 `promotion` 清单，明确 adapter 包、metadata 校验和在线只读 smoke 三个晋级 active 的条件。
- `scripts/validate_cases.py` 现在要求 candidate 案例声明 `example_output`，防止候选真实工作流缺少可离线展示的 JSON envelope 样例。
- `scripts/validate_cases.py` 现在会校验 `example_output.data.command` 是否匹配 manifest 中声明的业务命令，避免样例输出和案例命令漂移。
- `scripts/validate_cases.py` 现在会校验离线样例输出中的 `data.quality`，要求样例显式展示成功质量状态和正数 `row_count`。
- `scripts/validate_cases.py` 的终端输出、JSON 和 Markdown 报告现在会展示 candidate 案例的 `promotion` 晋级清单，维护者可直接从 CI artifact 判断候选案例下一步。
- `release_readiness.py` 的文本与 Markdown 报告现在会显示案例库 active/candidate/known-gap/total 汇总，发版复盘可直接看到候选案例管道。
- `release_readiness.py` 默认要求案例库至少保留 8 个 active/candidate/known-gap 资产，防止真实案例库目标在后续维护中无声回退。
- `release_readiness.py --report` 现在会输出 `Candidate Promotions` 小节，把候选案例晋级 active 的三项动作直接带入发版 readiness artifact。
- 官网 quickstart 现在暴露每周维护者循环和 `next_actions` 入口，让网站读者也能从 roadmap 进入可验证发布切片。
- README 双语路线图入口现在链接每周维护者循环，并说明 `release_readiness.py --json` / `check_release_cadence.py --json` 的 `next_actions` 可用于选择下一块可验证发布切片。
- `check_release_cadence.py --json` 现在输出 `missing_commit_days`，cadence/readiness 的 `next_actions` 会直接提示本周还差几个独立提交日。
- `check_release_cadence.py` 的 JSON 与默认文本输出现在包含 `next_actions`，单独检查每周提交节奏时也会提示下一步。
- `release_readiness.py --json` 现在会在顶层输出 `next_actions`，方便 CI、agent 或维护脚本自动读取下一步动作。
- `release_readiness.py` 的默认文本输出现在也会显示 `next_actions`，维护者不生成 Markdown 报告也能看到下一步动作。
- `release_readiness.py --report` 现在会输出 `Next Actions` 小节，把提交天数、案例库、发布草案、CI、发布 workflow、项目元数据和包校验阻塞映射为维护者下一步动作。
- `release_readiness.py --report` 现在会输出 `Weekly Review` 小节，把每周复盘问题和当前 gate 证据放在同一份 Markdown artifact 中。
- `release_readiness.py` 的项目元数据 gate 现在会校验每周维护者循环文档及 roadmap/release cadence 入口，防止持续发布机制在发版前漂移。
- `release_readiness.py` 的项目元数据 gate 现在会校验 `docs/good-first-issues.md`、README good-first-issue 入口和贡献者上手地图链接，防止首次贡献路径漂移。
- `release_readiness.py` 的项目元数据 gate 现在会校验 README 双语 marketplace 示例保留真实 `market publish` 包名，防止安装示例回退到旧格式。
- `docs/good-first-issues.md` 新增 `Issue 拆分清单`，并用文档测试要求每个候选任务保留具体文件和本地验证命令，方便维护者把任务池转成可复现的 `good first issue`。
- `docs/roadmap-2026-q3.md` 与 `docs/release-cadence.md` 现在链接每周维护者循环，帮助维护者把路线图切成可发布、可验证的小版本。
- 官网 quickstart 现在在首次成功路径后提示 `docs/good-first-issues.md`，把首次贡献者引导到默认离线、可本地验证的任务池。
- 官网 quickstart 现在在首次成功路径后提示 `Real Demo Case Proposal`，把公开只读真实工作流引导到案例库贡献和离线验收路径。
- `release_readiness.py` 的项目元数据 gate 现在会校验 README 双语首页是否保留 10 分钟成功路径、抽取质量、release readiness 和真实案例贡献入口。
- `README.md` / `README.zh.md` 的 quickstart 入口现在说明首次成功后可通过 `Real Demo Case Proposal` 贡献新的公开只读真实案例。
- `docs/quickstart-10min.md` 新增首次成功后的贡献路径，指向 `Real Demo Case Proposal`、`cases/manifest.json`、`cases/examples/` 和案例库离线验收命令。
- `docs/contributor-starter.md` 新增 Issue 与 PR 模板入口，说明 bug、feature、真实 demo 候选和 PR 提交分别应准备的可复现信息。
- `release_readiness.py` 的项目元数据 gate 现在会校验 GitHub PR 模板、issue 模板与 issue template config 是否存在且包含关键字段，避免关键开源协作入口和安全上报入口在发版前漂移。
- `.github/PULL_REQUEST_TEMPLATE.md` 更新为按改动类型提示案例库、release readiness 和零密钥 PR 门禁验证，减少贡献者跑错检查的概率。
- `docs/release-cadence.md` 新增 readiness 报告排障流程，要求维护者优先读取 `Gate Issues` 并逐项关闭 gate 失败原因。
- `docs/contributor-starter.md` 的发布脚本验证路径改为优先使用 `release_readiness.py` 总入口，并用测试固定贡献者文档不会退回单点 cadence 检查。
- `release_readiness.py --report` 现在会在 Markdown 报告中列出各 gate 的具体失败原因，CI artifact 可直接用于定位发版阻塞项。
- `release_readiness.py` 新增项目元数据 gate，发布前会校验 PyPI `description` / `readme` / project URLs，以及 LICENSE、贡献、安全和支持入口文件。
- `.github/workflows/release.yml` 在发布构建前清理 `dist/`，并在 `uv build` 后运行 `uvx twine check dist/*` 校验本次 wheel/sdist 元数据。
- `pyproject.toml` 新增 PyPI `description` 和 `readme` 元数据，让发布包包含 README long description。
- `release_readiness.py --release-tag` 支持校验已打 tag 的发布状态，避免 tag workflow 把当前 tag 误判成“下一版”。
- `.github/workflows/release.yml` 在构建和发布前新增 `Release Preflight`，会运行 `release_readiness.py --strict --release-tag ... --report`，防止 tag 发布绕过 readiness 门禁。
- `scripts/release_readiness.py` 现在会校验 `.github/workflows/release.yml` 的 tag 触发、CI 复用、构建、GitHub Release 和 PyPI 发布链路，避免正式发版 workflow 漂移。
- CI 新增 `Release Readiness Report` job，在 PR/主分支生成并上传 `release-readiness-report` artifact，便于持续观察下一版发版阻塞项。
- `scripts/validate_cases.py` 现在要求 active 案例声明 `example_output`，并校验样例路径、JSON envelope、`meta.case_id` 和非空 `data.results`。
- `scripts/check_release_cadence.py` / `scripts/release_readiness.py` 现在会校验 `CHANGELOG.md` 的 `[Unreleased]` compare 链接是否从最新 tag 指向 `HEAD`，避免发布说明范围漂移。
- `scripts/validate_cases.py` 现在会检查 `cases/manifest.json` 中 `docs` 的 Markdown 锚点和 active 案例命令域名一致性，避免真实案例链接或命令漂移。
- `docs/releases/v0.14.4-draft.md` 新增案例库映射，release notes 会链接 `cases/README.md`、`cases/manifest.json` 和 `search-extraction-gap` 离线复现。
- `scripts/release_readiness.py` 新增 `--require-packages`，正式发版前可强制要求 `--packages-dir` 完成 demo adapter 包离线校验。
- `README.md` / `README.zh.md` 同步 v0.14.4 抽取质量与 release readiness 入口，说明 `data.quality`、`--strict-quality` 和 `E_EMPTY_RESULT` 的用户含义。
- `scripts/release_readiness.py` 新增 CI release gate 检查，发布前会确认案例库和抽取质量回归 job 仍在默认 CI 中。
- CI 新增 `Extract Quality Regression` job，在零真实 LLM key 环境中显式运行抽取质量、结构化 `browser extract` 和生成数据命令回归。
- 生成 adapter 的 JSON 输出新增 `data.quality` 汇总，并修复 extract 步骤调用 `browser extract --mode` 时内置命令不识别该参数的问题。
- `browser extract --mode ... --json` 在结构化提取时新增 `data.quality`，便于手动调试 list/table/attribute 结果是否为空或字段缺失。
- `browser extract --mode ... --strict-quality` 可在结构化提取质量未通过时返回 `E_EMPTY_RESULT`，便于本地脚本和 CI 将空抽取或关键字段缺失判为失败。
- 生成的 `list-` / `search-` 数据命令现在会在抽取质量为 `empty` 或 `partial` 时返回 `E_EMPTY_RESULT`，避免“命令成功但字段为空或缺失”的误判。
- 官网 Quick Start 同步 v0.14.3 首次成功路径：先运行 `doctor` 摘要和真实 demo adapter，再配置 LLM 生成自定义命令。
- CI 新增 `Case Catalog Validation` job，在 PR/主分支默认离线运行 `scripts/validate_cases.py --strict` 与案例库结构测试，防止真实案例索引漂移。
- `market install` 收紧包内容校验：拒绝缺失声明文件、缺失哈希和未声明额外文件，并在覆盖安装前先完成完整校验，避免坏包产生无意义备份。
- `market install --json` 对安装失败返回 `INSTALL_FAILED` 和针对性 `error.fix`，覆盖重复安装、哈希不匹配、manifest 缺失字段、未声明文件与不安全路径场景。
- `verify --json` 在已安装 adapter 存在 `manifest.json` 时新增 manifest v1、domain、files/file_hashes 和已安装文件哈希诊断；无 market manifest 的本机 adapter 会标记为 `manifest.status = "missing"` 但不判定失败。

## [0.14.3] - 2026-06-10

### Added
- 新增 `docs/roadmap-2026-q3.md`，基于 v0.2~v0.14 迭代轨迹制定 2026 Q3 路线图，聚焦新用户可用性、真实案例库、adapter 生命周期、贡献者入口与运行可靠性。
- 新增 `docs/release-cadence.md`，固化每周至少 1 个版本、每周至少 3 天提交记录的发布与提交节奏。
- 新增 `cases/manifest.json` 与 `cases/README.md`，把 v0.14 真实 demo 和搜索抽取短板复盘沉淀为可维护案例库，并新增离线结构校验测试。
- 新增 `docs/quickstart-10min.md`，提供不依赖 LLM key 的 demo adapter 首次成功路径，以及生成自定义 adapter 的后续路径。
- `doctor --json` 新增 `data.summary` 分层行动建议，并为每个 check 补充 `severity` 与 `action` 字段，帮助新用户区分必须修复、建议优化和诊断信息。
- `doctor` 非 JSON 输出新增面向人的摘要视图，按“必须修复 / 建议处理 / 诊断信息”展示行动项。
- 新增 `scripts/check_release_cadence.py`，本地检查版本 tag、本周提交天数、CHANGELOG Unreleased 和工作区状态；`scripts/publish.sh` 改为优先使用 `PYPI_TOKEN` 环境变量。
- 新增 `docs/contributor-starter.md`，提供 good-first-issue 清单、模块地图、复现问题最小包和按风险选择验证范围的贡献者入口。

### Verification
- `.venv/bin/python -m pytest tests/test_doctor.py tests/test_doctor_checks.py tests/test_doctor_v3.py tests/test_obscura_integration_entrypoints.py tests/test_cases_manifest.py tests/test_release_cadence.py tests/test_contributor_docs.py -q --no-cov`
- `.venv/bin/ruff check src/cliany_site/commands/doctor.py scripts/check_release_cadence.py tests/test_doctor_v3.py tests/test_cases_manifest.py tests/test_release_cadence.py tests/test_contributor_docs.py`

## [0.14.2] - 2026-06-10

### Added
- **自主改进闭环基础设施**：新增 5 个维度的自主改进脚手架，使 OpenCode 可触发自主演进循环。
  - **维度1 确定性回归**：`tests/benchmarks/` 基线数据集（2 场景）+ `_parse_llm_response` / `_sanitize_actions_data` / `AdapterGenerator.generate` 三层回归测试 + 哨兵有效性闭环验证，零真实 LLM。
  - **维度2 运行时反馈**：扩展 `bug_report.yml` 新增 5 个结构化字段（target_url / error_code / axtree_snapshot / cliany_version / doctor_output）+ `auto-reproduce` label 触发的复现 workflow。
  - **维度3 具身浏览器验证**：`tests/embodied/` headless Chromium + CDPConnection + AXTree 集成测试，配套独立 `embodied-ci.yml` CI job。
  - **维度4 依赖哨兵**：`.github/dependabot.yml`（pip + github-actions，weekly）+ `dep-upgrade-verify.yml` 依赖升级验证 workflow。
  - **维度5 Agent 守则**：根 `AGENTS.md` 与包级 `src/cliany_site/AGENTS.md` 新增「AUTONOMOUS IMPROVEMENT GUARDRAILS」章节 + `.github/AUTONOMOUS_FIX.md` 自主修复协议总文档。
- **benchmark 回归并入 PR 门禁**：`ci.yml` 新增 `benchmark-regression` job（零密钥，`CLIANY_QA_OFFLINE=1`，`timeout-minutes: 10`）。

## [0.14.1] - 2026-05-28

### Added
- **3 个新错误码**：`E_PAGE_NOT_READY`（页面未就绪超时）、`E_PARSE_FAILED`（解析异常）、`E_EMPTY_RESULT`（空结果，list-/search- opt-in），统一"空结果 vs 显式失败"语义。
- **list-/search- 命令空结果检测**：生成器模板新增 opt-in 空结果 guard，防止静默空返回。
- **Obscura 友好错误提示**：explore/login 在 Obscura provider 下返回结构化友好提示，包含 `suggested_action` 和文档链接。
- **ADR-0008**：`docs/decisions/0008-failure-semantics.md` — 失败语义决策记录。
- **ADR-0009**：`docs/decisions/0009-provider-capability-matrix.md` — Provider 能力矩阵决策记录。
- **3 个新 qa 脚本**：`test_failure_semantics.sh`（4 场景）、`test_doctor_agent_md.sh`（2 场景）、`test_obscura_explore_friendly.sh`（2 场景）。

### Fixed
- **navigate/extract/action_runtime 失败语义**：readiness timeout 和解析异常统一返回 `ok=false` + 对应错误码，而非静默空结果。
- **doctor agent_md 双文件名检查**：同时识别 `AGENT.md` 和 `AGENTS.md`，sentinel 缺失时仅提示不重生成。
- **Obscura 能力声明修正**：`ObscuraProvider` 正确声明 `supports_navigation=False` / `supports_cookies=False`，与实际行为一致，修复 login feature gate 不拦截导致的挂起问题。
- **CDP 日志降噪**：`cdp_use.client` logger 设为 ERROR 级别，消除探索过程中的 WARNING 噪声。



### Added
- **4개 공개 데모 사이트 adapter 자산**: SuiteCRM Demo, ASF Jira, ASF Confluence, ASF Jenkins(builds.apache.org). GitHub Release v0.14.0 assets에 탑재.

### Changed
- **官网 "Real-World Use Cases" 섹션**: Case 2(기업 CRM) · Case 3(팀 도구함) 카드에서 CONCEPT 배지 제거, 실제 공개 데모 사이트 명령어 및 i18n 문案으로 교체.

### Docs
- **README.md / README.zh.md**: "Try Real Demos" 단락 추가, 제3자 유지 demo 사이트 disclaimer 포함.

## [0.13.0] - 2026-05-25

### Fixed
- **[Bug] loader.py::load_or_rebuild 未捕获 RuntimeError**：`build_manifest()` 调用现在被 `try/except` 包裹，异常时记录 `logger.warning` 并回退为空 manifest，不再向上传播
- **[Flaky] test_session_lock 不稳定测试修复**：改用 `patch.object(logger, "error")` 替代 caplog，测试确定性提升

### Added
- **doctor 命令增强**：新增 `versions` 检查项（Python 版本、cliany-site 版本、click/anthropic/openai 依赖版本）和 `adapter_stats` 检查项（adapter 数量、命令总数）
- **ERROR_FIX_HINTS 补全**：为 `ErrorCode` 类的所有 `E_*` 前缀常量（共 27 个）补充用户友好的修复提示

### Changed
- **envelope.py TypedDict 分离**：新增 `SuccessEnvelope`（`ok: Literal[True]`）和 `ErrorEnvelope`（`ok: Literal[False]`）分离 TypedDict；`Envelope` 保留为 Union 别名，向后兼容
- **核心模块 pyright strict**：`errors.py`、`response.py`、`atomic_io.py`、`envelope.py`、`loader.py` 进入 pyright strict 模式，0 errors

## [0.12.0] - 2026-05-21

### Fixed
- **[보안] tar 경로 순회 차단** (`tui/screens/adapter_list.py`): 악성 `.tar.gz` 임포트 시 경로 이탈 방지, `UnsafeArchiveError` 추가 (commit bbb13d6)
- **[안정성] binary/process.py PID 파일 경쟁 조건 수정**: portalocker 배타 락 + NamedTemporaryFile + os.replace()로 원자적 쓰기 보장 (commit 3924c00)
- **[안정성] loader.py manifest 경쟁 조건 수정**: portalocker.Lock + threading.RLock + 원자 쓰기로 동시 접근 안전성 확보 (commit e903f44)
- **[안정성] codegen/merger.py fsync 누락 수정**: flush + fsync + 디렉터리 fsync로 전력 이상 시 데이터 손실 방지 (commit 9b236cd)
- **[안정성] obscura 다운로드 재시도 없음 수정**: 지수 백오프 3회 재시도 구현, HTTPError/URLError 예외 계층 올바르게 처리 (commit 6e8c713)
- **[안정성] session.py / atomic_io.py 파일 락 및 로그 누락 수정**: portalocker + mkstemp + fdopen + fsync 패턴 적용, 파싱 실패 시 에러 로그 추가 (commit 74ee847)

### Changed
- **explorer/interactive.py 연쇄 except 세분화**: 브로드 Exception 블록을 구체적 예외 타입(AttributeError, RuntimeError, asyncio.TimeoutError 등)으로 분리, logger.extra 컨텍스트 필드 추가 (commit 60a9b59)
- **errors.py 에러 코드 통일**: `LOCK_TIMEOUT`, `UNSAFE_ARCHIVE` 2개 에러 코드 추가(후방 호환), ERROR_FIX_HINTS 힌트 메시지 보완 (commit 5bf36c4)

### Added
- **pytest-cov 및 portalocker 의존성 추가**: v0.12 가딩 작업 기반 인프라 (commit 5980712)
- **CI coverage 리포트**: GitHub Actions에 pytest-cov 플래그 + artifact 업로드 추가 (commit bff9074)
- **가관측성 단언 테스트 4종**: 로깅 마스킹, JSONFormatter, ERROR_FIX_HINTS 커버리지, envelope ok/success 호환성 (commit e4eb52c)
- **action_runtime.py 분기 커버리지 보완**: `_resolve_action_node`, `_attempt_adaptive_repair` 등 9개 분기 테스트 추가 (commit 74ee847)
- **성능 마이크로 벤치마크**: `tests/perf/` 디렉터리에 pytest-benchmark 기반 P95 회귀 임계값 테스트 추가 (commit 26ebc82)

### Internal
- **ADR-0007 안정성 가딩 결정 기록**: `docs/decisions/0007-v012-stability-hardening.md` 신규 작성 (commit 046cbcc)

## [0.11.0] - 2026-05-12

### Obscura 实验性浏览器后端集成
- **核心功能**：
  - 新增浏览器提供者抽象层（Browser Provider Abstraction），支持能力快照（Capability Snapshot）与特性门禁（Feature Gate）。
  - 新增 `ObscuraProvider` 与 `ChromeProvider` 包装层，Chrome 保持为默认提供者。
  - 显式启用方式：设置环境变量 `CLIANY_BROWSER_PROVIDER=obscura`。
  - **注意**：`explore` 命令在 Obscura 下已被门禁（Gated），目前不宣称完全支持。
- **Obscura 生命周期管理**：
  - 增加 `cliany-site obscura` 命令组：支持 `install/use/status/clean/rollback/upgrade/doctor`。
  - 实现二进制文件生命周期：包括 Manifest 管理、本地缓存、原子安装（Atomic Install）、Active 指针切换、回滚支持及进程管理器。
- **多平台支持**：
  - 支持 `darwin-arm64` (Apple Silicon), `darwin-x86_64` (Intel Mac), `linux-x86_64`, `windows-x86_64`。
- **测试与质量保证**：
  - 建立 Smoke（冒烟）、Compat（兼容性）、Benchmark（基准）三层测试体系。
  - 集成 CI Release Gates，确保发布质量。
- **文档与工程**：
  - 新增相关 ADR（决策记录）与 Obscura Experimental Guide 实验性指南。

## [0.10.0] - 2026-05-07

### BREAKING 变更
- **metadata schema v3 硬切换**：schema_version 2 及以下 adapter 标记为 legacy，需通过 `cliany-site migrate` 重新迁移或重新 explore 生成。

### 新功能（借鉴自 opencli）
- **DOM 剪枝 + 复合控件提取**（T02/T03）：AXTree 捕获时四层剪枝（深度/节点数/屏蔽角色/压缩序列），自动提取 `<select>` / `<input type=date>` / `<input type=file>` 的选项元数据，减少 prompt token 消耗 30%~50%。
- **Lazy Adapter Registry**（T05/T06）：`LazyAdapterRegistry` 替代全量 import，`discover()` 仅读 `metadata.json`，`get(domain, cmd)` 按需 `importlib.import_module()`，加快 CLI 启动 2~5x。
- **Repair Cache（修复缓存）**（T10）：heal 结果写入 `~/.cliany-site/adapters/{domain}/repair-cache.json`（LRU 100 条/domain），相同故障模式命中缓存可跳过 LLM 调用。
- **Network + Console Capture**（T11）：explore 阶段自动捕获 Network 请求（>1MB 停止）和 Console 日志（500 条滚动覆盖），存入 StepRecord，供诊断/回放使用。
- **Capability Routing**（T13）：探索时嗅探 API endpoints，replay 时自动路由 browser / api 双通道，`--force-browser` flag 强制走 browser 模式。
- **migrate 命令**（T12）：`cliany-site migrate [--json] [--dry-run]` 一键扫描并迁移所有 legacy adapter 到 schema_version 3，带 `.bak` 备份。
- **Diagnostic Mode**（T20/T22/T23）：`cliany-site --diagnose --json <domain> <cmd>` 在命令失败时触发 LLM 诊断，输出 `root_cause` + `suggested_fix`；生成的 adapter 模板已内置 `diagnose_if_enabled(ctx, failed)` hook。

### 新测试
- `tests/test_v010_integration.py`：10 项集成测试（CI 可跑，不依赖 Chrome/LLM key）
- `tests/fixtures/fake_llm.py`：`FakeChatModel` 用于离线 QA（`CLIANY_QA_OFFLINE=1`）
- `qa/test_v010_e2e.sh`：端到端 shell 测试套件

### 环境变量新增
- `CLIANY_QA_OFFLINE=1`：离线 QA 模式，配合 `CLIANY_QA_FAKE_LLM_RESPONSES` 使用
- `CLIANY_QA_FAKE_LLM_RESPONSES=<path>`：FakeChatModel 的 response 文件路径
- `--force-browser`：root flag，强制 replay 走 browser 通道
- `--diagnose`：root flag，命令失败时触发 LLM 诊断

## [0.9.3] - 2026-04-30

### 文档
- README.md 默认改为英文，新增 README.zh.md（中文完整版）
- 删除旧的 README.en.md
- 官网全面英文化：默认语言改为 en、style.css 注释翻译为英文、补齐 script.js 缺失英文翻译

### 官网
- 新增 5 张 v0.9.x 功能展示 cards（Smart Self-Healing、Static Verification、Self-Describing Contract、Atom Commands System、Metadata Schema v2）
- SEO meta 同步中英语言切换

## [0.9.2] - 2026-04-28

### 修复
- 录像 AXTree bytes 序列化 + explore 命令迁移到新 envelope 格式

## [0.9.1] - 2026-04-27

### 修复
- 修复 3 个运行时回归：根级 JSON 错误信封、legacy adapter 列表过滤、verify schema 资源打包

## [0.9.0] - 2026-04-26

### BREAKING CHANGES
- **metadata schema v2 hardcut**: `schema_version` 정수 필드 필수. 구 adapter 자동 거부 + `cliany-site explore <url>` 지침 출력.
- **envelope 통일**: 모든 명령 출력이 `{ok, version, command, data, error, meta}` 형식으로 전환. `success` 키는 하위 호환 alias.

### Added
- `cliany-site browser state/navigate/find/click/type/extract/wait/screenshot/eval` — 9개 atom 명령 (zero LLM)
- `cliany-site verify [domain]` — 정적(jsonschema+AST) + `--smoke` CDP 냉간 테스트
- `cliany-site --json --explain` — Agent 자기설명 엔드포인트
- `cliany-site adapter accept-heal <domain>` — healer sidecar 적용
- `cliany-site list --legacy` — 거부된 구 adapter 목록 표시
- `cliany-site doctor` — registry/legacy/agent_md/healed_pending 체크 추가
- `./AGENT.md` 자동 생성/갱신 (sentinel+hash 이중 보호)
- `--heal` 자가치유 플래그 (LLM 비용 cap: max_calls=3, max_tokens=4000)
- `CLIANY_HEAL_DISABLE`, `CLIANY_HEAL_MAX_CALLS`, `CLIANY_HEAL_MAX_TOKENS` 환경변수
- `CLIANY_NO_AGENT_MD=1` 환경변수로 AGENT.md 자동 재작성 억제

### Changed
- `explore` 성공 시 v2 metadata 원자 쓰기 + AGENT.md 자동 재작성
- `loader` — 구 adapter 하드 거부 (이전: 경고 후 로드)
- `codegen` — generated 명령이 run_atom() 통해 atom 명령을 호출 (직접 CDP 미사용)

### Removed
- 구 metadata (`schema_version` 없거나 문자열 "1") 자동 로드 지원 종료

### Migration
구 adapter → 재생성: `cliany-site explore <url> "<workflow>"`  
자세한 마이그레이션 절차: [docs/migration-0.9.md](docs/migration-0.9.md)

## [0.8.3] - 2026-04-13

### 新增
- **sandbox 执行预检**：为适配器命令接通 `--sandbox` 执行预检流程，限制跨域导航和危险操作

### 文档
- 添加 sandbox CLI 闭环设计与计划文档
- 官网新增「真实场景」Use Cases 展示模块（案例内容打磨与精简）

### 其他
- 更新 `.gitignore` 规则

## [0.8.2] - 2026-04-08

### 新增
- **adapter 命令级断点恢复**：为生成的站点命令补齐 `--resume`，可通过 `cliany-site <domain> <command> --resume` 从最近断点继续执行

### 变更
- 生成命令会先汇总完整动作序列，再统一传入执行引擎，避免断点恢复时出现分段索引错位
- README 中的断点续执行说明已对齐到真实 CLI 入口

### 修复
- 修复 `explorer` 包级导出导致的循环导入问题，避免 codegen 相关测试在收集阶段失败
- 修复 CLI 版本测试对旧版本号的硬编码断言，改为读取包元数据

### 文档
- 添加 `--resume` 闭环设计与实现计划文档
- 添加规划差距评审与规划项对账文档

## [0.8.1] - 2026-04-03

### 新增
- **官网 Use Cases 展示模块**：在 Features 和 How It Works 之间新增「真实场景」案例展示
- 3 个案例卡片：GitHub CLI 化（真实）、企业 CRM 无 API（概念）、团队工具箱（概念）
- Before/After 标签页切换交互
- 案例 1 终端 CSS 打字动画（IntersectionObserver 触发，支持 prefers-reduced-motion）
- 完整中英双语支持，44 个 `usecases.*` i18n 键
- 响应式布局：375/900/1280px 三视口适配

### 文档
- 官网新增 Use Cases 模块完整实施 walkthrough 文档

## [0.8.0] - 2026-04-02

### 新增
- **会话式探索**：支持交互式探索 (`--interactive`)，每步 LLM 规划后暂停，支持 CONFIRM/SKIP/MODIFY/ROLLBACK
- **增量扩展探索**：支持 `--extend <domain>`，加载已有适配器 metadata 作为 LLM 上下文，实现精准补全
- **探索录像系统**：自动保存截图、AXTree 和动作序列到 `~/.cliany-site/recordings/`
- **录像回放命令**：新增 `replay <domain>` 命令，Rich 终端回放探索全过程，支持 `--step` 逐步回放
- **优雅中断保护**：Ctrl-C 中断后自动保存已探索的中间结果，支持后续合并

## [0.7.1] - 2026-04-02

### 文档
- 修复 README.md「更新日志」和「贡献指南」区块的中英双语格式

## [0.7.0] - 2026-03-31

### 新增
- **多模态感知系统**：截图 + Vision LLM 双通道感知，提升探索和元素定位成功率
- 新增 `browser/screenshot.py` 截图采集模块，支持 CDP 截图和 base64 编码
- 新增 SoM（Set-of-Mark）标注引擎，在截图上绘制带编号的元素标签
- 新增 `explorer/vision.py` 多模态消息构建模块，支持 LangChain 图文混合消息
- 新增 Vision 视觉定位能力，作为元素解析 L3 层兜底策略
- 新增 5 个 Vision 配置项：`CLIANY_VISION_ENABLED`、`CLIANY_SCREENSHOT_FORMAT`、`CLIANY_SCREENSHOT_QUALITY`、`CLIANY_VISION_MIN_CONFIDENCE`、`CLIANY_VISION_SOM_MAX_LABELS`
- 新增 `Pillow` 可选依赖组 `[vision]`，用于 SoM 图像标注
- 新增 17 个测试用例覆盖截图和 Vision 模块

### 变更
- `capture_axtree()` 在 vision_enabled 时同步采集截图数据
- `_invoke_llm_with_retry()` 支持 LangChain Message 对象（图文混合输入）
- 探索循环在 Vision 模式下自动构建多模态 prompt
- 元素解析策略扩展为 4 层：L0 直接匹配 → L1 模糊打分 → L2 自适应修复 → L3 Vision 定位

### 文档
- 添加 v0.7.0 多模态感知实施计划文档
- 添加 v0.7.0 实施 walkthrough 文档

## [0.6.2] - 2026-03-31

### 新增
- 添加完整的开源社区基础设施文件

### 文档
- 添加 MIT LICENSE（版权 pearjelly，2026）
- 添加 CONTRIBUTING.md 贡献者指南（中英双语）
- 添加 CODE_OF_CONDUCT.md 行为准则（Contributor Covenant v2.1）
- 添加 SECURITY.md 安全漏洞报告政策
- 添加 SUPPORT.md 用户支持指引
- 添加 CHANGELOG.md（Keep-a-Changelog 格式，迁移历史版本）
- 添加 .github/ISSUE_TEMPLATE/（bug report / feature request / config）
- 添加 .github/PULL_REQUEST_TEMPLATE.md
- 添加 .pre-commit-config.yaml（ruff + mypy 本地工具）
- 更新 README.md（更新日志/贡献指南改为链接外部文件）

## [0.6.1] - 2026-03-31

### 修复
- 修复 extract 在某些情况下 Page 对象获取失败的问题

## [0.5.1] - 2026-03-31

### 新增
- 添加 LLM 调用重试机制，提升网络不稳定时的探索成功率
- 新增 Extract 数据抽取动作类型，支持从页面提取结构化数据并保存为 Markdown

### 变更
- CSS Selector 候选预计算，自动生成多个 selector 候选增强元素匹配韧性
- 探索提示词注入 selector 候选，extract 空 selector 告警

### 修复
- 修复合并周期保留 selector/extract_mode/fields_map 的问题
- 修正 QA 测试断言与实际 API 对齐

[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.16.226...HEAD
[0.16.226]: https://github.com/pearjelly/cliany.site/compare/v0.16.225...v0.16.226
[0.16.225]: https://github.com/pearjelly/cliany.site/compare/v0.16.224...v0.16.225
[0.16.224]: https://github.com/pearjelly/cliany.site/compare/v0.16.223...v0.16.224
[0.16.223]: https://github.com/pearjelly/cliany.site/compare/v0.16.222...v0.16.223
[0.16.222]: https://github.com/pearjelly/cliany.site/compare/v0.16.221...v0.16.222
[0.16.221]: https://github.com/pearjelly/cliany.site/compare/v0.16.220...v0.16.221
[0.16.220]: https://github.com/pearjelly/cliany.site/compare/v0.16.219...v0.16.220
[0.16.219]: https://github.com/pearjelly/cliany.site/compare/v0.16.218...v0.16.219
[0.16.218]: https://github.com/pearjelly/cliany.site/compare/v0.16.217...v0.16.218
[0.16.217]: https://github.com/pearjelly/cliany.site/compare/v0.16.216...v0.16.217
[0.16.216]: https://github.com/pearjelly/cliany.site/compare/v0.16.215...v0.16.216
[0.16.215]: https://github.com/pearjelly/cliany.site/compare/v0.16.214...v0.16.215
[0.16.214]: https://github.com/pearjelly/cliany.site/compare/v0.16.213...v0.16.214
[0.16.213]: https://github.com/pearjelly/cliany.site/compare/v0.16.212...v0.16.213
[0.16.212]: https://github.com/pearjelly/cliany.site/compare/v0.16.211...v0.16.212
[0.16.211]: https://github.com/pearjelly/cliany.site/compare/v0.16.210...v0.16.211
[0.16.210]: https://github.com/pearjelly/cliany.site/compare/v0.16.209...v0.16.210
[0.16.209]: https://github.com/pearjelly/cliany.site/compare/v0.16.208...v0.16.209
[0.16.208]: https://github.com/pearjelly/cliany.site/compare/v0.16.207...v0.16.208
[0.16.207]: https://github.com/pearjelly/cliany.site/compare/v0.16.206...v0.16.207
[0.16.206]: https://github.com/pearjelly/cliany.site/compare/v0.16.205...v0.16.206
[0.16.205]: https://github.com/pearjelly/cliany.site/compare/v0.16.204...v0.16.205
[0.16.204]: https://github.com/pearjelly/cliany.site/compare/v0.16.203...v0.16.204
[0.16.203]: https://github.com/pearjelly/cliany.site/compare/v0.16.202...v0.16.203
[0.16.202]: https://github.com/pearjelly/cliany.site/compare/v0.16.201...v0.16.202
[0.16.201]: https://github.com/pearjelly/cliany.site/compare/v0.16.200...v0.16.201
[0.16.200]: https://github.com/pearjelly/cliany.site/compare/v0.16.199...v0.16.200
[0.16.199]: https://github.com/pearjelly/cliany.site/compare/v0.16.198...v0.16.199
[0.16.198]: https://github.com/pearjelly/cliany.site/compare/v0.16.197...v0.16.198
[0.16.197]: https://github.com/pearjelly/cliany.site/compare/v0.16.196...v0.16.197
[0.16.196]: https://github.com/pearjelly/cliany.site/compare/v0.16.195...v0.16.196
[0.16.195]: https://github.com/pearjelly/cliany.site/compare/v0.16.194...v0.16.195
[0.16.194]: https://github.com/pearjelly/cliany.site/compare/v0.16.193...v0.16.194
[0.16.193]: https://github.com/pearjelly/cliany.site/compare/v0.16.192...v0.16.193
[0.16.192]: https://github.com/pearjelly/cliany.site/compare/v0.16.191...v0.16.192
[0.16.191]: https://github.com/pearjelly/cliany.site/compare/v0.16.190...v0.16.191
[0.16.190]: https://github.com/pearjelly/cliany.site/compare/v0.16.189...v0.16.190
[0.16.189]: https://github.com/pearjelly/cliany.site/compare/v0.16.188...v0.16.189
[0.16.188]: https://github.com/pearjelly/cliany.site/compare/v0.16.187...v0.16.188
[0.16.187]: https://github.com/pearjelly/cliany.site/compare/v0.16.186...v0.16.187
[0.16.186]: https://github.com/pearjelly/cliany.site/compare/v0.16.185...v0.16.186
[0.16.185]: https://github.com/pearjelly/cliany.site/compare/v0.16.184...v0.16.185
[0.16.184]: https://github.com/pearjelly/cliany.site/compare/v0.16.183...v0.16.184
[0.16.183]: https://github.com/pearjelly/cliany.site/compare/v0.16.182...v0.16.183
[0.16.182]: https://github.com/pearjelly/cliany.site/compare/v0.16.181...v0.16.182
[0.16.181]: https://github.com/pearjelly/cliany.site/compare/v0.16.180...v0.16.181
[0.16.180]: https://github.com/pearjelly/cliany.site/compare/v0.16.179...v0.16.180
[0.16.179]: https://github.com/pearjelly/cliany.site/compare/v0.16.178...v0.16.179
[0.16.178]: https://github.com/pearjelly/cliany.site/compare/v0.16.177...v0.16.178
[0.16.177]: https://github.com/pearjelly/cliany.site/compare/v0.16.176...v0.16.177
[0.16.176]: https://github.com/pearjelly/cliany.site/compare/v0.16.175...v0.16.176
[0.16.175]: https://github.com/pearjelly/cliany.site/compare/v0.16.174...v0.16.175
[0.16.174]: https://github.com/pearjelly/cliany.site/compare/v0.16.173...v0.16.174
[0.16.173]: https://github.com/pearjelly/cliany.site/compare/v0.16.172...v0.16.173
[0.16.172]: https://github.com/pearjelly/cliany.site/compare/v0.16.171...v0.16.172
[0.16.171]: https://github.com/pearjelly/cliany.site/compare/v0.16.170...v0.16.171
[0.16.170]: https://github.com/pearjelly/cliany.site/compare/v0.16.169...v0.16.170
[0.16.169]: https://github.com/pearjelly/cliany.site/compare/v0.16.168...v0.16.169
[0.16.168]: https://github.com/pearjelly/cliany.site/compare/v0.16.167...v0.16.168
[0.16.167]: https://github.com/pearjelly/cliany.site/compare/v0.16.166...v0.16.167
[0.16.166]: https://github.com/pearjelly/cliany.site/compare/v0.16.165...v0.16.166
[0.16.165]: https://github.com/pearjelly/cliany.site/compare/v0.16.164...v0.16.165
[0.16.164]: https://github.com/pearjelly/cliany.site/compare/v0.16.163...v0.16.164
[0.16.163]: https://github.com/pearjelly/cliany.site/compare/v0.16.162...v0.16.163
[0.16.162]: https://github.com/pearjelly/cliany.site/compare/v0.16.161...v0.16.162
[0.16.161]: https://github.com/pearjelly/cliany.site/compare/v0.16.160...v0.16.161
[0.16.160]: https://github.com/pearjelly/cliany.site/compare/v0.16.159...v0.16.160
[0.16.159]: https://github.com/pearjelly/cliany.site/compare/v0.16.158...v0.16.159
[0.16.158]: https://github.com/pearjelly/cliany.site/compare/v0.16.157...v0.16.158
[0.16.157]: https://github.com/pearjelly/cliany.site/compare/v0.16.156...v0.16.157
[0.16.156]: https://github.com/pearjelly/cliany.site/compare/v0.16.155...v0.16.156
[0.16.155]: https://github.com/pearjelly/cliany.site/compare/v0.16.154...v0.16.155
[0.16.154]: https://github.com/pearjelly/cliany.site/compare/v0.16.153...v0.16.154
[0.16.153]: https://github.com/pearjelly/cliany.site/compare/v0.16.152...v0.16.153
[0.16.152]: https://github.com/pearjelly/cliany.site/compare/v0.16.151...v0.16.152
[0.16.151]: https://github.com/pearjelly/cliany.site/compare/v0.16.150...v0.16.151
[0.16.150]: https://github.com/pearjelly/cliany.site/compare/v0.16.149...v0.16.150
[0.16.149]: https://github.com/pearjelly/cliany.site/compare/v0.16.148...v0.16.149
[0.16.148]: https://github.com/pearjelly/cliany.site/compare/v0.16.147...v0.16.148
[0.16.147]: https://github.com/pearjelly/cliany.site/compare/v0.16.146...v0.16.147
[0.16.146]: https://github.com/pearjelly/cliany.site/compare/v0.16.145...v0.16.146
[0.16.145]: https://github.com/pearjelly/cliany.site/compare/v0.16.144...v0.16.145
[0.16.144]: https://github.com/pearjelly/cliany.site/compare/v0.16.143...v0.16.144
[0.16.143]: https://github.com/pearjelly/cliany.site/compare/v0.16.142...v0.16.143
[0.16.142]: https://github.com/pearjelly/cliany.site/compare/v0.16.141...v0.16.142
[0.16.141]: https://github.com/pearjelly/cliany.site/compare/v0.16.140...v0.16.141
[0.16.140]: https://github.com/pearjelly/cliany.site/compare/v0.16.139...v0.16.140
[0.16.139]: https://github.com/pearjelly/cliany.site/compare/v0.16.138...v0.16.139
[0.16.138]: https://github.com/pearjelly/cliany.site/compare/v0.16.137...v0.16.138
[0.16.137]: https://github.com/pearjelly/cliany.site/compare/v0.16.136...v0.16.137
[0.16.136]: https://github.com/pearjelly/cliany.site/compare/v0.16.135...v0.16.136
[0.16.135]: https://github.com/pearjelly/cliany.site/compare/v0.16.134...v0.16.135
[0.16.134]: https://github.com/pearjelly/cliany.site/compare/v0.16.133...v0.16.134
[0.16.133]: https://github.com/pearjelly/cliany.site/compare/v0.16.132...v0.16.133
[0.16.132]: https://github.com/pearjelly/cliany.site/compare/v0.16.131...v0.16.132
[0.16.131]: https://github.com/pearjelly/cliany.site/compare/v0.16.130...v0.16.131
[0.16.130]: https://github.com/pearjelly/cliany.site/compare/v0.16.129...v0.16.130
[0.16.129]: https://github.com/pearjelly/cliany.site/compare/v0.16.128...v0.16.129
[0.16.128]: https://github.com/pearjelly/cliany.site/compare/v0.16.127...v0.16.128
[0.16.127]: https://github.com/pearjelly/cliany.site/compare/v0.16.126...v0.16.127
[0.16.126]: https://github.com/pearjelly/cliany.site/compare/v0.16.125...v0.16.126
[0.16.125]: https://github.com/pearjelly/cliany.site/compare/v0.16.124...v0.16.125
[0.16.124]: https://github.com/pearjelly/cliany.site/compare/v0.16.123...v0.16.124
[0.16.123]: https://github.com/pearjelly/cliany.site/compare/v0.16.122...v0.16.123
[0.16.122]: https://github.com/pearjelly/cliany.site/compare/v0.16.121...v0.16.122
[0.16.121]: https://github.com/pearjelly/cliany.site/compare/v0.16.120...v0.16.121
[0.16.120]: https://github.com/pearjelly/cliany.site/compare/v0.16.119...v0.16.120
[0.16.119]: https://github.com/pearjelly/cliany.site/compare/v0.16.118...v0.16.119
[0.16.118]: https://github.com/pearjelly/cliany.site/compare/v0.16.117...v0.16.118
[0.16.117]: https://github.com/pearjelly/cliany.site/compare/v0.16.116...v0.16.117
[0.16.116]: https://github.com/pearjelly/cliany.site/compare/v0.16.115...v0.16.116
[0.16.115]: https://github.com/pearjelly/cliany.site/compare/v0.16.114...v0.16.115
[0.16.114]: https://github.com/pearjelly/cliany.site/compare/v0.16.113...v0.16.114
[0.16.113]: https://github.com/pearjelly/cliany.site/compare/v0.16.112...v0.16.113
[0.16.112]: https://github.com/pearjelly/cliany.site/compare/v0.16.111...v0.16.112
[0.16.111]: https://github.com/pearjelly/cliany.site/compare/v0.16.110...v0.16.111
[0.16.110]: https://github.com/pearjelly/cliany.site/compare/v0.16.109...v0.16.110
[0.16.109]: https://github.com/pearjelly/cliany.site/compare/v0.16.108...v0.16.109
[0.16.108]: https://github.com/pearjelly/cliany.site/compare/v0.16.107...v0.16.108
[0.16.107]: https://github.com/pearjelly/cliany.site/compare/v0.16.106...v0.16.107
[0.16.106]: https://github.com/pearjelly/cliany.site/compare/v0.16.105...v0.16.106
[0.16.105]: https://github.com/pearjelly/cliany.site/compare/v0.16.104...v0.16.105
[0.16.104]: https://github.com/pearjelly/cliany.site/compare/v0.16.103...v0.16.104
[0.16.103]: https://github.com/pearjelly/cliany.site/compare/v0.16.102...v0.16.103
[0.16.102]: https://github.com/pearjelly/cliany.site/compare/v0.16.101...v0.16.102
[0.16.101]: https://github.com/pearjelly/cliany.site/compare/v0.16.100...v0.16.101
[0.16.100]: https://github.com/pearjelly/cliany.site/compare/v0.16.99...v0.16.100
[0.16.99]: https://github.com/pearjelly/cliany.site/compare/v0.16.98...v0.16.99
[0.16.98]: https://github.com/pearjelly/cliany.site/compare/v0.16.97...v0.16.98
[0.16.97]: https://github.com/pearjelly/cliany.site/compare/v0.16.96...v0.16.97
[0.16.96]: https://github.com/pearjelly/cliany.site/compare/v0.16.95...v0.16.96
[0.16.95]: https://github.com/pearjelly/cliany.site/compare/v0.16.94...v0.16.95
[0.16.94]: https://github.com/pearjelly/cliany.site/compare/v0.16.93...v0.16.94
[0.16.93]: https://github.com/pearjelly/cliany.site/compare/v0.16.92...v0.16.93
[0.16.92]: https://github.com/pearjelly/cliany.site/compare/v0.16.91...v0.16.92
[0.16.91]: https://github.com/pearjelly/cliany.site/compare/v0.16.90...v0.16.91
[0.16.90]: https://github.com/pearjelly/cliany.site/compare/v0.16.89...v0.16.90
[0.16.89]: https://github.com/pearjelly/cliany.site/compare/v0.16.88...v0.16.89
[0.16.88]: https://github.com/pearjelly/cliany.site/compare/v0.16.87...v0.16.88
[0.16.87]: https://github.com/pearjelly/cliany.site/compare/v0.16.86...v0.16.87
[0.16.86]: https://github.com/pearjelly/cliany.site/compare/v0.16.85...v0.16.86
[0.16.85]: https://github.com/pearjelly/cliany.site/compare/v0.16.84...v0.16.85
[0.16.84]: https://github.com/pearjelly/cliany.site/compare/v0.16.83...v0.16.84
[0.16.83]: https://github.com/pearjelly/cliany.site/compare/v0.16.82...v0.16.83
[0.16.82]: https://github.com/pearjelly/cliany.site/compare/v0.16.81...v0.16.82
[0.16.81]: https://github.com/pearjelly/cliany.site/compare/v0.16.80...v0.16.81
[0.16.80]: https://github.com/pearjelly/cliany.site/compare/v0.16.79...v0.16.80
[0.16.79]: https://github.com/pearjelly/cliany.site/compare/v0.16.78...v0.16.79
[0.16.78]: https://github.com/pearjelly/cliany.site/compare/v0.16.77...v0.16.78
[0.16.77]: https://github.com/pearjelly/cliany.site/compare/v0.16.76...v0.16.77
[0.16.76]: https://github.com/pearjelly/cliany.site/compare/v0.16.75...v0.16.76
[0.16.75]: https://github.com/pearjelly/cliany.site/compare/v0.16.74...v0.16.75
[0.16.74]: https://github.com/pearjelly/cliany.site/compare/v0.16.73...v0.16.74
[0.16.73]: https://github.com/pearjelly/cliany.site/compare/v0.16.72...v0.16.73
[0.16.72]: https://github.com/pearjelly/cliany.site/compare/v0.16.71...v0.16.72
[0.16.71]: https://github.com/pearjelly/cliany.site/compare/v0.16.70...v0.16.71
[0.16.70]: https://github.com/pearjelly/cliany.site/compare/v0.16.69...v0.16.70
[0.16.69]: https://github.com/pearjelly/cliany.site/compare/v0.16.68...v0.16.69
[0.16.68]: https://github.com/pearjelly/cliany.site/compare/v0.16.67...v0.16.68
[0.16.67]: https://github.com/pearjelly/cliany.site/compare/v0.16.66...v0.16.67
[0.16.66]: https://github.com/pearjelly/cliany.site/compare/v0.16.65...v0.16.66
[0.16.65]: https://github.com/pearjelly/cliany.site/compare/v0.16.64...v0.16.65
[0.16.64]: https://github.com/pearjelly/cliany.site/compare/v0.16.63...v0.16.64
[0.16.63]: https://github.com/pearjelly/cliany.site/compare/v0.16.62...v0.16.63
[0.16.62]: https://github.com/pearjelly/cliany.site/compare/v0.16.61...v0.16.62
[0.16.61]: https://github.com/pearjelly/cliany.site/compare/v0.16.60...v0.16.61
[0.16.60]: https://github.com/pearjelly/cliany.site/compare/v0.16.59...v0.16.60
[0.16.59]: https://github.com/pearjelly/cliany.site/compare/v0.16.58...v0.16.59
[0.16.58]: https://github.com/pearjelly/cliany.site/compare/v0.16.57...v0.16.58
[0.16.57]: https://github.com/pearjelly/cliany.site/compare/v0.16.56...v0.16.57
[0.16.56]: https://github.com/pearjelly/cliany.site/compare/v0.16.55...v0.16.56
[0.16.55]: https://github.com/pearjelly/cliany.site/compare/v0.16.54...v0.16.55
[0.16.54]: https://github.com/pearjelly/cliany.site/compare/v0.16.53...v0.16.54
[0.16.53]: https://github.com/pearjelly/cliany.site/compare/v0.16.52...v0.16.53
[0.16.52]: https://github.com/pearjelly/cliany.site/compare/v0.16.51...v0.16.52
[0.16.51]: https://github.com/pearjelly/cliany.site/compare/v0.16.50...v0.16.51
[0.16.50]: https://github.com/pearjelly/cliany.site/compare/v0.16.49...v0.16.50
[0.16.49]: https://github.com/pearjelly/cliany.site/compare/v0.16.48...v0.16.49
[0.16.48]: https://github.com/pearjelly/cliany.site/compare/v0.16.47...v0.16.48
[0.16.47]: https://github.com/pearjelly/cliany.site/compare/v0.16.46...v0.16.47
[0.16.46]: https://github.com/pearjelly/cliany.site/compare/v0.16.45...v0.16.46
[0.16.45]: https://github.com/pearjelly/cliany.site/compare/v0.16.44...v0.16.45
[0.16.44]: https://github.com/pearjelly/cliany.site/compare/v0.16.43...v0.16.44
[0.16.43]: https://github.com/pearjelly/cliany.site/compare/v0.16.42...v0.16.43
[0.16.42]: https://github.com/pearjelly/cliany.site/compare/v0.16.41...v0.16.42
[0.16.41]: https://github.com/pearjelly/cliany.site/compare/v0.16.40...v0.16.41
[0.16.40]: https://github.com/pearjelly/cliany.site/compare/v0.16.39...v0.16.40
[0.16.39]: https://github.com/pearjelly/cliany.site/compare/v0.16.38...v0.16.39
[0.16.38]: https://github.com/pearjelly/cliany.site/compare/v0.16.37...v0.16.38
[0.16.37]: https://github.com/pearjelly/cliany.site/compare/v0.16.36...v0.16.37
[0.16.36]: https://github.com/pearjelly/cliany.site/compare/v0.16.35...v0.16.36
[0.16.35]: https://github.com/pearjelly/cliany.site/compare/v0.16.34...v0.16.35
[0.16.34]: https://github.com/pearjelly/cliany.site/compare/v0.16.33...v0.16.34
[0.16.33]: https://github.com/pearjelly/cliany.site/compare/v0.16.32...v0.16.33
[0.16.32]: https://github.com/pearjelly/cliany.site/compare/v0.16.31...v0.16.32
[0.16.31]: https://github.com/pearjelly/cliany.site/compare/v0.16.30...v0.16.31
[0.16.30]: https://github.com/pearjelly/cliany.site/compare/v0.16.29...v0.16.30
[0.16.29]: https://github.com/pearjelly/cliany.site/compare/v0.16.28...v0.16.29
[0.16.28]: https://github.com/pearjelly/cliany.site/compare/v0.16.27...v0.16.28
[0.16.27]: https://github.com/pearjelly/cliany.site/compare/v0.16.26...v0.16.27
[0.16.26]: https://github.com/pearjelly/cliany.site/compare/v0.16.25...v0.16.26
[0.16.25]: https://github.com/pearjelly/cliany.site/compare/v0.16.24...v0.16.25
[0.16.24]: https://github.com/pearjelly/cliany.site/compare/v0.16.23...v0.16.24
[0.16.23]: https://github.com/pearjelly/cliany.site/compare/v0.16.22...v0.16.23
[0.16.22]: https://github.com/pearjelly/cliany.site/compare/v0.16.21...v0.16.22
[0.16.21]: https://github.com/pearjelly/cliany.site/compare/v0.16.20...v0.16.21
[0.16.20]: https://github.com/pearjelly/cliany.site/compare/v0.16.19...v0.16.20
[0.16.19]: https://github.com/pearjelly/cliany.site/compare/v0.16.18...v0.16.19
[0.16.18]: https://github.com/pearjelly/cliany.site/compare/v0.16.17...v0.16.18
[0.16.17]: https://github.com/pearjelly/cliany.site/compare/v0.16.16...v0.16.17
[0.16.16]: https://github.com/pearjelly/cliany.site/compare/v0.16.15...v0.16.16
[0.16.15]: https://github.com/pearjelly/cliany.site/compare/v0.16.14...v0.16.15
[0.16.14]: https://github.com/pearjelly/cliany.site/compare/v0.16.13...v0.16.14
[0.16.13]: https://github.com/pearjelly/cliany.site/compare/v0.16.12...v0.16.13
[0.16.12]: https://github.com/pearjelly/cliany.site/compare/v0.16.11...v0.16.12
[0.16.11]: https://github.com/pearjelly/cliany.site/compare/v0.16.10...v0.16.11
[0.16.10]: https://github.com/pearjelly/cliany.site/compare/v0.16.9...v0.16.10
[0.16.9]: https://github.com/pearjelly/cliany.site/compare/v0.16.8...v0.16.9
[0.16.8]: https://github.com/pearjelly/cliany.site/compare/v0.16.7...v0.16.8
[0.16.7]: https://github.com/pearjelly/cliany.site/compare/v0.16.6...v0.16.7
[0.16.6]: https://github.com/pearjelly/cliany.site/compare/v0.16.5...v0.16.6
[0.16.5]: https://github.com/pearjelly/cliany.site/compare/v0.16.4...v0.16.5
[0.16.4]: https://github.com/pearjelly/cliany.site/compare/v0.16.3...v0.16.4
[0.16.3]: https://github.com/pearjelly/cliany.site/compare/v0.16.2...v0.16.3
[0.16.2]: https://github.com/pearjelly/cliany.site/compare/v0.16.1...v0.16.2
[0.16.1]: https://github.com/pearjelly/cliany.site/compare/v0.16.0...v0.16.1
[0.16.0]: https://github.com/pearjelly/cliany.site/compare/v0.15.9...v0.16.0
[0.15.9]: https://github.com/pearjelly/cliany.site/compare/v0.15.8...v0.15.9
[0.15.8]: https://github.com/pearjelly/cliany.site/compare/v0.15.7...v0.15.8
[0.15.7]: https://github.com/pearjelly/cliany.site/compare/v0.15.6...v0.15.7
[0.15.6]: https://github.com/pearjelly/cliany.site/compare/v0.15.5...v0.15.6
[0.15.5]: https://github.com/pearjelly/cliany.site/compare/v0.15.4...v0.15.5
[0.15.4]: https://github.com/pearjelly/cliany.site/compare/v0.15.3...v0.15.4
[0.15.3]: https://github.com/pearjelly/cliany.site/compare/v0.15.2...v0.15.3
[0.15.2]: https://github.com/pearjelly/cliany.site/compare/v0.15.1...v0.15.2
[0.15.1]: https://github.com/pearjelly/cliany.site/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/pearjelly/cliany.site/compare/v0.14.4...v0.15.0
[0.14.4]: https://github.com/pearjelly/cliany.site/compare/v0.14.3...v0.14.4
[0.11.0]: https://github.com/pearjelly/cliany.site/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/pearjelly/cliany.site/compare/v0.9.3...v0.10.0
