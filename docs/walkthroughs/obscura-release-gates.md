# Obscura CI/Release 门禁说明

本文档定义了 Obscura 作为实验性功能发布到生产环境前必须通过的质量门禁。

## 1. 测试分层体系

所有更改必须通过以下三层测试，才能被视为符合 Experimental 可用标准：

### Layer 1: Smoke (冒烟测试)
- **命令**: `bash qa/test_obscura_smoke.sh`
- **目标**: 验证二进制文件的基本安装、启动、生命周期管理和核心原子命令（Navigate, Screenshot）。
- **CI 任务**: `obscura-smoke`

### Layer 2: Compat (兼容性测试)
- **命令**: `bash qa/test_obscura_compat.sh`
- **目标**: 验证在 `CLIANY_BROWSER_PROVIDER=obscura` 模式下，现有的适配器（由 Chrome 生成）是否能正确执行非 AXTree 依赖的动作。

### Layer 3: Benchmark (基准测试)
- **命令**: `bash qa/test_obscura_benchmark.sh`
- **目标**: 对比 Obscura 与 Chrome 的启动延迟和内存占用。结果必须符合预期范围，不应出现显著退化。

## 2. CI 门禁规则

1. **强制性**: `obscura-smoke` 任务必须在所有 PR 中通过。
2. **Experimental 声明**: 只有当 Layer 1 和 Layer 2 完全通过时，才允许在文档和 `list` 命令中宣称该版本为 `experimental`。
3. **平台完整性**: 必须在 `darwin`, `linux`, `windows` 三个平台上都完成基准测试，方可发布。

## 3. 发布标准

在将 `experimental` 标签升级为正式支持前，必须满足：
- [ ] AXTree 导出功能实现并经过充分验证。
- [ ] 错误率低于 Chrome 提供商的 1.1 倍。
- [ ] 完成全量适配器回归测试。
