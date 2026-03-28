---
name: cliany-site
description: Use when the user wants to automate web workflows into CLI commands via Chrome CDP and LLM. Supports exploring pages, generating adapters, and replaying actions through the cliany-site tool.
license: Apache-2.0
compatibility: opencode, claude-code, openclaw, codex
metadata:
  homepage: "https://github.com/pearjelly/cliany.site"
  version: "0.1.1"
---

# cliany-site Skill

## 概述

`cliany-site` 将任意网页工作流自动化为可执行的 CLI 命令。它通过 Chrome CDP 协议捕获页面可访问性树（AXTree），借助 LLM（Claude/GPT-4o）分析工作流并生成对应的 Python/Click 命令行适配器，以标准 JSON 格式输出结果。

## 何时使用

- 用户想要自动化网页工作流（表单提交、搜索、导航等）
- 用户想把网页操作变成可重复执行的 CLI 命令
- 用户想检查 cliany-site 环境是否就绪
- 用户想管理网站登录会话
- 用户想查看或运行已生成的适配器命令
- 用户提到 "cliany-site"、"网页自动化"、"CDP"、"浏览器 CLI" 等关键词

## 前置条件

1. **Python 3.11+**，已安装 `cliany-site`（`pip install -e .`）
2. **Chrome 浏览器**（cliany-site 可自动启动 CDP 调试实例，或手动 `--remote-debugging-port=9222`）
3. **LLM API Key** — 至少配置一个：
   - `CLIANY_ANTHROPIC_API_KEY`（推荐）
   - `CLIANY_OPENAI_API_KEY`
   - 旧版 `ANTHROPIC_API_KEY`（仍兼容）

运行 doctor 命令验证：

```bash
cliany-site doctor --json
```

成功时输出：
```json
{
  "success": true,
  "data": {"cdp": true, "llm": true, "adapters_dir": "/Users/you/.cliany-site/adapters"},
  "error": null
}
```

## 安装

```bash
git clone https://github.com/pearjelly/cliany.site.git
cd cliany.site
pip install -e .

# 验证
cliany-site --version
cliany-site doctor --json
```

### LLM 配置

通过环境变量或 `.env` 文件配置：

```bash
# Anthropic（推荐）
export CLIANY_LLM_PROVIDER=anthropic
export CLIANY_ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI 替代方案
export CLIANY_LLM_PROVIDER=openai
export CLIANY_OPENAI_API_KEY="sk-..."
```

配置文件查找顺序（优先级从低到高）：
1. `~/.config/cliany-site/.env`
2. `~/.cliany-site/.env`
3. 项目目录 `.env`
4. 系统环境变量

## 命令参考

### doctor — 环境检查

```bash
cliany-site doctor [--json]
```

检查所有前置条件：CDP 连接、LLM Key、adapter 目录结构。

**输出字段：**
- `cdp` (bool)：Chrome CDP 是否可用
- `llm` (bool)：LLM API Key 是否已配置
- `adapters_dir` (str)：adapter 存储路径

**始终先运行 doctor** 确认环境就绪。

### login — 网站登录

```bash
cliany-site login <url> [--json]
```

打开指定 URL，等待用户手动完成登录，自动保存 Session 至 `~/.cliany-site/sessions/`。

**使用场景：** 在探索需要认证的工作流之前。

### explore — 探索并生成工作流

```bash
cliany-site explore <url> <workflow_description> [--json]
```

核心命令，流程如下：
1. 通过 CDP 连接 Chrome
2. 捕获页面 AXTree
3. 将 AXTree 和工作流描述发送给 LLM
4. LLM 规划并逐步执行操作
5. 在 `~/.cliany-site/adapters/<domain>/` 生成 Click CLI 适配器

**参数：**
- `url`：目标网页 URL
- `workflow_description`：工作流描述（自然语言）

**示例：**
```bash
cliany-site explore "https://github.com" "搜索 cliany.site 仓库并查看 README" --json
```

### list — 列出适配器

```bash
cliany-site list [--json]
```

列出所有已生成的 adapter 域名。

