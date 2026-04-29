# cliany-site

[![PyPI version](https://img.shields.io/pypi/v/cliany-site)](https://pypi.org/project/cliany-site/)
[![Python](https://img.shields.io/pypi/pyversions/cliany-site)](https://pypi.org/project/cliany-site/)
[![CI](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml/badge.svg)](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/pearjelly/cliany.site)](LICENSE)

> 🌐 Languages: [English](README.md) | [简体中文](README.zh.md)

> **⚠️ v0.9.0 BREAKING**: metadata schema v2 硬切换。旧 adapter（无 schema_version）将被自动拒绝。  
> 重新生成：`cliany-site explore <url> "<workflow>"`

> 将任意网页操作自动化为可调用的 CLI 命令

cliany-site 基于 browser-use 和大语言模型（LLM），通过 Chrome CDP 协议实现从网页探索到代码生成、回放的全流程自动化。一条命令探索、一条命令执行，把复杂的网页工作流变成可重复调用的 CLI 工具。

## 特性

### 核心能力

- **零侵入探索** — Chrome CDP 捕获页面 AXTree，无需注入脚本
- **LLM 驱动代码生成** — Claude / GPT-4o 理解页面语义，自动生成 Python CLI 命令
- **LLM 调用重试机制** — 网络抖动时自动重试，提升探索成功率
- **标准 JSON 输出** — 所有命令支持 `--json`，输出统一 `{success, data, error}` 信封
- **持久化 Session** — 跨命令保持 Cookie / LocalStorage 登录状态
- **动态适配器加载** — 按域名自动注册 CLI 子命令，随时扩展
- **Chrome 自动管理** — 自动检测并启动 Chrome 调试实例
- **Extract 数据抽取** — 支持从页面提取结构化数据，保存为 Markdown

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

### v0.9.x 新功能

- **Metadata Schema v2 硬切换** — 强制使用 schema_version=2，旧 adapter 自动拒绝并提示 `cliany-site explore <url> "<workflow>"` 重新生成
- **智能自愈 (`--heal`)** — AXTree 快照 diff + selector 热修复，无需重新 explore；支持修复上限（cap）和旁路记录（sidecar）
- **静态校验 (`verify`)** — 不打开浏览器，检查 adapter schema、签名、依赖完整性；`cliany-site verify <domain> --json`
- **自描述端点 (`--explain`)** — `cliany-site --json --explain` 输出机器可读的 Agent 契约，便于自动化集成
- **AGENT.md 自动改写** — 项目 AGENT.md 含哨兵+hash，新功能上线自动改写，保持 agent 契约最新
- **原子命令系统** — generated commands 调用可复用的 atom commands，而非内嵌 CDP 操作，跨适配器共享
- **统一信封 (`ok()`)** — 所有内置命令使用统一 `{success, data, error}` 输出格式
- **Doctor 扩展健康检查** — 涵盖 registry / legacy adapter 检测 / agent-md 一致性验证
- **断点续执行 (`--resume`)** — adapter 命令失败后记录断点，支持从断点恢复；`cliany-site <domain> <command> --resume`

## 快速开始 (v0.9.0+)

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
```

也支持 `.env` 文件配置，查找顺序：`~/.config/cliany-site/.env` → `~/.cliany-site/.env` → 项目目录 `.env` → 环境变量。

### 验证环境

```bash
cliany-site doctor --json
```

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

```bash
# 打包适配器
cliany-site market publish github.com --version 1.0.0

# 安装适配器
cliany-site market install ./github.com.cliany-adapter.tar.gz

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
| `verify <domain>` | `[--json]` | 静态校验 adapter schema、签名、依赖完整性 |
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

**全局选项：** `--json` `--verbose` `--debug` `--cdp-url <ws://host:port>` `--headless` `--sandbox` `--explain`

## 架构概览

```
cliany-site/src/cliany_site/
├── cli.py              # 主入口，SafeGroup 全局异常捕获
├── config.py           # 统一配置中心（环境变量 + .env）
├── errors.py           # 异常层级体系 + 错误码
├── response.py         # JSON 信封 {success, data, error}
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

## 贡献指南 / Contributing

欢迎参与贡献！请查阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境搭建、代码规范和 PR 流程。

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR workflow.

## 限制说明

- 需要 Chrome/Chromium（自动启动或手动 `--remote-debugging-port=9222`）
- 需要有效的 LLM API Key（Anthropic 或 OpenAI）
- 生成的命令依赖页面 DOM 结构，大幅页面改版后可能需要重新 explore（小幅变化由模糊匹配和自愈机制处理）
- Session 不跨浏览器 Profile 共享
- 跨域 iframe 默认启用递归采集（可通过 `CLIANY_CROSS_ORIGIN_IFRAMES` 配置）

## 更新日志 / Changelog

查看完整更新日志：[CHANGELOG.md](CHANGELOG.md)

See full changelog: [CHANGELOG.md](CHANGELOG.md)
