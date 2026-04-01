# 贡献指南 / Contributing Guide

感谢你对 cliany-site 的关注！这份指南将帮助你了解如何参与项目的开发和维护。

Thank you for your interest in cliany-site! This guide will help you understand how to participate in the development and maintenance of the project.

## 如何报告 Bug / How to Report Bugs

如果你发现了问题，请按照以下步骤操作：
1. 在 [Issues](https://github.com/pearjelly/cliany.site/issues) 中搜索是否已有类似的报告。
2. 如果没有，请提交一个新的 Issue。
3. 请详细描述问题，包括：使用的命令、预期结果、实际结果、错误日志以及你的环境信息（可运行 `cliany-site doctor --json` 获取）。

If you find a bug, please follow these steps:
1. Search the [Issues](https://github.com/pearjelly/cliany.site/issues) to see if a similar report already exists.
2. If not, submit a new Issue.
3. Please describe the issue in detail, including: the command used, expected results, actual results, error logs, and your environment information (you can run `cliany-site doctor --json` to get this).

## 如何提出功能建议 / How to Request Features

我们欢迎任何提升工具效率的建议：
1. 在提交建议前，请检查是否有类似的提案。
2. 提交 Issue 时请选择 "Feature Request" 模板。
3. 请清晰描述该功能的实际使用场景和预期行为。

We welcome any suggestions to improve the efficiency of the tool:
1. Before submitting a suggestion, please check if there is a similar proposal.
2. Select the "Feature Request" template when submitting an Issue.
3. Please clearly describe the actual use case and expected behavior of the feature.

## 开发环境搭建 / Development Setup

项目使用 `uv` 或 `pip` 管理依赖。建议在虚拟环境中进行开发。

The project uses `uv` or `pip` to manage dependencies. It is recommended to develop in a virtual environment.

```bash
# 克隆仓库 / Clone repository
git clone https://github.com/pearjelly/cliany.site.git
cd cliany.site

# 安装开发依赖 / Install development dependencies
pip install -e ".[dev,test]"
```

## 运行测试 / Running Tests

```bash
# 运行单元测试 / Run unit tests
pytest tests/ -v

# 运行集成测试（需要 Chrome）/ Run integration tests (requires Chrome)
bash qa/run_all.sh
```

> 注意：`qa/` 目录下的集成测试需要一个已启动并开放 CDP 调试端口（`--remote-debugging-port=9222`）的 Chrome 实例。
>
> Note: Integration tests in `qa/` require a running Chrome instance with CDP debug port (`--remote-debugging-port=9222`) open.

## 提交代码流程 / Contribution Workflow

1. **Fork** 本仓库到你的账号。
2. **Branch**: 基于 `master` 分支创建功能分支，命名规范：`feat/your-feature` 或 `fix/your-bug`。
3. **Develop**: 编写代码并确保通过质量检查。
4. **Commit**: 遵循 Conventional Commits 规范提交代码（详见下方约定）。
5. **PR**: 提交 Pull Request 到本仓库的 `master` 分支。

1. **Fork** this repository to your account.
2. **Branch**: Create a feature branch based on the `master` branch, naming convention: `feat/your-feature` or `fix/your-bug`.
3. **Develop**: Write code and ensure it passes quality checks.
4. **Commit**: Follow the Conventional Commits specification to commit code (see conventions below).
5. **PR**: Submit a Pull Request to the `master` branch of this repository.

## 代码风格 / Code Style

项目使用 `ruff` 进行代码检查和格式化，使用 `mypy` 进行静态类型检查。配置信息参考 `pyproject.toml`。

The project uses `ruff` for linting and formatting, and `mypy` for static type checking. Refer to `pyproject.toml` for configuration.

```bash
# 运行质量检查 / Run quality checks
ruff check src/
ruff format --check src/
mypy src/cliany_site/
```

### Pre-commit Hooks

我们提供了 `pre-commit` 配置（`.pre-commit-config.yaml`）以方便本地开发。这是一个**本地工具**，并非 CI 强制要求，但强烈建议安装以减少 PR 往返次数。

We provide a `pre-commit` configuration (`.pre-commit-config.yaml`) for local development convenience. This is a **local tool** and not enforced by CI, but it is highly recommended to install it to reduce PR round-trips.

```bash
# 安装并配置 pre-commit / Install and configure pre-commit
pip install pre-commit
pre-commit install
```

## Commit Message 约定 / Commit Conventions

我们遵循 Conventional Commits 规范。提交信息以中文为主，格式如下：

We follow the Conventional Commits specification. Commit messages are primarily in Chinese, in the following format:

`type(scope): 简洁描述`

**常用类型 (types):**
- `feat`: 新功能 (new feature)
- `fix`: 修复 Bug (bug fix)
- `docs`: 文档变更 (documentation changes)
- `chore`: 构建过程或辅助工具的变动 (build process or auxiliary tool changes)
- `refactor`: 重构（既不是新增功能，也不是修改 bug 的代码变动） (refactoring)
- `test`: 增加测试 (adding tests)

**示例 (Example):**
`feat(explorer): 增加提取结构化数据的功能`

## PR 审查说明 / PR Review Process

- 所有 PR 至少需要一名维护者的审查通过后方可合并。
- 维护者通常会在几个工作日内处理 PR。
- 请确保 PR 描述清晰，并关联相关的 Issue。

- All PRs require approval from at least one maintainer before merging.
- Maintainers usually process PRs within a few business days.
- Please ensure the PR description is clear and associated with relevant Issues.

## 报告问题 / Reporting Issues

提交 Bug 或功能建议时，请使用 [Issue 模板](https://github.com/pearjelly/cliany.site/issues/new/choose)。

如发现安全漏洞，**请勿在公开 Issue 中披露**，请查阅 [SECURITY.md](SECURITY.md) 了解私密报告流程。

When submitting bugs or feature suggestions, please use the [Issue templates](https://github.com/pearjelly/cliany.site/issues/new/choose).

If you discover a security vulnerability, **do not disclose it in a public Issue**. Please see [SECURITY.md](SECURITY.md) for the private reporting process.
