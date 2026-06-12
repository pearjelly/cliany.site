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
python scripts/release_readiness.py --json
python scripts/release_readiness.py --report /tmp/cliany-release-readiness.md
```

`plan_next_iteration.py` 会把 release readiness、publication audit、commit cadence 和 candidate cases 汇总成一个推荐切片；如果它提示最新本地 tag 尚未公开可见，先完成发布同步，再扩大下一版范围。计划 JSON、文本输出和 Markdown report 会带上 `publication_visibility`，用 `published`、`local_only`、`dirty_worktree`、`tag_not_visible` 或 `needs_remote_check` 给出一眼可读的发布可见性结论和 summary；也会带上 `candidate_issue_gate`，用 `blocked_by_publication`、`review_required` 或 `ready` 说明当前是否 `can_create_issues`、是否 `requires_maintainer_review`，并把 `reason_codes`、`reason_descriptions`、`required_actions` 和 `evidence` 带给维护者和自动化；`reason_codes` 会用 `publication_not_published`、`dirty_worktree`、`local_release_only`、`tag_not_visible`、`needs_remote_check` 或 `release_draft_issues` 给脚本一个稳定原因层，`reason_descriptions` 会给这些原因码提供 human-readable 可读说明；`evidence` 会保留 `publication_ok`、`publication_visibility_status`、`publication_worktree_clean`、`publication_remote_checked`、`publication_branch`、`publication_latest_tag`、`publication_ahead_count`、`release_draft_ok`、`release_draft_path` 和 `release_draft_issue_count`，让工具能审计 gate 结论来自哪些输入；也会带上 `publication_next_actions`，直接列出 publication audit 的具体待办，例如本地分支 ahead 数、tag 尚未发布和是否需要 `--remote` 复核；也会带上 `publication_ref_context`，把 repo root、branch、latest tag、local HEAD、tag commit 和 remote check 状态带到周初计划里；也会带上 `publication_worktree_clean` / `publication_worktree_status`，把 worktree 是否干净和具体 status 行带到周初计划里；也会带上 `publication_publish_commands`，把 publication audit 里的 branch/tag push 和 `python scripts/check_release_publication.py --remote --json` 复核命令直接带到周初计划里；`publication_publish_script_command` 还会给出 `--publish-script /tmp/cliany-publish-release.sh` 生成命令，方便维护者先审阅脚本再手动执行。计划 JSON、文本输出和 Markdown report 也会带上 `release_draft_issues`，把下一版 release draft 缺失或 snippet 校验失败的具体原因直接列出来，避免只看到笼统的 `release draft validation failed`。它的 Markdown 报告会输出 `Candidate Issue Gate`、`Candidate Issue Gate Reason Codes`、`Candidate Issue Gate Reason Descriptions`、`Candidate Issue Gate Evidence`、`Candidate Issue Metadata` 和 `Candidate Promotion Tasks`，把能否创建候选 issue、该判断的稳定原因码、原因码可读说明、publication/release draft 证据、每个 candidate 的 issue title、labels、`adapter_package`、`metadata_validation` 和 `online_smoke` 证据项带到同一份周初计划里，并在 `Candidate Issue Body Templates` 里生成可复制的 GitHub issue body；每个 body 都包含 `Reproduction Context`，保留 target URL，并把 candidate commands 和 offline validation commands 作为子列表列出。需要批量创建候选案例任务时，`--issues-dir` 会额外写出每个 candidate 的 body 文件、`artifact-manifest.json`、`issue-metadata.json`、`publication-handoff.json`、`release-draft-handoff.json`、`README.md` 和可审阅的 `create-issues.sh`，其中 `artifact-manifest.json` 会保留 target version、candidate count、candidate cases、blockers、next actions、candidate issue gate、publication status、publication visibility、publication next actions、publication publish commands、文件名、review order、validation commands、`create_issues_dry_run_command`、`create_issues_safety`、`issue_body_inventory`、`issue_body_summary` 和 `artifact_bundle_summary`，作为整个 artifacts 包的机器可读入口；`artifact_bundle_summary` 会汇总 target version、candidate/body/review item 数量、inventory hash、gate 状态和脚本安全布尔值，方便工具先判断是否需要展开完整 manifest；`issue_body_inventory` 会记录每个 body 的 case、文件名、byte_count 和 sha256，方便工具确认 body 文件没有漂移；`issue_body_summary` 会记录 body_count、total_byte_count 和 inventory_sha256，方便工具快速判断整批 body 是否变化；`issue-metadata.json` 会保留 issue title、labels、target URL、candidate commands、offline validation commands、body file name、body file path 和 create command，artifacts `README.md` 会带 `Candidate Summary` 表，列出 case、issue body 文件、target URL 和命令数量，也会在 `Issue Body Inventory` 表展示每个 body 的字节数和 SHA-256，并在 `Issue Body Summary` 下展示 body_count、total_byte_count 和 inventory_sha256，还会在 `Artifact Bundle Summary` 下展示 target_version、candidate_count、body_count、review_item_count、candidate_issue_gate_status、can_create_issues、dry_run_supported 和 preflight_required，也会在 `Publication Handoff` 下展示 candidate issue gate、can_create_issues、gate summary、gate reason codes、gate reason descriptions、gate evidence latest tag、gate evidence ahead count、gate evidence worktree clean、gate evidence release draft ok、gate evidence release draft issues、visibility、visibility summary、`Publication Next Actions`、latest tag、local HEAD、`worktree_clean` 和 `Publication Publish Script`，在 `Release Draft Handoff` 下展示 release draft path 和 release draft issues，并在 `Create Issues Safety` 下展示 `dry_run_supported`、`dry_run_env`、`dry_run_command`、`preflight_required`、`preflight_command` 和 `preflight_json`，在审阅清单里要求先确认这些 release draft issues 与 publication next actions 已处理或明确延后，再核对复现字段；`publication-handoff.json` 会保留 publication 状态、candidate issue gate、visibility、next actions、publication next actions、ref context、worktree status 和 publish commands；`release-draft-handoff.json` 会保留 target version、release draft path 和 release draft issues，方便工具读取而不解析 README；脚本不会自动执行，正常执行前会先跑 `python scripts/check_release_publication.py --strict --json`，把 preflight JSON 写入 `/tmp/cliany-issue-publication-check.json`，避免在最新本地 release 尚未公开时继续派发新任务；如果 preflight 失败，脚本会把这份 JSON 打印出来再退出。维护者也可以用 `CLIANY_CREATE_ISSUES_DRY_RUN=1 ./create-issues.sh` 进入 dry-run mode，只打印 `gh issue create` 命令，不运行 publication preflight，也不创建 issue。计划 JSON 里的 `issue_artifacts_command` 和 artifacts `README.md` 会保留复现命令，例如 `python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues`，方便维护者重新生成同一批候选 issue artifacts。Markdown 报告里的 `Weekly Review` 小节会把本页最后的 6 个复盘问题和当前证据放在一起；发版前优先引用这份报告，避免手工复盘和 readiness gate 脱节。

`plan_next_iteration.py` 的 JSON、默认文本输出和 Markdown report 会展示 `publication_next_action_count` 与 `publication_publish_command_count`，让维护者在周初计划里先判断发布待办规模，再展开 publication next actions 和 publish commands。

`artifact_bundle_summary.review_order_sha256` 会对 `review_order` 做稳定 SHA-256 摘要；artifacts `README.md` 的 `Artifact Bundle Summary` 也会展示 `review_order_sha256`，让工具能先检查 review order hash，再决定是否展开完整 manifest。

`artifact_bundle_summary` 也会带上 `candidate_cases_sha256`，让工具只读整包摘要就能判断 candidate case 列表是否漂移。

`artifact_bundle_summary` 也会带上 `issue_body_summary_sha256`，让工具只读整包摘要就能判断 issue body summary 是否漂移。

`artifact_bundle_summary` 也会带上 `issue_metadata_count` 和 `issue_metadata_sha256`，让工具只读整包摘要就能判断 issue metadata 是否漂移；这个摘要覆盖 case、title、labels、target URL、commands、offline commands 和 body 文件名，不包含本机输出路径。

`artifact_bundle_summary` 还会带上 `artifact_files_key_count` 和 `artifact_files_sha256`，让工具只读整包摘要就能判断 artifacts 文件映射是否漂移。

`artifact_bundle_summary` 还会带上 `issue_artifacts_command_sha256`，让工具只读整包摘要就能判断 artifacts 复现命令是否漂移。

`artifact_bundle_summary` 还会带上 `publication_visibility_key_count`、`publication_visibility_sha256` 和 `publication_visibility_summary_sha256`，让工具只读整包摘要就能判断发布可见性对象结构/内容或 summary 文本是否漂移。

当 `candidate_issue_gate.reason_codes` 同时包含 publication 阻塞和 `release_draft_issues` 时，`required_actions` 会先列 publication 待办，再列 `Resolve release draft issue: ...`，让维护者无需交叉读取 release draft handoff 才能知道下一步修什么。

`candidate_issue_gate.required_action_count` 和 `candidate_issue_gate.required_actions_sha256` 会对 gate 待办做数量与稳定摘要；Markdown report 和 artifacts `README.md` 也会展示 required actions hash，方便工具先判断 gate action set 是否变化。

`candidate_issue_gate.reason_code_count` 和 `candidate_issue_gate.reason_codes_sha256` 会对 gate 原因码做数量与稳定摘要；Markdown report 和 artifacts `README.md` 也会展示 reason codes hash，方便工具先判断 gate reason set 是否变化。

`artifact_bundle_summary` 会带上 `candidate_issue_gate_key_count` 和 `candidate_issue_gate_sha256`，让工具只读整包摘要就能判断整个 candidate issue gate 是否漂移。

`artifact_bundle_summary` 也会带上 `candidate_issue_gate_reason_description_count` 和 `candidate_issue_gate_reason_descriptions_sha256`，让工具只读整包摘要就能判断 gate reason descriptions 是否漂移。

`artifact_bundle_summary` 也会带上 `candidate_issue_gate_reason_code_count`、`candidate_issue_gate_reason_codes_sha256`、`candidate_issue_gate_required_action_count` 和 `candidate_issue_gate_required_actions_sha256`，让工具只读整包摘要就能判断 gate reason/action set 是否需要展开。

`artifact_bundle_summary` 还会带上 `publication_ok`、`publication_visibility_status` 和 `release_draft_issue_count`，让工具只读整包摘要就能分辨发布阻塞和 release draft 阻塞分别来自哪里。

`artifact_bundle_summary` 还会带上 `requires_maintainer_review`，让工具只读整包摘要就能判断候选 issue gate 是否仍需人工审阅。

`artifact_bundle_summary` 还会带上 `candidate_issue_gate_summary_sha256`，让工具只读整包摘要就能判断 gate summary 是否漂移。

`artifact_bundle_summary` 还会带上 `candidate_issue_gate_evidence_key_count` 和 `candidate_issue_gate_evidence_sha256`，让工具只读整包摘要就能判断 gate evidence 是否漂移。

`artifact_bundle_summary` 还会带上 `blocker_count`、`next_action_count` 和 `publication_next_action_count`，让工具只读整包摘要就能判断本轮待办规模。

`scripts/check_release_publication.py` 的 JSON、默认文本输出和 Markdown report 会展示 `next_action_count` 与 `publish_command_count`，让维护者先判断发布待办规模，再展开具体 next actions 和 publish commands。

`artifact_bundle_summary` 还会带上 `blockers_sha256`、`next_actions_sha256` 和 `publication_next_actions_sha256`，让工具只读整包摘要就能判断 blockers 和 action lists 是否漂移。

`artifact_bundle_summary` 还会带上 `publication_handoff_key_count` 和 `publication_handoff_sha256`，让工具只读整包摘要就能判断 publication handoff 是否漂移。

`artifact_bundle_summary` 还会带上 `publication_ref_context_key_count`、`publication_ref_context_sha256`、`publication_publish_command_count` 和 `publication_publish_commands_sha256`，让工具只读整包摘要就能判断 publication ref context 结构/内容或 publish commands 数量/内容是否漂移。

`artifact_bundle_summary` 还会带上 `publication_publish_script_command_sha256`，让工具只读整包摘要就能判断发布脚本生成命令是否漂移。

`artifact_bundle_summary` 还会带上 `publication_worktree_status_count` 和 `publication_worktree_status_sha256`，让工具只读整包摘要就能判断 publication worktree status 是否漂移。

`artifact_bundle_summary` 还会带上 `release_draft_handoff_key_count` 和 `release_draft_handoff_sha256`，让工具只读整包摘要就能判断 release draft handoff 是否漂移。

`artifact_bundle_summary` 还会带上 `release_draft_issues_sha256`，让工具只读整包摘要就能判断 release draft issues 列表是否漂移。

`artifact_bundle_summary` 还会带上 `validation_command_count` 和 `validation_commands_sha256`，让工具只读整包摘要就能判断 validation commands 是否漂移。

`artifact_bundle_summary` 还会带上 `review_checklist_count` 和 `review_checklist_sha256`，让工具只读整包摘要就能判断 review checklist 是否漂移。

`artifact_bundle_summary` 还会带上 `create_issues_safety_contract_key_count` 和 `create_issues_safety_contract_sha256`，让工具只读整包摘要就能判断 create issues safety contract 是否漂移；这个摘要只覆盖 dry-run/preflight 契约，不包含本机脚本路径。

`artifact-manifest.json` 中的 publication ref context、publication worktree status 和 publication publish script command 会复用 `publication-handoff.json` 的同源字段，方便工具先读取 manifest 再决定是否继续展开详细 handoff。

`artifact-manifest.json` 也会保留 release draft path 和 release draft issues，与 `release-draft-handoff.json` 同源，方便工具先判断下一版草案是否已准备好。

`artifact-manifest.json` 还会保留 `issue_artifacts_command`，让维护者和自动化能从同一个入口复现当前候选任务产物包。

`artifact-manifest.json` 会带 `schema_version`，这是 artifacts manifest 自身的格式版本，用于脚本在解析前判断字段语义。

`artifact-manifest.json` 的 `validation_commands` 会包含 `python scripts/check_release_publication.py --json`，方便维护者在创建候选 issue 前重新复核发布可见性。

`artifact-manifest.json` 的 `validation_commands` 也会包含 `python scripts/release_readiness.py --target-version <version> --json`，方便维护者在同一入口复核下一版 release gate。

artifacts `README.md` 的 `Validation Commands` 会和 `artifact-manifest.json.validation_commands` 保持同源，列出 `plan_next_iteration.py --json`、`release_readiness.py --target-version <version> --json`、`check_release_publication.py --json` 和 `validate_cases.py --strict`，避免维护者只照 README 操作时漏跑 release readiness 或 publication audit。

`artifact-manifest.json` 还会包含 `review_checklist`，把 README 里的候选任务审阅清单同步为机器可读字段。

`artifact-manifest.json` 的 `candidate_issue_gate` 会和 `publication-handoff.json` 同源，用 `can_create_issues` 把硬性 publication preflight 和 release draft 人工审阅区分开，并用 `evidence` 保留 gate 判定所用的 release/publication 证据。

`plan_next_iteration.py` 的默认文本输出会把 `candidate_issue_gate.evidence` 展开成缩进列表，方便维护者在终端里直接审阅 publication visibility、latest tag、ahead count 和 release draft issue count。

`candidate_issue_gate.evidence.release_draft_path` 使用 `docs/releases/v<version>-draft.md` 这样的仓库相对路径，避免候选 issue artifacts 泄漏维护者本机绝对路径。

如果 readiness 只剩 `commit days N/3`，本周继续做小而可验证的增量；如果存在 gate issue，优先关闭具体 gate，再继续新功能。

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
| 只剩 `commit days N/3` | 不发版，继续保持本周三天提交记录 |
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
