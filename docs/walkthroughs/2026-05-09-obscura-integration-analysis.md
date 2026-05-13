# Obscura 集成可行性分析

日期：2026-05-09  
结论：**可以集成，但应先作为可选浏览器 Provider / 外部 CDP 后端接入，不建议直接替换 Chrome 或作为默认依赖。**

## 背景

cliany-site 的目标是把任意网站工作流转成可复用 CLI 命令。当前核心链路是：

1. 通过 Chrome CDP 连接浏览器；
2. 使用 `browser-use` 的 `BrowserSession` 和 `DomService` 捕获页面结构、选择器映射、iframe / Shadow DOM 信息；
3. 将 AXTree、截图、网络和控制台信息交给 LLM 规划动作；
4. 生成 Click adapter；
5. 回放时通过 `action_runtime.py` 执行 click / type / select / navigate / submit 等动作，并支持模糊定位、自愈和录制回放。

Obscura 是 Rust 编写的轻量级 headless browser，面向 AI agent 和网页爬取场景。它通过 `obscura serve --port 9222` 暴露 CDP WebSocket，宣称可与 Puppeteer / Playwright 兼容，并支持 stealth、tracker blocking、DOM-to-Markdown 等能力。

## 直接契合点

### 1. 外部 CDP 后端

当前项目已经支持 `--cdp-url` 和 `CLIANY_CDP_URL`，`CDPConnection` 会通过 `BrowserProfile(cdp_url=...)` 连接外部 CDP 服务。因此 Obscura 最低成本的接入方式是：

```bash
obscura serve --port 9222 --stealth
cliany-site --cdp-url http://127.0.0.1:9222 doctor --json
cliany-site --cdp-url http://127.0.0.1:9222 explore "https://example.com" "提取页面标题" --json
```

这不需要把 Rust crate 嵌入 Python 包，也不需要改变 adapter 生成逻辑。

### 2. 低资源 / 服务端运行

Obscura 的核心卖点是低内存、单二进制、无需安装 Chrome。它适合 cliany-site 的以下场景：

- Docker / CI / 远程服务器中运行探索或回放；
- 多任务并发探索时降低浏览器进程开销；
- 不希望用户手动安装 Chrome 的轻量部署；
- 对反自动化检测敏感的网站探索。

### 3. Stealth 与反检测

cliany-site 的探索阶段依赖页面可访问性和可交互性。Obscura 的 stealth 模式提供 `navigator.webdriver` 隐藏、指纹随机化、tracker blocking 等能力，可能提高部分网站的探索成功率。

### 4. DOM-to-Markdown 作为未来优化方向

Obscura 提供 `LP.getMarkdown` CDP 扩展域。cliany-site 当前主要依赖 `browser-use` 生成的 AXTree / selector map，Markdown 不能替代动作定位，但可以作为 LLM 上下文补充，用于：

- 页面正文提取；
- 数据抽取命令；
- 降低部分 prompt token；
- 诊断模式中的页面语义摘要。

## 主要风险

### 1. CDP 覆盖范围可能不足

这是最大的集成风险。Obscura README 列出的 CDP 域包括 Target、Page、Runtime、DOM、Network、Fetch、Storage、Input 和自定义 LP，但 cliany-site 当前链路间接依赖 `browser-use`，可能调用更多 Chrome 行为。

需要重点验证：

- `BrowserSession.start()` 是否能通过 Obscura CDP 完成连接；
- `DomService.get_serialized_dom_tree()` 是否能正常生成 selector map；
- `browser_session.get_dom_element_by_index()` 是否可用；
- `browser_session.take_screenshot()` 是否可用；
- `browser_session._cdp_get_cookies()` / `_cdp_set_cookies()` 是否可用；
- 输入、点击、导航、新标签页、iframe、Shadow DOM 是否符合现有回放预期。

如果其中任一项依赖 Obscura 未实现的 CDP 方法，就会影响 explore、login、recording、vision、自愈或 replay。

### 2. 不适合直接替代 Chrome 默认行为

Chrome / Chromium 是 cliany-site 当前隐含基准，尤其在复杂前端、登录态、下载、文件上传、跨域 iframe、截图、可访问性树等方面更成熟。Obscura 更适合作为“快速、轻量、stealth”的可选后端，而不是默认后端。

### 3. 分发与平台支持成本

Obscura 是 Rust 单二进制，Python 包无法像普通 Python 依赖一样通过 `pip install` 直接获得稳定跨平台能力。若要自动管理 Obscura，需要处理：

- macOS / Linux / Windows 架构差异；
- 二进制下载、校验和缓存；
- 进程生命周期管理；
- 端口冲突；
- Apache-2.0 NOTICE / license 合规。

### 4. 项目成熟度与语义差异

Obscura 当前定位是快速发展的 AI / scraping 浏览器，不是完整 Chromium。即使 CDP 连接成功，也可能在事件时序、页面生命周期、cookie 行为、截图格式、网络 idle 判断上与 Chrome 存在差异。

