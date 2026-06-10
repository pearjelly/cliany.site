# 10 分钟成功路径

**适用版本：** v0.14.2+  
**目标：** 先跑通一个真实 adapter，再决定是否配置 LLM 生成自己的命令。

## 路径 A：先验证 CLI 与真实 demo

这条路径优先验证安装、命令入口、adapter 安装和只读执行体验。它不要求你先配置 LLM key。

### 1. 安装

```bash
pip install cliany-site
cliany-site --version
```

源码开发时：

```bash
git clone https://github.com/pearjelly/cliany.site.git
cd cliany.site
pip install -e ".[dev,test]"
```

### 2. 检查本机环境

```bash
cliany-site doctor
```

先看 human summary 中的三类提示。Chrome/CDP 或 LLM key 的错误不一定阻塞 demo adapter 的静态安装，但会影响 `login` 和 `explore`。

- `必须修复`：先处理，否则关键路径不可用。
- `建议处理`：建议处理；例如没有 LLM key 时仍可先安装/执行已有 adapter。
- `诊断信息`：通常无需动作。

摘要中的 `下一步` 会直接告诉你当前应该先运行真实 demo adapter、配置 LLM key，还是先修复必须项。

自动化脚本可以使用 JSON：

```bash
cliany-site doctor --json
```

重点看 `data.summary`：

- `must_fix`：先处理，否则关键路径不可用。
- `should_fix`：建议处理；例如没有 LLM key 时仍可先安装/执行已有 adapter。
- `info`：诊断信息，通常无需动作。
- `capabilities`：按 `manage_adapters`、`run_browser_workflows`、`generate_adapters` 展示当前可用路径和 blockers。
- `recommended_next_step`：和 human 输出中的 `下一步` 一致，可用于脚本判断后续引导。

### 3. 下载一个 demo adapter

到 [GitHub Release v0.14.1](https://github.com/pearjelly/cliany.site/releases/tag/v0.14.1) 下载只读 demo adapter，例如：

```bash
cliany-site market install ./issues.apache.org.cliany-adapter-v0.14.0.tar.gz
cliany-site list --json
cliany-site verify issues.apache.org --json
```

### 4. 执行只读命令

```bash
cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json
```

预期结果：

- 命令输出是 `{ok, data, error, meta}` JSON envelope。
- `ok=true` 时，`data` 中应包含只读查询结果。
- 如果第三方 demo 站点临时不可用，把问题按站点可用性处理，不要先假设本地安装失败。

更多案例见 [cases/README.md](../cases/README.md)。

## 路径 B：生成自己的站点命令

这条路径会调用 LLM 并连接 Chrome/CDP，适合在路径 A 跑通后继续。

### 1. 配置 LLM

Anthropic:

```bash
export CLIANY_LLM_PROVIDER=anthropic
export CLIANY_ANTHROPIC_API_KEY="sk-ant-..."
```

OpenAI-compatible:

```bash
export CLIANY_LLM_PROVIDER=openai
export CLIANY_OPENAI_API_KEY="sk-..."
```

### 2. 准备 Chrome

cliany-site 可以自动管理 Chrome，也可以连接你自己启动的 CDP：

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.cliany-site/chrome-profile"
```

### 3. 探索并生成 adapter

```bash
cliany-site explore "https://github.com" "搜索 cliany.site 仓库并查看 README" --json
cliany-site list --json
```

### 4. 执行生成命令

生成的 domain 和 command 以 `cliany-site list --json` 输出为准，例如：

```bash
cliany-site github.com search --query "cliany.site" --json
```

## 常见分叉

| 情况 | 下一步 |
|------|--------|
| 没有 LLM key | 先跑路径 A 的 demo adapter、`list`、`verify`、`market` |
| 没有 Chrome/CDP | 先跑 `verify`、`list`、`market install`，再处理 `doctor` 提示 |
| 使用 Obscura provider | 目前不要用它跑 `explore`；Chrome 仍是探索默认路径 |
| 命令成功但没有业务数据 | 记录为任务级失败，参考 [搜索抽取复盘](../cases/cliany-site-case-review.md) |
| 第三方 demo 站点不可用 | 在案例库中标记 `degraded`，保留 adapter 离线校验 |

## 判断是否成功

一次有效的首次成功应满足：

- `cliany-site --version` 正常。
- `cliany-site doctor` 返回可读摘要和 `下一步`；`cliany-site doctor --json` 返回结构化 JSON 与 `recommended_next_step`。
- 至少一个 demo adapter 能安装、列出、验证。
- 至少一个只读命令返回 JSON envelope。
- 如果继续使用 `explore`，生成结果能被 `list` 发现，并能用 `--json` 执行。

## 跑通后的下一步

- 想贡献新的公开只读场景：使用 GitHub 的 `Real Demo Case Proposal` issue 模板，准备目标 URL、只读工作流、期望 CLI 命令、离线 JSON envelope 样例和验证方式。
- 想把候选场景变成案例库条目：更新 [cases/manifest.json](../cases/manifest.json)，补充 `cases/examples/` 下的样例输出，再运行 `python scripts/validate_cases.py --strict`。
- 想提交 PR：参考 [贡献者上手地图](contributor-starter.md)，按改动类型选择最小验证范围。
