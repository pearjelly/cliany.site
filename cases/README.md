# cliany-site 案例库

**状态：** 起步维护中  
**索引文件：** [manifest.json](manifest.json)  
**目标：** 用真实案例说明 cliany-site 适合做什么、不适合过度承诺什么，并把案例沉淀成可验证资产。

## 案例分层

| 层级 | 用途 | 是否进入默认 CI |
|------|------|----------------|
| 离线结构校验 | 校验案例索引、命令、文档链接不腐烂 | 是 |
| 离线样例输出 | 展示 active 案例的 JSON envelope 形状和典型字段 | 是 |
| 结构化离线命令 | 每个案例声明 `validation.offline_commands`，让维护者能直接复制本地验证命令 | 是 |
| adapter metadata 校验 | 校验本地 demo adapter 包结构、哈希和 metadata schema v3 | 可选，本地 release asset 存在时 |
| 在线 smoke | 访问第三方 demo 站点并执行只读命令 | 否，第三方站点不稳定 |
| 完整 explore 回归 | Chrome + LLM 从头探索生成 adapter | 手动或受保护 workflow |

## 当前案例

| ID | 场景 | 状态 | 价值 |
|----|------|------|------|
| `suitecrm-accounts` | SuiteCRM demo 账户列表 | active | 企业 CRM 查询，无 API 后台操作 CLI 化；样例输出见 [suitecrm-accounts.json](examples/suitecrm-accounts.json) |
| `apache-jira-issues` | ASF Jira issue 列表 | active | DevOps/项目管理列表读取；样例输出见 [apache-jira-issues.json](examples/apache-jira-issues.json) |
| `apache-confluence-search` | ASF Confluence 页面搜索 | active | 团队知识库搜索；样例输出见 [apache-confluence-search.json](examples/apache-confluence-search.json) |
| `apache-jenkins-jobs` | ASF Jenkins job 列表 | active | 构建状态查询；样例输出见 [apache-jenkins-jobs.json](examples/apache-jenkins-jobs.json) |
| `pypi-project-search` | PyPI 项目搜索 | candidate | Python 包注册表搜索候选；样例输出见 [pypi-project-search.json](examples/pypi-project-search.json)，待生成 adapter 包和在线 smoke 后晋级 active |
| `npm-package-search` | npm 包搜索 | candidate | JavaScript 包注册表搜索候选；样例输出见 [npm-package-search.json](examples/npm-package-search.json)，待生成 adapter 包和在线 smoke 后晋级 active |
| `crates-io-crate-search` | crates.io crate 搜索 | candidate | Rust 包注册表搜索候选；样例输出见 [crates-io-crate-search.json](examples/crates-io-crate-search.json)，待生成 adapter 包和在线 smoke 后晋级 active |
| `search-extraction-gap` | 搜索结果抽取复盘 | known-gap | 明确「页面交互强、列表抽取弱」的产品边界 |

## Candidate Cases

`candidate` 表示真实公开只读工作流已经进入案例管道，但尚未承诺已有 release adapter 包。候选案例必须有期望命令、离线样例输出、`promotion` 清单和 `promotion_evidence` 状态；当 adapter 包、metadata 校验和在线只读 smoke 都准备好后，再改为 `active`。

`promotion` 至少包含：

- `adapter_package`：要生成或发布的 adapter 包资产，候选新包名应沿用 `market publish` 生成的 `<domain>-<version>.cliany-adapter.tar.gz` 格式。
- `metadata_validation`：包资产准备好后要运行的离线 metadata 校验；candidate 包应使用 `--include-candidate-packages`，避免只校验 active release 包。
- `online_smoke`：晋级前需要手动确认的公开只读 smoke 命令或结果。

`promotion_evidence` 必须为同样三项任务记录结构化状态：

- `status`：只能是 `pending`、`complete` 或 `blocked`。
- `evidence`：任务完成时必须记录证据，例如 release asset 名、`validate_cases.py --packages-dir` 结果或在线 JSON envelope 摘要。
- `next_action`：任务仍为 `pending` / `blocked` 时必须记录下一步动作。

### Candidate 晋级任务拆分

维护者把 candidate 转成 GitHub issue 时，不要把“晋级 active”打包成一个大任务。优先拆成三条可以独立验收的小 issue：

