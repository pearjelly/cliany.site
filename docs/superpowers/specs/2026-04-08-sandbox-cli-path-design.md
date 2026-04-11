# CLI 执行主路径 sandbox 闭环设计

**日期：** 2026-04-08
**主题：** 将 root CLI 的 `--sandbox` 从仅写入 `ctx.obj` 提升为对 CLI adapter 执行主路径真实生效

## 背景

当前仓库已经具备沙箱能力模块：

- `src/cliany_site/sandbox.py` 提供 `SandboxPolicy`
- 支持 `validate_navigation()`、`validate_action()`、`validate_action_steps()`
- root CLI 已暴露 `--sandbox`，并写入 `ctx.obj["sandbox"]`

但实际执行链路仍未接线：

- 生成的 adapter 命令不会读取 `sandbox`
- 执行前不会自动做动作预检
- README 已承诺“`--sandbox` 限制跨域导航和危险操作”，但当前行为尚未真正兑现

因此，本次目标是完成一个最小但真实的闭环：让 `--sandbox` 在 CLI adapter 执行主路径上实际生效。

## 目标

1. 让 root `--sandbox` 对生成 adapter 命令的执行路径真实生效
2. 在执行前阻断违反沙箱规则的动作，避免进入浏览器执行
3. 保持现有 `sandbox.py` 规则为唯一策略来源，避免重复实现
4. 将 README 承诺与真实行为对齐

## 非目标

本次不处理：

- `sdk.execute(...)` 的沙箱接入
- `serve` / HTTP API 的沙箱接入
- 运行时中途动态放宽或修改策略
- 对历史已生成 adapter 的自动迁移

## 方案选择

本次采用：**仅接入 CLI adapter 执行主路径**。

理由：

- root `--sandbox` 本来就是 CLI 语义，优先作用于 CLI 主路径最自然
- 改动范围最小，可直接验证“承诺是否兑现”
- 避免在同一轮把 SDK / API 一并卷入，降低联动风险

## 设计细节

### 1. 生效位置

在代码生成模板层接入，而不是改动 `action_runtime.py` 核心语义。

具体落点：

- `src/cliany_site/codegen/templates.py`

生成的 adapter 命令在执行前：

1. 从 `ctx.find_root().obj` 读取 `sandbox`
2. 若为真，则构造 `SandboxPolicy.from_domain(DOMAIN)`
3. 对完整 `action_steps` 执行 `validate_action_steps(...)`
4. 若存在违规项，立即返回错误响应，不调用 `execute_action_steps(...)`

### 2. 规则来源

继续完全复用 `src/cliany_site/sandbox.py`：

- 跨域 `navigate`
- `javascript:` / `file://` / `data:text/html`
- `evaluate` / `execute_js`
- `download`

本次不新增规则，不修改策略模型。

### 3. 错误反馈

若触发违规，返回标准错误响应，包含：

- 通用错误码（沿用现有执行失败语义）
- 首个违规项摘要
- 简短修复提示，例如“关闭 `--sandbox` 或重新 explore 以调整动作路径”

这样用户能明确知道：

- 是沙箱阻断，不是浏览器或元素定位失败
- 哪一步动作违反了策略

### 4. README 对齐

README 保留“`--sandbox` 限制跨域导航和危险操作”的主描述，同时补充边界说明：

- 当前优先作用于 CLI adapter 执行路径
- SDK / HTTP API 的程序化入口暂不在本轮闭环范围内

### 5. 对历史 adapter 的影响

由于接入点在代码生成模板：

- 新生成或重新生成的 adapter 会自动具备沙箱预检
- 历史已生成 adapter 不会自动获得该能力

README / 文档应避免暗示“仓库中所有历史 adapter 立即自动受控”。

## 影响范围

### 代码

- `src/cliany_site/codegen/templates.py`

### 文档

- `README.md`

### 测试

- `tests/test_codegen.py`
- 如需补更贴近行为的用例，可扩展 `tests/test_security.py` 或新增模板/CLI 侧测试

## 验收标准

满足以下条件即视为完成：

1. root `--sandbox` 能被生成 adapter 命令读取
2. 生成命令在执行前调用 `validate_action_steps(...)`
3. 遇到跨域导航或危险动作时，命令直接返回错误，不调用 `execute_action_steps(...)`
4. 同域安全动作在 `--sandbox` 下仍可正常通过预检
5. README 中关于 `--sandbox` 的说明与真实行为一致
