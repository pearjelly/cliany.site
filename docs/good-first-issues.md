# Good First Issues

**适用版本：** v0.14.4+
**目标：** 给首次贡献者一组不需要真实 LLM key、不依赖第三方站点在线、能用本地命令验证的贡献入口。

这些任务不是 GitHub issue 的替代品，而是维护者创建 `good first issue` 时的候选池。每条任务都要能被拆成一个小 PR，并在 PR 描述里写清验证命令。

## 选择原则

- 默认离线：优先使用 fixture、文档测试、schema 校验或 `CLIANY_QA_OFFLINE=1`。
- 范围单一：一次只改一个模块、一个案例或一条文档路径。
- 用户价值明确：让新用户更容易跑通、让案例更可信、让错误更好复现。
- 验证可复制：PR 中必须贴出至少一个本地命令输出。

## 候选任务

| Label | 任务 | 主要文件 | 验证 |
|-------|------|----------|------|
| `docs` | 改进 10 分钟成功路径中的某一步说明，减少新用户第一次运行时的分叉 | `docs/quickstart-10min.md`, `README.md`, `README.zh.md` | `git diff --check` |
| `cases` | 为一个公开只读工作流补候选案例、离线 JSON envelope 样例和 `promotion` 清单 | `cases/manifest.json`, `cases/examples/` | `python scripts/validate_cases.py --strict` |
| `cases` | 把一个已有 candidate 的晋级阻塞拆成 adapter package、metadata validation、online smoke 三个可执行子任务 | `cases/README.md`, `cases/manifest.json` | `python scripts/validate_cases.py --report /tmp/cliany-case-report.md` |
| `cases` | 为 candidate 的 `adapter_package` 子任务整理包名、发布草案和 release asset 检查清单 | `cases/README.md`, `docs/releases/` | `python scripts/validate_cases.py --json` |
| `cases` | 为 candidate 的 `metadata_validation` 子任务补充离线验收说明或失败样例 | `cases/README.md`, `scripts/validate_cases.py`, `tests/test_validate_cases.py` | `pytest tests/test_validate_cases.py -q --no-cov` |
| `cases` | 为 candidate 的 `online_smoke` 子任务整理只读命令、质量字段和 PR 证据模板 | `cases/README.md`, `docs/good-first-issues.md` | `git diff --check` |
| `cases` | 把 `case-catalog-report` 中 Candidate Promotion Tasks / 带 `Reproduction Context` 和 `Evidence Bundle` 的 Issue Body Template 复制成 GitHub issue 草稿 | `scripts/validate_cases.py`, `cases/README.md` | `python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md` |
| `cases` | 为 candidate promotion issue 附上机器可读证据包，并用 `primary_next_task` 标出首要 case/task/status/evidence，用 `promotion_command_plan` 标出含 `llm_live_preflight` 的四步执行计划 | `docs/good-first-issues.md`, `cases/manifest.json` | `python -m cliany_site --json cases --case-id pypi-project-search --evidence-bundle --json` |
| `doctor` | 为一个已有 doctor check 补充更具体的 action 文案，并覆盖 human/JSON 输出 | `src/cliany_site/commands/doctor.py`, `tests/test_doctor_v3.py` | `pytest tests/test_doctor_v3.py -q --no-cov` |
| `release` | 改进 release readiness 或 cadence 的 `next_actions` 文案，让阻塞项更可执行 | `scripts/release_readiness.py`, `scripts/check_release_cadence.py` | `python scripts/release_readiness.py --json` 和 `pytest tests/test_release_readiness.py tests/test_release_cadence.py -q --no-cov` |
| `extract` | 为抽取质量补一个空结果、全空字段或部分缺字段的离线 fixture 回归 | `tests/fixtures/`, `tests/test_extract_quality.py` | `pytest tests/test_extract_quality.py tests/test_search_extraction_gap_fixture.py -q --no-cov` |
| `metadata` | 为 adapter metadata 或 package manifest 增加一个离线校验用例 | `src/cliany_site/metadata.py`, `scripts/validate_cases.py`, `tests/` | 相关 pytest + `ruff check` |

## Issue 拆分清单

维护者把上表任务转成 GitHub issue 时，至少保留这些字段，避免 `good first issue` 变成不可复现的泛泛建议：

- **期望改动范围**：明确要改的文件、模块或文档段落，避免顺手重构。
- **推荐验证命令**：复制上表验证列中的命令，并说明是否需要 `CLIANY_QA_OFFLINE=1`。
- **相关文件链接**：指向主要文件、fixture、issue 模板或案例 manifest。
- **复现上下文**：candidate promotion issue 应保留 `Issue Body Template` 里的 `Reproduction Context`，包括 target URL、candidate commands 和 offline validation commands。
- **证据包命令**：candidate promotion issue 应附上 `cliany-site cases --case-id <id> --evidence-bundle --json` 输出，并优先引用其中的 `primary_next_task`、`primary_next_task_runbook` 和 `promotion_command_plan`，方便维护者确认 pending tasks、当前 evidence、首要 case/task/status、下一步动作，以及 adapter package、metadata validation、online smoke 对应的执行命令。使用 `python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues` 生成 issue artifacts 时，先审阅 README `Candidate Summary` 中的 `Primary Evidence Status` / `Primary Acceptance Criteria`，并对比 `case_promotion_evidence_primary_runbook_steps` / hash 是否漂移，再创建 GitHub issue。
- **验收证据**：要求 PR 描述粘贴本地命令结果，文档改动至少包含 `git diff --check`。
- **明确非目标**：写清不需要真实 LLM key、不要访问第三方站点、不要写入 `~/.cliany-site/` 运行时状态。

## 不适合第一次贡献

- 需要真实 OpenAI/Obscura key 的 explore 成功率调优。
- 依赖第三方站点实时可用的端到端测试。
- metadata schema 的破坏性变更。
- 重写 CI workflow、provider 抽象或 action runtime。
- 把 `~/.cliany-site/` 下的 adapter/session/snapshot 运行时状态写进仓库。

## 维护者使用方式

创建 GitHub issue 时，从上表选一个任务，并补上：

- 期望改动范围。
- 推荐验证命令。
- 相关文件链接。
- 明确的非目标，例如“不需要真实 LLM key”“不要访问第三方站点”。

如果任务来自真实案例库，优先引用 `cases/manifest.json` 中的 `promotion` 字段，保持 issue、case report 和 release readiness artifact 的下一步一致。
如果任务来自 candidate promotion，优先复制带 `Reproduction Context`、`Promotion Command Plan` 和 `Evidence Bundle` 的 `Issue Body Template`，并附上 `cliany-site cases --case-id <id> --evidence-bundle --json` 的机器可读输出；把 `primary_next_task`、`primary_next_task_runbook`、`promotion_command_plan` 和 `case_promotion_evidence_primary_runbook_steps` 写进 issue 摘要或首条评论，让 issue 描述和 `cases/manifest.json` 中的 `promotion_evidence` 保持一致。
