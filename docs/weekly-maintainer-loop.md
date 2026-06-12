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

`plan_next_iteration.py` 会把 release readiness、publication audit、commit cadence 和 candidate cases 汇总成一个推荐切片；如果它提示最新本地 tag 尚未公开可见，先完成发布同步，再扩大下一版范围。计划 JSON、文本输出和 Markdown report 会带上 `publication_next_actions`，直接列出 publication audit 的具体待办，例如本地分支 ahead 数、tag 尚未发布和是否需要 `--remote` 复核；也会带上 `publication_worktree_clean` / `publication_worktree_status`，把 worktree 是否干净和具体 status 行带到周初计划里；也会带上 `publication_publish_commands`，把 publication audit 里的 branch/tag push 和 `python scripts/check_release_publication.py --remote --json` 复核命令直接带到周初计划里；`publication_publish_script_command` 还会给出 `--publish-script /tmp/cliany-publish-release.sh` 生成命令，方便维护者先审阅脚本再手动执行。计划 JSON、文本输出和 Markdown report 也会带上 `release_draft_issues`，把下一版 release draft 缺失或 snippet 校验失败的具体原因直接列出来，避免只看到笼统的 `release draft validation failed`。它的 Markdown 报告会输出 `Candidate Issue Metadata` 和 `Candidate Promotion Tasks`，把每个 candidate 的 issue title、labels、`adapter_package`、`metadata_validation` 和 `online_smoke` 证据项带到同一份周初计划里，并在 `Candidate Issue Body Templates` 里生成可复制的 GitHub issue body；每个 body 都包含 `Reproduction Context`，保留 target URL，并把 candidate commands 和 offline validation commands 作为子列表列出。需要批量创建候选案例任务时，`--issues-dir` 会额外写出每个 candidate 的 body 文件、`issue-metadata.json`、`publication-handoff.json`、`README.md` 和可审阅的 `create-issues.sh`，其中 `issue-metadata.json` 会保留 issue title、labels、target URL、candidate commands、offline validation commands、body file name、body file path 和 create command，artifacts `README.md` 会带 `Candidate Summary` 表，列出 case、issue body 文件、target URL 和命令数量，也会在 `Publication Handoff` 下展示 `Publication Next Actions`、`worktree_clean` 和 `Publication Publish Script`，并在审阅清单里要求先确认这些 publication next actions 已处理或明确延后，再核对复现字段；`publication-handoff.json` 会保留 publication 状态、next actions、publication next actions、worktree status 和 publish commands；脚本不会自动执行，执行前会先跑 `python scripts/check_release_publication.py --strict --json`，把 preflight JSON 写入 `/tmp/cliany-issue-publication-check.json`，避免在最新本地 release 尚未公开时继续派发新任务；如果 preflight 失败，脚本会把这份 JSON 打印出来再退出。计划 JSON 里的 `issue_artifacts_command` 和 artifacts `README.md` 会保留复现命令，例如 `python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues`，方便维护者重新生成同一批候选 issue artifacts。Markdown 报告里的 `Weekly Review` 小节会把本页最后的 6 个复盘问题和当前证据放在一起；发版前优先引用这份报告，避免手工复盘和 readiness gate 脱节。

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
