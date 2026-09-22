# 工作流与批处理结果协议修复

日期：2026-09-22。状态：Unreleased，尚未进入 PyPI v0.16.356。

## 复现与修改

`tests/test_workflow_envelopes.py` 使用真实 Click 命令和项目的 ok/err 构造器返回 JSON，再由 ClickAdapterExecutor 解析并进入工作流、批处理。旧代码只读取 success，导致 ok=true 被误报失败；还会把旧 success=true 配合非零退出码当作成功。

修复前新增回归 8 failed、9 passed。修复后，新增回归及现有 workflow/batch 测试共 103 项通过。

完整离线测试 2831 项通过（6 项既有警告），Ruff 与 Mypy（123 个源文件）通过。

- 兼容 boolean ok 与旧 boolean success；两者共存时以 ok 为准，不把字符串或数字的真值当作成功。
- 新版错误结果保留错误说明，重试耗尽后不执行后续步骤；重试成功即停止重试。
- CLI 非零退出码不得被成功 JSON 覆盖；JSON 数组或标量不被当作结果对象。
- 返回数据可通过既有 `$prev.data.name` 传给下一步；工作流 steps 和批处理 results 的序列化输出新增 data，避免命令已经取得的数据在输出时丢失。

## 范围

此次验证的是编排层的结果协议，不是新的浏览器或公网案例证据。未改写条件表达式语法、数组索引解析、CLI 并发隔离或浏览器上下文。并行状态判定只以线程安全的自定义测试执行器验证，不将其声称为并发 CliRunner 安全性保证。

与当日其他未发布修复合并到下一发布窗口，仍需版本、官网、GitHub Release、PyPI 和标准发布检查；当天三个 tag 已达上限，不重复发版。
