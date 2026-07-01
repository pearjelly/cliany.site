# 每周维护者循环

**适用范围：** v0.14.4 之后的持续迭代  
**目标：** 把路线图、真实案例、发布门禁和提交节奏变成每周可重复执行的维护动作。

这份文档不是新的路线图，而是维护者每周选择下一版最小可交付内容时的操作顺序。路线图回答“往哪里走”，本循环回答“本周先做哪一小块、如何证明它值得发布”。

## 1. 周初：选一个可发布主题

从 [Q3 路线图](roadmap-2026-q3.md) 的五条主线里选一个主题，并把目标压缩成一个 patch 或 minor 能交付的结果：

| 主线 | 本周最小切片示例 | 必备证据 |
|------|------------------|----------|
| 新用户可用性 | 缩短 quickstart、改进 `doctor` action、补官网入口 | README/官网/doctor 测试 |
| 真实案例库 | 新增或修正一个公开只读案例、补离线样例 | `scripts/validate_cases.py --strict` |
| adapter 生命周期 | 补包格式、安装、回滚或 verify 说明 | lifecycle 文档或安装/verify 测试 |
| 贡献者闭环 | 改 issue/PR 模板、复现指南、good-first-issue 路径 | 文档测试或模板校验 |
| 运行可靠性 | 收敛一个错误码、抽取质量或 replay 诊断 | 针对性单测 + 错误语义说明 |

周初先运行：

```bash
python scripts/plan_next_iteration.py --json
python scripts/plan_next_iteration.py --report /tmp/cliany-next-iteration.md
python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues
python scripts/plan_next_iteration.py --packages-dir ~/.cliany-site/packages --require-packages --json
python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --include-candidate-packages --strict
python scripts/release_readiness.py --json
python scripts/release_readiness.py --report /tmp/cliany-release-readiness.md
```

正式检查 demo adapter 包资产时，把同一组 `--packages-dir ~/.cliany-site/packages --require-packages` 参数传给 `plan_next_iteration.py`；计划器会把这些参数透传给 release readiness，并写入 validation commands 和 issue artifacts 复现命令。
需要给 candidate 案例补 adapter package evidence 时，再运行 `python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --include-candidate-packages --strict`，它会按 `adapter_domain-<version>.cliany-adapter.tar.gz` 约定校验候选包，而不改变默认 release gate 的 candidate 包检查范围。

`plan_next_iteration.py` 会把 release readiness、publication audit、commit cadence 和 candidate cases 汇总成一个推荐切片；如果它提示最新本地 tag 尚未公开可见，先完成发布同步，再扩大下一版范围。计划 JSON、文本输出和 Markdown report 会带上 `publication_visibility`，用 `published`、`local_only`、`dirty_worktree`、`tag_not_visible` 或 `needs_remote_check` 给出一眼可读的发布可见性结论和 summary；`check_release_publication.py --json` / `--report` 还会输出 `tag_publish_decision`，用 `manual_decision_required`、`ready_to_push`、`published`、`blocked_by_worktree`、`missing_tag` 或 `needs_remote_check` 说明 tag 是否可推、是否需要人工选择和对应 `required_action`；也会带上 `candidate_issue_gate`，用 `blocked_by_publication`、`review_required` 或 `ready` 说明当前是否 `can_create_issues`、是否 `requires_maintainer_review`，并把 `reason_codes`、`reason_descriptions`、`required_actions` 和 `evidence` 带给维护者和自动化；`reason_codes` 会用 `publication_not_published`、`dirty_worktree`、`local_release_only`、`tag_not_visible`、`needs_remote_check`、`release_draft_issues` 或 `release_readiness_blockers` 给脚本一个稳定原因层，`reason_descriptions` 会给这些原因码提供 human-readable 可读说明；`evidence` 会保留 `publication_ok`、`publication_visibility_status`、`publication_worktree_clean`、`publication_remote_checked`、`publication_branch`、`publication_latest_tag`、`publication_ahead_count`、`release_draft_ok`、`release_draft_path` 和 `release_draft_issue_count`，并在存在非草案类 release readiness blocker 时追加 `release_readiness_blocker_count`、`release_readiness_primary_blocker` 和 `release_readiness_blockers_sha256`，让工具能审计 gate 结论来自哪些输入；也会带上 `publication_next_actions`，直接列出 publication audit 的具体待办，例如本地分支 ahead 数、tag 尚未发布和是否需要 `--remote` 复核；也会带上 `publication_ref_context`，把 repo root、branch、latest tag、local HEAD、tag commit 和 remote check 状态带到周初计划里；也会带上 `publication_worktree_clean` / `publication_worktree_status`，把 worktree 是否干净和具体 status 行带到周初计划里；也会带上 `publication_publish_commands`，把 publication audit 里的 branch/tag push 和 `python scripts/check_release_publication.py --remote --json` 复核命令直接带到周初计划里；`publication_publish_script_path` 会结构化给出可审阅发布脚本的默认输出路径，`publication_publish_script_path_sha256` 会给出该路径的稳定摘要，`publication_publish_script_command` 还会给出 `--publish-script /tmp/cliany-publish-release.sh` 生成命令，`publication_publish_script_command_sha256` 会给出该命令的稳定摘要，方便维护者先审阅脚本再手动执行；生成脚本的注释头会展示 next/publish 的 count、SHA-256 和 primary 字段，让维护者执行前确认脚本对应的发布动作集；脚本执行前还会重新运行 publication audit，并在 next/publish hash 漂移时退出，避免继续执行过期发布命令。计划 JSON、文本输出和 Markdown report 也会带上 `release_draft_issues`，把下一版 release draft 缺失或 snippet 校验失败的具体原因直接列出来，避免只看到笼统的 `release draft validation failed`。它还会带上 `case_promotion_evidence_summary`，在周初计划里直接展示 candidate 晋级任务的 `candidate_count`、`task_count`、`pending_count`、`blocked_count`、`complete_count`、`primary_next_action` 和任务明细，维护者不必另跑 `validate_cases.py --report` 也能看到本周最小证据动作。它的 Markdown 报告会输出 `Candidate Issue Gate`、`Candidate Issue Gate Reason Codes`、`Candidate Issue Gate Reason Descriptions`、`Candidate Issue Gate Evidence`、`Candidate Promotion Evidence Summary`、`Candidate Issue Metadata` 和 `Candidate Promotion Tasks`，把能否创建候选 issue、该判断的稳定原因码、原因码可读说明、publication/release draft/release readiness 证据、每个 candidate 的 issue title、labels、priority rank/reason、`adapter_package`、`metadata_validation`、`online_smoke` 和 `promotion_evidence` 当前状态带到同一份周初计划里，并在 `Candidate Issue Body Templates` 里生成可复制的 GitHub issue body；每个 body 都包含 `Reproduction Context`，保留 target URL，并把 candidate commands、offline validation commands、当前 evidence 状态和下一步动作作为子列表列出。需要批量创建候选案例任务时，`--issues-dir` 会额外写出每个 candidate 的 body 文件、`artifact-manifest.json`、`issue-metadata.json`、`publication-handoff.json`、`release-draft-handoff.json`、`README.md` 和可审阅的 `create-issues.sh`，其中 `artifact-manifest.json` 会保留 target version、candidate count、candidate cases、`case_promotion_evidence_summary`、blockers、next actions、`next_action_count`、`primary_next_action`、`next_actions_sha256`、candidate issue gate、publication status、publication visibility、publication next actions、publication publish commands、publication publish script path、publication publish script path hash、publication publish script command hash、文件名、review order、validation commands、`create_issues_dry_run_command`、`create_issues_safety`、`issue_body_inventory`、`issue_body_summary` 和 `artifact_bundle_summary`，作为整个 artifacts 包的机器可读入口；`artifact_bundle_summary` 会汇总 target version、candidate/body/review item 数量、inventory hash、gate 状态和脚本安全布尔值，方便工具先判断是否需要展开完整 manifest；`issue_body_inventory` 会记录每个 body 的 case、文件名、byte_count 和 sha256，方便工具确认 body 文件没有漂移；`issue_body_summary` 会记录 body_count、total_byte_count 和 inventory_sha256，方便工具快速判断整批 body 是否变化；`issue-metadata.json` 会保留 issue title、labels、target URL、candidate commands、offline validation commands、`promotion_evidence`、`promotion_evidence_primary_task`、`evidence_bundle_primary_next_task`、`evidence_bundle_command`、`evidence_bundle_json_command`、body file name、body file path 和 create command，issue metadata summary 也会覆盖首要 evidence task、evidence bundle 首要下一步和这两条 evidence bundle 命令；artifacts `README.md` 会带 `Candidate Summary` 表，列出 case、issue body 文件、target URL、candidate/offline command 数量、priority rank/reason、`Primary Evidence Task`、`Evidence Bundle Primary Next Task`、`Evidence Bundle` 和 `Evidence Bundle JSON`，让维护者不用展开 JSON 也能看到首要 evidence task、排序原因、evidence bundle 首要下一步并直接复制证据包命令，也会带 `Candidate Promotion Evidence Summary` 表展示 candidate 晋级证据摘要，也会在 `Issue Body Inventory` 表展示每个 body 的字节数和 SHA-256，并在 `Issue Body Summary` 下展示 body_count、total_byte_count 和 inventory_sha256，还会在 `Artifact Bundle Summary` 下展示 target_version、candidate_count、body_count、review_item_count、candidate_issue_gate_status、can_create_issues、dry_run_supported 和 preflight_required，也会在 `Publication Handoff` 下展示 candidate issue gate、can_create_issues、gate summary、gate reason codes、gate reason descriptions、gate evidence latest tag、gate evidence ahead count、gate evidence worktree clean、gate evidence release draft ok、gate evidence release draft issues、visibility、visibility summary、`Publication Next Actions`、latest tag、local HEAD、`worktree_clean`、`publish_script_path` 和 `Publication Publish Script`，在 `Release Draft Handoff` 下展示 release draft path 和 release draft issues，并在 `Create Issues Safety` 下展示 `dry_run_supported`、`dry_run_env`、`dry_run_command`、`preflight_required`、`preflight_command` 和 `preflight_json`，在审阅清单里要求先确认这些 release draft issues 与 publication next actions 已处理或明确延后，再核对复现字段；`publication-handoff.json` 会保留 publication 状态、candidate issue gate、visibility、next actions、publication next actions、ref context、worktree status、publish commands 和 publish script path；`release-draft-handoff.json` 会保留 target version、release draft path 和 release draft issues，方便工具读取而不解析 README；脚本不会自动执行，正常执行前会先复跑 planner JSON 的 candidate issue gate preflight，把 preflight JSON 写入 `/tmp/cliany-issue-gate-check.json`，并检查 `candidate_issue_gate.can_create_issues`；如果 planner preflight 失败或 gate 不允许创建 issue，脚本会把这份 JSON 打印出来再退出；如果 gate 标记 `requires_maintainer_review` 但仍允许创建，则会打印首要 required action 后继续。维护者也可以用 `CLIANY_CREATE_ISSUES_DRY_RUN=1 ./create-issues.sh` 进入 dry-run mode，只打印 `gh issue create` 命令，不运行 candidate issue gate preflight，也不创建 issue。计划 JSON 里的 `issue_artifacts_command` 和 artifacts `README.md` 会保留复现命令，例如 `python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues`，方便维护者重新生成同一批候选 issue artifacts。Markdown 报告里的 `Weekly Review` 小节会把本页最后的 6 个复盘问题和当前证据放在一起；发版前优先引用这份报告，避免手工复盘和 readiness gate 脱节。

