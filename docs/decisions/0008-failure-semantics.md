# ADR 0008: 失败语义规范 (Failure Semantics Specification)

**状态**: 已接受

**日期**: 2026-05-26

## Status

已接受。

## Context

在 v0.14.0 的集成测试和生产环境模拟中，我们发现系统在处理非预期页面状态时存在"静默失败"的问题：
1. **页面就绪超时**：`navigate.py` 在等待页面 Readiness 时超时，原本被捕获并转化为 `success=true` 但返回空数据，导致下游逻辑在错误的基础上继续执行。
2. **提取/解析失败**：当页面 DOM 结构发生微调导致 Atom 提取失败时，系统倾向于返回空列表 `[]` 并标识为 `ok=true`，而非明确报告 `E_PARSE_FAILED`。
3. **语义真空**：对于 `list-*` 或 `search-*` 类命令，返回 `[]` 可能代表"未找到"（业务逻辑正常）或"由于故障没拿到"（系统错误），目前两者在 JSON 信封中无法区分。

这种模糊的失败语义违反了 "Fail Fast" 和 "Explicit Failure" 原则，增加了调试难度。

## Decision

为了统一全链路的失败表达，我们决定在 runtime、atom 和 adapter 模板三层实施严谨的失败语义：

1. **显式失败信封**：
   - 任何非预期的基础设施异常（超时、断连、解析崩溃）必须返回 `envelope.ok=false`。
   - 引入并标准化三个关键错误码（见 `src/cliany_site/envelope.py:41-43`）：
     - `E_PAGE_NOT_READY`: 页面加载或 readiness 等待超时。
     - `E_PARSE_FAILED`: 提取器无法匹配任何已知结构或解析过程崩溃。
     - `E_EMPTY_RESULT`: 业务层面的空结果（仅限特定命令）。

2. **`E_EMPTY_RESULT` 的 Opt-in 机制**：
   - 为避免破坏 `detail` 或 `get` 类命令的真空语义（有时返回空是正常的），`E_EMPTY_RESULT` 仅在 `list-` 或 `search-` 开头的命令中自动启用。
   - 实现逻辑：在 `src/cliany_site/codegen/templates.py:677-749` 中，adapter 模板在聚合结果后会检查 `data` 是否为空，若为空则将 `ok=true` 翻转为 `ok=false` 并附带此错误码。

3. **错误修复提示 (Fix Hints)**：
   - 每一个新增的错误码必须在 `src/cliany_site/errors.py:93-95` 中有对应的 `ERROR_FIX_HINTS` 条目，提供可操作的解决建议（如：增加 `--wait-timeout` 或使用 `--heal`）。

4. **双轨过渡策略**：
   - 保留 `src/cliany_site/response.py` 以兼容旧版适配器。
   - 所有新生成的代码和核心重构统一切换至 `src/cliany_site/envelope.py` 提供的 TypedDict 体系。

## Consequences

- **向后兼容性**：用户编写的脚本如果依赖 `success=true + []` 来判断"未找到"，在升级到 v0.14.0 后可能需要捕获 `E_EMPTY_RESULT`。
- **稳定性**：系统不再会在受损的页面状态下尝试执行后续动作，显著减少了级联故障。
- **文档需求**：需要在 CHANGELOG 中明确说明 `E_EMPTY_RESULT` 的语义变化。

## References

- 计划文档: `.sisyphus/plans/local-test-fixes.md`
- 预留后续引用: ADR 0009
- 关键参考点:
  - `src/cliany_site/envelope.py:41-43` (ErrorCode 定义)
  - `src/cliany_site/errors.py:93-95` (Fix Hints 内容)
  - `src/cliany_site/codegen/templates.py:744-749` (Empty Result Check 注入逻辑)
