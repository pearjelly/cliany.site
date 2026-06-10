# cliany-site 2026 Q3 路线图

**制定日期：** 2026-06-10  
**基线版本：** v0.14.2  
**目标周期：** 2026-06-10 ~ 2026-08-05  
**配套节奏：** [release-cadence.md](release-cadence.md)、[weekly-maintainer-loop.md](weekly-maintainer-loop.md)

## 一句话定位

cliany-site 要成为「把真实网页工作流沉淀成可复用 CLI/SDK/API 能力」的开源项目，而不是只展示一次性浏览器自动化 demo 的玩具。

## 当前判断

从 v0.2 到 v0.14 的迭代轨迹看，项目已经完成了从 MVP 到工程化工具的第一阶段：

- v0.2~v0.5：补齐异常、日志、配置、测试、CI、workflow、SDK/API、marketplace、安全、iframe/Shadow DOM。
- v0.7~v0.10：增强多模态感知、交互式探索、resume、自愈、metadata schema、atom 命令、诊断模式。
- v0.11~v0.14：引入 Obscura provider、发布门禁、稳定性加固、失败语义、真实 demo、自主改进脚手架。

下一阶段的核心问题不是「还能加什么能力」，而是：

1. 新用户能否在 10 分钟内跑通一个有价值的真实场景。
2. 贡献者能否在没有真实 LLM key 的情况下稳定复现、修复、验证问题。
3. 生成出来的 adapter 能否被分享、安装、回归验证，并在页面变化后可维护。
4. 项目是否有稳定的周发布节奏，让外部用户看到持续演进。

## 北极星指标

| 指标 | 2026-06-10 基线 | 2026-08-05 目标 |
|------|------------------|------------------|
| 新用户首次成功路径 | README 信息完整，但真实路径偏长 | 10 分钟内完成 doctor + demo adapter + replay |
| 离线回归能力 | 已有 benchmark/embodied/QA 脚手架 | PR 默认零密钥跑完核心生成与 replay 回归 |
| 真实案例资产 | v0.14 有 4 个 demo adapter 资产 | 至少 8 个可验证案例，覆盖 CRM、DevOps、知识库、搜索/抽取 |
| adapter 可维护性 | verify/heal/check 已具备基础能力 | demo adapter 每周自动健康检查并产出报告 |
| 贡献者入口 | CONTRIBUTING + issue 模板 | good-first-issue 清单、模块地图、复现模板完整 |
| 发布节奏 | 已发布 v0.14.2 | 每周至少 1 个版本，每周至少 3 天有提交 |

## 产品主线

### 主线 A：新用户可用性

目标：让用户不需要理解所有内部架构，就能完成「安装 -> 检查 -> 运行真实 demo -> 生成自己的命令」。

优先交付：

- `doctor` 输出按「必须修复 / 建议优化 / 信息」分层。
- README 和官网提供一条最短成功路径。
- demo adapter 有明确安装、验证、执行命令。
- 无 Chrome、无 LLM key、Obscura 不支持 explore 等场景给出可执行下一步。

### 主线 B：真实案例库

目标：用真实公开站点证明项目价值，并形成稳定回归资产。

优先交付：

- 建立 `cases/` 案例索引：场景、站点、命令、验证方式、维护状态。
- 每个案例至少包含：探索目标、生成命令、示例输出、失败排查。
- 对 demo adapter 增加离线 metadata 校验和可选在线 smoke。
- 官网展示真实案例，不再新增概念性案例。

### 主线 C：adapter 生命周期

目标：把 adapter 当成可分发、可验证、可升级的开源资产。

优先交付：

- 统一 adapter 包格式说明和兼容性矩阵。
- `market` 命令文档化：publish/install/rollback 的真实流程。
- adapter 版本、schema、依赖、生成来源进入可检查 metadata。
- check/report 输出可以作为 CI artifact 保存。

### 主线 D：贡献者与自动修复闭环

目标：让外部 issue 能尽量转化为可复现输入，让 agent/maintainer 可以稳定修复。

优先交付：

- issue 模板继续收集 `doctor --json`、AXTree snapshot、错误码、版本。
- `.github/AUTONOMOUS_FIX.md` 与本路线图保持同步。
- PR 门禁默认使用 `CLIANY_QA_OFFLINE=1`，禁止依赖真实 LLM key。
- 给出 good-first-issue 与模块 ownership 提示。

