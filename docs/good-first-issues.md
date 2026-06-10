# Good First Issues

**适用版本：** v0.14.4+
**目标：** 给首次贡献者一组不需要真实 LLM key、不依赖第三方站点在线、能用本地命令验证的贡献入口。

这些任务不是 GitHub issue 的替代品，而是维护者创建 `good first issue` 时的候选池。每条任务都要能被拆成一个小 PR，并在 PR 描述里写清验证命令。

## 选择原则

- 默认离线：优先使用 fixture、文档测试、schema 校验或 `CLIANY_QA_OFFLINE=1`。
- 范围单一：一次只改一个模块、一个案例或一条文档路径。
- 用户价值明确：让新用户更容易跑通、让案例更可信、让错误更好复现。
- 验证可复制：PR 中必须贴出至少一个本地命令输出。

## 候选任务

| Label | 任务 | 主要文件 | 验证 |
|-------|------|----------|------|
| `docs` | 改进 10 分钟成功路径中的某一步说明，减少新用户第一次运行时的分叉 | `docs/quickstart-10min.md`, `README.md`, `README.zh.md` | `git diff --check` |
| `cases` | 为一个公开只读工作流补候选案例、离线 JSON envelope 样例和 `promotion` 清单 | `cases/manifest.json`, `cases/examples/` | `python scripts/validate_cases.py --strict` |
| `cases` | 把一个已有 candidate 的晋级阻塞拆成 adapter package、metadata validation、online smoke 三个可执行子任务 | `cases/README.md`, `cases/manifest.json` | `python scripts/validate_cases.py --report /tmp/cliany-case-report.md` |
| `doctor` | 为一个已有 doctor check 补充更具体的 action 文案，并覆盖 human/JSON 输出 | `src/cliany_site/commands/doctor.py`, `tests/test_doctor_v3.py` | `pytest tests/test_doctor_v3.py -q --no-cov` |
| `release` | 改进 release readiness 或 cadence 的 `next_actions` 文案，让阻塞项更可执行 | `scripts/release_readiness.py`, `scripts/check_release_cadence.py` | `python scripts/release_readiness.py --json` 和 `pytest tests/test_release_readiness.py tests/test_release_cadence.py -q --no-cov` |
| `extract` | 为抽取质量补一个空结果、全空字段或部分缺字段的离线 fixture 回归 | `tests/fixtures/`, `tests/test_extract_quality.py` | `pytest tests/test_extract_quality.py tests/test_search_extraction_gap_fixture.py -q --no-cov` |
| `metadata` | 为 adapter metadata 或 package manifest 增加一个离线校验用例 | `src/cliany_site/metadata.py`, `scripts/validate_cases.py`, `tests/` | 相关 pytest + `ruff check` |

## 不适合第一次贡献

- 需要真实 OpenAI/Obscura key 的 explore 成功率调优。
- 依赖第三方站点实时可用的端到端测试。
- metadata schema 的破坏性变更。
- 重写 CI workflow、provider 抽象或 action runtime。
- 把 `~/.cliany-site/` 下的 adapter/session/snapshot 运行时状态写进仓库。

## 维护者使用方式

创建 GitHub issue 时，从上表选一个任务，并补上：

- 期望改动范围。
- 推荐验证命令。
- 相关文件链接。
- 明确的非目标，例如“不需要真实 LLM key”“不要访问第三方站点”。

如果任务来自真实案例库，优先引用 `cases/manifest.json` 中的 `promotion` 字段，保持 issue、case report 和 release readiness artifact 的下一步一致。
