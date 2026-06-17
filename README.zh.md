# cliany-site

[![PyPI version](https://img.shields.io/pypi/v/cliany-site)](https://pypi.org/project/cliany-site/)
[![Python](https://img.shields.io/pypi/pyversions/cliany-site)](https://pypi.org/project/cliany-site/)
[![CI](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml/badge.svg)](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/pearjelly/cliany.site)](LICENSE)

> 🌐 Languages: [English](README.md) | [简体中文](README.zh.md)

> **🧪 v0.14.4 质量门禁**：结构化抽取现在返回 `data.quality`，`browser extract --strict-quality` 可将空结果或关键字段缺失判为 `E_EMPTY_RESULT`，生成的 `list-` / `search-` 命令也会输出抽取质量；`scripts/release_readiness.py` 会在发版前统一检查案例库、CI 门禁、发布草案、CHANGELOG 和每周提交节奏。详见 [v0.14.4 发布草案](docs/releases/v0.14.4-draft.md)。
> **🧭 v0.14.3 开源可用性增强**：新增 Q3 路线图、10 分钟成功路径、真实 demo 案例索引、面向人的 `doctor` 摘要、贡献者上手地图和本地发布节奏检查，详见 [CHANGELOG.md](CHANGELOG.md)。
> **🤖 v0.14.2 自主改进闭环**：新增 5 维度自主改进脚手架——确定性 benchmark 回归测试、headless Chrome 具身验证、Dependabot 依赖哨兵、运行时反馈闭环、Agent 守则文档，使 OpenCode 可触发自主演进循环，详见 [CHANGELOG.md](CHANGELOG.md)。  
> **🔧 v0.14.1 修复与增强**：新增 `E_PAGE_NOT_READY` / `E_PARSE_FAILED` / `E_EMPTY_RESULT` 错误码、修复 navigate/extract/action_runtime 失败语义、doctor 同时识别 `AGENT.md` / `AGENTS.md`、Obscura 能力声明修正（navigation/cookies）、list-/search- 命令空结果 opt-in 检测、Obscura 友好错误提示，详见 [CHANGELOG.md](CHANGELOG.md)。  
> **✨ v0.14.0 真实演示上线**：官网案例 2 (企业 CRM) 和案例 3 (团队工具箱) 现已支持真实的公开 demo 站点 — SuiteCRM Demo、ASF Jira、ASF Confluence、ASF Jenkins。详见 [体验真实演示](#体验真实演示)。
> **✨ v0.13.0 开发者体验加固**：修复 loader RuntimeError bug、稳定 test_session_lock 测试、补全 ERROR_FIX_HINTS 27 条提示、新增 SuccessEnvelope/ErrorEnvelope TypedDict、核心模块 pyright strict（0 errors）、doctor 命令增强（versions + adapter_stats），详见 [CHANGELOG.md](CHANGELOG.md)。  
> **🔒 v0.12.0 稳定性与质量加固**：新增文件锁保护（manifest/session 并发写安全）、tar 路径穿越防护、Obscura 下载重试、统一错误码体系，详见 [CHANGELOG.md](CHANGELOG.md)。  
> **🚀 v0.11.0 已发布**: 新增实验性 Obscura 浏览器提供者、多平台二进制支持及生命周期管理。  
> ⚠️ **v0.10.0 BREAKING**: metadata schema v3 硬切换。请使用 `cliany-site migrate` 升级旧版适配器。

> 将任意网页操作自动化为可调用的 CLI 命令

cliany-site 基于 browser-use 和大语言模型（LLM），通过 Chrome CDP 协议实现从网页探索到代码生成、回放的全流程自动化。一条命令探索、一条命令执行，把复杂的网页工作流变成可重复调用的 CLI 工具。

## 特性

### 核心能力

- **零侵入探索** — Chrome CDP 捕获页面 AXTree，无需注入脚本
- **LLM 驱动代码生成** — Claude / GPT-4o 理解页面语义，自动生成 Python CLI 命令
- **LLM 调用重试机制** — 网络抖动时自动重试，提升探索成功率
- **可重试 LLM 上游故障信号** — `explore --json` 会把网关、限流或服务不可用归类为 `E_LLM_UNAVAILABLE`，返回清洗后的重试详情，而不是原始 HTML。
- **统一 JSON 信封** — 所有命令支持 `--json`，输出机器可读的 `{ok, data, error, meta}` 信封 (v1)
- **持久化 Session** — 跨命令保持 Cookie / LocalStorage 登录状态
- **动态适配器加载** — 按域名自动注册 CLI 子命令，随时扩展
- **自动浏览器管理** — 自动管理 Chrome 调试实例或实验性 Obscura 二进制文件
- **带质量信号的数据抽取** — 支持从页面提取结构化数据、保存 Markdown 报告，并通过 `data.quality` 或严格模式下的 `E_EMPTY_RESULT` 标记空结果与字段缺失

### 开发体验

- **适配器增量合并** — 重复 explore 同一网站时智能合并，保留已有命令
- **原子命令系统** — 自动提取可复用的原子操作，跨适配器共享
- **实时进度反馈** — explore/execute 过程中展示 Rich 进度条和 NDJSON 流式事件
- **智能自愈** — AXTree 快照对比，selector 热修复，无需重新 explore
- **CSS Selector 候选预计算** — 预生成多个 selector 候选，提升元素匹配韧性
- **断点续执行** — adapter 命令失败后记录断点，可通过 `cliany-site <domain> <command> --resume` 从断点恢复
- **会话式探索** — `--interactive` 逐步确认、`--extend <domain>` 增量扩展、探索录像自动保存（`~/.cliany-site/recordings/`）

### 企业级特性

- **Headless & 远程浏览器** — 支持 `--headless` 和 `--cdp-url ws://host:port`，可在服务器/Docker 中运行
- **Obscura 生命周期管理** — 专属 `obscura` 命令组，支持二进制安装、回滚和健康检查
- **YAML 工作流编排** — 声明式多步骤工作流，步骤间数据传递 + 条件判断 + 重试策略
- **数据驱动批量执行** — CSV/JSON 批量参数，并发控制，汇总报告
- **Session 加密存储** — Fernet 对称加密 + 系统 Keychain 密钥管理
- **沙箱执行模式** — `--sandbox` 限制跨域导航和危险操作；当前优先作用于 CLI adapter 执行路径
- **生成代码安全审计** — AST 静态分析检测 eval/exec/os.system 等危险模式

### 生态集成

- **Python SDK** — `from cliany_site import explore, execute`，程序化调用
- **HTTP API** — `cliany-site serve --port 8080` 启动 REST API 服务
- **适配器市场** — 打包、安装、卸载、回滚适配器，团队共享自动化能力
- **TUI 管理界面** — 基于 Textual 的终端 UI，可视化管理适配器
- **iframe/Shadow DOM** — 递归 AXTree 采集，跨域 iframe 和 Shadow DOM 穿透

### v0.11.0 新功能

- **Obscura 实验性提供者** — 集成 Obscura 轻量级浏览器后端。通过 `CLIANY_BROWSER_PROVIDER=obscura` 启用。
- **Obscura 命令组** — 新增 `cliany-site obscura` 命令：`install/use/status/clean/rollback/upgrade/doctor`。
- **多平台支持** — 为 `darwin-arm64`, `darwin-x86_64`, `linux-x86_64`, `windows-x86_64` 提供预构建二进制文件。
- **能力快照与特性门禁** — 浏览器提供者抽象层，支持显式能力路由。
- **注意**: `explore` 目前在 Obscura 下被门禁（暂不支持）。探索功能仍默认使用 Chrome。

### v0.10.0 新功能 (BREAKING)

> ⚠️ **BREAKING**: metadata schema v3 硬切换。v2 适配器必须进行迁移。  
> 运行 `cliany-site migrate --json` 以升级所有旧版适配器。

- **DOM 剪枝与复合控件** — 4 层 AXTree 剪枝（深度/数量/角色/压缩）+ 自动提取 `<select>` / `<input type=date>` / `<input type=file>` 选项元数据。减少 30-50% 的提示词 Token 消耗。
- **Lazy Adapter Registry** — `discover()` 仅读取 `metadata.json`；`get(domain, cmd)` 按需加载。CLI 启动速度提升 2-5 倍。
- **修复缓存** — 修复结果缓存于 `~/.cliany-site/adapters/{domain}/repair-cache.json`（每域名 LRU 100 条）。重复故障可跳过 LLM 调用。
- **网络与控制台捕获** — 探索阶段自动捕获网络请求（超过 1MB 停止）和控制台日志（500 条环形缓冲区），存储在 StepRecord 中。
- **能力路由** — 在探索时嗅探 API 端点；回放时自动在浏览器/API 间路由。通过 `--force-browser` 强制走浏览器模式。
- **`migrate` 命令** — `cliany-site migrate [--json] [--dry-run]` 扫描并升级所有旧版适配器至 schema v3，并保留 `.bak` 备份。
- **诊断模式** — `cliany-site --diagnose --json <domain> <cmd>` 在失败时触发 LLM 诊断，输出 `root_cause`（根本原因）+ `suggested_fix`（建议修复）。通过 `diagnose_if_enabled()` 内置于生成的适配器模板中。

### v0.9.x 新功能

- **Metadata Schema v2 硬切换** — 强制使用 schema_version=2，旧 adapter 自动拒绝并提示 `cliany-site explore <url> "<workflow>"` 重新生成
- **智能自愈 (`--heal`)** — AXTree快照 diff + selector 热修复，无需重新 explore；支持修复上限（cap）和旁路记录（sidecar）
- **静态校验 (`verify`)** — 不打开浏览器，检查 adapter schema、签名、依赖完整性；`cliany-site verify <domain> --json`
- **自描述端点 (`--explain`)** — `cliany-site --json --explain` 输出机器可读的 Agent 契约，便于自动化集成
- **AGENT.md 自动改写** — 项目 AGENT.md 含哨兵+hash，新功能上线自动改写，保持 agent 契约最新
- **原子命令系统** — generated commands 调用可复用的 atom commands，而非内嵌 CDP 操作，跨适配器共享
- **统一信封 (`ok()`)** — 所有内置命令使用统一 `{ok, data, error, meta}` 输出格式
- **Doctor 扩展健康检查** — 涵盖 registry / legacy adapter 检测 / agent-md 一致性验证
- **断点续执行 (`--resume`)** — adapter 命令失败后记录断点，支持从断点恢复；`cliany-site <domain> <command> --resume`

## 快速开始 (v0.11.0+)

首次上手建议先走 [10 分钟成功路径](docs/quickstart-10min.md)：先运行真实 demo adapter，再配置 LLM 生成自己的命令；跑通后可通过 `Real Demo Case Proposal` 路径贡献新的公开只读案例。

### 安装

```bash
# PyPI 安装
pip install cliany-site

# 或源码安装
git clone https://github.com/pearjelly/cliany.site.git
cd cliany.site
pip install -e .
```

### 基础流程

```bash
# 环境确认
cliany-site doctor --json

# explore 前可选：真实调用一次 provider 做 live preflight
cliany-site doctor --llm-live --json

# 查看维护中的真实 demo 案例
cliany-site cases --json
cliany-site cases --status candidate --promotion-plan
cliany-site cases --json --status candidate --promotion-plan
cliany-site cases --case-id pypi-project-search --json
cliany-site cases --case-id pypi-project-search --issue-template
cliany-site cases --case-id pypi-project-search --evidence-bundle
cliany-site cases --case-id pypi-project-search --evidence-bundle --json

# 探索网页工作流（需要 LLM）
cliany-site explore "https://github.com" "搜索后查看结果" --json

# 查看已生成的命令
cliany-site list --json

# 执行已生成的命令（无需 LLM）
cliany-site github.com search --query "cliany-site" --json

# 静态校验
cliany-site verify github.com --json

# 查询 Agent 契约
cliany-site --json --explain
```

### 配置

```bash
# LLM Provider（二选一）
export CLIANY_LLM_PROVIDER=anthropic
export CLIANY_ANTHROPIC_API_KEY="sk-ant-..."

# 或 OpenAI
export CLIANY_LLM_PROVIDER=openai
export CLIANY_OPENAI_API_KEY="sk-..."

# 实验性：Obscura 浏览器提供者
# export CLIANY_BROWSER_PROVIDER=obscura
```

也支持 `.env` 文件配置，查找顺序：`~/.config/cliany-site/.env` → `~/.cliany-site/.env` → 项目目录 `.env` → 环境变量。

如果 `explore --json` 返回 `E_LLM_UNAVAILABLE`，表示 LLM provider 返回了可重试的上游故障，例如 `502 Bad Gateway`、限流或服务暂不可用。JSON 信封会包含 `details.retryable`、`details.status_code` 和 `details.phase`；请稍后重试，或切换 `CLIANY_LLM_PROVIDER` / `CLIANY_OPENAI_BASE_URL`。这不代表生成的 adapter 或 AXTree selector map 已损坏。

### 实验性：Obscura 浏览器提供者

Obscura 是一个轻量级浏览器提供者，目前处于**实验性**阶段。探索功能仍默认使用 Chrome。

> **注意**: Obscura 暂不支持 `explore` (AXTree/Accessibility)。请将其用于执行现有适配器或轻量级导航任务。

#### 支持平台
- `darwin-arm64` (Apple Silicon)
- `darwin-x86_64` (Intel Mac)
- `linux-x86_64`
- `windows-x86_64`

#### 设置与使用
```bash
# 1. 安装 Obscura 二进制文件 (版本 >= 0.1.0)
cliany-site obscura install 0.1.0 --json

# 2. 启用 Obscura 作为提供者
export CLIANY_BROWSER_PROVIDER=obscura

# 3. 检查状态
cliany-site obscura status --json

# 4. 切回 Chrome
unset CLIANY_BROWSER_PROVIDER
```

更多详情请参阅 [Obscura 实验性指南](docs/walkthroughs/obscura-experimental-guide.md)。

### 验证环境

```bash
cliany-site doctor --json
cliany-site doctor --llm-live --json
```

默认 `doctor` 只检查本地配置、CDP、目录和 key，不会真实调用 LLM provider。准备运行耗时较长的 `explore` 前，可以追加 `--llm-live` 做一次真实 provider 预检；如果遇到网关、限流或服务不可用，会以 `llm_live` warning 返回 `details.error_code=E_LLM_UNAVAILABLE`。

## 使用示例

### 基础流程

```bash
# 1. 探索工作流
cliany-site explore "https://github.com" "搜索仓库并查看 README" --json

# 2. 查看已生成命令
cliany-site list --json

# 3. 执行生成的命令
cliany-site github.com search --query "browser-use" --json
```

### 结构化抽取质量

```bash
# 从当前浏览器页面抽取卡片数据
cliany-site browser extract \
  --selector ".result-card" \
  --mode list \
  --fields-json '{"title": ".title", "url": "a@href"}' \
  --json

# 如果所有行为空或关键字段缺失，则直接失败
cliany-site browser extract \
  --selector ".result-card" \
  --mode list \
  --fields-json '{"title": ".title", "url": "a@href"}' \
  --strict-quality \
  --json
```

结构化抽取响应会包含 `data.quality`。生成的 `list-` 和 `search-` adapter 命令也会输出这份质量摘要，并在抽取质量为空或关键字段部分缺失时返回 `E_EMPTY_RESULT`，让自动化脚本能区分“命令执行了”和“确实拿到了可用数据”。

### 会话式探索（v0.8）

```bash
# 交互式探索（每步确认）
cliany-site explore "https://github.com" "搜索仓库" --interactive

# 增量扩展已有适配器
cliany-site explore "https://github.com" "查看 Issues 列表" --extend github.com

# 回放探索录像
cliany-site replay github.com --step
```

### Python SDK

```python
from cliany_site.sdk import ClanySite

async with ClanySite() as cs:
    result = await cs.explore("https://github.com", "搜索仓库")
    adapters = await cs.list_adapters()
```

## 体验真实演示

以下适配器可在 [GitHub Release v0.14.1](https://github.com/pearjelly/cliany.site/releases/tag/v0.14.1) 的资源中下载。
可维护案例索引见 [cases/README.md](cases/README.md) 与 [cases/manifest.json](cases/manifest.json)。
可以运行 `cliany-site cases --json`，直接从 CLI 查看 active demo、candidate 工作流、离线验证命令和 candidate 晋级下一步；`promotion_evidence_summary.primary_next_task` 会把自动化指向第一个待推进的 candidate 任务，`promotion_evidence_summary.primary_next_task_acceptance_criteria` 会直接给出该任务必须贴上的完成证据。追加 `--promotion-plan` 可直接输出所有匹配 candidate 的晋级队列；同时加 `--json` 可读取 `promotion_plan.primary_next_item`、每个 candidate 的首要任务和未完成 `task_queue`。使用 `cliany-site cases --case-id pypi-project-search --json` 可以展开单个案例的验证和晋级详情；去掉 `--json` 时会输出适合复制交接的 Promotion Tasks。追加 `--issue-template` 可直接打印带 Acceptance Criteria 的 candidate 晋级 GitHub issue body；同时加 `--json` 会额外输出 `issue_template_primary_task`，让自动化不用解析 Markdown 就能读取首要待补证据任务。追加 `--evidence-bundle` 可输出结构化本地证据清单；再加 `--json` 可得到机器可读的 evidence bundle，其中 `promotion_command_plan` 会列出 adapter package、metadata validation 和 online smoke 的执行命令，`acceptance_criteria` 会列出每个任务必须附上的完成证据。运行 `python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues` 可生成可审阅的候选 issue artifacts；其中 README 会在创建 issue 前展示 `Primary Evidence Status`、`Primary Acceptance Criteria` 和 `primary_next_task_acceptance_criteria`。

### SuiteCRM Demo (企业 CRM)
```bash
# 1. 安装适配器
cliany-site market install ./demo.suiteondemand.com.cliany-adapter-v0.14.0.tar.gz

# 2. 登录 (会打开浏览器 — 请使用 https://demo.suiteondemand.com/ 提供的 demo 账号)
cliany-site login https://demo.suiteondemand.com/

# 3. 查询账户 (登录后无需开启浏览器)
cliany-site demo.suiteondemand.com list-accounts --limit 5 --json
```

### ASF Jira (任务追踪)
```bash
cliany-site market install ./issues.apache.org.cliany-adapter-v0.14.0.tar.gz
cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json
```

### ASF Confluence (Wiki)
```bash
cliany-site market install ./cwiki.apache.org.cliany-adapter-v0.14.0.tar.gz
cliany-site cwiki.apache.org search-pages --space SPARK --query "release" --json
```

### ASF Jenkins (构建状态)
```bash
cliany-site market install ./builds.apache.org.cliany-adapter-v0.14.0.tar.gz
cliany-site builds.apache.org list-jobs --json
```

> **免责声明**：以上 demo 站点由第三方维护，可能临时不可用。cliany-site 仅提供 CLI 适配层，不控制 demo 数据或可用性。


### HTTP API

```bash
# 启动服务
cliany-site serve --port 8080

# 调用 API
curl http://localhost:8080/doctor
curl http://localhost:8080/adapters
curl -X POST http://localhost:8080/explore \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com", "workflow": "搜索仓库"}'
```

### YAML 工作流编排

```yaml
# workflow.yaml
name: GitHub 搜索流程
steps:
  - name: 搜索仓库
    adapter: github.com
    command: search
    params:
      query: "cliany-site"
  - name: 查看详情
    adapter: github.com
    command: view
    params:
      repo: "$prev.data.results[0].name"
```

```bash
cliany-site workflow run workflow.yaml --json
cliany-site workflow validate workflow.yaml --json
```

### 批量执行

```bash
# 从 CSV 批量执行
cliany-site workflow batch github.com search data.csv --concurrency 3 --json
```

### 适配器市场

运行时目录、`.cliany-adapter.tar.gz` 包格式、兼容性约束与回滚流程见 [Adapter 生命周期与包格式](docs/adapter-lifecycle.md)。

```bash
# 打包适配器
cliany-site market publish github.com --version 1.0.0

# 安装适配器
cliany-site market install ~/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz

# 回滚
cliany-site market rollback github.com
```

## 命令参考

| 命令 | 参数 | 说明 |
|------|------|------|
| `doctor` | `[--json]` | 检查环境（CDP、LLM Key、目录结构） |
| `login <url>` | `[--json]` | 打开 URL 等待登录，保存 Session |
| `explore <url> <workflow>` | `[--json] [--interactive] [--extend <domain>] [--record]` | 探索工作流，生成 adapter |
| `list` | `[--json]` | 列出已生成的 adapter |
| `cases` | `[--case-id <id>] [--status <status>] [--detail] [--issue-template] [--evidence-bundle] [--promotion-plan] [--json]` | 列出维护中的真实 demo 案例和候选工作流 |
| `verify <domain>` | `[--json]` | 静态校验适配器 schema、签名、依赖完整性 |
| `migrate` | `[--json] [--dry-run]` | 迁移所有旧版适配器至 schema v3 |
| `replay <domain>` | `[--session <id>] [--step]` | 回放探索录像，终端展示每步截图和动作 |
| `check <domain>` | `[--json] [--fix]` | 检查适配器健康状态 |
| `tui` | | 启动 TUI 管理界面 |
| `serve` | `[--host] [--port]` | 启动 HTTP API 服务 |
| `market publish <domain>` | `[--version] [--json]` | 打包导出适配器 |
| `market install <path>` | `[--force] [--json]` | 安装适配器包 |
| `market uninstall <domain>` | `[--json]` | 卸载适配器 |
| `market rollback <domain>` | `[--index] [--json]` | 回滚到备份版本 |
| `workflow run <file>` | `[--json] [--dry-run]` | 执行 YAML 工作流 |
| `workflow validate <file>` | `[--json]` | 验证工作流文件 |
| `workflow batch <adapter> <cmd> <data>` | `[--concurrency] [--json]` | 批量执行 |
| `report list` | `[--domain] [--json]` | 列出执行报告 |
| `report show <id>` | `[--json]` | 查看报告详情 |
| `<domain> <command>` | `[--json] [args...]` | 执行适配器中的命令 |

**全局选项：** `--json` `--verbose` `--debug` `--cdp-url <ws://host:port>` `--headless` `--sandbox` `--explain` `--force-browser` `--diagnose`

## 架构概览

```
cliany-site/src/cliany_site/
├── cli.py              # 主入口，SafeGroup 全局异常捕获
├── config.py           # 统一配置中心（环境变量 + .env）
├── errors.py           # 异常层级体系 + 错误码
├── response.py         # JSON 信封 {ok, data, error, meta} (v1)
├── logging_config.py   # 结构化日志（JSON format + 脱敏）
├── sdk.py              # Python SDK（同步 + 异步）
├── server.py           # HTTP API 服务（aiohttp）
├── security.py         # Session 加密（Fernet + Keychain）
├── sandbox.py          # 沙箱策略执行
├── audit.py            # 代码安全审计（AST 分析）
├── marketplace.py      # 适配器市场（打包/安装/回滚）
├── browser/            # CDP 连接 + AXTree + Chrome 启动 + iframe
├── explorer/           # LLM 工作流探索 + 原子提取 + 验证
├── codegen/            # 代码生成（模板/参数推导/去重/合并）
├── workflow/           # YAML 编排 + 批量执行
├── commands/           # 内置 CLI 命令
└── tui/                # Textual 终端 UI
```

## 安全特性

- **Session 加密**：Fernet 对称加密，密钥存入系统 Keychain（macOS Keychain / Linux Secret Service），无 Keychain 时降级为文件密钥
- **沙箱模式**：`--sandbox` 限制 navigate 同域、禁止 `javascript:` / `file://` / `data:` URL、禁止文件下载；本轮闭环优先覆盖 CLI adapter 执行路径
- **代码审计**：codegen 输出自动 AST 扫描，检测 `eval` / `exec` / `os.system` / `subprocess` 等危险调用

## 路线图 / Roadmap

当前迭代计划见 [docs/roadmap-2026-q3.md](docs/roadmap-2026-q3.md)。发布与提交节奏见 [docs/release-cadence.md](docs/release-cadence.md)：每天至少一个可验证版本，每周至少三天有提交记录。维护者可按 [每周维护者循环](docs/weekly-maintainer-loop.md) 选择下一块可验证发布切片，并读取 `scripts/release_readiness.py --json`、`scripts/check_release_cadence.py --json` 或 `scripts/check_release_publication.py --json` 输出的 `next_actions` 与 `primary_next_action`，同时确认最新本地 tag 是否已经公开可见。自动化可比对 `next_actions_sha256`、`publication_blockers_sha256`、`publication_next_actions_sha256`、`publication_publish_commands_sha256` 和 `target_tag_commands_sha256`，无需解析 Markdown report 就能检测发布动作是否漂移。

## 贡献指南 / Contributing

欢迎参与贡献！请查阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境搭建、代码规范和 PR 流程。

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR workflow.

首次贡献者可以从 [贡献者上手地图](docs/contributor-starter.md) 或 [Good First Issues](docs/good-first-issues.md) 候选清单开始；这两条路径默认不需要真实 LLM key，并附带本地验证命令。

## 限制说明

- 需要 Chrome/Chromium（自动启动或手动 `--remote-debugging-port=9222`）
- 需要有效的 LLM API Key（Anthropic 或 OpenAI）
- 生成的命令依赖页面 DOM 结构，大幅页面改版后可能需要重新 explore（小幅变化由模糊匹配和自愈机制处理）
- Session 不跨浏览器 Profile 共享
- 跨域 iframe 默认启用递归采集（可通过 `CLIANY_CROSS_ORIGIN_IFRAMES` 配置）

## 更新日志 / Changelog

查看完整更新日志：[CHANGELOG.md](CHANGELOG.md)

See full changelog: [CHANGELOG.md](CHANGELOG.md)
