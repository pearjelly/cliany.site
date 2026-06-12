# 更新日志

本项目的所有显著更改都将记录在此文件中。

本文件的格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
并且本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

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

[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.16.29...HEAD
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
