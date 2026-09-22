# 工作流命令行失败契约

日期：2026-09-22。状态：Unreleased，未发布到 PyPI。

真实 Click 测试命令先返回一项成功数据，再返回 E_EMPTY_RESULT。它经过根 CLI、ClickAdapterExecutor 和实际 workflow/batch 引擎，不模拟引擎的执行结果。

旧代码在 workflow run 和 workflow batch 的普通输出、根 --json、子命令 --json 三种模式中均以 0 退出。JSON 模式先打印错误，再打印独立报告，无法作为单个 JSON 文档解析。新增回归修复前 6 failed、1 passed。

修复后失败统一非零退出。JSON stdout 只有一个既有错误信封，报告放在 error.details 中，保留成功步骤的数据和失败项的具体错误。成功批处理仍为零退出并保留 data。93 项相关回归通过。

本地全量离线回归 2866 项通过；Ruff 通过，Mypy 检查 123 个源文件通过。

此测试验证命令行结果协议，不是浏览器或公网新证据。失败时原先试图解析第二个 JSON 文档的调用方应改读 error.details。本修复等待下一发布窗口，与此前核心执行修复一起完成 GitHub Release、PyPI 与官网发布；当前公开基线仍为 v0.16.356。
