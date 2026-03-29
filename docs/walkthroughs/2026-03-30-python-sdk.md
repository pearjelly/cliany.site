# Phase 4.2 Python SDK + HTTP API 服务

**日期:** 2026-03-30
**Phase:** 4.2 (v0.5.0 生态建设)
**状态:** 已完成

## 概述

为 cliany-site 提供程序化调用接口——Python SDK（异步上下文管理器 + 同步便捷函数）和 HTTP API 服务，使其能被外部程序、Jupyter Notebook、CI/CD 管道等场景集成。

## 变更清单

### 4.2.1 Python SDK — ClanySite 异步上下文管理器

**文件:** `src/cliany_site/sdk.py` (新增, ~625 行)

- `ClanySite` 类支持 `async with` 上下文管理器，自动管理 CDP 连接生命周期
- 核心方法：`explore()`, `execute()`, `login()`, `doctor()`, `list_adapters()`, `save_session()`, `navigate()`, `get_page_info()`
- 所有方法返回标准信封 `{"success": bool, "data": {...}, "error": ...}`，不抛异常、不 print、不 sys.exit
- Lazy 初始化：CDP 和 BrowserSession 在首次使用时创建，`doctor()` / `list_adapters()` 无需浏览器
- `_run_async()` 辅助函数处理同步调用场景（无事件循环用 `asyncio.run`，有事件循环用 `ThreadPoolExecutor`）

### 4.2.2 同步便捷函数

**文件:** `src/cliany_site/sdk.py` (同文件底部)

- `explore()`, `execute()`, `login()`, `doctor()`, `list_adapters()` 同步版本
- 内部创建临时 `ClanySite` 实例，通过 `_run_async()` 桥接异步调用
- 公开 API 导出至 `src/cliany_site/__init__.py`

### 4.2.3 HTTP API 服务

**文件:** `src/cliany_site/server.py` (新增, ~170 行)

- `APIServer` 类基于 aiohttp，封装 `ClanySite` SDK 为 RESTful 端点
- 端点：`GET /health`, `GET /doctor`, `GET /adapters`, `POST /explore`, `POST /execute`, `POST /login`
- 请求校验：缺少必填字段返回 400，JSON 解析失败返回 400
- App 关闭时自动清理 SDK 资源

**文件:** `src/cliany_site/commands/serve.py` (新增, ~20 行)

- Click 命令 `serve`，支持 `--host` / `--port` 参数
- 从根上下文继承 `cdp_url` / `headless` 配置

### 4.2.4 CLI 集成

**文件:** `src/cliany_site/cli.py` (修改)

- 注册 `serve` 命令到根 CLI group

**文件:** `src/cliany_site/__init__.py` (修改)

- 导出 `ClanySite`, `explore`, `execute`, `login`, `doctor`, `list_adapters`

**文件:** `src/cliany_site/errors.py` (修改)

- 新增 `BAD_REQUEST` 错误码

## 设计决策

| 决策 | 原因 |
|------|------|
| SDK 返回 dict 而非 raise | 外部集成方无需 try/except，统一判断 `result["success"]` |
| Lazy 初始化 CDP | `doctor()` 和 `list_adapters()` 不需要浏览器连接 |
| WorkflowExplorer 自管理 CDP | 与现有 engine.py 行为一致，不干扰 SDK 的连接 |
| 使用 aiohttp 做 HTTP 服务 | 已是 browser-use 的传递依赖，无需新增框架 |
| 方法内部 lazy import | 减少启动开销，仅在实际调用时加载重量级依赖 |
| `_run_async()` 使用 ThreadPoolExecutor | 处理 Jupyter 等已有事件循环的场景 |

## 测试覆盖

**文件:** `tests/test_sdk.py` (新增, ~900 行, 49 项测试)

| 测试类 | 覆盖范围 | 数量 |
|--------|----------|------|
| `TestClanySiteContextManager` | enter/exit、close、ensure_cdp/session | 5 |
| `TestClanySiteInit` | 默认/自定义参数 | 2 |
| `TestSDKDoctor` | 全通过、CDP 失败、无 LLM key | 3 |
| `TestSDKListAdapters` | 空列表、有适配器、详情模式 | 3 |
| `TestSDKExecute` | 适配器/命令未找到、成功、参数、dry_run、失败、空 actions | 7 |
| `TestSDKExplore` | CDP 不可用、LLM 错误、成功创建 | 3 |
| `TestSDKLogin` | 无效 URL、成功、无 cookies | 3 |
| `TestSDKNavigate` | 成功、失败 | 2 |
| `TestSDKGetPageInfo` | 成功 | 1 |
| `TestSDKSaveSession` | 成功 | 1 |
| `TestSyncFunctions` | list_adapters、doctor、_run_async | 3 |
| `TestAPIServer` | build_app、health/adapters/doctor/explore/execute/login 端点、cleanup | 14 |
| `TestServeCLI` | serve 命令存在 | 1 |
| `TestPackageExports` | 公开 API 可导入 | 1 |

全量测试：568 通过，0 失败

## 用法示例

```python
# 同步便捷函数
from cliany_site.sdk import explore, execute, doctor, list_adapters

result = doctor()
if result["success"]:
    print("环境正常")

adapters = list_adapters()
print(adapters["data"]["adapters"])

# 异步上下文管理器
from cliany_site.sdk import ClanySite

async with ClanySite() as cs:
    result = await cs.explore("https://github.com", "搜索仓库")
    adapters = await cs.list_adapters()
```

```bash
# HTTP API 服务
cliany-site serve --host 0.0.0.0 --port 8080

# 调用示例
curl http://localhost:8080/health
curl http://localhost:8080/doctor
curl -X POST http://localhost:8080/explore -d '{"url":"https://github.com","workflow":"搜索仓库"}'
```

## 排查指南

| 问题 | 原因 | 解决 |
|------|------|------|
| `aiohttp` 导入失败 | 未安装 aiohttp | `pip install aiohttp`（通常随 browser-use 安装） |
| 同步函数在 Jupyter 中报错 | 已有事件循环冲突 | `_run_async()` 自动处理，若仍有问题改用 `async with ClanySite()` |
| SDK 方法返回 `success: false` | 内部异常被捕获 | 检查 `result["error"]["code"]` 和 `result["error"]["fix"]` |
| HTTP API 400 错误 | 请求缺少必填字段 | 检查请求体 JSON 是否包含必填字段（url, workflow 等） |