Candidate issue artifacts 的 review checklist 会要求维护者核对 `issue-metadata.json` 中的 `candidate_package_validation_command`，确保候选包验证命令和 target URL、candidate commands、offline validation commands 一起通过创建 issue 前的复核。

`cliany-site cases --case-id <id> --evidence-bundle --json`、candidate issue body 和 `issue-metadata.json` 也会输出 `promotion_command_plan`，把 candidate 晋级执行顺序拆成 `llm_live_preflight`、`adapter_package`、`metadata_validation`、`online_smoke` 四条命令；其中后三条仍是决定能否晋级 active 的真实证据。Evidence bundle 还会输出 `primary_next_task_runbook`，promotion plan 会输出 `primary_runbook`，把首要任务的 preflight、执行命令和验收证据排成可执行步骤；`plan_next_iteration.py --issues-dir` 生成的 `candidate_promotions`、`issue-metadata.json`、issue body 和 artifacts `README.md` 也会保留 `evidence_bundle_primary_next_task_runbook`。只读 evidence bundle、planner JSON 或 issue artifacts 的维护工具不必从自然语言 next action 推断该运行哪条命令，也不必猜测是否要先跑 live LLM preflight。

`scripts/validate_cases.py --json` 会用 `promotion_command_plan_summary` 汇总 candidate 晋级命令是否完整；`plan_next_iteration.py` 会把它透传为 `case_promotion_command_plan_summary`，并写入默认文本输出、Markdown report、candidate issue artifacts manifest 和 `artifact_bundle_summary` compact 字段。只读周计划或 artifacts 的维护工具可以直接展示 `all_declared`、`missing_command_count`、candidate count、command count 和 summary hash，先拦截缺少 live preflight、`explore` 或 adapter smoke 命令的 candidate。`artifact_bundle_summary` 中对应字段为 `case_promotion_command_plan_summary_sha256`、`case_promotion_command_plan_candidate_count`、`case_promotion_command_plan_command_count`、`case_promotion_command_plan_missing_command_count` 和 `case_promotion_command_plan_all_declared`。

`Candidate Issue Body Templates` 里的每个 body 还会包含 `Primary Evidence Task` 小节，直接展示当前首要待补 evidence task、状态、现有证据和下一步；已经 `complete` 且带 evidence 的 task 不会被选为首要待办。

`plan_next_iteration.py` 的默认文本输出会在 `candidate_promotions` 下展开 `evidence_bundle_primary_next_task`；Markdown report 的 `Candidate Issue Metadata` 表也会展示 `Priority Rank`、`Priority Reason` 和 `Evidence Bundle Primary Next Task`，不用生成 issue artifacts 也能看到候选排序原因和 evidence bundle 首要下一步。

`plan_next_iteration.py` 的顶层 JSON、默认文本输出和 Markdown report 也会展示 `case_promotion_evidence_primary_next_task`、`case_promotion_evidence_primary_next_action`、`case_promotion_evidence_summary_sha256` 和 `case_promotion_command_plan_summary_sha256`，让维护工具不用展开完整 `case_promotion_evidence_summary` 就能直接定位首要 candidate evidence 任务，并在不生成 issue artifacts 的情况下检测 candidate evidence / command plan 摘要是否漂移。

`plan_next_iteration.py` 还会输出 `plan_report_command`，默认给出 `python scripts/plan_next_iteration.py --target-version <version> --report /tmp/cliany-next-iteration.md`，让维护者和自动化能从 JSON 或默认文本直接复现同一份 Markdown 周计划报告。

`plan_next_iteration.py` 也会把 publication audit 的 `tag_publish_decision` 透传为 `publication_tag_publish_decision`，并同步写入 JSON、默认文本输出、Markdown report、`artifact-manifest.json`、`publication-handoff.json` 和 artifacts `README.md`。维护工具可以直接读取 `status`、`can_push_tag`、`latest_tag`、`tag_points_at_head`、`tag_published`、`required_action` 和 `target_tag_release_gate_status`，无需重新解析 `publication_ref_context` 或自然语言 next action；当周计划仍有 readiness blocker 时，`target_tag_release_gate_status=blocked_by_readiness`，`target_tag_release_gate_blockers_sha256` 可用于检测 blocker 列表是否漂移。`commit days N/3` 只作为周节奏提醒保留在 cadence next actions，不再单独让目标 tag gate 进入 `blocked_by_readiness`。

