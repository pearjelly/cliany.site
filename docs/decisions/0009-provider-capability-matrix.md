# ADR 0009: Provider × Command 能力矩阵

**状态**: 已接受

**日期**: 2026-05-26

## 背景

随着 v0.11.0 引入实验性的 Obscura 浏览器提供商，系统从单一的 Chrome 驱动转向了多 Provider 架构。然而，不同的 Provider 在底层协议实现上存在显著差异（例如 Obscura 不支持 AXTree 捕获）。这导致用户在使用某些核心命令（如 `explore` 或 `login`）时，若切换到能力不足的 Provider，会遭遇非预期的失败或混淆。

目前的 `feature_gate` 机制虽然在内部拦截了不支持的操作，但缺乏一份面向开发者和用户的清晰能力分布图，导致维护成本增加。用户多次反馈在 Obscura 模式下 `explore` 失效的问题，本质上是由于缺乏明确的能力约束说明。

## 决策

建立并维护 Provider × Command 的能力矩阵，作为功能路由和错误处理的权威依据。

### 1. 能力矩阵表

| Command / Feature | Chrome | Obscura | 关键依赖能力 |
| :--- | :---: | :---: | :--- |
| `explore` | ✅ | ❌ | `supports_axtree` |
| `login` | ✅ | ✅ | `supports_navigation`, `supports_cookies` |
| `navigate` | ✅ | ✅ | `supports_navigation` |
| `extract` | ✅ | ✅ | `supports_screenshot`, `supports_navigation` |
| `recording` | ✅ | ✅ | `supports_network_events` |
| Fuzzy Replay | ✅ | ✅ | `supports_navigation` |

### 2. 约束与拦截策略

- **CLI 拦截**: 当用户指定的 Provider 不具备执行目标命令所需的能力时，CLI 必须在预检阶段通过 `feature_gate` 进行拦截。
- **错误响应**: 拦截后必须返回 `E_MISSING_CAPABILITY` 错误码，并在 `details` 中包含 `suggested_action`（例如建议切换回 Chrome）和 `missing_capability` 字段。
- **同步更新**: 每当新增 Provider（如 Playwright 或 WebDriver）或新增核心 Feature 时，必须同步更新此 ADR 中的矩阵表。

## 后果

- **正面**: 减少了用户因 Provider 能力差异导致的困惑；为后续新增 Provider 提供了明确的兼容性实现清单；增强了 CLI 的防御性编程能力。
- **负面/权衡**: 维护矩阵表需要额外的文档成本；在 Provider 快速迭代期间，文档可能存在短暂滞后。

## 引用

- `src/cliany_site/providers/capabilities.py:39-71` (feature_gate 实现)
- [ADR 0002: 适配器元数据 Schema v2 规范](docs/decisions/0002-adapter-metadata-v2.md)
- [ADR 0004: 统一 JSON 信封协议 v1](docs/decisions/0004-json-envelope-v1.md)
- [ADR 0005: 错误码体系与异常链规范](docs/decisions/0005-error-codes-and-exception-chaining.md)
- [ADR 0008: TUI 适配器管理界面交互规范](docs/decisions/0008-tui-adapter-management.md)
- 本计划: `.sisyphus/plans/local-test-fixes.md`
