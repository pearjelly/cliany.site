# cliany-site 发布与提交节奏

**制定日期：** 2026-06-10  
**适用范围：** v0.14.2 之后的持续迭代

## 目标

- 至少每周发布 1 个版本。
- 每周至少 3 天有提交记录。
- 每个版本都能说明用户价值、验证方式和风险。
- PR/CI 默认零真实 LLM key，避免污染贡献者和 fork PR 环境。

## 周节奏

| 时间 | 动作 | 输出 |
|------|------|------|
| 周一 | 定义本周版本目标 | 更新 issue/docs/CHANGELOG Unreleased，提交 `docs` 或 `test` |
| 周三 | 合并核心实现 | 提交 `feat` 或 `fix`，补充针对性测试 |
| 周五 | 发版准备与发布 | 更新版本号、CHANGELOG、README/官网必要入口，打 tag |

允许周末发布补丁，但补丁不能替代下一周的正式 release train。

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
- [ ] `pyproject.toml` 版本号与 tag 一致。
- [ ] README/README.zh/官网中受影响的版本文案同步。
- [ ] 运行离线默认检查：`CLIANY_QA_OFFLINE=1 pytest tests/ -q`。
- [ ] 对 CLI 或 adapter 行为有影响时，运行相关 `qa/*.sh` 脚本。
- [ ] 对官网有影响时，按 `AGENTS.md` 的 Vercel 步骤部署 `site/`。
- [ ] tag 使用 `vX.Y.Z` 格式，触发 `.github/workflows/release.yml`。

如果某项无法完成，必须在 CHANGELOG 或 release notes 中说明原因和风险。

## 推荐命令

```bash
# 汇总检查发布节奏（默认只报告，不失败）
python scripts/check_release_cadence.py
python scripts/check_release_cadence.py --json

# 严格检查：不满足时 exit 1，适合发版前本地门禁
python scripts/check_release_cadence.py --strict

# 查看本周提交天数
git log --since='monday' --date=short --pretty=format:'%ad' | sort -u

# 查看待发布差异
git log --oneline "$(git describe --tags --abbrev=0)..HEAD"

# 离线默认检查
CLIANY_QA_OFFLINE=1 pytest tests/ -q

# 构建检查
uv build

# 打 tag
git tag v0.15.0
git push origin master --tags
```

`check_release_cadence.py` 会检查当前 `pyproject.toml` 版本、最新 tag、本周唯一提交日期数、`CHANGELOG.md` Unreleased 是否有内容，以及工作区是否干净。默认模式用于观察，`--strict` 用于发版前拦截。

## 提交规则

每周至少保留三天有意义提交：

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

## 异常情况

- 如果本周只有文档和流程改进，也发布 patch，保持节奏。
- 如果 CI 失败，不发正式版本；可以提交修复直到 release gate 通过。
- 如果上游 demo 站点不可用，把案例标记为 degraded，不静默删除。
- 如果用户反馈暴露高风险 bug，优先 patch，再回到当周计划。
