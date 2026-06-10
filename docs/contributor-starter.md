# 贡献者上手地图

**适用版本：** v0.14.2+  
**目标：** 帮助首次贡献者在不需要真实 LLM key 的情况下找到可复现、可验证、低风险的贡献入口。

## 先跑通本地环境

```bash
pip install -e ".[dev,test]"
cliany-site --version
cliany-site doctor
```

默认优先选择不依赖外部服务的检查：

```bash
CLIANY_QA_OFFLINE=1 pytest tests/ -q --no-cov
ruff check src/ tests/
python scripts/check_release_cadence.py
python scripts/validate_cases.py --strict
```

如果只改文档或案例，可以跑更窄的测试：

```bash
pytest tests/test_cases_manifest.py tests/test_release_cadence.py -q --no-cov
```

## Good First Issues

这些任务适合第一次贡献，通常不需要 Chrome、真实 LLM key 或第三方站点在线。

| 方向 | 可以做什么 | 主要文件 | 验证 |
|------|------------|----------|------|
| 案例库 | 新增或修正 `cases/manifest.json` 条目、补充案例说明 | `cases/`, `scripts/validate_cases.py`, `tests/test_cases_manifest.py` | `python scripts/validate_cases.py --strict` 和 `pytest tests/test_cases_manifest.py tests/test_validate_cases.py -q --no-cov` |
| 文档路径 | 改进 10 分钟成功路径、贡献指南、发布节奏说明 | `docs/`, `README.md`, `README.zh.md` | `git diff --check` |
| doctor 提示 | 补充某个 check 的 action 文案或测试 | `src/cliany_site/commands/doctor.py`, `tests/test_doctor_v3.py` | `pytest tests/test_doctor_v3.py -q --no-cov` |
| 发布节奏 | 改进本地 cadence 检查或 release checklist | `scripts/check_release_cadence.py`, `docs/release-cadence.md` | `pytest tests/test_release_cadence.py -q --no-cov` |
| 错误语义 | 为已有错误码补测试或提示，不改 contract | `src/cliany_site/envelope.py`, `src/cliany_site/errors.py`, `tests/test_error_uniformity.py` | 相关单测 + `ruff check` |
| 静态校验 | 扩展 schema/metadata/manifest 的离线校验 | `src/cliany_site/metadata.py`, `schemas/`, `tests/test_metadata.py` | 相关单测 |

不建议第一次贡献就做：

- 需要真实 LLM key 的 explore 成功率调优。
- 需要第三方 demo 站点稳定在线的端到端测试。
- metadata schema 的破坏性变更。
- provider 抽象或 Obscura 生命周期大改。

## 模块地图

| 你想改 | 先看哪里 | 注意事项 |
|--------|----------|----------|
| CLI 命令入口 | `src/cliany_site/cli.py`, `src/cliany_site/commands/` | 根 `--json` contract 不要破坏 |
| 环境检查 | `src/cliany_site/commands/doctor.py` | human 输出和 JSON 输出都要考虑 |
| 浏览器/CDP | `src/cliany_site/browser/` | 避免真实浏览器依赖进入默认单测 |
| 探索与 LLM | `src/cliany_site/explorer/` | PR 默认走 `CLIANY_QA_OFFLINE=1` |
| adapter 生成 | `src/cliany_site/codegen/` | 不生成 `eval`/`exec`/`os.system` |
| adapter 加载 | `src/cliany_site/loader.py`, `src/cliany_site/metadata.py` | runtime 状态不写入 repo |
| workflow/batch | `src/cliany_site/workflow/` | 优先用离线 fixture 复现 |
| SDK/API | `src/cliany_site/sdk.py`, `src/cliany_site/server.py` | 保持 envelope 字段稳定 |
| TUI | `src/cliany_site/tui/` | 加 smoke 测试，避免依赖真实 terminal 状态 |
| 案例与官网 | `cases/`, `site/`, `docs/` | 第三方站点不可用时标记 degraded |

## 复现问题的最小包

提交 bug 或修复前，尽量准备这些信息：

- `cliany-site --version`
- `cliany-site doctor --json`
- 触发命令和完整参数
- `error.code` 或 `doctor.data.summary`
- 如果是页面定位问题，提供 AXTree snapshot 或最小 HTML fixture
- 如果是 adapter 问题，提供 `metadata.json` 的脱敏片段

## PR 验证策略

按改动风险选择验证范围：

| 改动 | 最小验证 |
|------|----------|
| 纯文档 | `git diff --check` |
| 案例索引 | `python scripts/validate_cases.py --strict` 和 `pytest tests/test_cases_manifest.py tests/test_validate_cases.py -q --no-cov` |
| 发布脚本 | `pytest tests/test_release_cadence.py -q --no-cov` 和 `bash -n scripts/publish.sh` |
| doctor/CLI | doctor 相关单测 + `ruff check src/cliany_site/commands/doctor.py` |
| codegen/loader/action_runtime | 相关单测 + `CLIANY_QA_OFFLINE=1 pytest tests/ -q --no-cov` |
| 浏览器具身路径 | 默认单测先过，再按需跑 `tests/embodied/` 或 `qa/*.sh` |

## 贡献边界

- 不提交 `~/.cliany-site/`、adapter/session/snapshot 运行时状态。
- 不提交真实 API key、cookie、PyPI token 或浏览器 profile。
- 不把真实 LLM key 放进 PR 测试路径。
- 不新增脆弱 CSS selector 作为默认兜底；优先 AXTree 语义匹配。
- 不重写现有 CI workflow；需要时扩展或新增独立 job。
