# ADR 0006: Obscura 三平台支持策略

**状态**: 已接受

**日期**: 2026-05-12

## 背景

Obscura 是一个二进制分发项，需要确保其在 cliany-site 支持的主要平台上都能正确运行。

## 决策

1. **支持矩阵**:
   - `darwin-arm64` (Apple Silicon)
   - `darwin-x86_64` (Intel Mac)
   - `linux-x86_64`
   - `windows-x86_64`
2. **显式不支持**: 其他平台（如 `linux-arm64`）在尝试安装或运行时将抛出 `UnsupportedPlatformError(E_UNSUPPORTED_PLATFORM)` 并显式失败。
3. **Artifact 命名规范**:
   - `obscura-aarch64-apple-darwin.tar.gz`
   - `obscura-x86_64-apple-darwin.tar.gz`
   - `obscura-x86_64-unknown-linux-gnu.tar.gz`
   - `obscura-x86_64-pc-windows-msvc.zip`
4. **版本控制**: 引入 `MIN_VERSION="0.1.0"` 约束，低于此版本的二进制将被拒绝加载。

## 备选方案

- 尝试在不支持的平台上编译。放弃原因：Obscura 是闭源二进制，无法自行编译。

## 后果

- **正面**: 明确了兼容性边界，降低了跨平台维护成本。
- **负面/权衡**: 某些 Linux ARM 用户（如 Raspberry Pi）将无法使用此功能。
