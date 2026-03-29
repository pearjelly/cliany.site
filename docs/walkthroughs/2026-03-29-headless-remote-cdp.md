# Headless 模式 & 远程 CDP 连接 — Phase 3.1

**日期**: 2026-03-29
**阶段**: Phase 3 — 场景拓展 (v0.4.0)

## 背景

原版 cliany-site 仅支持连接本地 `localhost:9222` 上的 Chrome 实例，无法用于远程服务器、Docker 容器或 CI 环境。Phase 3.1 增加了：

1. **远程 CDP 连接** — 通过 `--cdp-url` 指定任意 CDP 端点
2. **Headless 模式** — 通过 `--headless` 启动无头 Chrome
3. **容器化部署** — Dockerfile + docker-compose 一键运行

## 变更内容

### 3.1.1 远程 CDP 连接

**核心变更**: `src/cliany_site/browser/cdp.py`

| 新增 | 说明 |
|------|------|
| `_parse_cdp_url(url)` | 解析 `ws://host:port`、`http://host:port`、`host:port` 三种格式 |
| `CDPConnection(cdp_url=, headless=)` | 构造函数新增两个参数，回退读取 config |
| `is_remote` 属性 | 判断连接目标是否为非本地地址 |
| `_resolve_host_port()` | 统一解析主机和端口 |
| `_probe_remote()` | 异步 HTTP 探测远程 CDP 是否可用 |
| `cdp_from_context(ctx)` | 工厂函数，从 Click context 提取 `cdp_url`/`headless` |

**行为差异**:

- **本地模式** (`--cdp-url` 为空或 localhost): `check_available()` 调用 `ensure_chrome()` 自动启动 Chrome
- **远程模式** (`--cdp-url` 指向远程主机): `check_available()` 仅执行 HTTP 探测，不尝试启动本地 Chrome

### 3.1.1 CLI 全局选项

**变更文件**: `src/cliany_site/cli.py`

```python
@click.option("--cdp-url", default="", help="CDP 远程地址 (ws://host:port)")
@click.option("--headless", is_flag=True, help="使用 headless 模式启动 Chrome")
```

选项值存入 `ctx.obj["cdp_url"]` 和 `ctx.obj["headless"]`，所有子命令通过 `cdp_from_context(ctx)` 读取。

### 3.1.1 子命令适配

所有内置命令和生成的 adapter 模板均已更新：

| 命令 | 文件 | 变更 |
|------|------|------|
| `doctor` | `commands/doctor.py` | `cdp_from_context(ctx)` → 传入 `_run_checks()` |
| `login` | `commands/login.py` | `cdp_from_context(ctx)` → 传入 `_capture_session()` |
| `explore` | `commands/explore.py` | `cdp_from_context()` → 传递 `cdp_url`/`headless` 给 `WorkflowExplorer` |
| `check` | `commands/check.py` | `cdp_from_context(ctx)` → 传入 `_get_current_elements()` |
| 生成的 adapter | `codegen/templates.py` | 3 种模板块均使用 `cdp_from_context(ctx)` |

### 3.1.2 Headless 模式

**变更文件**: `src/cliany_site/browser/launcher.py`

- `ensure_chrome()` 新增 `headless: bool = False` 参数
- 当 `headless=True` 时，传递 `--headless=new` 给 Chrome 启动命令

### 3.1.3 容器化部署

新增三个文件：

| 文件 | 说明 |
|------|------|
| `Dockerfile` | Python 3.11-slim + chromium + fonts-noto-cjk，默认 `CLIANY_HEADLESS=true` |
| `docker-compose.yml` | 服务定义，API Key 环境变量透传，卷挂载 `~/.cliany-site` |
| `.dockerignore` | 排除 `.venv`、`__pycache__`、`.git` 等 |

### 3.1.3 配置中心集成

**变更文件**: `src/cliany_site/config.py`

新增两个配置字段：

| 字段 | 环境变量 | 默认值 |
|------|----------|--------|
| `cdp_url: str` | `CLIANY_CDP_URL` | `""` |
| `headless: bool` | `CLIANY_HEADLESS` | `False` |

## 使用示例

```bash
# 连接远程 CDP (如 Docker 容器中的 Chrome)
cliany-site --cdp-url ws://192.168.1.100:9222 doctor --json

# 本地 headless 模式
cliany-site --headless explore "https://example.com" "查看首页" --json

# 组合使用
cliany-site --cdp-url ws://chrome-host:9222 --headless login "https://github.com" --json

# Docker 一键启动
docker compose up -d
docker compose exec cliany cliany-site doctor --json

# 环境变量方式（无需每次传参）
export CLIANY_CDP_URL=ws://192.168.1.100:9222
export CLIANY_HEADLESS=true
cliany-site doctor --json
```

## 测试覆盖

新增 `tests/test_remote_cdp.py`，38 个测试覆盖：

| 测试类 | 数量 | 覆盖范围 |
|--------|------|----------|
| `TestParseCdpUrl` | 6 | URL 解析各格式 |
| `TestCDPConnectionInit` | 5 | 构造函数参数优先级 |
| `TestIsRemote` | 6 | 本地/远程判断 |
| `TestResolveHostPort` | 4 | 主机端口解析回退 |
| `TestCheckAvailableRemote` | 3 | 远程探测 vs 本地启动 |
| `TestConnectRemote` | 2 | `is_local` 标志传递 |
| `TestCdpFromContext` | 4 | 工厂函数各场景 |
| `TestConfigCdpUrlAndHeadless` | 4 | 配置字段和环境变量 |
| `TestEnsureChromeHeadless` | 3 | headless 参数传递 |
| `TestGetPagesRemote` | 1 | 远程主机端口使用 |

## 验证结果

```
ruff check:  All checks passed!
mypy:        Success: no issues found in 50 source files
pytest:      346 passed in 0.52s
```
