# Obscura 测试分层策略

**日期**: 2026-05-11  
**状态**: 草案  
**关联 ADR**: 参见 `docs/decisions/`

## 概述

本文档描述针对 Obscura browser provider 的三层测试分层策略，以及如何与现有 `qa/run_all.sh` 和 pytest 体系集成。

---

## 三层测试架构

### Layer 1 — Smoke（基础连通）

| 属性 | 说明 |
|------|------|
| **目标** | 验证 Obscura binary 可启动、CDP 可连通、provider 可初始化 |
| **入口** | `qa/test_obscura_smoke.sh` |
| **环境** | 需要真实 Obscura binary（路径由 `~/.cliany-site/bin/obscura/active` 指定的 `version/obscura`） |
| **CI 策略** | optional — 仅当 managed binary 可用且已设置 active version 时运行，否则自动 SKIP |
| **关键特性** | 支持 `--dry-run` flag，可在无 binary 环境中预览检查项 |

**运行方式**：
```bash
bash qa/test_obscura_smoke.sh --dry-run   # 预览模式
bash qa/test_obscura_smoke.sh             # 实际运行（需要 binary）
```

**检查项**：
1. `~/.cliany-site/bin/obscura/active` 存在，且指向的 `version/obscura` 二进制存在且可执行
2. `obscura --version` 输出非空
3. `cliany-site doctor --json` 返回合法 envelope
4. doctor 中 obscura provider status 为 `ok`（如已实现）

---

### Layer 2 — Compat（命令/能力兼容）

| 属性 | 说明 |
|------|------|
| **目标** | 验证每个 CLI 命令在 Obscura provider 配置下不崩溃，或有明确 gate |
| **入口** | `qa/test_obscura_compat.sh` |
| **环境** | 不需要真实 Obscura binary，使用现有命令验证 envelope 格式 |
| **CI 策略** | required — 每次 PR 都运行 |
| **关键特性** | 使用 `[GATE]` 状态标记预期不支持的命令（算 PASS） |

**运行方式**：
```bash
bash qa/test_obscura_compat.sh
```

**检查项**：
1. `doctor --json` 返回合法 envelope
2. `list --json` 不因 obscura 配置崩溃
3. `--explain` 返回合法 JSON
4. `explore` 对非法 URL 返回结构化 envelope
5. `verify <unknown-domain>` 返回结构化错误 envelope

---

### Layer 3 — Benchmark（速度/稳定性对比）

| 属性 | 说明 |
|------|------|
| **目标** | Chrome vs Obscura 性能指标对比，机器可判定 pass/fail |
| **入口** | `qa/test_obscura_benchmark.sh` |
| **输出** | JSON 文件（见下方 schema） |
| **阈值** | `--threshold <pct>`，默认 200%（`delta_pct > threshold` 即 FAIL，`== threshold` 算 PASS） |
| **CI 策略** | release-only / nightly — **不在** `run_all.sh` 默认运行 |

**运行方式**：
```bash
bash qa/test_obscura_benchmark.sh --output result.json --threshold 200
```

---

## Benchmark 结果 JSON Schema

```json
{
  "platform": "darwin-arm64",
  "timestamp": "2026-01-01T00:00:00Z",
  "provider": "obscura",
  "scenarios": [
    {"name": "chrome_provider_init", "duration_ms": 50.0, "success": true},
    {"name": "chrome_capability_snapshot", "duration_ms": 40.0, "success": true},
    {"name": "obscura_provider_init", "duration_ms": 45.0, "success": true},
    {"name": "obscura_capability_snapshot", "duration_ms": 38.0, "success": true}
  ],
  "comparison": {
    "chrome_baseline_ms": 45.0,
    "obscura_ms": 41.5,
    "delta_pct": -7.8
  }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `platform` | string | `{os}-{arch}` 格式，如 `darwin-arm64` |
| `timestamp` | ISO8601 string | 测试执行时间（UTC） |
| `provider` | string | 固定为 `"obscura"` |
| `scenarios` | array | 各场景的耗时记录，每项包含 `name`、`duration_ms`、`success` |
| `scenarios[].name` | string | 场景名称（如 `chrome_provider_init`） |
| `scenarios[].duration_ms` | float | 该场景平均耗时（毫秒，10 次采样均值） |
| `scenarios[].success` | bool | 场景是否执行成功 |
| `comparison.chrome_baseline_ms` | float | Chrome 侧 init + snapshot 平均耗时（ms） |
| `comparison.obscura_ms` | float | Obscura 侧 init + snapshot 平均耗时（ms） |
| `comparison.delta_pct` | float | `(obscura - chrome) / chrome × 100`，负值表示更快 |

**PASS/FAIL 判定规则**：`delta_pct > threshold_pct` → FAIL；`delta_pct <= threshold_pct` → PASS（含等于阈值）。

Schema 由 `tests/test_obscura_testplan.py` 中的 `_validate_benchmark_schema()` 验证，与 `tests/test_obscura_benchmark.py` 中的 `validate_benchmark_schema()` 保持一致。

---

## 与 `qa/run_all.sh` 的集成策略

现有 `run_all.sh` 串行执行所有 QA 脚本并汇总 PASS/FAIL 计数。

**集成策略**：

| 脚本 | 集成到 run_all.sh | 说明 |
|------|-------------------|------|
| `test_obscura_smoke.sh` | 可选，手动添加 | binary 不可用时自动 SKIP，不影响整体结果 |
| `test_obscura_compat.sh` | 可选，手动添加 | 每次 PR 运行，无外部依赖 |
| `test_obscura_benchmark.sh` | **不添加** | release-only，不应在常规 PR CI 中运行 |

如需在 CI 中启用 smoke/compat，可在 `run_all.sh` 末尾添加：

```bash
OBS_ACTIVE="${HOME}/.cliany-site/bin/obscura/active"
if [ -f "$OBS_ACTIVE" ]; then
  OBS_VER=$(cat "$OBS_ACTIVE" | tr -d '[:space:]')
  if [ -x "${HOME}/.cliany-site/bin/obscura/${OBS_VER}/obscura" ]; then
    run_script "$SCRIPT_DIR/test_obscura_smoke.sh"
  fi
fi
run_script "$SCRIPT_DIR/test_obscura_compat.sh"
```

---

## pytest 集成

`tests/test_obscura_testplan.py` 验证测试计划的结构完整性：

- QA 脚本文件存在性
- smoke 脚本支持 `--dry-run`
- benchmark 脚本包含 JSON 输出逻辑
- benchmark 脚本未被加入 `run_all.sh`
- strategy 文档存在
- benchmark JSON schema 校验（缺字段应失败）

运行：
```bash
uv run pytest -q tests/test_obscura_testplan.py
```

---

## 目录约定

```
qa/
├── test_obscura_smoke.sh        # Layer 1：基础连通（binary 可用时运行）
├── test_obscura_compat.sh       # Layer 2：命令兼容（每次 PR）
└── test_obscura_benchmark.sh    # Layer 3：性能基准（release-only）

tests/
└── test_obscura_testplan.py     # pytest：验证测试计划结构和 schema

docs/walkthroughs/
└── obscura-test-strategy.md     # 本文档
```
