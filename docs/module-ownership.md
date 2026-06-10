# 模块 Ownership 与验证地图

**适用版本：** v0.14.4+  
**目标：** 帮助贡献者把一个问题快速归到正确模块，选择最小验证命令，并避开高风险边界。

这份文档不是 CODEOWNERS，也不指定个人负责人；它按维护领域定义 owner area。创建 issue、拆 good first issue 或写 PR 描述时，优先引用这里的模块归属和验证命令。

## Ownership 地图

| Owner area | 主要路径 | 典型改动 | 最小验证 |
|------------|----------|----------|----------|
| CLI contract | `src/cliany_site/cli.py`, `src/cliany_site/commands/` | 命令参数、root `--json`、错误 envelope | `pytest tests/test_cli_integration.py tests/test_error_uniformity.py -q --no-cov` |
| First-run diagnostics | `src/cliany_site/commands/doctor.py`, `docs/quickstart-10min.md` | `doctor` check、`summary.capabilities`、新手下一步 | `pytest tests/test_doctor_v3.py tests/test_quickstart_docs.py -q --no-cov` |
| Browser and replay runtime | `src/cliany_site/browser/`, `src/cliany_site/action_runtime.py` | CDP、AXTree、语义匹配、动作回放 | `pytest tests/test_action_runtime.py tests/test_browser_part_c.py -q --no-cov` |
| Explorer and LLM planning | `src/cliany_site/explorer/`, `tests/benchmarks/` | prompt contract、离线 LLM fixture、探索循环 | `CLIANY_QA_OFFLINE=1 pytest tests/test_v010_integration.py tests/benchmarks/ -q --no-cov` |
| Adapter generation | `src/cliany_site/codegen/`, `src/cliany_site/codegen/runtime_helpers.py` | 生成命令、数据抽取命令、模板安全 | `pytest tests/test_codegen.py tests/test_generated_orchestration.py -q --no-cov` |
| Adapter lifecycle | `src/cliany_site/marketplace.py`, `src/cliany_site/commands/market.py`, `src/cliany_site/commands/verify.py`, `docs/adapter-lifecycle.md` | publish/install/rollback、manifest、包哈希、verify | `pytest tests/test_marketplace.py tests/test_verify.py tests/test_adapter_lifecycle_docs.py -q --no-cov` |
| Case catalog | `cases/`, `scripts/validate_cases.py` | 真实案例、离线样例、candidate promotion | `python scripts/validate_cases.py --strict` 和 `pytest tests/test_cases_manifest.py tests/test_validate_cases.py -q --no-cov` |
| Release operations | `scripts/release_readiness.py`, `scripts/check_release_cadence.py`, `.github/workflows/` | 发版门禁、提交节奏、CI artifact | `pytest tests/test_release_readiness.py tests/test_release_cadence.py -q --no-cov` |
| Contributor experience | `docs/contributor-starter.md`, `docs/good-first-issues.md`, `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md` | issue/PR 模板、首次贡献任务池、模块入口 | `pytest tests/test_contributor_docs.py tests/test_good_first_issues_docs.py -q --no-cov` |
| Website and public docs | `site/`, `README.md`, `README.zh.md`, `docs/` | 官网入口、README 示例、用户教程 | `pytest tests/test_site_content.py tests/test_readme_current_features.py -q --no-cov` |

## 变更分流规则

- 如果改动会影响 JSON envelope、错误码或 root `--json`，按 CLI contract 处理，并额外检查下游生成命令。
- 如果改动需要真实 LLM key、第三方站点在线或用户 Chrome 状态，先补离线 fixture；PR 默认仍要能在 `CLIANY_QA_OFFLINE=1` 下给出证据。
- 如果改动涉及 adapter 包、manifest 或 release asset，必须同时检查 adapter lifecycle 和 case catalog。
- 如果改动只是文档，也要跑对应文档测试或 `git diff --check`，并确认 README、官网、release draft 是否需要同步。
- 如果改动涉及 `~/.cliany-site/`，测试必须使用临时 HOME，不提交运行时状态。

## PR 描述模板片段

```markdown
Owner area:
Changed paths:
Validation:
Risk boundary:
```

`Owner area` 取自上表；`Validation` 至少填一个可复制命令；`Risk boundary` 写清没有真实 LLM key、第三方在线依赖或 runtime 状态入库。