## 许可证判断

Obscura 仓库 `LICENSE` 和 `Cargo.toml` 显示为 **Apache-2.0**。cliany-site 当前是 MIT。Apache-2.0 与 MIT 一般兼容，但如果分发 Obscura 二进制或派生修改，需要保留 Apache-2.0 license、版权声明，并按需处理 NOTICE 文件。

建议短期只把 Obscura 作为用户自备外部程序，不随 cliany-site 包分发；这样合规和维护成本最低。

## 推荐集成方案

### 阶段 1：文档级支持（推荐先做）

目标：不改核心代码，验证 Obscura 能否通过现有 `--cdp-url` 工作。

内容：

- 在 README / docs 增加 “使用 Obscura 作为实验性 CDP 后端” 文档；
- 提供启动命令：`obscura serve --port 9222 --stealth`；
- 提供 cliany-site 命令示例；
- 明确标记为 experimental；
- 列出已知限制：截图、AXTree、登录态、iframe、Shadow DOM 需按站点验证。

成功标准：

- `doctor --json` 通过；
- `browser navigate / eval / extract` 基础命令通过；
- 至少一个简单站点的 `explore` 能生成 adapter；
- 生成 adapter 能成功 replay。

### 阶段 2：实验性 Provider 开关

目标：让用户通过配置显式选择 Obscura，同时仍保留 Chrome 默认路径。

候选接口：

- `CLIANY_BROWSER_PROVIDER=chrome|obscura`；
- `CLIANY_OBSCURA_PATH=/path/to/obscura`；
- `CLIANY_OBSCURA_STEALTH=1`；
- `cliany-site --browser-provider obscura ...`。

实现位置：

- `src/cliany_site/config.py`：增加 provider 与 obscura 配置；
- `src/cliany_site/browser/cdp.py`：在本地 CDP 不可用且 provider 为 obscura 时启动 Obscura；
- `src/cliany_site/commands/doctor.py`：展示 provider、binary、CDP 兼容性检查；
- `docs/`：补充实验说明和排错步骤。

注意：不要把 Obscura 和 Chrome 的启动逻辑混在一起，应抽象为 browser provider，避免 `launcher.py` 继续膨胀。

### 阶段 3：利用 `LP.getMarkdown` 优化上下文

目标：在 Obscura 后端可用时，使用 Markdown 作为 LLM 的补充上下文，而不是替换 selector map。

实现建议：

- 新增能力探测：检查 CDP 是否支持 `LP.getMarkdown`；
- 在 `capture_axtree()` 返回中增加可选 `markdown` 字段；
- 在 prompt 中作为 “页面正文摘要” 补充；
- 保持动作定位仍以 selector map / ref 为准。

## 不建议的方案

### 不建议把 Obscura 作为默认依赖

原因：跨平台二进制管理、CDP 兼容性和长期稳定性尚未被本项目验证。

### 不建议直接嵌入 Rust crate

cliany-site 是 Python CLI 包，当前架构天然通过 CDP 与浏览器解耦。嵌入 Rust crate 会引入构建、发布和 ABI 复杂度，收益不如外部 CDP provider 明确。

### 不建议用 Obscura Markdown 替代 AXTree

Markdown 有利于语义理解，但不能提供稳定的动作 ref、元素边界、属性、iframe / Shadow DOM 定位信息。替代 AXTree 会破坏现有 replay 和 healing 机制。

## 最小验证清单

建议用独立脚本或 QA shell 添加实验套件，不先改生产逻辑：

1. 启动：`obscura serve --port 9222 --stealth`；
2. 健康检查：`cliany-site --cdp-url http://127.0.0.1:9222 doctor --json`；
3. 基础 CDP：浏览器子命令 `navigate`、`eval`、`extract`；
4. 页面结构：确认 `capture_axtree()` 生成非空 `element_tree` 和 `selector_map`；
5. 截图：确认 `capture_screenshot()` 返回有效图片；
6. 动作回放：click / type / submit / navigate；
7. 登录态：`login` 保存 cookies，重放时能恢复；
8. 录制：`--record` 能保存 manifest、截图、AXTree；
9. 复杂页面：含动态 JS、iframe、Shadow DOM 的站点；
10. 对比 Chrome：同一 workflow 在 Chrome 与 Obscura 下的成功率、耗时、失败原因。

## 最终建议

短期建议：**支持用户自带 Obscura，通过现有 `--cdp-url` 使用，并补充实验文档和 QA 验证。**

中期建议：如果最小验证清单通过，再实现 `browser provider` 抽象，把 Obscura 作为实验性 provider。默认仍为 Chrome。

长期建议：仅在 Obscura 对 cliany-site 所需 CDP 方法稳定覆盖后，才考虑自动下载二进制、doctor 深度诊断和 `LP.getMarkdown` 上下文优化。
