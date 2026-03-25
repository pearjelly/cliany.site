# cliany-site

将任意网页操作自动化为可调用的 CLI 命令。基于 browser-use 和 LLM，通过 CDP 协议实现从网页探索到代码生成、回放的全流程自动化。

cliany-site 是一个旨在打破网页交互与命令行界限的自动化工具。它基于 browser-use 库，利用大语言模型（LLM）对网页可访问性树（AXTree）的深度理解，将复杂的网页工作流直接转化为结构化的 Python/Click 命令行工具。

**核心工作流程：**
1. **探索阶段 (Explore)：** LLM 实时分析当前页面结构，自主规划路径并生成可执行的自动化脚本。
2. **执行阶段 (Run)：** 通过生成的 CLI 命令快速回放录制好的工作流。系统采用属性模糊匹配技术，即使网页 UI 发生微调，也能精准定位元素并稳定运行。

通过将 CDP 协议的底层控制能力与 LLM 的推理能力结合，cliany-site 让开发者能够像调用本地脚本一样操控复杂的 Web 应用，大幅提升了浏览器自动化的开发效率与维护性。

## 特性

- **零侵入探索**：通过 Chrome CDP 协议捕获页面 AXTree，自动分析工作流
- **LLM 驱动代码生成**：调用 Claude / GPT-4o 将探索结果转化为可执行 Click 命令
- **标准 JSON 输出**：所有命令支持 `--json` 选项，输出统一 `{success, data, error}` 信封
- **持久化 Session**：跨命令保持 Cookie / LocalStorage 登录状态
- **动态 Adapter 加载**：每个网站生成独立 adapter，按域名动态注册为子命令

## 快速开始

### 安装

```bash
cd cliany-site
pip install -e .
```

### Chrome CDP 配置

启动 Chrome 时开启远程调试端口：

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug

# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

验证 Chrome CDP 是否可用：

```bash
curl http://localhost:9222/json
```

### LLM API Key 配置

cliany-site 支持 Anthropic 和 OpenAI 两种 LLM Provider。

```bash
# 方式一：使用 Anthropic（默认）
export CLIANY_LLM_PROVIDER=anthropic
export CLIANY_ANTHROPIC_API_KEY="sk-ant-..."
export CLIANY_ANTHROPIC_MODEL="claude-3-5-haiku-20241022"  # 可选，默认 claude-3-5-haiku-20241022
export CLIANY_ANTHROPIC_BASE_URL="https://api.anthropic.com"  # 可选，支持代理

# 方式二：使用 OpenAI
export CLIANY_LLM_PROVIDER=openai
export CLIANY_OPENAI_API_KEY="sk-..."
export CLIANY_OPENAI_MODEL="gpt-4o-mini"  # 可选，默认 gpt-4o-mini
export CLIANY_OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选，支持代理（建议显式带 /v1）
```

**向后兼容**：旧版环境变量 `ANTHROPIC_API_KEY` 仍可使用（但不推荐）。

#### 使用 .env 文件配置

除了环境变量，cliany-site 也支持通过 `.env` 文件配置。配置文件查找顺序（优先级从低到高）：

1. `~/.config/cliany-site/.env`（XDG 用户配置）
2. `~/.cliany-site/.env`（旧版兼容路径）
3. 项目目录 `.env`（项目级配置）
4. 系统环境变量（最高优先级，会覆盖 .env 文件中的同名变量）

> OpenAI 兼容接口建议将 `CLIANY_OPENAI_BASE_URL` 配置为包含 `/v1` 的地址（如 `https://your-proxy/v1`）。若仅填写 host（如 `https://your-proxy`），程序会自动补齐 `/v1`。

示例 `.env` 文件：

```bash
# 项目目录或 ~/.cliany-site/.env
CLIANY_LLM_PROVIDER=anthropic
CLIANY_ANTHROPIC_API_KEY=sk-ant-...
CLIANY_OPENAI_API_KEY=sk-...
```

## 使用示例

### 1. 检查环境

```bash
cliany-site doctor --json
```

输出示例：
```json
{
  "success": true,
  "data": {
    "cdp": true,
    "llm": true,
    "adapters_dir": "/Users/you/.cliany-site/adapters"
  },
  "error": null
}
```

### 2. 登录网站

```bash
cliany-site login "https://github.com" --json
```

等待浏览器完成登录后，Session 自动保存至 `~/.cliany-site/sessions/`。

### 3. 探索工作流

```bash
cliany-site explore "https://github.com" "搜索 cliany.site 仓库并查看 README" --json
```

探索完成后，自动生成 adapter 至 `~/.cliany-site/adapters/github.com/`。

### 4. 查看已生成命令

```bash
cliany-site list --json
```

输出示例：
```json
{
  "success": true,
  "data": {
    "adapters": ["github.com", "example.com"]
  },
  "error": null
}
```

### 5. 执行生成的命令

```bash
cliany-site github.com search --query "browser-use" --json
```

## 命令参考

| 命令 | 参数 | 说明 |
|------|------|------|
| `doctor` | `[--json]` | 检查环境前置条件（CDP、LLM Key、目录结构） |
| `login <url>` | `[--json]` | 打开 URL 并等待手动登录，保存 Session |
| `explore <url> <workflow>` | `[--json]` | 探索 URL 工作流，生成 adapter CLI 命令 |
| `list` | `[--json]` | 列出所有已生成的 adapter |
| `<domain> <command>` | `[--json] [args...]` | 执行指定域名 adapter 中的命令 |

所有命令均支持 `--json` 选项，失败时 exit 1，成功时 exit 0。

## 架构概览

```
cliany-site
├── cli.py          主入口，SafeGroup 捕获全局异常
├── response.py     JSON 信封 {success, data, error}
├── errors.py       错误码定义（CDP_UNAVAILABLE 等）
├── session.py      Cookie/LocalStorage 持久化
├── loader.py       Adapter 动态加载与注册
├── browser/
│   ├── cdp.py      CDP WebSocket 连接
│   └── axtree.py   无障碍树捕获
├── commands/       doctor / login / explore / list
├── explorer/       WorkflowExplorer + 数据模型
└── codegen/        AdapterGenerator，LLM 代码生成
```

生成的 adapter 存放在 `~/.cliany-site/adapters/<domain>/`，包含：
- `commands.py`：Click 命令组
- `metadata.json`：生成元数据

## 限制说明

- 需要已运行并开启 `--remote-debugging-port=9222` 的 Chrome 实例
- 需要有效的 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY`
- 生成的命令依赖页面 DOM 结构，页面更新后可能需要重新 explore
- Session 不跨浏览器 Profile 共享
- 目前不支持 iframe 内元素的自动操作
