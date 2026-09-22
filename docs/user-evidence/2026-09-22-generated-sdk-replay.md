# 生成适配器的 SDK / HTTP 回放

日期：2026-09-22。修复尚未发布；PyPI 基线仍为 v0.16.356。

## 真实产物复现

测试直接构造确定性的 ExploreResult，经 AdapterGenerator.generate 和 save_adapter 保存 v3 适配器。没有调用 LLM，也没有手写 metadata 来模拟生成器。

修复前，SDK 返回 COMMAND_NOT_FOUND；HTTP POST /execute 返回同一错误和 404。生成器使用 commands，SDK 只找 command_defs。此外，action_type/target_url/target_ref/fields_map 与执行器字段不同，SDK 也未收集提取结果。

## 验证

`tests/embodied/test_explore_embodied.py::test_generated_adapter_returns_real_form_data` 在真实 Chromium、本地表单和隔离 HOME 中验证：

1. 从保存的 source_url 开始，不依赖事先导航到目标表单。
2. 输入 Name、点击 Apply、提取 output 为结构化 name 字段。
3. 每次使用新的 SDK/session，输入 Ada 和 Grace，分别返回对应的 `data.results[0].data`，质量状态为 ok。
4. 同一产物经过真实 aiohttp POST /execute，也返回 200 和对应数据。HTTP 服务仅监听测试 loopback。

SDK 与 HTTP 两个真实测试均通过。单元回归另外检查默认参数、显式参数、全局 action_index 到命令内索引转换、自动识别占位参数、必填参数、源地址 sandbox、命令列表提示、空结果与字段缺失。明确允许空结果时，只允许真正的零匹配，不会让存在但空白的字段通过。

最终本地完整离线测试：2814 passed，6 项既有警告；Ruff 与 Mypy（123 个源文件）通过。

## 边界与后续

- 没有改写已安装的自动生成代码，没有修改生成器；旧 command_defs 路径保留兼容。
- SDK/HTTP 沿用既有 success envelope，新增 results 与 quality。未宣称它和 CLI 的 ok envelope 或每步结果格式完全一致。
- 未完成真实模型探索、生成 CLI 的上下文贯通、reuse_atom、复杂参数类型与重复动作的跨入口一致性验收，也未晋级任何公网 candidate。
- 本轮与独立 click/type 修复同属下一版 Unreleased。当天三个 tag 已用尽，下一发布窗口完成标准发布全流程；不将 master 的修复表述为 PyPI 已可用。