| 子任务 | 适合贡献者 | 完成证据 |
|--------|------------|----------|
| `llm_live_preflight` | 负责启动 candidate 晋级的维护者 | 运行 `cliany-site doctor --llm-live --json`，确认 `summary.llm_live_preflight.ready=true` 且 `llm_live` 没有阻塞 `ready_for_explore`，再进入真实 `explore` |
| `adapter_package` | 熟悉 `explore` / `market publish` 的维护者 | 生成 `<domain>-<version>.cliany-adapter.tar.gz`，并把包资产放到 release candidate 或本地 `~/.cliany-site/packages` |
| `metadata_validation` | 首次贡献者或文档/测试贡献者 | 运行 `python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --include-candidate-packages --strict`，确认目标 candidate 包通过 schema v3、manifest hash 和 domain 校验 |
| `online_smoke` | 能手动访问第三方公开站点的维护者 | 运行 candidate 声明的只读命令，保存 JSON envelope 摘要，并确认 `data.quality.ok=true` 和 `row_count>0` |

每个 issue 都应引用对应 case id、`promotion` 字段、`promotion_evidence` 状态和推荐验证命令；如果任一子任务还没完成，案例继续保持 `candidate`，不要提前改成 `active`。

如果 `cliany-site doctor --llm-live --json` 显示 `generate_adapters.ready=false`，或 `llm_live` 返回 warning/error（例如 `E_LLM_UNAVAILABLE` 或 `E_UNKNOWN` connection error），维护者应停止本轮 `explore`，把 doctor JSON / 错误摘要贴回 issue，并让 `adapter_package` 保持 `pending` 或标记为 `blocked`；不要用失败的上游调用伪造成 adapter package 证据。

运行 `python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md` 会在 Markdown 报告中生成 `Candidate Promotion Evidence Summary`、`LLM Live Preflight Evidence Fields`、`Candidate Promotion Command Plan Summary`、`Candidate Evidence Bundle Commands` 和 `Candidate Promotion Tasks` 小节。Evidence Bundle 命令会指向 `cliany-site cases --case-id <id> --evidence-bundle` 和 `cliany-site cases --case-id <id> --evidence-bundle --json`，方便维护者先输出本地证据清单；Promotion Evidence Summary 汇总 candidate 数量、pending/blocked/complete 任务数、`primary_next_task`、primary next action、`llm_live_preflight_evidence_field_count` 和 `llm_live_preflight_evidence_fields_sha256`，让维护者和自动化能直接定位首要 case/task/status/evidence 以及需要贴回的 doctor preflight 字段；Promotion Command Plan Summary 汇总 `promotion_command_plan_summary` 的 candidate 数量、命令总数、缺失命令数、缺失 case/task 和 `all_declared` 状态；Promotion Tasks 可以直接把其中的 `Issue Body Template` 复制到 GitHub issue。模板会保留 `Reproduction Context`、`Promotion Command Plan`、`Acceptance Criteria`、`adapter_package`、`metadata_validation`、`online_smoke` 三类证据任务、`promotion_evidence` 当前状态、验收证据和非目标边界。`python scripts/validate_cases.py --json` 的 candidate 条目也会输出 `promotion_command_plan`、`promotion_command_plan_count` 和 `promotion_command_plan_missing_tasks`，让自动化可以直接读取包含 `llm_live_preflight` 的四步执行计划而不必解析 Markdown。

创建 candidate promotion issue 时，正文可以复制 `--issue-template` 的输出；该模板会包含 `Primary Runbook`、LLM/doctor blocker comments、`Doctor Preflight Evidence Fields` 和带可粘贴占位符的 `Doctor Preflight Evidence Template`。同时加 `--json` 时，`issue_template_primary_task` 会带同一组 acceptance、runbook、preflight 字段和 `doctor_preflight_evidence_template` 映射，方便 issue bot 不解析 Markdown 也能读取首要证据任务。附件或评论应附上 `--evidence-bundle --json` 的机器可读结果，例如 `cliany-site cases --case-id pypi-project-search --evidence-bundle --json`。普通 `cliany-site cases --status candidate` 输出也会在 `Candidate 下一步` 中显示 `preflight_required`、`preflight_blocker` 和 `runbook_first`，方便只读 human handoff 的维护者先确认 live LLM gate。这样后续维护者能直接对比 issue、case report 和 `promotion_evidence`，确认哪些晋级证据仍在 pending。