当 candidate issue gate 因非草案类 release readiness blocker（例如 projected daily release cap）进入 `release_readiness_blockers` 时，`publication-handoff.json` 顶层会同步提供 `release_readiness_blocker_count`、`release_readiness_primary_blocker` 和 `release_readiness_blockers_sha256`，artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 也会展示同一组字段。只读 handoff 或 README 顶部摘要的维护工具可以直接解释目标 tag 为什么暂停，而不必展开嵌套的 gate evidence。

`plan_next_iteration.py` 还会输出结构化 `commit_cadence`，保留 `status`、`commit_days`、`commit_day_count`、`min_commit_days`、`missing_commit_days`、`next_actions` 和 `summary`。Markdown report 会在指标表展示 `commit_cadence_status`、`commit_cadence_missing_commit_days` 和 `commit_cadence_summary`；candidate issue artifacts 的 `artifact-manifest.json` 会保留完整 `commit_cadence`，`publication-handoff.json` 和 artifacts `README.md` 的 `Publication Handoff` 会展示 `commit_cadence_status`、`commit_cadence_missing_commit_days` 和 `commit_cadence_primary_next_action`，artifacts `README.md` 还会单独输出 `Commit Cadence` 小节和 `Commit Cadence Next Actions`，`artifact_bundle_summary` 会展示 `commit_cadence_commit_day_count`、`commit_cadence_min_commit_days`、`commit_cadence_missing_commit_days`、`commit_cadence_next_action_count`、`commit_cadence_primary_next_action`、`commit_cadence_commit_days_sha256` 和 `commit_cadence_next_actions_sha256`。只读计划摘要、handoff 或 README 的维护者可以直接判断本周还差几个独立提交日。

`artifact_bundle_summary` 也会输出 `publication_tag_publish_decision_key_count`、`publication_tag_publish_decision_sha256`、key preview/tail/boundary hash、`publication_tag_publish_decision_status`、`publication_tag_can_push`、`publication_tag_required_action_sha256` 和 `publication_target_tag_release_gate_*` 摘要字段。只读取整包摘要的维护工具可以先展示 tag 是否可推、是否需要人工决策、目标 tag 是否仍被 readiness blocker 挡住，并检测 `publication_tag_publish_decision` 对象是否漂移。

`candidate_issue_gate.evidence` 也会带上 `publication_tag_decision_status`、`publication_tag_can_push` 和 `publication_tag_required_action`，artifacts `README.md` 的 `Publication Handoff` 会展示 `gate_evidence_tag_decision`、`gate_evidence_tag_can_push` 和 `gate_evidence_tag_required_action`。只读取 candidate gate 的工具可以直接解释为什么当前不能创建候选 issue。

`plan_next_iteration.py` 的 JSON、默认文本输出和 Markdown report 会展示 `publication_next_action_count`、`publication_next_actions_sha256`、`publication_primary_next_action`、`publication_publish_command_count`、`publication_publish_commands_sha256`、`publication_primary_publish_command`、`publication_publish_script_path`、`publication_publish_script_path_sha256`、`publication_publish_script_command` 与 `publication_publish_script_command_sha256`，让维护者在周初计划里先判断发布待办规模、首要发布动作、首条发布命令、列表是否漂移，并直接看到可审阅发布脚本的路径、路径摘要、生成命令和命令摘要，再展开 publication next actions 和 publish commands；如果 planner 使用 `--remote` / `--remote-name` 运行，发布脚本生成命令也会保留同一组 remote audit 参数。

`release_readiness.py --json` 和 `--report` 也会输出 `publication_summary` 与 `publication_summary_sha256`。维护者优先看 `publication_summary.status`、`publication_summary.worktree_clean`、`publication_summary.ahead_count`、`publication_summary.latest_tag`、`publication_summary.target_tag`、`publication_summary.target_tag_status`、`publication_summary.target_tag_release_gate_status`、`publication_summary.target_tag_release_gate_blocker_count`、`publication_summary.target_tag_primary_command`、`publication_summary.primary_next_action` 和 `publication_summary.primary_publish_command`，就能判断当前是 `published` 还是 `blocked`，本地 worktree 是否挡住发布，目标 release tag 是什么，目标 tag 是否仍 `blocked_by_readiness`，以及第一条该执行的发布动作和发布命令；只读发版预检 artifact 的工具也可以直接读取顶层别名 `publication_summary_primary_next_action` 与 `publication_summary_primary_publish_command`，再用 `publication_summary_sha256`、`publication_next_actions_sha256`、`publication_publish_commands_sha256`、`target_tag_commands_sha256` 和 `target_tag_release_gate_blockers_sha256` 检测这组摘要、发布待办列表、发布命令列表、目标 tag 命令和 readiness blocker 列表是否漂移，按需展开 `publication_ref_context`、`publication_next_actions`、`publication_publish_commands`、`publication_tag_publish_decision.target_tag_commands` 或 `publication_tag_publish_decision.target_tag_release_gate_blockers`。

提交后进入发布流程时，维护者先读取 `release_readiness.py --json` 或 Markdown report 中的 `standard_release_flow`、`standard_release_flow_status`、`standard_release_flow_primary_next_action`、`standard_release_flow_commands_sha256` 和 `standard_release_flow_sha256`。这组字段把标准发版动作压缩成可审阅步骤：严格 release readiness、整理 `CHANGELOG.md`、更新 `pyproject.toml`、离线验证、推送分支、创建/推送目标 tag，以及 `python scripts/check_release_publication.py --remote --json` 远端复核；如果使用自定义 `--remote-name`，strict readiness 和远端复核命令都会保留它。如果 status 仍是 `blocked`，先执行 primary next action，不要跳过 gate 直接 tag。

`plan_next_iteration.py` 也会透传同一组 `standard_release_flow*` 字段到 JSON、默认文本输出和 Markdown report。当 release readiness 已经给出 `standard_release_flow.primary_next_action` 且 publication 仍未通过时，周计划的顶层 `next_actions[0]` 会先采用这条标准流程首要动作，再展示目标 release tag 动作；维护者可以把周初计划和提交后的 release readiness 报告放在一起核对，确认两边没有把目标 tag 命令提前到 release gate 之前。

使用 `--issues-dir` 生成候选任务交接包时，`artifact-manifest.json`、`publication-handoff.json`、artifacts `README.md` 的 `Publication Handoff` 和 `artifact_bundle_summary` 也会展示 standard release flow 摘要，包括 `standard_release_flow_status`、`standard_release_flow_primary_next_action`、`standard_release_flow_command_count`、`standard_release_flow_commands_sha256` 和 `standard_release_flow_sha256`。只读 artifacts 的维护工具可以不展开 release readiness report，也能先判断标准发版 gate 是否仍是 `blocked`。

`release_readiness.py --report` 会在 JSON 和 Markdown report 中输出 `release_mode` / `release_tag`；只有显式 `--release-tag` 的 tagged preflight 通过后，`Weekly Review` 才会把下一步显示为发布已验证 tag。普通 `--target-version` readiness 即使版本和 tag 已匹配，也仍提示准备打 tag，避免目标版本自检和 tag 发布前自检互相混淆。

发布 workflow 完成后，用 `python scripts/check_release_publication.py --remote --distribution --json` 做最终公开渠道审计。`--remote` 证明 branch/tag refs 已经公开，`--distribution` 额外读取 GitHub Release latest tag 和 PyPI latest version；自动化优先看 `distribution_ok`、`distribution.github_release_tag`、`distribution.pypi_version` 和 `distribution.next_actions_sha256`，确保标准发版流程不只停在 git tag 可见，而是真的完成 GitHub Release 与 PyPI 发布。

