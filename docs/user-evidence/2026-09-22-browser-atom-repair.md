# 独立 click/type 命令修复证据

日期：2026-09-22。发布基线：v0.16.356；本记录描述尚未发布的后续修复。

## 复现

新增 `tests/embodied/test_explore_embodied.py::test_browser_cli_changes_real_form`，在隔离 HOME 和本地静态表单上启动真实 Chromium，并通过独立进程运行 `python -m cliany_site --cdp-url ... browser click/type ... --json`。

修复前两个参数化测试均失败：CLI 返回非零状态和 `E_UNKNOWN`。两个命令调用当前 browser-use 不存在的 `execute_action`；旧单元测试用 AsyncMock 人工提供了该方法，未覆盖真实接口。

## 修复与验证范围

- 使用 AXTree 语义定位得到 ref，再获取 live node，通过 ClickElementEvent / TypeTextEvent / SendKeysEvent 执行动作并等待 handler 结果。
- 点击 Apply 后，表单输出从 untouched 变为 seed。
- 在测试预置的末尾光标处输入 Ada，字段保留原值，得到 seedAda；无 submit 时输出不变。不承诺自动把任意光标移到末尾。
- `--clear --submit` 输入 Grace 后，字段与提交输出均为 Grace。
- 空文本且无 clear 时保留 Grace，并可提交；显式 clear 配合空文本才清空字段。该边界规避底层 TypeTextEvent 把空文本视作清空的行为。
- 单元测试覆盖 ref/text 路径、clear/submit 组合、live node 消失、handler 错误与断开连接；输入失败后不得继续发送 Enter。

本地真实 CLI 浏览器测试 2 项通过；完整离线测试 2801 项通过（6 项既有警告），Ruff 与 Mypy（123 个源文件）通过。未调用 LLM，未修改已安装或自动生成的 adapter，不代表生成命令与 SDK 端到端一致性已验证。

## 发布交接

今天已发布 v0.16.354、v0.16.355、v0.16.356，达到每日 3 tag 上限。本修复保留在 Unreleased，官网和包版本继续声明已发布的 v0.16.356。

下个发布窗口先读取当前 master、tags、cadence 和 CI，不根据本记录猜测远端状态。完成版本、CHANGELOG、roadmap、官网和 release notes 更新，以及完整离线、静态、构建、readiness、最终 SHA 的 CI/Embodied CI、tag、Release、PyPI exact/latest、Vercel 和浏览器核验、strict publication audit。现有每日 10:00 自动化仍为 ACTIVE，无需新建重复任务。
