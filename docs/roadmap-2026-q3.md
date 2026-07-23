# cliany-site 2026 Q3 路线图

- **制定日期：** 2026-06-10
- **校准日期：** 2026-07-23
- **基线版本：** v0.16.271
- **目标周期：** 2026-06-10 ~ 2026-08-05
- **公开视图：** [public-roadmap.md](public-roadmap.md)
- **配套节奏：** [release-cadence.md](release-cadence.md)、[每周维护者循环](weekly-maintainer-loop.md)

## 一句话定位

cliany-site 要成为「把真实网页工作流沉淀成可复用 CLI/SDK/API 能力」的开源项目，而不是只展示一次性浏览器自动化 demo 的玩具。

## 已完成校准

2026-06-10 的原始路线图以 v0.14.2 为基线；到 2026-07-23 已准备发布到 v0.16.271。过去几周的实际进展已经提前完成了原计划中的多项基础建设：

- 首次成功路径：README、README.zh、官网和 `doctor` 输出已经围绕 10 分钟路径、真实 demo、LLM live preflight 和可执行下一步重新组织。
- 真实案例库：`cliany-site cases` 已成为案例发现、单案例展开、issue template、evidence bundle 和 promotion plan 的统一入口。
- 发布门禁：`release_readiness.py`、`check_release_cadence.py`、`check_release_publication.py` 已覆盖版本号、CHANGELOG、草案、CI/release workflow、远端 refs、tag 决策、每日发布上限、GitHub Release、PyPI 和 publication audit。
- Candidate 晋级证据：candidate 案例已经具备 promotion command plan、acceptance criteria、LLM preflight blocker handoff、issue artifacts 和 machine-readable evidence summary。
- 运行可靠性：`E_LLM_UNAVAILABLE`、结构化抽取质量、adapter 生成安全审计、Windows/Embodied CI 和离线案例验收已经进入默认维护面；list/search 命令可用 `expects_nonempty=false` 将合法零匹配保留为 `ok=true`，同时继续输出 `data.quality`，重新 explore 合并、打包和安装也会保留该声明。

这意味着 Q3 后续重点不再是「搭脚手架」，而是把已搭好的维护系统转换成用户可见的真实案例、可分发 adapter 资产和稳定集成路径。

截至 2026-07-22，PyPI、npm 和 crates.io package-search 案例仍是 candidate，尚未晋级为 active；`cliany-site doctor --llm-live --json` 的 live LLM preflight 仍是生成 adapter package 与执行 online smoke 前必须保留的 blocker，而不是可由文档或离线证据替代的成功证明。

## 当前判断

下一阶段的核心问题是：

1. 用户是否能在不理解内部发布/证据系统的情况下，看到清晰的公开路线和真实可运行场景。
2. 维护者是否能把 candidate 案例推进到 active，而不是只持续生产交接字段。
3. adapter 包是否能从本地生成资产变成可下载、可安装、可验证、可回滚的 release asset；远程安装必须绑定 HTTPS 和 SHA-256。
4. 探索、抽取、回放失败时，错误是否足够可解释，可以直接转化为测试、issue 或修复。
5. SDK/API/headless/remote CDP 是否有可复制示例，证明项目不只适合本机手动 CLI。

## 北极星指标

| 指标 | 2026-07-01 基线 | 2026-08-05 目标 |
|------|------------------|------------------|
| 新用户首次成功路径 | 文档路径已成型，仍需更多真实资产支撑 | 10 分钟内完成安装、doctor、真实 demo replay，并知道下一步是否需要 LLM |
| 真实案例资产 | 4 个 active，3 个 candidate，1 个 known gap | 至少 8 个可验证案例；candidate 晋级证据和 release asset 可追溯 |
| adapter 可维护性 | metadata/package 校验和安全审计已进入门禁 | demo adapter 有 release asset、安装验证、回归报告和失败修复建议 |
| 探索/抽取可靠性 | LLM outage 和抽取质量已有结构化信号 | 常见失败能定位到 provider、页面状态、selector、字段质量或能力边界 |
| 集成可用性 | CLI 主路径强，SDK/API/headless 示例偏弱 | SDK、HTTP API、headless/remote CDP 均有可复制最小示例 |
| 发布节奏 | v0.16.257，GitHub Release / PyPI / 官网发布流程已跑通，PyPI latest 缓存滞后可由版本专属 endpoint 复核，官网 alias 由 `vercel inspect www.cliany.site` 复核，primary adapter handoff command aliases 与 doctor preflight evidence state 已进入维护者路径 | 每天 1~3 个可验证版本；每周至少 3 天有提交；发布后 publication audit 为绿 |

