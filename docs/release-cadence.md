# cliany-site 发布与提交节奏

**制定日期：** 2026-06-10  
**适用范围：** v0.14.2 之后的持续迭代

## 目标

- 每天至少发布 1 个可验证版本。
- 每天最多发布 3 个版本；超过上限时只做计划、验证或未发布的准备工作，等下一天再 tag。
- 每周至少 3 天有提交记录。
- 每个版本都能说明用户价值、验证方式和风险。
- PR/CI 默认零真实 LLM key，避免污染贡献者和 fork PR 环境。

## 每日发布循环

每日版本必须是小切片：要么推进一个真实案例、一个贡献者入口、一个 adapter 生命周期证据、一个失败语义修复，或一个发布/官网同步门禁。当天没有足够代码改动时，允许发布文档、案例证据或 release handoff patch，但仍要走完整发布流程。当天已经达到 3 个版本后，不再创建 release tag，也不触发 GitHub Release、PyPI 或官网生产发布；后续工作只进入下一版草案、测试或未发布代码准备。

推荐顺序：

1. 运行 `python scripts/plan_next_iteration.py --json`，读取 `recommended_theme`、`recommended_slice`、`primary_next_action` 和 `standard_release_flow_primary_next_action`。
   如果 `commit_cadence.release_count_today >= commit_cadence.max_daily_releases` 或 `daily_release_limit_ok=false`，当天停止 tag 发布。
2. 选择能当天验证的最小切片，并在 `docs/releases/vX.Y.Z-draft.md` 写清用户价值、风险、验证命令和剩余阻塞。
3. 实现或补证据后运行 `python scripts/release_readiness.py --strict --target-version X.Y.Z`、`python scripts/validate_cases.py --strict`，必要时加相关 `pytest` 或 `qa/*.sh`。
4. 更新 `CHANGELOG.md`、`pyproject.toml`、README/README.zh/官网中受影响入口。
5. 创建并推送 `vX.Y.Z` tag，等待 `.github/workflows/release.yml` 更新 GitHub Release 和 PyPI。
6. 对官网有影响时按 `AGENTS.md` 的 Vercel 步骤在 `site/` 部署，并在 release notes 里记录官网同步。

## 周节奏

| 时间 | 动作 | 输出 |
|------|------|------|
| 周一 | 定义本周版本目标 | 更新 issue/docs/CHANGELOG Unreleased，提交 `docs` 或 `test` |
| 周三 | 合并核心实现 | 提交 `feat` 或 `fix`，补充针对性测试 |
| 周五 | 发版准备与发布 | 更新版本号、CHANGELOG、README/官网必要入口，打 tag |

允许周末发布补丁，但补丁不能替代下一周的正式 release train。每日发布是对这个周节奏的更细粒度执行，不降低三天提交记录和发版门禁要求。

维护者每周选题、实现和复盘的操作顺序见 [每周维护者循环](weekly-maintainer-loop.md)。当 readiness 只剩提交天数不足时，继续做小而可验证的增量；当存在具体 gate issue 时，优先关闭 gate issue 再扩展新功能。

## 版本类型

| 类型 | 何时使用 | 示例 |
|------|----------|------|
| patch | 修复、文档、CI、兼容性小改 | `v0.14.3` |
| minor | 新命令、新用户可见能力、行为增强 | `v0.15.0` |
| major | 破坏性 schema/CLI contract 变更 | `v1.0.0` 之后再考虑 |

0.x 阶段仍遵循 semver 精神：任何 adapter schema、CLI 参数、JSON envelope 的破坏性变化都必须写迁移说明。

## 发布检查清单

发布前至少完成：

- [ ] `CHANGELOG.md` 的 `Unreleased` 内容移动到目标版本。
- [ ] `CHANGELOG.md` 底部 `[Unreleased]` compare 链接从最新 tag 指向 `HEAD`。
- [ ] `pyproject.toml` 版本号与 tag 一致。
- [ ] README/README.zh/官网中受影响的版本文案同步。
- [ ] 运行离线默认检查：`CLIANY_QA_OFFLINE=1 pytest tests/ -q`。
- [ ] 运行统一发版门禁：`python scripts/release_readiness.py --strict`。
- [ ] 运行真实案例库离线验收：`python scripts/validate_cases.py --strict`。
- [ ] 对 CLI 或 adapter 行为有影响时，运行相关 `qa/*.sh` 脚本。
- [ ] 对官网有影响时，按 `AGENTS.md` 的 Vercel 步骤部署 `site/`。
- [ ] tag 使用 `vX.Y.Z` 格式，触发 `.github/workflows/release.yml`。

如果某项无法完成，必须在 CHANGELOG 或 release notes 中说明原因和风险。

## 推荐命令

