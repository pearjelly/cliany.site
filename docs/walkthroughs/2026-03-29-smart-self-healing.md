# Phase 2.2 — 智能自愈增强

**日期:** 2026-03-29
**范围:** AXTree 快照存储、执行前预检、selector 热修复、check 命令

## 变更概述

为适配器增加自愈能力。当目标网站 UI 发生变化（元素移位、改名、ID 变更）时，
系统能自动检测差异并提供修复建议，无需每次都重新 explore。

## 架构设计

```
explore → 生成适配器 → 同时保存 AXTree 快照
                           │
                           ▼
cliany-site check <domain> [--fix]
    │
    ├── 加载快照元素 (snapshot.py)
    ├── 连接 CDP，捕获当前页面 AXTree
    ├── 对比快照 vs 当前 (healthcheck.py)
    │    ├── score >= 55 → matched (健康)
    │    ├── score 30-54 → changed (可修复)
    │    └── score < 30  → missing (缺失)
    └── --fix → 自动回写 metadata.json
```

## 新增文件

| 文件 | 职责 |
|------|------|
| `src/cliany_site/snapshot.py` | AXTree 快照 save/load/list |
| `src/cliany_site/healthcheck.py` | 元素对比、差异评分、selector 修复 |
| `src/cliany_site/commands/check.py` | `cliany-site check` CLI 命令 |
| `tests/test_snapshot.py` | 快照模块 16 个测试 |
| `tests/test_healthcheck.py` | 健康检查 31 个测试 |
| `tests/test_check.py` | check 命令 14 个测试 |

## 修改文件

| 文件 | 变更 |
|------|------|
| `src/cliany_site/codegen/generator.py` | `save_adapter()` 中新增快照保存调用 |
| `src/cliany_site/cli.py` | 注册 `check_cmd` |

## 核心模块说明

### snapshot.py — 快照存储

快照存储路径: `~/.cliany-site/adapters/<domain>/snapshots/<command>.json`

```python
save_snapshot(domain, command_name, selector_entries, page_url) → path
load_snapshot(domain, command_name) → dict | None
list_snapshots(domain) → list[str]
save_explore_snapshots(domain, explore_result, selector_maps) → list[str]
```

快照 JSON 结构:
```json
{
  "domain": "example.com",
  "command_name": "search",
  "page_url": "https://example.com",
  "element_count": 3,
  "elements": [
    {"target_name": "...", "target_role": "...", "target_ref": "...", "target_attributes": {}}
  ],
  "saved_at": "2026-03-29T..."
}
```

### healthcheck.py — 差异对比与修复

评分算法镜像 `action_runtime._score_candidate()`：

| 维度 | 完全匹配 | 部分匹配 |
|------|---------|---------|
| name | 40 | 20 (包含关系) |
| role | 15 | - |
| id | 30 | - |
| name attr | 20 | - |
| aria-label | 20 | - |
| placeholder | 18 | - |
| href | 18 | - |
| title | 12 | - |
| type | 12 | - |

阈值:
- `MATCH_THRESHOLD = 30` — score >= 30 视为找到对应元素
- `DIFF_THRESHOLD = 0.30` — 30% 以上元素异常则判定不健康

### commands/check.py — check 命令

```bash
cliany-site check example.com --json       # 检查健康状态
cliany-site check example.com --fix --json  # 检查并自动修复
```

输出示例:
```json
{
  "success": true,
  "data": {
    "domain": "example.com",
    "healthy": true,
    "commands": [
      {
        "command": "search",
        "status": "healthy",
        "healthy": true,
        "snapshot_count": 3,
        "current_count": 45,
        "matched": 3,
        "missing": 0,
        "changed": 0,
        "diff_ratio": 0.0
      }
    ]
  }
}
```

## 验证结果

```
ruff check src/ tests/    → All checks passed!
mypy src/cliany_site/     → Success: no issues found in 46 source files
pytest tests/ -v          → 307 passed (新增 61 个测试)
```

## 测试覆盖

| 测试文件 | 测试数 | 覆盖范围 |
|---------|--------|---------|
| test_snapshot.py | 16 | save/load/list/explore_snapshots |
| test_healthcheck.py | 31 | 评分、对比、修复、边界条件 |
| test_check.py | 14 | 命令路由、mock 浏览器、auto-fix |
| **总计新增** | **61** | |
| **项目总计** | **307** | |