## 双视图维护规则

- 本文件是维护者执行版，允许包含版本节奏、门禁、验收命令和内部风险。
- [public-roadmap.md](public-roadmap.md) 是用户公开版，只描述用户会获得什么能力、哪些功能稳定、哪些仍实验性。
- 两份文档必须共享同一阶段划分：已完成、近期、中期、Q3 后段。
- 当本文件调整对外承诺、目标日期或能力状态时，同步检查公开版；当只调整内部命令、CI 或 release gate 时，不强制更新公开版。

## 产品主线

### 主线 A：真实案例与首次成功

目标：让新用户先跑通一个可理解的只读真实场景，再决定是否配置 LLM 生成自己的命令。

优先交付：

- 将 `pypi-project-search`、`npm-package-search`、`crates-io-crate-search` 从 candidate 推进到 active。
- 每个 active 案例都有 release adapter 包、离线 metadata 校验、只读 online smoke 摘要和示例 JSON envelope。
- README、README.zh、官网和公开路线图只展示已验证路径，不把 candidate 描述成已可用能力。

### 主线 B：adapter 生命周期

目标：adapter 能被生成、审计、打包、安装、验证、回滚，并在失败时有可执行修复建议。

优先交付：

- 明确 release asset 命名、hash、metadata schema v3、domain 校验和安装回滚路径。
- `market publish/install/rollback` 形成可复制的真实流程。
- `verify`、`validate_cases.py --packages-dir`、release readiness package gate 输出同一套失败原因。
- 生成代码安全审计继续阻止危险调用，不为通过测试放宽安全边界。

### 主线 C：探索、抽取与失败解释

目标：降低「偶尔成功」的浏览器自动化印象，强调可观测、可恢复、可解释。

优先交付：

- 继续扩充搜索/列表抽取质量 fixture，明确默认严格零匹配、`expects_nonempty=false` 的合法零匹配、字段缺失、partial quality 和严格模式错误；所有路径保留 `data.quality`。
- `explore` 失败区分 LLM provider、CDP、页面就绪、AXTree 语义匹配和能力不支持。
- 保持 AXTree 语义匹配原则，不引入脆弱 CSS selector 兜底。
- 失败报告能直接转成 issue 模板字段或回归测试输入。

### 主线 D：贡献者与维护自动化

目标：外部贡献者能在零真实 LLM key 环境下复现、修复、验证；维护者能按证据推进 release train。

优先交付：

- 贡献者入口继续围绕 `CLIANY_QA_OFFLINE=1`、case catalog、release readiness artifact 和 good-first issue 组织。
- Candidate issue artifacts 只作为证据交接，不替代真实 adapter package / online smoke。
- CI 继续扩展而不是重写，PR 默认不依赖真实 LLM key。
- 每周维护循环以 readiness/report 的 gate issues 为起点，而不是凭聊天记录判断。

### 主线 E：SDK/API 与远程运行

目标：证明 cliany-site 不只适合本机交互式 CLI，也能被服务、脚本和 headless 环境集成。

优先交付：

- SDK 最小示例覆盖 explore、execute、error envelope。
- HTTP API 示例覆盖启动、调用、错误处理和 session 边界。
- Docker/headless/remote CDP 路径重新验证，并记录不支持或实验性边界。
- Obscura 继续标注为实验性 provider；除非真实成功率明显提升，不新增 provider。

## 阶段计划

> 版本号是方向锚点，不再假设每周只对应一个 minor。每日仍按 1~3 个可验证版本发布；达到每日上限后只做下一版准备。