Evidence bundle 的 JSON 会为每个任务输出 `acceptance_criteria`，并在顶层提供同名任务到验收条件的映射。`primary_next_task_acceptance_criteria` 会把当前首要任务需要贴的证据单独抬出来，避免自动化只知道要运行哪条命令，却不知道应该把什么结果作为完成证据。`primary_next_task_runbook` 会把首要任务拆成有序步骤；当首要任务是 `adapter_package` 时，第一步是 `cliany-site doctor --llm-live --json`，之后才是 explore 命令和验收证据。JSON 顶层、`primary_next_task` 和 `adapter_package` 任务也会输出 `doctor_preflight_evidence_fields`，方便维护者在 CDP 或 LLM gate 失败时直接贴回 `summary.capabilities.run_browser_workflows.ready`、`checks[cdp].status`、`checks[llm_live].details.error_code` 等 blocker 字段。人类 Markdown 输出也会展示 `Acceptance criteria` 和 `Primary next runbook` 小节，方便直接复制到 GitHub issue 评论。

如果要一次查看所有 candidate 的可执行晋级队列，可以运行 `cliany-site cases --status candidate --promotion-plan`。该输出会按证据进度列出每个 candidate 的首要 task、命令、handoff、acceptance、issue template 命令和 evidence bundle JSON 命令；追加 `--json` 后可读取 `promotion_plan.primary_next_item`、`promotion_plan.primary_runbook`、`promotion_plan.primary_issue_template_command`、`promotion_plan.candidates[*].issue_template_json_command` 和未完成任务的 `promotion_plan.task_queue`，用于维护脚本或 issue bot 排队处理真实证据并直接生成候选晋级 issue body。`python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues` 生成的 `candidate_promotions[*].issue_template_command`、`candidate_promotions[*].issue_template_json_command`、`issue-metadata.json` 和 artifacts README 的 Issue Template / Issue Template JSON 列也会展示同一组命令，方便只读 planner artifacts 的维护工具复现 issue body。

## 维护规则

- 新增真实 demo 时，先更新 `manifest.json`，再补充 README/官网展示。
- 候选真实 demo 先用 `candidate`，不要在 release asset 准备好之前标记为 `active`。
- 如果只是提出候选场景，优先使用 GitHub 的 `Real Demo Case Proposal` issue 模板，说明目标 URL、只读工作流、期望命令、离线样例输出和验证方式。
- 第三方站点不可用时，将 `status` 标记为 `degraded`，不要直接删除案例。
- 每个 active 案例至少要有一个 `commands` 示例和一种 `validation` 方式。
- 每个案例必须提供 `validation.offline_commands`，命令应保持本地可运行，例如 `python scripts/validate_cases.py --strict`、`python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict`、`python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --include-candidate-packages --strict` 或相关 pytest。
- 每个 active/candidate 案例必须提供 `example_output`，指向 `cases/examples/` 下的离线 JSON envelope 样例；样例必须包含 `data.quality.ok=true`、`status=ok` 和正数 `row_count`，只展示字段形状和典型数据，不作为第三方站点实时内容承诺。
- 每个 candidate 案例必须提供 `promotion_evidence`，并为 `adapter_package`、`metadata_validation`、`online_smoke` 记录当前状态；`pending` / `blocked` 必须写明 `next_action`，`complete` 必须写明 `evidence`。
- 已知短板用 `known-gap` 记录，作为路线图输入，而不是藏在聊天记录里。
- 案例运行产生的 adapter/session/snapshot 仍必须保存在 `~/.cliany-site/`，不能写入 repo。

## 离线验收

默认验收只检查索引结构、文档链接和锚点、状态、命令域名一致性、离线样例输出和验证说明，不访问第三方站点：

```bash
python scripts/validate_cases.py
python scripts/validate_cases.py --json
python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md
python scripts/validate_cases.py --strict
pytest tests/test_search_extraction_gap_fixture.py -q --no-cov
```

CI 的 `Case Catalog Validation` job 会上传 `case-catalog-report` artifact，供 PR 诊断和 release notes 复盘引用。

报告中的 `Offline Validation Commands` 小节会汇总每个案例声明的 `validation.offline_commands`，维护者可以直接复制这些命令作为 PR 或 release 证据。

报告中的 `Candidate Handoff Matrix` 小节会把 candidate 的 target URL、推荐命令和离线验证命令放到同一张表里，方便贡献者不打开 `cases/manifest.json` 也能获得基本复现上下文。

