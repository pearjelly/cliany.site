# ADR 0004: Obscura 浏览器提供商抽象层设计

**状态**: 已接受

**日期**: 2026-05-12

## 背景

为了引入 Obscura 作为实验性的浏览器提供商，系统需要支持在不同的浏览器实现（Chrome 与 Obscura）之间进行切换。目前的架构中，CDP 连接逻辑与特定提供商耦合较紧，需要引入一套统一的提供商抽象层。

## 决策

1. **Provider Factory**: 引入提供商工厂模式。通过 `CLIANY_BROWSER_PROVIDER` 环境变量决定激活哪个提供商。
2. **默认行为**: 若未设置该环境变量，系统默认使用 `Chrome` 提供商，确保向后兼容性。
3. **显式 Opt-in**: 用户必须通过设置 `CLIANY_BROWSER_PROVIDER=obscura` 显式开启 Obscura 模式。
4. **三层边界**:
   - **CLI Commands 层**: 负责解析环境参数并调用工厂获取提供商实例。
   - **Provider 抽象层**: 定义标准接口（如 `navigate`, `screenshot`, `get_cookies` 等）。
   - **实现层**: 具体的 `ChromeProvider` 和 `ObscuraProvider`。

## 备选方案

- 自动嗅探模式：根据系统是否安装 Obscura 自动切换。放弃原因：实验性功能应由用户显式控制风险。

## 后果

- **正面**: 架构更清晰，未来支持更多浏览器内核（如 Firefox/WebKit）变得更容易。
- **负面/权衡**: 增加了系统配置的复杂度，用户需要了解提供商切换机制。