`artifact_bundle_summary` 会带上 `artifact_bundle_summary_key_count` 和 `artifact_bundle_summary_keys_sha256`，让工具只读整包摘要就能判断 summary 自身字段规模和字段清单是否漂移。

`artifact_bundle_summary` 也会带上 `artifact_bundle_summary_key_preview_count`、`artifact_bundle_summary_key_preview` 和 `artifact_bundle_summary_key_preview_sha256`，让工具只读整包摘要就能先检查 summary 前几个关键字段的顺序与内容，再决定是否展开完整字段清单。

`artifact_bundle_summary` 还会带上 `artifact_bundle_summary_key_tail_count`、`artifact_bundle_summary_key_tail` 和 `artifact_bundle_summary_key_tail_sha256`，让工具只读整包摘要就能检查 summary 末尾字段的顺序与内容，避免只看前缀时遗漏尾部字段漂移。

`artifact_bundle_summary` 还会带上 `artifact_bundle_summary_first_key`、`artifact_bundle_summary_last_key` 和 `artifact_bundle_summary_key_boundary_sha256`，让工具不展开完整字段清单也能先确认 summary 首尾字段边界是否符合预期。

`artifact_bundle_summary` 也会带上 `artifact_manifest_first_key`、`artifact_manifest_last_key` 和 `artifact_manifest_key_boundary_sha256`，让工具只读整包摘要就能确认 `artifact-manifest.json` 顶层字段清单首尾边界是否符合预期。

`artifact_bundle_summary` 还会带上 `artifact_manifest_key_preview_count`、`artifact_manifest_key_preview` 和 `artifact_manifest_key_preview_sha256`，让工具只读整包摘要就能检查 `artifact-manifest.json` 顶层字段清单前几个关键字段的顺序与内容。

`artifact_bundle_summary` 也会带上 `artifact_manifest_key_tail_count`、`artifact_manifest_key_tail` 和 `artifact_manifest_key_tail_sha256`，让工具只读整包摘要就能检查 `artifact-manifest.json` 顶层字段清单末尾字段的顺序与内容。

`artifact_bundle_summary.review_order_sha256` 会对 `review_order` 做稳定 SHA-256 摘要；artifacts `README.md` 的 `Artifact Bundle Summary` 也会展示 `review_order_sha256`，让工具能先检查 review order hash，再决定是否展开完整 manifest。

`artifact_bundle_summary` 还会带上 `review_order_first_item`、`review_order_last_item` 和 `review_order_boundary_sha256`，让工具只读整包摘要就能确认审阅顺序首尾边界是否符合预期。

`artifact_bundle_summary` 还会带上 `review_order_preview_count`、`review_order_preview` 和 `review_order_preview_sha256`，让工具只读整包摘要就能看到审阅顺序入口，并判断 review order preview 是否漂移。

`artifact_bundle_summary` 也会带上 `review_order_tail_count`、`review_order_tail` 和 `review_order_tail_sha256`，让工具只读整包摘要就能检查审阅顺序末尾入口，并判断 review order tail 是否漂移。

`artifact_bundle_summary` 还会带上 `artifact_manifest_schema_version`、`artifact_manifest_key_count` 和 `artifact_manifest_keys_sha256`，让工具只读整包摘要就能判断 `artifact-manifest.json` 的字段语义版本、顶层字段规模和字段清单是否漂移，再决定是否展开完整 manifest。

`artifact_bundle_summary` 也会带上 `artifact_manifest_payload_key_count` 和 `artifact_manifest_payload_sha256`，让工具只读整包摘要就能判断除 summary 自身之外的 manifest payload 是否漂移，避免递归 hash。

`artifact_bundle_summary` 还会带上 `artifact_manifest_payload_first_key`、`artifact_manifest_payload_last_key` 和 `artifact_manifest_payload_key_boundary_sha256`，让工具不展开完整字段清单也能先确认除 summary 自身之外的 manifest payload 首尾字段边界是否符合预期。

`artifact_bundle_summary` 还会带上 `artifact_manifest_payload_key_preview_count`、`artifact_manifest_payload_key_preview` 和 `artifact_manifest_payload_key_preview_sha256`，让工具只读整包摘要就能检查除 summary 自身之外的 manifest payload 前几个字段的顺序与内容。

`artifact_bundle_summary` 也会带上 `artifact_manifest_payload_key_tail_count`、`artifact_manifest_payload_key_tail` 和 `artifact_manifest_payload_key_tail_sha256`，让工具只读整包摘要就能检查除 summary 自身之外的 manifest payload 末尾字段的顺序与内容。

`artifact_bundle_summary` 也会带上 `candidate_cases_sha256`，让工具只读整包摘要就能判断 candidate case 列表是否漂移。

`artifact_bundle_summary` 还会带上 `candidate_cases_first_case`、`candidate_cases_last_case` 和 `candidate_cases_boundary_sha256`，让工具只读整包摘要就能确认 candidate case 列表首尾边界是否符合预期。

`artifact_bundle_summary` 还会带上 `candidate_cases_preview_count`、`candidate_cases_preview` 和 `candidate_cases_preview_sha256`，让工具只读整包摘要就能看到 candidate case 列表入口，并判断 preview 是否漂移。

`artifact_bundle_summary` 也会带上 `candidate_cases_tail_count`、`candidate_cases_tail` 和 `candidate_cases_tail_sha256`，让工具只读整包摘要就能检查 candidate case 列表末尾入口，并判断 tail 是否漂移。

`artifact_bundle_summary` 还会带上 `case_promotion_evidence_summary_key_count`、`case_promotion_evidence_summary_keys_sha256`、`case_promotion_evidence_summary_first_key`、`case_promotion_evidence_summary_last_key`、`case_promotion_evidence_summary_key_boundary_sha256`、`case_promotion_evidence_summary_key_preview_count`、`case_promotion_evidence_summary_key_preview`、`case_promotion_evidence_summary_key_preview_sha256`、`case_promotion_evidence_summary_key_tail_count`、`case_promotion_evidence_summary_key_tail`、`case_promotion_evidence_summary_key_tail_sha256` 和 `case_promotion_evidence_summary_sha256`，让工具只读整包摘要就能判断 candidate 晋级证据摘要的字段集合和内容是否漂移。

`artifact_bundle_summary` 也会带上 `case_promotion_evidence_candidate_count`、`case_promotion_evidence_task_count`、`case_promotion_evidence_pending_count`、`case_promotion_evidence_blocked_count`、`case_promotion_evidence_complete_count`、`case_promotion_evidence_primary_next_action`、`case_promotion_evidence_primary_case_id`、`case_promotion_evidence_primary_task`、`case_promotion_evidence_primary_status`、`case_promotion_evidence_primary_evidence_sha256`、`case_promotion_evidence_primary_detail_sha256` 和 `case_promotion_evidence_primary_next_task_sha256`，让只读整包摘要的维护工具能展示 candidate 晋级证据规模、首要动作、对应 case/task/status、当前证据 hash、首要任务对象 hash 和 `primary_next_task` hash，而不必展开完整 task 明细。

`artifact_bundle_summary` 还会带上 `issue_body_inventory_preview_count`、`issue_body_inventory_preview` 和 `issue_body_inventory_preview_sha256`，让工具只读整包摘要就能看到 issue body inventory 入口，并判断 inventory preview 是否漂移。

`artifact_bundle_summary` 还会带上 `issue_body_inventory_first_entry`、`issue_body_inventory_last_entry` 和 `issue_body_inventory_boundary_sha256`，让工具只读整包摘要就能确认 issue body inventory 首尾边界是否符合预期。

