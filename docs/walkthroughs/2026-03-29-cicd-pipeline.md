# CI/CD 流水线搭建

**日期**: 2026-03-29
**阶段**: Phase 2.4 — CI/CD 流水线
**版本目标**: v0.3.0

## 变更概览

为 cliany-site 项目建立完整的 CI/CD 流水线，涵盖代码质量检查、类型检查、自动化测试和发布。

## 工具配置 (pyproject.toml)

### Ruff (lint)
- target-version: py311, line-length: 120
- 规则集: E/F/W/I/UP/B/SIM
- per-file-ignores: `prompts.py` 和 `generator.py` 豁免 E501（长中文 prompt 模板和代码生成模板）
- isort 配置: known-first-party = cliany_site

### Mypy (type check)
- python_version: 3.11
- ignore_missing_imports: true（第三方库无 stub）
- check_untyped_defs: true（检查无类型注解函数体）
- warn_return_any / warn_unused_configs: true

### 开发依赖
- `[project.optional-dependencies.dev]`: ruff>=0.11, mypy>=1.15
- `[project.optional-dependencies.test]`: pytest>=8.0, pytest-asyncio>=0.23, pytest-mock>=3.14

## Ruff 修复 (118 → 0 errors)

### 自动修复 (75 errors)
`ruff check src/ --fix` 修复了 import 排序、未使用 import、过时语法等。

### 手动修复 (43 errors)

| 类别 | 数量 | 策略 |
|------|------|------|
| E501 (prompts.py) | ~20 | per-file-ignores 豁免 |
| E501 (generator.py) | ~7 | per-file-ignores 豁免 |
| E501 (merger/explore/adapter_list) | 3 | 拆行 / 字符串拼接 |
| B904 (raise from) | 6 | 添加 `from exc` / `from None` |
| SIM102 (nested if) | 3 | 合并为 `and` 表达式 |
| SIM110 (any()) | 1 | 替换为 `any()` 生成器 |
| SIM105 (contextlib.suppress) | 2 | 替换 try-except-pass |
| SIM108 (ternary) | 1 | 替换为三元表达式 |
| B007 (unused loop var) | 1 | 重命名为 `_cmd_name` |
| SIM114 (combine branches) | 1 | 合并 if/elif 为 `or` |

## Mypy 修复 (21 → 0 errors)

| 文件 | 错误类型 | 修复方式 |
|------|----------|----------|
| validator.py | no-any-return | `str()` 包装 `dict.get()` 返回值 |
| generator.py | assignment | 显式类型注解 `dict[str, Any]` |
| launcher.py | no-any-return | 中间变量显式类型注解 |
| loader.py | var-annotated | `list[dict[str, Any]]` 注解 |
| merger.py | assignment/arg-type | 循环变量重命名避免类型冲突 |
| adapter_detail.py | var-annotated/attr-defined | 类型注解 + dict 访问替代属性访问 |
| session.py | no-any-return/attr-defined | 中间变量注解 + 补充 type: ignore |
| cdp.py | no-any-return | 中间变量显式类型注解 |
| axtree.py | no-any-return | 变量显式类型注解 |
| engine.py | no-any-return | 中间变量显式类型注解 |
| doctor.py | assignment | `dict[str, Any]` 注解 |

## CI Workflow (.github/workflows/ci.yml)

触发条件: push 到 master / PR 到 master

三个并行 job:
1. **lint**: ruff check src/
2. **typecheck**: mypy src/cliany_site/
3. **test**: pytest tests/ (矩阵: Python 3.11/3.12/3.13)

使用 `astral-sh/setup-uv` 加速依赖安装。

## Release Workflow (.github/workflows/release.yml)

触发条件: push tag `v*`

流程:
1. 先运行完整 CI (复用 ci.yml)
2. `uv build` 构建 wheel + sdist
3. 创建 GitHub Release（附带构建产物）
4. Trusted Publisher 模式发布到 PyPI

## 验证结果

```
$ uv run ruff check src/
All checks passed!

$ uv run mypy src/cliany_site/
Success: no issues found in 41 source files

$ uv run pytest tests/ -v
208 passed in 0.50s
```

## 修改文件清单

### 新建
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`

### 修改
- `pyproject.toml` — ruff/mypy/dev 依赖配置
- `src/cliany_site/cli.py` — B904 raise from
- `src/cliany_site/action_runtime.py` — B904 raise from
- `src/cliany_site/explorer/engine.py` — B904, SIM105, E501, mypy 类型注解
- `src/cliany_site/explorer/validator.py` — SIM108, mypy str() 包装
- `src/cliany_site/codegen/generator.py` — SIM102/SIM110/SIM114, mypy 类型注解
- `src/cliany_site/codegen/merger.py` — E501 拆行, mypy 变量重命名
- `src/cliany_site/loader.py` — SIM105, mypy 类型注解
- `src/cliany_site/session.py` — mypy 类型注解 + type: ignore
- `src/cliany_site/browser/cdp.py` — mypy 类型注解
- `src/cliany_site/browser/axtree.py` — mypy 类型注解
- `src/cliany_site/browser/launcher.py` — mypy 类型注解
- `src/cliany_site/commands/doctor.py` — mypy dict[str, Any] 注解
- `src/cliany_site/commands/explore.py` — E501 拆行
- `src/cliany_site/tui/screens/adapter_detail.py` — B007, mypy dict 访问
- `src/cliany_site/tui/screens/adapter_list.py` — E501 拆行