### 执行适配器命令

```bash
cliany-site <domain> <command> [args...] [--json]
```

**示例：**
```bash
cliany-site github.com search --query "browser-use" --json
```

### tui — 终端管理界面

```bash
cliany-site tui
```

可视化管理适配器、查看操作日志。

## 输出格式

所有命令均支持 `--json` 输出标准 JSON 信封：

```json
{
  "success": true,
  "data": { "..." },
  "error": null
}
```

失败时：
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

**常见错误码：**

| 错误码 | 含义 |
|--------|------|
| `CDP_UNAVAILABLE` | Chrome 未启动或未开启 9222 端口 |
| `LLM_KEY_MISSING` | 未设置 LLM API Key |
| `COMMAND_NOT_FOUND` | 未知命令或 adapter 不存在 |
| `EXPLORE_FAILED` | 工作流探索失败 |

**退出码：** `0` 成功，`1` 失败

## 典型工作流

### 第 1 步：验证环境
```bash
cliany-site doctor --json
```

### 第 2 步：登录（如需）
```bash
cliany-site login "https://target-site.com" --json
```

### 第 3 步：探索工作流
```bash
cliany-site explore "https://target-site.com" "描述工作流" --json
```

### 第 4 步：使用生成的命令
```bash
cliany-site list --json
cliany-site target-site.com <generated-command> [args] --json
```

### 第 5 步：增量探索
重复 explore 同一域名可添加新命令，已有命令不受影响。

## 自动化脚本示例

```bash
#!/bin/bash
set -e

# 检查环境
result=$(cliany-site doctor --json)
if ! echo "$result" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); exit(0 if d['success'] else 1)"; then
  echo "环境检查失败"
  exit 1
fi

# 探索工作流
cliany-site explore "https://example.com" "提交联系表单" --json

# 执行生成的命令
cliany-site example.com submit --name "Test" --email "test@test.com" --json
```

## 架构说明

- **适配器存储**：`~/.cliany-site/adapters/<domain>/`（commands.py + metadata.json）
- **Session 存储**：`~/.cliany-site/sessions/`
- **AXTree 选择器**：模糊元素匹配，能适应轻微的 UI 变化
- **增量合并**：重复 explore 同一域名时自动合并，不破坏已有命令
- **原子命令**：可复用的操作（登录、搜索等），跨适配器共享

## 安全与隐私

- cliany-site 通过 CDP 连接本地 Chrome 实例（`localhost:9222`）
- LLM API 调用发送页面 AXTree（可访问性结构，非视觉内容）至配置的 Provider
- Session Cookie 存储在本地 `~/.cliany-site/sessions/`
- 生成的适配器仅包含 Click CLI 代码和元数据，不嵌入凭证
- 除配置的 LLM API 外，不向其他外部端点发送数据

## 外部端点

| 端点 | 用途 | 发送的数据 |
|------|------|-----------|
| 配置的 LLM API（Anthropic/OpenAI） | 工作流分析与操作规划 | 页面 AXTree 结构、工作流描述 |
| `localhost:9222` | Chrome CDP 连接 | CDP 协议命令 |

## 信任声明

使用此 Skill 时，页面可访问性树数据将发送至您配置的 LLM Provider（Anthropic 或 OpenAI）进行工作流分析。请仅在信任您的 LLM Provider 处理您浏览页面的结构化内容时使用。

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| `CDP_UNAVAILABLE` | 运行 `cliany-site doctor` 自动启动 Chrome，或手动启动 `--remote-debugging-port=9222` |
| `LLM_KEY_MISSING` | 设置 `CLIANY_ANTHROPIC_API_KEY` 或 `CLIANY_OPENAI_API_KEY` |
| explore 未产生命令 | 提供更具体的工作流描述；确保页面已完全加载 |
| 适配器命令执行失败 | 页面结构可能已变化，重新运行 explore 重新生成 |
| 登录会话过期 | 重新运行 `cliany-site login <url>` |

## QA 验证

```bash
bash qa/doctor_check.sh
bash qa/run_all.sh
```
