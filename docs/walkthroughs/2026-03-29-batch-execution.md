# 数据驱动批量执行 — Phase 3.3

**日期**: 2026-03-29
**阶段**: Phase 3 — 场景拓展 (v0.4.0)

## 背景

Phase 3.2 实现了 YAML 工作流编排，支持多步骤串联。但实际场景中，同一命令需要对大量数据逐条执行（如批量搜索、批量导入等）。Phase 3.3 新增数据驱动批量执行引擎，支持：

1. **CSV/JSON 数据源** — 从文件加载参数列表
2. **并发控制** — `--concurrency N` 限制并行度
3. **汇总报告** — 成功/失败/耗时统计，逐条结果记录

## 新增/修改文件

| 文件 | 行数 | 职责 |
|------|------|------|
| `workflow/batch.py` | 191 | 数据加载 + 批量执行引擎 + 结果模型 |
| `commands/workflow.py` | 170 | 新增 `workflow batch` CLI 命令（+57 行） |
| `errors.py` | — | 新增 `BATCH_DATA_ERROR`、`BATCH_PARTIAL_FAILURE` 错误码 |
| `tests/test_batch.py` | 244 | 21 个测试 |

## 数据源格式

### CSV

```csv
query,limit
hello,10
world,20
cliany-site,5
```

首行为表头，作为参数名；后续每行作为一组执行参数。

### JSON

```json
[
  {"query": "hello", "limit": "10"},
  {"query": "world", "limit": "20"},
  {"query": "cliany-site", "limit": "5"}
]
```

顶层必须是数组，每项是一个参数对象。

## CLI 用法

```bash
# 串行执行（默认）
cliany-site workflow batch github.com search data.csv --json

# 并发执行（3 个并行）
cliany-site workflow batch github.com search data.csv --concurrency 3 --json

# JSON 数据源
cliany-site workflow batch github.com search data.json --json
```

## 输出格式

### 全部成功

```json
{
  "success": true,
  "data": {
    "total": 3,
    "succeeded": 3,
    "failed": 0,
    "elapsed_ms": 1523.4,
    "results": [
      {"index": 0, "params": {"query": "hello"}, "success": true, "error": null, "elapsed_ms": 502.1},
      {"index": 1, "params": {"query": "world"}, "success": true, "error": null, "elapsed_ms": 498.3},
      {"index": 2, "params": {"query": "cliany"}, "success": true, "error": null, "elapsed_ms": 510.7}
    ]
  },
  "error": null
}
```

### 部分失败

错误码 `BATCH_PARTIAL_FAILURE`，exit code 1，同时输出汇总报告：

```json
{
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "elapsed_ms": 1600.0,
  "results": [
    {"index": 0, "params": {"query": "hello"}, "success": true, "error": null, "elapsed_ms": 500.0},
    {"index": 1, "params": {"query": "bad"}, "success": false, "error": "元素未找到", "elapsed_ms": 800.0},
    {"index": 2, "params": {"query": "world"}, "success": true, "error": null, "elapsed_ms": 300.0}
  ]
}
```

## 架构设计

### 核心流程

```
CSV/JSON 文件  ──load_batch_data()──▶  list[dict[str, str]]
                                              │
                                              ▼
                                       run_batch(step, data, executor, concurrency)
                                              │
                       ┌──────────────────────┼──────────────────────┐
                       │ concurrency=1        │ concurrency>1        │
                       │ 串行循环             │ ThreadPoolExecutor   │
                       ▼                      ▼                      │
                 _execute_one_item()    _execute_one_item() × N     │
                       │                      │                      │
                       └──────────────────────┴──────────────────────┘
                                              │
                                              ▼
                                       BatchResult.to_dict()
```

### 关键类

- **`BatchDataError`** — 数据加载异常（文件不存在、格式错误、空数据）
- **`BatchItemResult`** — 单条执行结果：`index` / `params` / `success` / `data` / `error` / `elapsed_ms`
- **`BatchResult`** — 汇总：`total` / `succeeded` / `failed` / `results` / `elapsed_ms`

### 参数合并策略

`_execute_one_item()` 将 `StepDef.params`（来自命令定义）与 `row_params`（来自数据行）合并：

```python
merged = {**step.params, **row_params}  # 数据行覆盖默认参数
final_params = interpolate_params(merged, context)  # 支持变量插值
```

### 并发模型

- `concurrency=1`：普通 for 循环，按顺序逐条执行
- `concurrency>1`：`ThreadPoolExecutor(max_workers=concurrency)`，使用 `as_completed` 收集结果，最后按 `index` 排序保证输出顺序一致

## 错误码

| 错误码 | 含义 |
|--------|------|
| `BATCH_DATA_ERROR` | 数据文件加载失败（不存在 / 格式错误 / 空数据） |
| `BATCH_PARTIAL_FAILURE` | 批量执行中有部分条目失败 |

## 测试覆盖

21 个测试，覆盖以下场景：

- `load_batch_data`：CSV 正常加载、JSON 正常加载、文件不存在、不支持的格式、空 CSV、空 JSON、JSON 非数组
- `BatchItemResult` / `BatchResult`：数据模型字段、`to_dict()` 输出
- `run_batch`：串行全部成功、串行部分失败、并发执行、空数据
- `_execute_one_item`：成功、失败、异常捕获、参数合并
- CLI 集成：`workflow batch` 命令调用、无效数据文件报错

## 验证结果

```
ruff check src/ tests/       → All checks passed!
mypy src/cliany_site/        → Success: no issues found in 56 source files
pytest tests/ -v             → 432 passed in 0.72s
```