报告中的 `Candidate Evidence Bundle Commands` 小节会为每个 candidate 输出 human 和 JSON 两种 `cliany-site cases --case-id <id> --evidence-bundle` 命令。`Candidate Promotion Evidence Summary` 小节会汇总所有 candidate 子任务的状态、`primary_next_task`、primary next action、`primary_next_task_acceptance_criteria`、`llm_live_preflight_evidence_field_count` 和 `llm_live_preflight_evidence_fields_sha256`，方便维护者先决定本周该推进哪项证据、要收集哪种完成证明，以及 doctor preflight blocker 应贴回哪些字段。`LLM Live Preflight Evidence Fields` 小节会列出 `summary.llm_live_preflight`、`checks[llm_live].details.error_code` 等同一组字段；`scripts/release_readiness.py --json` / `--report` 也会用 `case_promotion_llm_live_preflight_evidence_fields`、字段数和 hash 暴露这组 release gate 证据。`Candidate Promotion Command Plan Summary` 小节会展示 `promotion_command_plan_summary.all_declared`、`missing_command_count` 和缺失 case/task，维护者可以在创建 issue 前先确认每个 candidate 都有 `llm_live_preflight`、adapter package、metadata validation、online smoke 四步可执行命令。`Candidate Promotion Tasks` 小节会把 candidate 的 `promotion` 清单和 `promotion_evidence` 状态转成可复制 issue body，包括 `Promotion Command Plan`、`Acceptance Criteria`、package asset、metadata validation、online smoke 三类验收证据、当前状态、下一步动作，以及“不要提前标记 active”“不要依赖真实 LLM key 或写入 repo runtime 状态”等非目标。JSON 校验输出中的 `promotion_command_plan_missing_tasks` 可用于在创建 issue 前拦截缺少 live preflight、`explore` 或 adapter smoke 命令的 candidate；`acceptance_criteria` 和 `primary_next_task_acceptance_criteria` 可用于拦截“命令已跑但完成证据没有贴齐”的交接问题。`python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues` 生成的 artifacts README 也会在 `Candidate Summary` 中展示 `Primary Evidence Status`、`Primary Acceptance Criteria`、`doctor_preflight_evidence_fields`，并在 `Candidate Promotion Evidence Summary` 中展示 `primary_next_task_acceptance_criteria`、`case_promotion_evidence_primary_llm_live_preflight_required`、`case_promotion_evidence_primary_llm_live_preflight_blocker_comment`、`case_promotion_evidence_primary_doctor_preflight_blocker_comment` 和任务级 `Acceptance Criteria`，让创建 GitHub issue 前的审阅面与 case report 保持一致。

`search-extraction-gap` 的最小复现页面固定在 [tests/fixtures/search_extraction_gap.html](../tests/fixtures/search_extraction_gap.html)，用于离线验证搜索结果列表中链接或摘要缺失时应被判为 `partial` 质量问题。

如果本地有从 GitHub Release 下载的 demo adapter 包，可以额外检查 active 案例声明的安装包是否存在、tarball 是否安全可读、`manifest.json` 是否与 `adapter_domain` 匹配、声明文件哈希是否一致，以及 `metadata.json` 是否为 schema v3：

```bash
python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict
python scripts/release_readiness.py --packages-dir ~/.cliany-site/packages --require-packages --strict
```

如果要给 candidate 案例补齐 adapter package evidence，使用显式 candidate 包检查命令，按 `<domain>-<version>.cliany-adapter.tar.gz` 约定定位候选包：

```bash
python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --include-candidate-packages --strict
```

当包校验失败时，`scripts/validate_cases.py --report` 会在 Package 列输出 `next:` 建议，例如重新生成 schema v3 metadata、修正 `adapter_domain`、重建 hash 或补齐 `commands.py` / `metadata.json`。这些建议只帮助维护者定位 release asset 问题，不会自动修改 `~/.cliany-site/packages`。

## 下一步

- 在正式发版前，把 GitHub Release 候选 demo adapter 包下载到 `~/.cliany-site/packages`，再运行 `scripts/release_readiness.py --packages-dir ~/.cliany-site/packages --require-packages --strict`。
- 将 `search-extraction-gap` 继续拆成更细的抽取能力设计任务：列表检测、字段映射、任务级验收。当前已用最小 HTML fixture 固定 partial 字段缺失语义，并让 `browser extract --strict-quality` 与生成的 `list-` / `search-` 数据命令都能把空结果或字段缺失判为 `E_EMPTY_RESULT`。
