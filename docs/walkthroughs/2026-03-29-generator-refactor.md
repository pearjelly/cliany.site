# generator.py 拆分重构 — Phase 3.4

**日期**: 2026-03-29
**阶段**: Phase 3 — 场景拓展 (v0.4.0)

## 背景

`codegen/generator.py` 原有 1172 行，承载了命名转换、去重逻辑、参数推导、模板渲染、持久化等多个职责，不利于独立测试和维护。

## 变更内容

将 `generator.py` 拆分为 5 个模块，各模块职责清晰：

| 模块 | 行数 | 职责 |
|------|------|------|
| `naming.py` | 72 | 命令名/函数名/参数名转换，文本清洗 |
| `dedup.py` | 121 | 参数化去重、连续点击去重、冗余动作去重 |
| `params.py` | 82 | `{{param}}` 自动检测，参数覆盖映射构建 |
| `templates.py` | 551 | 所有 Click 代码块渲染（命令、空命令、原子命令、执行块、装饰器等） |
| `generator.py` | 441 | 协调层：`AdapterGenerator` 类 + `save_adapter` 持久化 |

### 拆分前后对比

```
拆分前:  generator.py     1172 行 (单文件)
拆分后:  5 个模块合计       1267 行 (增量来自 __all__ 声明和向后兼容委托)
         generator.py       441 行 (-62.4%)
```

### 模块依赖关系

```
generator.py
  ├── naming.py          (无外部依赖)
  ├── templates.py
  │     ├── naming.py
  │     ├── dedup.py     → explorer/models.py
  │     └── params.py    → dedup.py, explorer/models.py
  └── (save_adapter 保留在 generator.py)
```

### 向后兼容

`AdapterGenerator` 类保留了下划线前缀的委托方法（`_to_command_name`、`_sanitize_inline_text` 等），确保现有代码通过实例调用的路径不受影响。

### 测试更新

- `test_codegen.py` 导入路径更新为直接从 `naming`/`templates` 模块导入
- 新增 `TestBackwardCompatDelegates` 测试类验证委托方法正确性
- 总测试数 307 → 308（+1）

## 验证结果

```
ruff check src/ tests/    → All checks passed!
mypy src/cliany_site/     → Success: no issues found in 50 source files
pytest tests/ -q          → 308 passed in 0.53s
```

## 配置变更

`pyproject.toml` 的 `[tool.ruff.lint.per-file-ignores]` 新增 `templates.py` 的 E501 豁免（模板字面量行长超限）。