`artifact_bundle_summary` 也会带上 `issue_body_inventory_tail_count`、`issue_body_inventory_tail` 和 `issue_body_inventory_tail_sha256`，让工具只读整包摘要就能检查 issue body inventory 末尾入口，并判断 inventory tail 是否漂移。

`artifact_bundle_summary` 还会带上 `issue_body_summary_key_count` 和 `issue_body_summary_keys_sha256`，让工具只读整包摘要就能检查 issue body summary 的字段集合是否漂移。

`artifact_bundle_summary` 还会带上 `issue_body_summary_first_key`、`issue_body_summary_last_key` 和 `issue_body_summary_key_boundary_sha256`，让工具只读整包摘要就能确认 issue body summary 字段集合首尾边界是否符合预期。

`artifact_bundle_summary` 还会带上 `issue_body_summary_key_preview_count`、`issue_body_summary_key_preview` 和 `issue_body_summary_key_preview_sha256`，让工具只读整包摘要就能看到 issue body summary 字段集合入口，并判断 key preview 是否漂移。

`artifact_bundle_summary` 也会带上 `issue_body_summary_key_tail_count`、`issue_body_summary_key_tail` 和 `issue_body_summary_key_tail_sha256`，让工具只读整包摘要就能检查 issue body summary 字段集合末尾入口，并判断 key tail 是否漂移。

`artifact_bundle_summary` 也会带上 `issue_body_summary_sha256`，让工具只读整包摘要就能判断 issue body summary 是否漂移。

`artifact_bundle_summary` 也会带上 `issue_metadata_count` 和 `issue_metadata_sha256`，让工具只读整包摘要就能判断 issue metadata 是否漂移；这个摘要覆盖 case、title、labels、target URL、commands、offline commands、`promotion_evidence`、`promotion_evidence_primary_task`、`evidence_bundle_primary_next_task`、`evidence_bundle_command`、`evidence_bundle_json_command` 和 body 文件名，不包含本机输出路径。

`artifact_bundle_summary` 还会带上 `issue_metadata_first_item`、`issue_metadata_last_item` 和 `issue_metadata_boundary_sha256`，让工具只读整包摘要就能确认 issue metadata 首尾边界是否符合预期。

`artifact_bundle_summary` 还会带上 `issue_metadata_preview_count`、`issue_metadata_preview` 和 `issue_metadata_preview_sha256`，让工具只读整包摘要就能看到 issue metadata 入口，并判断 metadata preview 是否漂移。

`artifact_bundle_summary` 也会带上 `issue_metadata_tail_count`、`issue_metadata_tail` 和 `issue_metadata_tail_sha256`，让工具只读整包摘要就能检查 issue metadata 末尾入口，并判断 metadata tail 是否漂移。

`artifact_bundle_summary` 还会带上 `artifact_files_key_count` 和 `artifact_files_sha256`，让工具只读整包摘要就能判断 artifacts 文件映射是否漂移。

`artifact_bundle_summary` 还会带上 `artifact_files_first_key`、`artifact_files_last_key` 和 `artifact_files_key_boundary_sha256`，让工具只读整包摘要就能检查 artifacts 文件映射首尾边界，并判断 files key boundary 是否漂移。

`artifact_bundle_summary` 还会带上 `artifact_files_key_preview_count`、`artifact_files_key_preview` 和 `artifact_files_key_preview_sha256`，让工具只读整包摘要就能看到 artifacts 文件映射字段入口，并判断 files key preview 是否漂移。

`artifact_bundle_summary` 还会带上 `artifact_files_key_tail_count`、`artifact_files_key_tail` 和 `artifact_files_key_tail_sha256`，让工具只读整包摘要就能检查 artifacts 文件映射末尾入口，并判断 files key tail 是否漂移。

`artifact_bundle_summary` 还会带上 `issue_artifacts_command_sha256` 和 `plan_report_command_sha256`，让工具只读整包摘要就能判断 artifacts 复现命令或 Markdown 周计划报告命令是否漂移。

`artifact_bundle_summary` 还会带上 `publication_visibility_key_count`、`publication_visibility_sha256`、`publication_visibility_first_key`、`publication_visibility_last_key`、`publication_visibility_key_boundary_sha256`、`publication_visibility_key_preview_count`、`publication_visibility_key_preview`、`publication_visibility_key_preview_sha256`、`publication_visibility_key_tail_count`、`publication_visibility_key_tail`、`publication_visibility_key_tail_sha256` 和 `publication_visibility_summary_sha256`，让工具只读整包摘要就能判断发布可见性对象结构、首尾边界、字段入口、末尾入口、内容或 summary 文本是否漂移。

当 `candidate_issue_gate.reason_codes` 同时包含 publication 阻塞和 `release_draft_issues` 时，`required_actions` 会先列 publication 待办，再列 `Resolve release draft issue: ...`，让维护者无需交叉读取 release draft handoff 才能知道下一步修什么。

`candidate_issue_gate.required_action_count` 和 `candidate_issue_gate.required_actions_sha256` 会对 gate 待办做数量与稳定摘要；Markdown report 和 artifacts `README.md` 也会展示 required actions hash，方便工具先判断 gate action set 是否变化。

`candidate_issue_gate.reason_code_count` 和 `candidate_issue_gate.reason_codes_sha256` 会对 gate 原因码做数量与稳定摘要；Markdown report 和 artifacts `README.md` 也会展示 reason codes hash，方便工具先判断 gate reason set 是否变化。

`artifact_bundle_summary` 会带上 `candidate_issue_gate_key_count` 和 `candidate_issue_gate_sha256`，让工具只读整包摘要就能判断整个 candidate issue gate 是否漂移。

`artifact_bundle_summary` 也会带上 `candidate_issue_gate_reason_description_count` 和 `candidate_issue_gate_reason_descriptions_sha256`，让工具只读整包摘要就能判断 gate reason descriptions 是否漂移。

`artifact_bundle_summary` 也会带上 `candidate_issue_gate_reason_code_count`、`candidate_issue_gate_reason_codes_sha256`、`candidate_issue_gate_required_action_count` 和 `candidate_issue_gate_required_actions_sha256`，让工具只读整包摘要就能判断 gate reason/action set 是否需要展开。

`artifact_bundle_summary` 还会带上 `candidate_issue_gate_first_reason_code`、`candidate_issue_gate_last_reason_code` 和 `candidate_issue_gate_reason_code_boundary_sha256`，让工具只读整包摘要就能检查 gate reason code 首尾边界。

`artifact_bundle_summary` 还会带上 `candidate_issue_gate_first_required_action`、`candidate_issue_gate_last_required_action` 和 `candidate_issue_gate_required_action_boundary_sha256`，让工具只读整包摘要就能检查 gate required action 首尾边界。

`artifact_bundle_summary` 还会带上 `candidate_issue_gate_primary_reason_code`、`candidate_issue_gate_primary_reason_description` 和 `candidate_issue_gate_primary_required_action`，让工具只读整包摘要就能展示首要阻塞原因、原因说明和首个维护动作。

`candidate_issue_gate` 本体也会带上 `primary_reason_code`、`primary_reason_description` 和 `primary_required_action`，`publication-handoff.json` 会把它们同步提升为 `candidate_issue_gate_primary_reason_code`、`candidate_issue_gate_primary_reason_description` 和 `candidate_issue_gate_primary_required_action` 顶层别名，artifacts `README.md` 的 `Publication Handoff` 会同步展示 `gate_primary_reason_code`、`gate_primary_reason_description` 和 `gate_primary_required_action`。只读取 gate 或 handoff 的工具可以直接渲染首要原因与动作，不必解析 `reason_codes[0]` 或 `required_actions[0]`。

`artifact_bundle_summary` 也会带上 `publication_handoff_candidate_issue_gate_primary_reason_code`、`publication_handoff_candidate_issue_gate_primary_reason_description` 和 `publication_handoff_candidate_issue_gate_primary_required_action`，让只读取整包摘要的维护工具能检查 publication handoff 顶层 gate primary 别名是否和 gate 本体一致。