```bash
# 汇总检查下一版是否可发布（默认只报告，不失败）
python scripts/release_readiness.py
python scripts/release_readiness.py --json
python scripts/release_readiness.py --report /tmp/cliany-release-readiness.md
python scripts/release_readiness.py --target-version 0.15.0 --json
python scripts/release_readiness.py --packages-dir ~/.cliany-site/packages --require-packages --strict

# 汇总检查发布节奏（默认只报告，不失败）
python scripts/check_release_cadence.py
python scripts/check_release_cadence.py --json

# 检查最新本地 release commit/tag 是否已经可从 upstream 或远端看到
python scripts/check_release_publication.py
python scripts/check_release_publication.py --json
python scripts/check_release_publication.py --remote --json
python scripts/check_release_publication.py --remote --report /tmp/cliany-release-publication.md

# 检查真实案例库（默认离线、不访问第三方站点）
python scripts/validate_cases.py
python scripts/validate_cases.py --json
python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md

# 严格检查：不满足时 exit 1，适合发版前本地门禁
python scripts/release_readiness.py --strict
python scripts/validate_cases.py --strict

# 查看本周提交天数
git log --since='monday' --date=short --pretty=format:'%ad' | sort -u

# 查看待发布差异
git log --oneline "$(git describe --tags --abbrev=0)..HEAD"

# 离线默认检查
CLIANY_QA_OFFLINE=1 pytest tests/ -q

# 构建检查
rm -rf dist
uv build
uvx twine check dist/*

# 打 tag
git tag v0.15.0
git push origin master --tags
```

`release_readiness.py` 是发版前总入口，会同时检查下一版草案、每周提交/版本 tag 节奏、`CHANGELOG.md` Unreleased 状态与 compare 链接、工作区清洁度、真实案例库离线验收、默认 CI release gates、tag 发布 workflow、PyPI 项目元数据和开源社区入口文件。默认模式用于观察，`--strict` 用于发版前拦截，`--report` 可生成 Markdown readiness 摘要供发版复盘引用；正式发版前加上 `--packages-dir ~/.cliany-site/packages --require-packages`，确保 demo adapter release assets 也完成离线校验。报告中的 `Gate Issues` 小节是维护者排障入口：先修具体 gate 失败原因，再重新运行 `python scripts/release_readiness.py --strict`，不要只根据顶层 blocker 文案判断是否可以发版。

CI 的 `Release Readiness Report` job 会在 PR/主分支生成 `release-readiness-report` artifact。该 job 不使用 `--strict`，用于持续观察下一版距离发版还差什么；真正发版仍以本地 `python scripts/release_readiness.py --strict` 为准。维护者查看 artifact 时，优先读取 `Gate Issues`，将其中的 `cadence`、`cases/*`、`draft`、`ci`、`release_workflow`、`project_metadata` 或 `package_gate` 项逐条关闭。

`.github/workflows/release.yml` 的 tag 发布流程还会在构建前运行 `Release Preflight`，执行 `python scripts/release_readiness.py --strict --release-tag "${{ github.ref_name }}" --report release-readiness-report.md`。`--release-tag` 用于校验“当前 tag 正在发布”的状态，避免把已 bump 的版本误判成下一版；正式 tag 发布会再次拦截版本号、CHANGELOG、发布草案、CI gate、release workflow 和工作区状态问题。

发布 workflow 会先清理 `dist/`，再运行 `uv build` 和 `uvx twine check dist/*`，用于在 GitHub Release 和 PyPI 发布前发现 wheel/sdist 元数据问题，并避免历史构建产物污染检查结果。

`check_release_publication.py` 用于发布后的本地审计：默认只读取本地 upstream 跟踪信息，不访问网络；传入 `--remote` 时会用 `git ls-remote` 检查实时远端 branch 和 tag refs。它会报告当前分支相对 upstream 的 ahead/behind、最新 tag 是否指向 HEAD、tag commit 是否已进入 upstream，以及需要执行的 `next_actions`。JSON、文本和 Markdown report 还会输出 `worktree_clean`、`worktree_status` 和 `publish_commands`，把 `git push origin master`、`git push origin vX.Y.Z` 和 `python scripts/check_release_publication.py --remote --json` 这类可复制命令放在一起；如果 worktree 不干净，`next_actions` 会先要求提交、stash 或丢弃本地改动，`publish_commands` 只保留重新运行 publication audit 的命令，避免维护者从 JSON 里直接复制 push。传入 `--report /tmp/cliany-release-publication.md` 时会保存 Markdown 报告，便于发版复盘或 CI artifact 留档；传入 `--publish-script /tmp/cliany-publish-release.sh` 时会写出可审阅的 shell 脚本并设置可执行权限，脚本顶部会带 `Publication context` 注释，列出 repo_root、branch、upstream、latest_tag、local_head、tag_commit、ahead_count 和 remote_checked，方便维护者确认脚本对应的本地 release。脚本执行时会先进入 `REPO_ROOT`，确认 `git rev-parse --show-toplevel` 仍是生成时的仓库根目录，再用 `EXPECTED_LOCAL_HEAD`、`EXPECTED_LATEST_TAG` 和 `EXPECTED_TAG_COMMIT` 做本地 stale preflight，并运行 `git status --porcelain` 确认工作区干净；如果当前 repo root、HEAD、latest tag、tag commit 或 worktree 状态已经变化，会打印 `Publish script is stale` 并退出，不执行后续 push。 当本地已经完成 tag 但尚未公开发布时，先运行 `python scripts/check_release_publication.py --json --publish-script /tmp/cliany-publish-release.sh`，确认需要 push 的 branch/tag，再由维护者手动决定是否触发真实 GitHub Release/PyPI 流程。