| 周期 | 主题 | 主要交付 | 验收标准 |
|------|------|----------|----------|
| 2026-06-10 ~ 2026-06-21 | 基础设施成型 | 首次成功路径、cases 命令、发布门禁、LLM preflight、CI 稳定化 | 已发布到 v0.16.256；Release/CI/Embodied CI 与 publication audit 全绿 |
| 2026-06-22 ~ 2026-07-07 | 真实案例晋级 | 3 个 candidate 案例补齐 adapter package、metadata validation、online smoke | `validate_cases.py --include-candidate-packages --strict` 通过；至少 1 个 candidate 晋级 active |
| 2026-07-08 ~ 2026-07-21 | adapter 生命周期闭环 | release asset 下载/安装/验证/回滚流程，package gate 与 failure hints 对齐 | README/官网展示可复制安装路径；package gate 失败给出明确 next action |
| 2026-07-22 ~ 2026-07-28 | 探索与抽取质量 | 搜索/列表抽取质量扩展，失败 envelope 与 issue 模板衔接 | 新增离线 fixture 和 pytest；默认严格零匹配、合法零匹配和 partial quality 都能稳定复现，且保留 `data.quality` |
| 2026-07-29 ~ 2026-08-05 | 1.0 alpha readiness | SDK/API/headless 示例，稳定/实验性能力清单，破坏性变更候选清单 | 发布 alpha readiness report；公开路线图标注下一阶段稳定承诺 |

## 近期执行队列

1. 选择一个 candidate 作为首要晋级对象，优先 `pypi-project-search`，因为 Python 用户与 PyPI 发布路径更贴近。
2. 运行 `cliany-site doctor --llm-live --json`，如果返回 `summary.llm_live_preflight.ready=false`、`E_LLM_UNAVAILABLE` provider connection failure 或 `generate_adapters.ready=false`，记录 blocker，不伪造 adapter package evidence。
3. 生成 candidate adapter 包后放入 `~/.cliany-site/packages`，运行 candidate package validation。
4. 完成只读 online smoke，记录 JSON envelope 摘要和 `data.quality`；只有案例明确要求非空结果时才以 `row_count>0` 为验收条件，合法零匹配须由 `expects_nonempty=false` 明示。
5. 将案例状态从 candidate 改为 active 前，同步 README、README.zh、官网、cases README 和公开路线图。

## 发布与验证节奏

每日发布以“小而可验证”为原则：先读 readiness/plan 输出，再选择一条能在当天闭环的切片，最后按标准发版流程公开到 GitHub Release、PyPI 和官网。每天发布 1~3 个版本；当 `daily_release_limit_ok=false` 或 `release_count_today` 已达到 `max_daily_releases`，当天不再创建 tag。

推荐维护命令：

```bash
python scripts/plan_next_iteration.py --remote --json
python scripts/release_readiness.py --strict --remote
python scripts/validate_cases.py --strict
CLIANY_QA_OFFLINE=1 pytest tests/ -q
python scripts/check_release_publication.py --remote --json
```

如果改动涉及 candidate package：

```bash
python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --include-candidate-packages --strict
python scripts/release_readiness.py --packages-dir ~/.cliany-site/packages --require-packages --strict
```

如果改动涉及官网，继续按 `AGENTS.md` 的 Vercel 步骤从 `site/` 部署到 `cliany.site` 项目。

## 不做清单

- 不为了显得强大继续堆新 provider，除非能提高真实成功率。
- 不把真实 LLM key 放进 PR 门禁或 fork PR workflow。
- 不新增脆弱 CSS selector 兜底；元素定位继续以 AXTree 语义匹配为主。
- 不在 repo 内写入 adapter/session/snapshot 运行时状态。
- 不重写现有 CI 基础设施；只能扩展或新增。
- 不把 candidate 案例包装成 active 能力；缺少 release asset 或 online smoke 时必须保持 candidate。
- 不扩大 v1.0 前的破坏性 schema 变更，除非有迁移命令和清晰公告。

## 每周复盘问题

每周发布前回答这 7 个问题：

1. 本周版本让真实用户更容易成功了吗？
2. 是否至少推进了一个真实案例、adapter asset 或失败语义？
3. 是否有至少一个可复现案例或测试保护这次改动？
4. 是否更新了 CHANGELOG、README/官网或相关 docs？
5. 是否仍满足零真实 LLM key 的 PR 门禁？
6. 是否满足每日发布上限和每周三天提交记录？
7. 下周最小可交付版本是什么？
