# cliany-site Skill

将任意网页工作流自动化为可调用 CLI 命令的 AI Agent Skill。

[![OpenCode](https://img.shields.io/badge/OpenCode-skill-blue?style=flat)](https://opencode.ai/docs/skills/)
[![Claude Code](https://img.shields.io/badge/Claude_Code-skill-purple?style=flat)](https://code.claude.com/docs/en/skills)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-skill-orange?style=flat)](https://clawhub.ai)
[![License](https://img.shields.io/badge/License-Apache_2.0-green?style=flat)](/LICENSE)

## 概述

cliany-site 通过 Chrome CDP 协议捕获页面可访问性树（AXTree），借助 LLM（Claude/GPT-4o）将网页操作转化为可执行的 Python/Click CLI 命令。此 Skill 让 AI 编程助手能够直接调用 cliany-site 来自动化任意网页工作流。

**核心能力：**
- 零侵入式网页探索（基于 AXTree，非 DOM 注入）
- LLM 驱动的工作流分析与代码生成
- 标准 JSON 信封输出，适合 agent 解析
- 跨命令 Session 持久化
- 按域名动态加载生成的 adapter 子命令
- 增量合并：重复 explore 不破坏已有命令

## 安装

### OpenCode

```bash
# 全局安装（所有项目可用）
mkdir -p ~/.config/opencode/skills/cliany-site
cp SKILL.md ~/.config/opencode/skills/cliany-site/SKILL.md

# 或项目级安装
mkdir -p .opencode/skills/cliany-site
cp SKILL.md .opencode/skills/cliany-site/SKILL.md
```

### Claude Code / OpenClaw

```bash
# 全局安装
mkdir -p ~/.claude/skills/cliany-site
cp SKILL.md ~/.claude/skills/cliany-site/SKILL.md

# 或 OpenClaw 专用路径
mkdir -p ~/.openclaw/skills/cliany-site
cp SKILL.md ~/.openclaw/skills/cliany-site/SKILL.md
```

### Codex

```bash
mkdir -p ~/.codex/skills/cliany-site
cp SKILL.md ~/.codex/skills/cliany-site/SKILL.md
```

### 一键安装（推荐）

```bash
bash scripts/install.sh
```

自动检测已安装的 AI 编程工具并安装到对应目录。

## 前置条件

1. Python 3.11+，已安装 `cliany-site`（`pip install -e .`）
2. Chrome 浏览器（cliany-site 可自动启动 CDP 调试实例）
3. LLM API Key：`CLIANY_ANTHROPIC_API_KEY` 或 `CLIANY_OPENAI_API_KEY`

## 使用示例

安装 Skill 后，直接在 AI 编程助手中描述需求：

```
帮我自动化 GitHub 上的仓库搜索工作流
```

```
用 cliany-site 检查一下环境是否准备好了
```

```
登录 https://example.com 然后探索提交表单的工作流
```

AI 助手会自动调用 cliany-site 的相关命令完成操作。

## 项目主页

- GitHub: https://github.com/pearjelly/cliany.site
- 文档: https://cliany.site

## 许可证

Apache License 2.0
