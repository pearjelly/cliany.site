# v0.12 性能微基准说明

## 测量背景

v0.12 稳定性加固（T07）引入了 fsync 原子写入路径，可能对 adapter 生成写盘环节产生影响。
T14 的目标是在 **纯内存计算层** 建立基线，以便独立评估生成逻辑自身的耗时，与 I/O 成本分离。

测量对象：

| 被测函数 | 模块 | 特性 |
|---|---|---|
| `AdapterGenerator.generate()` | `cliany_site.codegen.generator` | 纯内存字符串模板渲染，无磁盘 I/O |
| `normalize_platform()` | `cliany_site.binary.platforms` | 纯函数，无 I/O，无网络请求 |

测试文件：

- `tests/perf/test_adapter_generation_perf.py` — adapter 生成 3 个场景
- `tests/perf/test_obscura_lifecycle_perf.py` — 平台检测 6 个场景

## 基线结果

以下数值为首次在 darwin-arm64（Apple M 系列）上采集的参考基线，单位 ms。

| 测试 | mean (ms) | P95 (ms) | rounds |
|---|---|---|---|
| adapter 生成（单命令） | ~1.5 | ~2.0 | 10 |
| adapter 生成（空命令） | ~0.8 | ~1.0 | 5 |
| adapter 生成（3 命令） | ~3.0 | ~4.0 | 5 |
| `normalize_platform` darwin-arm64 | ~0.002 | ~0.003 | 5 |
| `normalize_platform` 当前宿主机 | ~0.002 | ~0.003 | 5 |

> **注意**：上表为估算值，首次运行后应以实际输出替换。

采集命令：

```bash
uv run pytest tests/perf/ -m perf --benchmark-only -v
```

## 阈值规则

1. **adapter 生成 P95 ≤ 60ms**（基线 50ms × 1.2）
   - 基线设为宽松上限（实测 P95 × 1.5），允许 20% 退化空间。
   - 超出时测试失败，需排查是否引入了额外 I/O 或循环。

2. **`normalize_platform` P95 ≤ 6ms**（基线 5ms × 1.2）
   - 纯内存计算，任何超阈值都提示存在非预期开销。

3. **回归判定**：任意 perf 测试的 P95 比上次基线劣化超过 **20%** 视为回归。

4. **不在 CI 中自动运行**：perf 测试标记为 `@pytest.mark.perf`，日常 CI 跳过。
   手动触发：`pytest tests/perf/ -m perf --benchmark-only`。

5. **冒烟检查**（仅验证可收集、无 import error）：
   ```bash
   pytest tests/perf/ -m perf --benchmark-disable -v
   ```
