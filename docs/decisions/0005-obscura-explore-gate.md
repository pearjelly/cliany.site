# ADR 0005: Obscura Explore 门禁与兼容性路线

**状态**: 已接受

**日期**: 2026-05-12

## 背景

Obscura 目前尚不支持导出 AXTree（Accessibility Tree），而 cliany-site 的 `explore` 命令强依赖 AXTree 进行语义理解和代码生成。因此，需要设计一套门禁机制，在 Obscura 模式下安全地拦截不支持的操作。

## 决策

1. **Capability Sniffing**: Provider 接口增加 `supports_axtree` 属性。
2. **Explore Gate**: 在 CLI commands 层实现门禁。如果当前提供商的 `supports_axtree` 为 `False`，则拦截 `explore` 命令。
3. **显式失败**: 拦截时抛出 `MissingCapabilityError(E_MISSING_CAPABILITY)`，并提示用户 Obscura 暂不支持探索功能。
4. **Chrome 路径豁免**: 默认的 Chrome 提供商不受此门禁限制，确保原有核心功能正常运行。
5. **允许执行**: 只要适配器已生成，Obscura 仍允许执行 `execute` 相关动作（如 `click`, `type`），只要这些动作不依赖实时的 AXTree 反馈。

## 备选方案

- 在 LLM 规划层拦截。放弃原因：太晚了，会浪费 Token。应在 CLI 入口处尽快拦截。

## 后果

- **正面**: 保护了用户体验，避免了在不支持 AXTree 的环境下启动昂贵的 LLM 探索流程。
- **负面/权衡**: 用户可能会对「能执行但不能探索」感到困惑，需要在文档中清晰说明。