Candidate issue artifacts `README.md` 会在 `Artifact Bundle Summary` 前展示 `Candidate Issue Gate Quick Summary`，把 gate status、`can_create_issues`、`requires_maintainer_review`、publication/release draft ok、blocker/next action 数量、publication publish command 数量、publication publish script path、publication publish script command、reason/action 数量、primary reason/action、latest tag、publication branch/upstream/remote、publication local HEAD/tag commit/upstream HEAD、publication tag state、publication published state、publication remote refs、publication worktree clean、publication ahead/behind 数、publication remote checked、release draft issue 数、release draft path、visibility 和 visibility summary 放到维护者最容易先读到的位置。

`artifact_bundle_summary` 还会带上 `publication_ok`、`publication_visibility_status`、`release_draft_ok` 和 `release_draft_issue_count`，让工具只读整包摘要就能分辨发布阻塞和 release draft 阻塞分别来自哪里。

`artifact_bundle_summary` 还会带上 `publication_remote_checked`、`publication_ahead_count` 和 `publication_behind_count`，让工具只读整包摘要就能判断本轮发布审计是否做过远端复核，以及本地分支领先/落后远端多少提交。

`artifact_bundle_summary` 还会带上 `publication_branch`、`publication_upstream` 和 `publication_remote`，让工具只读整包摘要就能判断候选 artifacts 对应的发布分支、上游和远端名称。

`artifact_bundle_summary` 还会带上 `publication_latest_tag` 和 `publication_tag_commit`，让工具只读整包摘要就能判断候选 artifacts 对应的最新本地 tag 以及该 tag 指向的提交。

`artifact_bundle_summary` 还会带上 `publication_local_head` 和 `publication_upstream_head`，让工具只读整包摘要就能判断候选 artifacts 对应的本地 HEAD 和上游 HEAD。

`artifact_bundle_summary` 还会带上 `publication_tag_points_at_head` 和 `publication_tag_commit_in_upstream`，让工具只读整包摘要就能判断最新本地 tag 是否指向 HEAD，以及该 tag commit 是否已经包含在上游分支中。

`artifact_bundle_summary` 还会带上 `publication_branch_published` 和 `publication_tag_published`，让工具只读整包摘要就能判断发布分支和最新本地 tag 是否已经公开可见。

`artifact_bundle_summary` 还会带上 `publication_remote_branch_head` 和 `publication_remote_tag_commit`，让工具只读整包摘要就能判断远端分支和远端 tag 在 remote check 时实际指向的提交。

`artifact_bundle_summary` 还会带上 `requires_maintainer_review`，让工具只读整包摘要就能判断候选 issue gate 是否仍需人工审阅。

`artifact_bundle_summary` 还会带上 `candidate_issue_gate_summary_sha256`，让工具只读整包摘要就能判断 gate summary 是否漂移。

`artifact_bundle_summary` 还会带上 `release_draft_handoff_key_preview_count`、`release_draft_handoff_key_preview`、`release_draft_handoff_key_preview_sha256`、`release_draft_handoff_key_tail_count`、`release_draft_handoff_key_tail` 和 `release_draft_handoff_key_tail_sha256`，让工具只读整包摘要就能检查 `release-draft-handoff.json` 字段清单前后窗口是否漂移。

`artifact_bundle_summary` 还会带上 `publication_ref_context_key_preview_count`、`publication_ref_context_key_preview`、`publication_ref_context_key_preview_sha256`、`publication_ref_context_key_tail_count`、`publication_ref_context_key_tail` 和 `publication_ref_context_key_tail_sha256`，让工具只读整包摘要就能检查 publication ref context 字段清单前后窗口是否漂移。

`artifact_bundle_summary` 还会带上 `candidate_issue_gate_evidence_key_count` 和 `candidate_issue_gate_evidence_sha256`，让工具只读整包摘要就能判断 gate evidence 是否漂移。

`artifact_bundle_summary` 还会带上 `candidate_issue_gate_evidence_first_key`、`candidate_issue_gate_evidence_last_key` 和 `candidate_issue_gate_evidence_key_boundary_sha256`，让工具只读整包摘要就能检查 gate evidence key 首尾边界。

`artifact_bundle_summary` 还会带上 `blocker_count`、`next_action_count` 和 `publication_next_action_count`，让工具只读整包摘要就能判断本轮待办规模。

`scripts/check_release_publication.py` 的 JSON、默认文本输出和 Markdown report 会展示 `next_action_count`、`next_actions_sha256`、`primary_next_action`、`publish_command_count`、`publish_commands_sha256` 与 `primary_publish_command`，让维护者先判断发布待办规模、首要动作、首条命令和列表是否漂移，再展开具体 next actions 和 publish commands。

`artifact_bundle_summary` 还会带上 `blockers_sha256`、`next_actions_sha256` 和 `publication_next_actions_sha256`，让工具只读整包摘要就能判断 blockers 和 action lists 是否漂移。

`artifact_bundle_summary` 还会带上 `next_action_first_item`、`next_action_last_item` 和 `next_action_boundary_sha256`，让工具只读整包摘要就能确认 next actions 首尾边界是否符合预期。

`artifact_bundle_summary` 也会带上 `next_action_preview_count`、`next_action_preview` 和 `next_action_preview_sha256`，让工具只读整包摘要就能看到 next actions 入口，并判断 next action preview 是否漂移。

`artifact_bundle_summary` 还会带上 `next_action_tail_count`、`next_action_tail` 和 `next_action_tail_sha256`，让工具只读整包摘要就能看到 next actions 末尾入口，并判断 next action tail 是否漂移。

`artifact_bundle_summary` 还会带上 `blocker_first_item`、`blocker_last_item` 和 `blocker_boundary_sha256`，让工具只读整包摘要就能确认 blockers 首尾边界是否符合预期。

`artifact_bundle_summary` 还会带上 `blocker_preview_count`、`blocker_preview` 和 `blocker_preview_sha256`，让工具只读整包摘要就能看到 blockers 入口，并判断 blocker preview 是否漂移。

`artifact_bundle_summary` 也会带上 `blocker_tail_count`、`blocker_tail` 和 `blocker_tail_sha256`，让工具只读整包摘要就能看到 blockers 末尾入口，并判断 blocker tail 是否漂移。

`artifact_bundle_summary` 还会带上 `publication_primary_next_action`、`publication_next_action_first_item`、`publication_next_action_last_item` 和 `publication_next_action_boundary_sha256`，让工具只读整包摘要就能展示第一条发布同步待办，并检查 publication next actions 首尾边界。它也会带上 `publication_next_action_preview_count`、`publication_next_action_preview`、`publication_next_action_preview_sha256`、`publication_next_action_tail_count`、`publication_next_action_tail` 和 `publication_next_action_tail_sha256`，让工具只读整包摘要就能看到发布待办的前后窗口。

`artifact_bundle_summary` 还会带上 `publication_handoff_key_count`、`publication_handoff_schema_version`、`publication_handoff_first_key`、`publication_handoff_last_key`、`publication_handoff_key_boundary_sha256` 和 `publication_handoff_sha256`，让工具只读整包摘要就能判断 publication handoff 字段规模、语义版本、key 首尾边界或内容是否漂移。它也会带上 `publication_handoff_key_preview_count`、`publication_handoff_key_preview`、`publication_handoff_key_preview_sha256`、`publication_handoff_key_tail_count`、`publication_handoff_key_tail` 和 `publication_handoff_key_tail_sha256`，让工具不用展开完整 `publication-handoff.json` 也能检查字段清单前后窗口。

`publication-handoff.json` 和 artifacts `README.md` 的 `Publication Handoff` 也会展示 `schema_version`，让只读取 handoff 的维护工具能先判断 publication handoff 的字段语义版本。

