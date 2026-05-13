# ADR 0002: Obscura Provider 兼容性判定与 AXTree 门禁

**状态**: 已接受

**日期**: 2026-05-11

## 1. 背景

cliany-site 的 `explore` 主链路依赖 `browser-use` 的 `DomService.get_serialized_dom_tree()`，
该方法内部调用 `Accessibility.getFullAXTree` CDP 方法（见 `browser_use/dom/service.py: _get_ax_tree_for_all_frames`）。
生成的 `selector_map` 和 `element_tree` 是 LLM 规划动作、生成 adapter 和 fuzzy replay 的核心数据基础。

Obscura 是 Rust 轻量级 headless browser，当前暴露的 CDP 域为：
`Target, Page, Runtime, DOM, Network, Fetch, Storage, Input, LP`。
**Accessibility 域未在 Obscura 官方文档中列出。**

Obscura 提供 `LP.getMarkdown` 自定义 CDP 扩展，可以提取页面 Markdown 文本，但：
- Markdown 文本不包含动作 ref（`@ref=N`）；
- 不提供 selector_map（元素属性、边界、frame_id、shadow_root_type）；
- 不支持 iframe / Shadow DOM 层级定位；
- 无法替代 replay 和 healing 所需的结构化元数据。

## 2. 决策

**缺失 Accessibility 域的 provider 不得宣称 fully supported explore。**

具体规则：

- `supports_axtree = ("Accessibility" in available_domains)`
- `supports_explore = supports_axtree`（explore 主链路必须有 AXTree）
- `LP.getMarkdown` **不是** AXTree 的等价替代，不得影响以上判定

这一判定编码为 `CapabilitySnapshot` + `assess_axtree_capability()` 函数，
位于 `src/cliany_site/providers/__init__.py`，并由 `tests/test_obscura_axtree_gate.py` 强制回归。

## 3. 约束

- Chrome 保持默认 provider，其 `supports_axtree == True` 不变。
- Obscura 只作为显式启用的实验性 provider（`CLIANY_BROWSER_PROVIDER=obscura`），
  且必须在 doctor 输出中以 `supports_explore: false` 警告用户。
- 当 `supports_explore == False` 时，`explore` 命令必须以 structured error 结束，
  不得静默降级为 `LP.getMarkdown` 模式（防止用户误以为生成了完整 adapter）。
- Task 2 负责扩展 `CapabilitySnapshot` 的完整 schema（`supports_login`、
  `supports_vision`、`supports_recording` 等）；本 ADR 只锁定 AXTree 门禁规则。

## 4. 后果

**正面**：

- 明确的能力边界防止用户在 Obscura 环境下运行 `explore` 后得到空或不完整的 adapter。
- `CapabilitySnapshot` 为后续 provider 抽象（Task 9）提供了可扩展的基础结构。
- 兼容门禁测试确保此约束不会被无意中破坏。

**负面 / 权衡**：

- Obscura 无法替代 Chrome 用于 explore 完整链路，直到其实现 Accessibility 域。
- `LP.getMarkdown` 的上下文优化价值（降低 prompt token、辅助数据提取）暂时无法在 explore 主链路体现；
  可在后续阶段作为可选补充上下文引入，但不影响 AXTree 门禁判定。
