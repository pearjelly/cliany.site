# 10 分钟成功路径

**目标：** 先确认 CLI 可用，验证一个已发布的只读 demo，再决定是否配置 LLM 生成自己的命令。

## 路径 A：先验证 CLI 并查看维护中的案例

这条路径优先验证安装、命令入口和维护中的公开案例。它不要求你先配置 LLM key；只查看案例也不需要 Chrome/CDP。执行已发布 demo 的最后一条只读命令时，仍按 `doctor` 的 CDP 提示准备浏览器。

### 1. 安装

```bash
pip install cliany-site
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

先看 human summary 中的三类提示。Chrome/CDP 或 LLM key 的提示不会阻塞本路径；它们会影响后续的 `login` 和 `explore`。

- `必须修复`：先处理，否则关键路径不可用。
- `建议处理`：建议处理；例如没有 LLM key 时仍可先查看维护中的案例。
- `诊断信息`：通常无需动作。

摘要中的 `下一步` 会直接告诉你当前应该配置 LLM key，还是先修复必须项。

自动化脚本可以使用 JSON：

```bash
cliany-site doctor --json
```

重点看 `data.summary`：

- `must_fix`：先处理，否则关键路径不可用。
- `should_fix`：建议处理；例如没有 LLM key 时仍可先查看维护中的案例。
- `info`：诊断信息，通常无需动作。
- `capabilities`：按 `manage_adapters`、`run_browser_workflows`、`generate_adapters` 展示当前可用路径和 blockers。
- `recommended_next_step`：和 human 输出中的 `下一步` 一致，可用于脚本判断后续引导。
- `ready_for_existing_adapters`：当前环境是否可运行已有 adapter；和 human 输出的 `Existing adapter runtime ready` 一致。
- `ready_for_demo_adapters`：当前是否真的有可用的已发布 active demo adapter asset；只有它为 `true` 时，才执行 demo 快速路径。
- `case_catalog_quickstart`：可立即运行的案例目录命令；在获取到 adapter 包之前，先用它查看公开案例和各自的验证路径。
- `demo_adapter_quickstart`：当 `available=true`、`deprecated=false` 时，`commands` 按顺序提供固定 HTTPS + SHA-256 安装、`verify` 和只读案例命令。它只会选择 `active`、无需登录的案例，不会把 candidate 当成可安装 demo。若 `deprecated=true` 或 `available=false`，不要执行其中的命令；读取 `replacement` 并改用 `case_catalog_quickstart`。

当 `ready_for_demo_adapters=true` 时，依次执行 `data.summary.demo_adapter_quickstart.commands` 中的三条命令：先安装并校验 archive，再运行 `verify`，最后执行只读案例命令。安装和静态校验成功只证明归档可用；第三方站点的实际返回仍以最后一条命令的 JSON envelope 为准。

### 3. 查看维护中的案例

```bash
cliany-site cases
```

这个命令会列出维护中的公开案例、状态和各案例当前的验证路径。先选择一个你关心的案例；需要机器可读输出时，可使用：

```bash
cliany-site cases --json
```

预期结果：

- 终端会显示案例库及每个案例的首条命令。
- `--json` 输出是 `{ok, data, error, meta}` JSON envelope；`ok=true` 时，`data` 中包含案例和验证信息。
- 以当前 `cases` 输出为准，不要从历史文档复制旧的发布归档文件名。

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
| 没有 LLM key | 路径 A 到 `cases` 即可完成；需要生成自己的命令时再配置 LLM |
| 没有 Chrome/CDP | 先完成路径 A，再按 `doctor` 提示为 `explore` 准备 Chrome |
| 使用 Obscura provider | 目前不要用它跑 `explore`；Chrome 仍是探索默认路径 |
| 命令成功但没有业务数据 | 记录为任务级失败，参考 [搜索抽取复盘](../cases/cliany-site-case-review.md) |

## 判断是否成功

一次有效的首次成功应满足：

- `cliany-site doctor` 返回可读摘要和 `下一步`；`cliany-site doctor --json` 返回结构化 JSON 与 `recommended_next_step`。
- `cliany-site cases` 能列出维护中的案例；`cliany-site cases --json` 返回结构化 JSON。
- 如果继续使用 `explore`，生成结果能被 `list` 发现，并能用 `--json` 执行。

## 跑通后的下一步

- 想贡献新的公开只读场景：使用 GitHub 的 `Real Demo Case Proposal` issue 模板，准备目标 URL、只读工作流、期望 CLI 命令、离线 JSON envelope 样例和验证方式。
- 想把候选场景变成案例库条目：更新 [cases/manifest.json](../cases/manifest.json)，补充 `cases/examples/` 下的样例输出，再运行 `python scripts/validate_cases.py --strict`。
- 想提交 PR：参考 [贡献者上手地图](contributor-starter.md)，按改动类型选择最小验证范围。
