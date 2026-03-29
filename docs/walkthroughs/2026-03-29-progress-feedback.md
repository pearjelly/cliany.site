# Phase 2.1 — 执行进度反馈

**日期:** 2026-03-29
**范围:** 为 explore 和 execute 流程添加实时进度反馈

## 变更概述

引入统一的进度回调协议 `ProgressReporter`，支持两种展示模式：
- 交互式终端：rich Live display（Spinner + 步骤表/进度条）
- JSON 模式：NDJSON 事件流输出到 stderr

## 架构设计

采用**回调协议模式**，将进度展示与业务逻辑解耦：

```
explore_cmd / adapter 命令
    │
    ├── json_mode=True  → NdjsonProgressReporter
    └── json_mode=False → RichProgressReporter
            │
            ▼
    WorkflowExplorer.explore(progress=reporter)
    execute_action_steps(progress=reporter)
```

### 回调协议

```python
class ProgressReporter(Protocol):
    def on_explore_start(self, url, workflow, max_steps) -> None: ...
    def on_explore_step_start(self, step, max_steps) -> None: ...
    def on_explore_llm_start(self, step) -> None: ...
    def on_explore_llm_done(self, step, actions_count) -> None: ...
    def on_explore_step_done(self, step, actions_count, elapsed_ms) -> None: ...
    def on_explore_done(self, total_steps, total_actions, total_commands, elapsed_ms) -> None: ...
    def on_execute_start(self, total_actions, domain, command) -> None: ...
    def on_execute_step_start(self, index, total, action_type, description) -> None: ...
    def on_execute_step_done(self, index, total, success, elapsed_ms, error=None) -> None: ...
    def on_execute_done(self, succeeded, failed, total, elapsed_ms) -> None: ...
```

### 三种实现

| 类 | 用途 | 输出 |
|----|------|------|
| `NullProgressReporter` | 默认值，无操作 | 无 |
| `RichProgressReporter` | 交互式终端 | rich Live (stderr) |
| `NdjsonProgressReporter` | --json 模式 | NDJSON 行 (stderr) |

## NDJSON 事件格式

每行一个 JSON 对象，包含 `event` 和 `ts` 字段：

```jsonl
{"event":"explore_start","url":"https://github.com","workflow":"搜索仓库","max_steps":10,"ts":1711700000.0}
{"event":"explore_step_start","step":0,"max_steps":10,"ts":1711700001.0}
{"event":"explore_llm_start","step":0,"ts":1711700002.0}
{"event":"explore_llm_done","step":0,"actions_count":3,"ts":1711700005.0}
{"event":"explore_step_done","step":0,"actions_count":3,"elapsed_ms":4500.0,"ts":1711700005.5}
{"event":"explore_done","total_steps":2,"total_actions":6,"total_commands":1,"elapsed_ms":9000.0,"ts":1711700010.0}
```

## 修改文件

| 文件 | 变更 |
|------|------|
| `src/cliany_site/progress.py` | 新建：ProgressReporter Protocol + 3 种实现 |
| `src/cliany_site/explorer/engine.py` | WorkflowExplorer.explore() 添加 `progress` 参数，在探索循环中触发回调 |
| `src/cliany_site/action_runtime.py` | execute_action_steps() 添加 `progress` 参数，在执行步骤中触发回调 |
| `src/cliany_site/commands/explore.py` | 根据 json_mode 创建对应 reporter 并传入 explorer |
| `tests/test_progress.py` | 17 个测试覆盖三种实现的完整生命周期 |

## 验证结果

```
ruff check src/         → All checks passed!
mypy src/cliany_site/   → Success: no issues found in 42 source files
pytest tests/ -v        → 225 passed in 0.51s
```

## 后续扩展

- 生成的 adapter 命令接入 progress（需修改 codegen/generator.py 模板）
- 支持自定义 reporter（用户可实现 Protocol 接口）
- WebSocket / SSE 推送进度（远程场景）