`publication-handoff.json` 和 artifacts `README.md` 的 `Publication Handoff` 也会展示 `primary_next_action`，让只读取 handoff 的维护工具不必展开完整待办列表就能展示第一条发布同步待办。

`publication-handoff.json.plan_report_command` 和 artifacts `README.md` 的 `Publication Handoff` 也会展示 `plan_report_command`，让处理发布门禁的维护工具能从 handoff 直接复现同一份 Markdown 周计划报告。

`publication-handoff.json.issue_artifacts_command` 和 artifacts `README.md` 的 `Publication Handoff` 也会展示 `issue_artifacts_command`，让处理发布门禁的维护工具能从 handoff 直接重新生成整包候选任务 artifacts。

`publication-handoff.json.plan_report_command_sha256`、`publication-handoff.json.issue_artifacts_command_sha256` 和 artifacts `README.md` 的 `Publication Handoff` 也会展示同一组命令 hash，让只读取 handoff 的维护工具能检测周计划报告命令或整包 artifacts 复现命令是否漂移。

`artifact_bundle_summary` 还会带上 `publication_ref_context_key_count`、`publication_ref_context_sha256`、`publication_ref_context_first_key`、`publication_ref_context_last_key`、`publication_ref_context_key_boundary_sha256`、`publication_publish_command_count` 和 `publication_publish_commands_sha256`，让工具只读整包摘要就能判断 publication ref context 结构/内容或 publish commands 数量/内容是否漂移，并快速检查 publication ref context key 首尾边界。

`artifact_bundle_summary` 还会带上 `publication_primary_publish_command`，让工具只读整包摘要就能展示第一条发布同步命令。

`artifact_bundle_summary` 还会带上 `publication_publish_first_command`、`publication_publish_last_command` 和 `publication_publish_command_boundary_sha256`，让工具只读整包摘要就能检查 publication publish commands 首尾边界。

`artifact_bundle_summary` 还会带上 `publication_publish_script_path_sha256` 和 `publication_publish_script_command_sha256`，让工具只读整包摘要就能判断发布脚本路径或生成命令是否漂移。

`publication-handoff.json` 和 artifacts `README.md` 的 `Publication Handoff` 也会展示 `publish_script_path_sha256` 与 `publish_script_command_sha256`，让只读取 handoff 的维护工具不必展开完整 manifest 就能检测发布脚本路径或命令漂移。

`publication-handoff.json` 和 artifacts `README.md` 的 `Publication Handoff` 也会展示 `publish_command_count` 和 `primary_publish_command`，让只读取 handoff 的维护工具不必展开完整命令列表就能判断发布命令规模并展示第一条同步命令。

`artifact_bundle_summary` 还会带上 `publication_worktree_status_count`、`publication_worktree_status_sha256`、`publication_worktree_status_first_item`、`publication_worktree_status_last_item` 和 `publication_worktree_status_boundary_sha256`，让工具只读整包摘要就能判断 publication worktree status 是否漂移，并快速检查 status 列表首尾边界。

`artifact_bundle_summary` 还会带上 `release_draft_handoff_key_count`、`release_draft_handoff_schema_version`、`release_draft_handoff_primary_issue`、`release_draft_handoff_primary_required_action`、`release_draft_handoff_first_key`、`release_draft_handoff_last_key`、`release_draft_handoff_key_boundary_sha256` 和 `release_draft_handoff_sha256`，让工具只读整包摘要就能判断 release draft handoff 字段规模、语义版本、首要问题/动作、key 首尾边界或内容是否漂移。

`artifact_bundle_summary` 还会带上 `release_draft_path` 和 `release_draft_path_sha256`，让工具只读整包摘要就能判断目标 release draft 路径是否漂移。

`artifact_bundle_summary` 还会带上 `release_draft_primary_issue`，让工具只读整包摘要就能展示第一条 release draft 阻塞原因。

`artifact_bundle_summary` 还会带上 `release_draft_required_action_count` 和 `release_draft_required_actions_sha256`，让工具只读整包摘要就能判断 release draft required actions 是否需要展开。

`artifact_bundle_summary` 还会带上 `release_draft_first_required_action`、`release_draft_last_required_action` 和 `release_draft_required_action_boundary_sha256`，让工具只读整包摘要就能检查 release draft required actions 首尾边界。

`artifact_bundle_summary` 还会带上 `release_draft_required_action_preview_count`、`release_draft_required_action_preview`、`release_draft_required_action_preview_sha256`、`release_draft_required_action_tail_count`、`release_draft_required_action_tail` 和 `release_draft_required_action_tail_sha256`，让工具只读整包摘要就能检查 release draft required actions 的前后窗口。

`artifact_bundle_summary` 还会带上 `release_draft_primary_required_action`，让工具只读整包摘要就能展示第一条 release draft 修复动作。

`artifact_bundle_summary` 还会带上 `release_draft_issues_sha256`，让工具只读整包摘要就能判断 release draft issues 列表是否漂移。

`artifact_bundle_summary` 还会带上 `release_draft_first_issue`、`release_draft_last_issue` 和 `release_draft_issue_boundary_sha256`，让工具只读整包摘要就能检查 release draft issues 首尾边界。

`artifact_bundle_summary` 还会带上 `release_draft_issue_preview_count`、`release_draft_issue_preview`、`release_draft_issue_preview_sha256`、`release_draft_issue_tail_count`、`release_draft_issue_tail` 和 `release_draft_issue_tail_sha256`，让工具只读整包摘要就能检查 release draft issues 的前后窗口。

`artifact_bundle_summary` 还会带上 `validation_command_count` 和 `validation_commands_sha256`，让工具只读整包摘要就能判断 validation commands 是否漂移。

`artifact_bundle_summary` 还会带上 `validation_first_command`、`validation_last_command` 和 `validation_command_boundary_sha256`，让工具只读整包摘要就能检查 validation commands 首尾边界。

`artifact_bundle_summary` 还会带上 `validation_command_preview_count`、`validation_command_preview`、`validation_command_preview_sha256`、`validation_command_tail_count`、`validation_command_tail` 和 `validation_command_tail_sha256`，让工具只读整包摘要就能检查 validation commands 的前后窗口。

`artifact_bundle_summary` 还会带上 `review_checklist_count`、`review_checklist_sha256`、`review_checklist_first_item`、`review_checklist_last_item` 和 `review_checklist_boundary_sha256`，让工具只读整包摘要就能判断 review checklist 是否漂移，并快速检查首尾边界。

`artifact_bundle_summary` 还会带上 `review_checklist_preview_count`、`review_checklist_preview`、`review_checklist_preview_sha256`、`review_checklist_tail_count`、`review_checklist_tail` 和 `review_checklist_tail_sha256`，让工具只读整包摘要就能检查 review checklist 的前后窗口。

`artifact_bundle_summary` 还会带上 `create_issues_safety_contract_key_count`、`create_issues_safety_contract_sha256`、`create_issues_safety_contract_first_key`、`create_issues_safety_contract_last_key` 和 `create_issues_safety_contract_key_boundary_sha256`，让工具只读整包摘要就能判断 create issues safety contract 是否漂移，并快速检查契约 key 首尾边界；这个摘要只覆盖 dry-run/preflight 契约，不包含本机脚本路径。

`artifact_bundle_summary` 还会带上 `create_issues_safety_contract_key_preview_count`、`create_issues_safety_contract_key_preview`、`create_issues_safety_contract_key_preview_sha256`、`create_issues_safety_contract_key_tail_count`、`create_issues_safety_contract_key_tail` 和 `create_issues_safety_contract_key_tail_sha256`，让工具只读整包摘要就能检查 create issues safety contract keys 的前后窗口。

`artifact-manifest.json` 中的 publication ref context、publication worktree status 和 publication publish script command 会复用 `publication-handoff.json` 的同源字段，方便工具先读取 manifest 再决定是否继续展开详细 handoff。