### 主线 E：运行可靠性

目标：降低「偶尔成功」的浏览器自动化印象，强调可观测、可恢复、可解释。

优先交付：

- 失败语义继续收敛：空结果、页面未就绪、解析失败、能力不支持必须区分。
- report/check/replay 串起来，失败时能定位到页面、动作、selector、错误码。
- 对高风险模块持续推进 pyright/mypy strict 和 perf benchmark。

## 8 周版本计划

> 版本命名遵循 semver。用户可见能力或行为变化用 minor，纯文档/修复用 patch。每周至少发布一个版本；若本周只有文档和小修，则发布 patch。

| 周期 | 目标版本 | 主题 | 验收标准 |
|------|----------|------|----------|
| 2026-06-10 ~ 2026-06-14 | v0.14.x | 路线图与节奏固化 | 路线图、发布节奏、README 入口合并；本周已有 v0.14.2 |
| 2026-06-15 ~ 2026-06-21 | v0.15.0 | 10 分钟成功路径 | README/官网新增最短路径；`doctor` 分层提示；至少 1 个 demo adapter 可按文档跑通 |
| 2026-06-22 ~ 2026-06-28 | v0.16.0 | 真实案例库一期 | `cases/` 索引成型；4 个现有 demo adapter 有验证说明；离线 metadata 校验进入 QA |
| 2026-06-29 ~ 2026-07-05 | v0.17.0 | 贡献者入口 | good-first-issue 清单、模块地图、复现指南；CI/QA 命令按贡献者路径重排 |
| 2026-07-06 ~ 2026-07-12 | v0.18.0 | adapter 生命周期 | adapter 包格式文档、兼容性矩阵、market 真实流程验证；report artifact 样例 |
| 2026-07-13 ~ 2026-07-19 | v0.19.0 | 探索成功率与诊断 | explore 失败报告结构化；prompt/selector 关键回归样本扩充；页面未就绪诊断更清晰 |
| 2026-07-20 ~ 2026-07-26 | v0.20.0 | SDK/API 可集成性 | SDK/HTTP API 示例可复制运行；schema/response contract 文档化；至少 1 个外部集成案例 |
| 2026-07-27 ~ 2026-08-02 | v0.21.0 | 远程与容器运行 | Docker/headless/remote CDP 路径重新验证；CI 增加最小 headless smoke 或文档化门禁 |
| 2026-08-03 ~ 2026-08-05 | v0.22.0 | 1.0 alpha 门禁 | 整理实验性能力标签；列出 1.0 阻塞项；发布 alpha readiness report |

## 每周工作节奏

每周固定三类提交日，保证节奏可见：

| 日程 | 提交类型 | 典型内容 |
|------|----------|----------|
| 周一 | `docs` / `test` | 本周目标、复现样本、回归测试或案例脚本 |
| 周三 | `feat` / `fix` | 本周核心能力或主要修复 |
| 周五 | `docs` / `chore(release)` | CHANGELOG、README/官网同步、版本发布 |

如果遇到紧急 bug，可在任意日期追加 patch，但不能替代三天提交节奏。

维护者每周选择最小可交付切片时，按 [每周维护者循环](weekly-maintainer-loop.md) 先读取 readiness 报告、选择一条产品主线、补足可验证证据，再决定发版或记录阻塞。

## 不做清单

- 不为了显得强大继续堆新 provider，除非能提高真实成功率。
- 不把真实 LLM key 放进 PR 门禁或 fork PR workflow。
- 不新增脆弱 CSS selector 兜底；元素定位继续以 AXTree 语义匹配为主。
- 不在 repo 内写入 adapter/session/snapshot 运行时状态。
- 不重写现有 CI 基础设施；只能扩展或新增。
- 不扩大 v1.0 前的破坏性 schema 变更，除非有迁移命令和清晰公告。

## 每周复盘问题

每周发布前回答这 6 个问题：

1. 本周版本让真实用户更容易成功了吗？
2. 是否有至少一个可复现案例或测试保护这次改动？
3. 是否更新了 CHANGELOG、README/官网或相关 docs？
4. 是否仍满足零真实 LLM key 的 PR 门禁？
5. 是否有三天提交记录？
6. 下周最小可交付版本是什么？
