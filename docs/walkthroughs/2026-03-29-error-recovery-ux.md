# Phase 2.3 错误恢复 UX

**日期**: 2026-03-29
**阶段**: Phase 2 — 用户体验升级 (v0.3.0)

## 变更概述

为 `execute_action_steps` 执行引擎添加三项错误恢复能力：

1. **断点续执行** — 执行失败时自动保存 checkpoint，支持 `start_index` 从断点恢复
2. **dry-run 模式** — 仅验证元素可定位性和 URL 有效性，不实际调度浏览器事件
3. **执行回放日志** — 每步记录 `page_url` 和 `elapsed_ms`，保存详细日志到 `~/.cliany-site/logs/`

## 改动文件

### 新增文件

| 文件 | 用途 |
|------|------|
| `src/cliany_site/checkpoint.py` | 断点保存/加载/清除 |
| `tests/test_checkpoint.py` | checkpoint 模块 15 个测试 |
| `tests/test_report_enhanced.py` | 增强报告 + 执行日志 8 个测试 |

### 修改文件

| 文件 | 变更内容 |
|------|----------|
| `src/cliany_site/action_runtime.py` | 新增 `start_index`、`dry_run` 参数；失败时保存 checkpoint，成功时清除；每步捕获 `page_url` 和 `elapsed_ms`；dry-run 分支仅做元素定位验证 |
| `src/cliany_site/report.py` | `ActionStepResult` 增加 `page_url`、`elapsed_ms` 字段；新增 `save_execution_log()` 函数 |
| `src/cliany_site/config.py` | 新增 `logs_dir` 属性 |
| `tests/test_config.py` | 更新 `to_dict` 测试包含 `logs_dir` |

## 设计决策

### 断点策略

- 当 `continue_on_error=False` 且步骤失败时，自动将已完成步骤索引保存到 `~/.cliany-site/checkpoints/<domain>_<command>.json`
- checkpoint 记录 `completed_indices`（已成功步骤）、`total_actions`、`params`、`saved_at`
- 调用方传入 `start_index` 即可从断点恢复，跳过已完成的步骤
- 全部步骤成功完成后自动清除 checkpoint 文件

### dry-run 实现

- `dry_run=True` 时，事件模块仍正常加载但不使用
- `navigate` 类型：仅验证 URL 合法性（调用 `normalize_navigation_url`）
- `click/type/select` 类型：仅调用 `_resolve_action_node()` 验证元素可定位
- `submit` 类型：调用 `_resolve_action_node()` 但允许找不到元素（因为 submit 有 fallback 到 Enter 键的逻辑）
- dry-run 模式下失败不保存 checkpoint（因为没有实际副作用）

### 执行日志

- 每个步骤执行前通过 `browser_session.get_current_page_url()` 捕获当前页面 URL
- 步骤计时通过 `time.monotonic()` 差值计算 `elapsed_ms`
- 日志保存到 `~/.cliany-site/logs/<domain>_<timestamp>.log.json`，与报告分开存储
- 日志格式比报告更详细，包含每步的 URL、耗时、错误信息

## execute_action_steps 新签名

```python
async def execute_action_steps(
    browser_session: Any,
    actions_data: list[dict[str, Any]],
    continue_on_error: bool = False,
    params: dict[str, Any] | None = None,
    domain: str = "",
    command_name: str = "",
    progress: ProgressReporter | None = None,
    start_index: int = 0,        # 新增：从第 N 步开始执行
    dry_run: bool = False,        # 新增：仅验证不实际执行
) -> None:
```

## checkpoint 文件格式

```json
{
  "domain": "example.com",
  "command_name": "search",
  "completed_indices": [0, 1, 2],
  "total_actions": 5,
  "params": {"query": "test"},
  "saved_at": "2026-03-29T12:00:00+00:00"
}
```

## 执行日志格式

```json
{
  "adapter_domain": "example.com",
  "command_name": "search",
  "started_at": "...",
  "finished_at": "...",
  "status": "partial_success",
  "summary": {"total": 5, "succeeded": 3, "failed": 2, "repaired": 0},
  "steps": [
    {
      "step_index": 0,
      "action_type": "navigate",
      "description": "打开首页",
      "success": true,
      "timestamp": "...",
      "page_url": "about:blank",
      "elapsed_ms": 1520.3
    }
  ]
}
```

## 验证结果

```
ruff check src/         → All checks passed!
mypy src/cliany_site/   → Success: no issues found in 43 source files
pytest tests/ -v        → 246 passed in 0.64s
```
