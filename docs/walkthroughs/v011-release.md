# cliany-site v0.11.0 发布说明

**日期:** 2026-05-12
**范围:** Obscura 浏览器后端集成, 二进制生命周期管理, 多平台支持, 测试体系

## 1. 摘要

cliany-site v0.11.0 引入了备受期待的 **Obscura 实验性浏览器后端集成**。Obscura 作为一个轻量级的浏览器驱动，旨在提供更快的启动速度和更低的资源占用。本次发布不仅完成了 Obscura 的初步集成，还构建了完整的浏览器提供者抽象层（Browser Provider Abstraction）和二进制生命周期管理体系，为未来的多驱动支持奠定了坚实基础。

## 2. Obscura 实验性集成

Obscura 目前处于 **Experimental（实验性）** 阶段，旨在收集早期反馈并验证其在真实环境中的稳定性。

### 核心特性
- **Provider 抽象层**: 实现了统一的浏览器接口，支持 Chrome 和 Obscura 的灵活切换。
- **Capability Gate**: 引入能力快照机制。目前 Obscura 优先支持执行（Execute）能力，对于依赖复杂 AXTree 的探索（Explore）功能目前处于门禁状态，暂不提供完整支持。
- **环境变量控制**: 通过 `CLIANY_BROWSER_PROVIDER=obscura` 显式开启。Chrome 仍然是默认的稳定驱动。

## 3. Obscura 生命周期管理

新增 `cliany-site obscura` 命令组，为用户提供一站式的驱动管理体验：
- **`install`**: 自动下载并原子化安装对应平台的二进制文件。
- **`use`**: 切换当前激活的版本。
- **`status`**: 查看当前安装状态、版本及运行环境。
- **`doctor`**: 专门针对 Obscura 环境的健康检查。
- **`rollback/upgrade`**: 便捷的版本回滚与升级支持。

## 4. 工业级二进制运维体系

我们为 Obscura 构建了一套完整的自动化运维逻辑：
- **Manifest 驱动**: 基于清单的版本管理。
- **本地缓存**: 避免重复下载，支持离线安装。
- **原子化更新**: 确保安装过程的完整性，防止中间状态导致的损坏。
- **进程管理**: 自动管理 Obscura 后台进程，提供更好的资源回收机制。

## 5. 多平台支持与质量门禁

### 平台覆盖
- **macOS**: Apple Silicon (arm64) & Intel (x86_64)
- **Linux**: x86_64
- **Windows**: x86_64

### 质量门禁 (Release Gates)
每个发布版本都必须通过三层测试筛选：
1. **Smoke**: 基础安装与核心原子命令验证。
2. **Compat**: 现有 Chrome 适配器的兼容性回放测试。
3. **Benchmark**: 启动延迟与内存占用基准测试，确保无性能退化。

## 6. 迁移与使用指南

### 开启 Obscura 尝试
```bash
# 1. 安装二进制
cliany-site obscura install 0.1.0 --json

# 2. 启用提供者
export CLIANY_BROWSER_PROVIDER=obscura

# 3. 验证状态
cliany-site obscura status --json
```

---

## 7. 结语

v0.11.0 是 cliany-site 向多后端、跨平台迈出的重要一步。虽然 Obscura 仍处于实验阶段，但其展示出的潜力和我们为此构建的抽象架构将极大扩展 cliany-site 的应用边界。

感谢所有参与 Obscura 集成测试和架构讨论的贡献者！