`release-draft-handoff.json` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `schema_version`，让只读取 handoff 的维护工具能先判断 release draft handoff 的字段语义版本。

`release-draft-handoff.json` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `release_draft_issue_count`，让只读取 handoff 的维护工具不必展开完整 issue 列表就能判断草案门禁规模。

`release-draft-handoff.json` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `release_draft_primary_issue`，让只读取 handoff 的维护工具不必解析完整列表就能拿到第一条草案阻塞原因。

`release-draft-handoff.json` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `release_draft_primary_required_action`，让只读取 handoff 的维护工具不必解析完整列表就能拿到第一条草案阻塞的处理动作。

`release-draft-handoff.json` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示通用别名 `primary_issue` 和 `primary_required_action`，让工具可以用和 publication handoff 一致的 primary 字段模型读取首要草案问题和处理动作。

`release-draft-handoff.json` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `release_draft_required_action_count`、`release_draft_required_actions_sha256` 和 `release_draft_required_actions`，让只读取 handoff 的维护工具不必自行把完整草案问题列表转换成可执行动作。

`release-draft-handoff.json` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `release_draft_ok`，让只读取 handoff 的维护工具不必根据 issue 数量自行推断草案门禁是否通过。

`release-draft-handoff.json` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `release_draft_path_sha256`，让只读取 handoff 的维护工具不必展开完整 manifest 就能检测草案路径漂移。

`release-draft-handoff.json` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `release_draft_issues_sha256`，让只读取 handoff 的维护工具不必展开完整 manifest 就能检测草案问题列表漂移。

`release-draft-handoff.json.plan_report_command` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `plan_report_command`，让处理草案门禁的维护工具能从 handoff 直接复现同一份 Markdown 周计划报告。

`release-draft-handoff.json.issue_artifacts_command` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示 `issue_artifacts_command`，让处理草案门禁的维护工具能从 handoff 直接重新生成整包候选任务 artifacts。

`release-draft-handoff.json.plan_report_command_sha256`、`release-draft-handoff.json.issue_artifacts_command_sha256` 和 artifacts `README.md` 的 `Release Draft Handoff` 也会展示同一组命令 hash，让只读取 handoff 的维护工具能检测周计划报告命令或整包 artifacts 复现命令是否漂移。

`artifact-manifest.json` 也会保留 release draft path 和 release draft issues，与 `release-draft-handoff.json` 同源，方便工具先判断下一版草案是否已准备好。

`artifact-manifest.json` 还会保留 `issue_artifacts_command` 和 `plan_report_command`，让维护者和自动化能从同一个入口复现当前候选任务产物包与 Markdown 周计划报告。

`artifact-manifest.json` 会带 `schema_version`，这是 artifacts manifest 自身的格式版本，用于脚本在解析前判断字段语义。

`artifact-manifest.json` 的 `validation_commands` 会包含 `python scripts/check_release_publication.py --json`；如果 planner 运行时带 `--remote` / `--remote-name`，这条 publication audit 命令也会继承相同远端参数，方便维护者在创建候选 issue 前重新复核同一个远端 refs 状态。

`artifact-manifest.json` 的 `validation_commands` 也会包含 `python scripts/release_readiness.py --target-version <version> --json`，方便维护者在同一入口复核下一版 release gate。

artifacts `README.md` 的 `Validation Commands` 会和 `artifact-manifest.json.validation_commands` 保持同源，列出 `plan_next_iteration.py --issues-dir`、`plan_next_iteration.py --report /tmp/cliany-next-iteration.md`、`plan_next_iteration.py --json`、`release_readiness.py --target-version <version> --json`、`check_release_publication.py --json`（必要时带 remote audit 参数）和 `validate_cases.py --strict`，避免维护者只照 README 操作时漏跑周计划报告、release readiness 或 publication audit。

`artifact-manifest.json` 还会包含 `review_checklist`，把 README 里的候选任务审阅清单同步为机器可读字段。

`artifact-manifest.json` 的 `candidate_issue_gate` 会和 `publication-handoff.json` 同源，用 `can_create_issues` 把硬性 issue 创建门禁和 release draft 人工审阅区分开，并用 `evidence` 保留 gate 判定所用的 release/publication 证据。

`create-issues.sh` 的硬性 publication preflight 现在由 `candidate_issue_gate.can_create_issues` 决定，避免只用 tag 是否指向 HEAD 来误挡正常的下一版准备态。
如果 preflight 失败，脚本会打印 `/tmp/cliany-issue-publication-check.json` 或 gate preflight JSON；需要手动复核发布状态时，可先运行 `python scripts/check_release_publication.py --strict --json`。

`plan_next_iteration.py` 的默认文本输出会把 `candidate_issue_gate.evidence` 展开成缩进列表，方便维护者在终端里直接审阅 publication visibility、latest tag、ahead count 和 release draft issue count。

`candidate_issue_gate.evidence.release_draft_path` 使用 `docs/releases/v<version>-draft.md` 这样的仓库相对路径，避免候选 issue artifacts 泄漏维护者本机绝对路径。

如果 readiness 的 cadence 只提示 `commit days N/3`，本周继续做小而可验证的增量，同时可以照常发布当天合格版本；如果存在真正 gate issue，优先关闭具体 gate，再继续新功能。

## 2. 周中：实现一个可验证切片

每个切片都要满足三件事：

- 能解释用户价值：新用户更容易成功、贡献者更容易复现、adapter 更容易维护，至少命中一个。
- 有可运行验证：优先选择离线测试、fixture、schema 校验或文档测试。
- 不扩大风险：不引入真实 LLM key、第三方站点强依赖、脆弱 CSS selector 兜底或 runtime 状态入库。

按改动类型选择最小验证：

| 改动类型 | 最小验证 |
|----------|----------|
| 文档/官网 | `git diff --check` + 对应文档测试 |
| 案例库 | `python scripts/validate_cases.py --strict` |
| 发布门禁 | `python scripts/release_readiness.py --json` + release readiness 测试 |
| CLI/doctor | 相关 pytest + `ruff check` |
| 抽取/生成/replay | 针对性回归 + `CLIANY_QA_OFFLINE=1` 覆盖必要路径 |

## 3. 周末：发版或明确阻塞

发版前执行：

```bash
python scripts/release_readiness.py --strict
python scripts/validate_cases.py --strict
CLIANY_QA_OFFLINE=1 pytest tests/ -q --no-cov
```

然后按 [发布与提交节奏](release-cadence.md) 移动 `CHANGELOG.md`、同步版本号、更新 release draft 或 release notes，并创建 `vX.Y.Z` tag。

如果不能发布，必须把原因写进发布草案或 `CHANGELOG.md` 的 `Unreleased` 语境中，避免“做了很多但不知道差什么”。常见判断：

| readiness 状态 | 动作 |
|----------------|------|
| 只提示 `commit days N/3` | 可发布当天合格版本，同时继续补足本周三天提交记录 |
| `cases` gate 失败 | 修案例 manifest、离线样例或文档锚点 |
| `draft` gate 失败 | 补目标版本、用户价值、风险、验证和剩余阻塞 |
| `ci` / `release_workflow` 失败 | 修默认零密钥门禁或 tag 发布 preflight |
| `project_metadata` 失败 | 修 PyPI 元数据、README 或社区入口文件 |
| `package_gate` 失败 | 重新生成或校验 demo adapter 包资产 |

## 4. 周复盘问题

每次发布或决定暂缓发布前，回答这 6 个问题：

1. 这周的版本是否让真实用户更容易成功？
2. 是否至少有一个测试、fixture、案例或报告能证明改动？
3. README、官网、贡献者文档或 release draft 是否已同步必要入口？
4. PR 默认路径是否仍然零真实 LLM key？
5. 本周是否已有至少三天提交记录？
6. 下一个最小可交付版本是什么？