`check_release_cadence.py` 会检查当前 `pyproject.toml` 版本、最新 tag、本周唯一提交日期数、当天 release tag 数量是否不超过 3、`CHANGELOG.md` Unreleased 是否有内容、`[Unreleased]` compare 链接是否指向最新 tag 到 `HEAD`，以及工作区是否干净。默认模式用于观察，`--strict` 用于发版前拦截。

当 cadence 未满足时，`check_release_cadence.py` 的文本输出和 `--json` 都会包含纯文本 `next_actions`，提示维护者继续补足本周提交天数、暂停超过 3 个版本/日的 tag 发布、修正 tag/version、更新 CHANGELOG compare 链接或清理工作区；渲染为文本时才添加列表符号。JSON 输出还会包含 `missing_commit_days`、`release_count_today`、`max_daily_releases`、`daily_release_limit_ok`、`primary_next_action` 和 `next_actions_sha256`，便于维护脚本直接判断本周还差几个独立提交日、当天是否已经达到发布上限、展示首要节奏动作并检测 action list 是否漂移。每日版本发布前也读取这些字段，确保“每天发版”不会掩盖本周提交日不足、tag/version 不一致、超过每日发布上限或未清理工作区。

`validate_cases.py` 会检查 `cases/manifest.json` 的结构、文档链接和 Markdown 锚点、active 案例命令域名一致性、离线样例输出和验证说明；传入 `--report` 时会生成 Markdown 验收报告，CI 会上传为 `case-catalog-report` artifact；传入 `--packages-dir ~/.cliany-site/packages` 时，还会离线检查 demo adapter 包中的 `manifest.json`、tarball 安全路径、声明文件哈希和 metadata schema v3。

## 提交规则

每周至少保留三天有意义提交；每天发布时优先复用这三类提交节奏：

- 第一天：计划、测试样本、复现输入或文档入口。
- 第二天：功能实现、bug 修复或行为收敛。
- 第三天：验证、发布文档、版本号或官网同步。

提交信息继续使用 Conventional Commits，描述以中文为主：

```text
docs(roadmap): 固化 Q3 迭代路线图
test(cases): 增加 demo adapter metadata 回归
feat(doctor): 按严重级别分组环境检查输出
chore(release): bump version to 0.15.0
```

## 发布记录模板

```markdown
## [0.15.0] - 2026-06-19

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Verification
- `CLIANY_QA_OFFLINE=1 pytest tests/ -q`
- `bash qa/run_all.sh`（如适用）
```

## 发布草案

当 `Unreleased` 已累计多个用户可见改动，但本周提交日或 CI 尚未满足正式发版条件时，先在 `docs/releases/` 写发布草案。草案必须说明目标版本、提交范围、用户价值、风险、验证命令和剩余阻塞项。

当前草案：

- [v0.14.4 发布草案](releases/v0.14.4-draft.md)
- [v0.15.0 发布草案](releases/v0.15.0-draft.md)
- [v0.15.1 发布草案](releases/v0.15.1-draft.md)
- [v0.15.2 发布草案](releases/v0.15.2-draft.md)
- [v0.15.3 发布草案](releases/v0.15.3-draft.md)

如果下一版是 minor，而不是默认的下一 patch，运行 readiness 时显式传入目标版本，例如：

```bash
python scripts/release_readiness.py --target-version 0.15.0 --json
python scripts/release_readiness.py --target-version 0.15.0 --strict
```

## 异常情况

- 如果本周只有文档和流程改进，也发布 patch，保持节奏。
- 如果 CI 失败，不发正式版本；可以提交修复直到 release gate 通过。
- 如果上游 demo 站点不可用，把案例标记为 degraded，不静默删除。
- 如果用户反馈暴露高风险 bug，优先 patch，再回到当周计划。
