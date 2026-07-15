# `market install --dry-run` 设计规格

**日期：** 2026-07-15
**目标版本：** v0.16.263
**状态：** 已获设计确认，等待规格复核

## 背景与目标

当前 `cliany-site market install <package>` 会直接校验并安装适配器包。用户在覆盖已有适配器前，无法先确认包是否安全、清单与哈希是否有效，以及安装是否会创建备份。本迭代新增只读预检能力，让适配器生命周期中的“下载后、安装前”步骤可验证、可脚本化。

目标是为本地 `.tar.gz` 适配器包提供与真实安装一致的校验和冲突判断，同时保证不创建、删除或修改任何运行时文件。

## 用户接口

新增命令：

```bash
cliany-site market install <pack_path> --dry-run [--force] [--json]
```

- `--dry-run` 是 `market install` 的布尔选项；未提供时保持现有安装行为和输出不变。
- `--json` 继续使用根命令的 JSON 输出约定。
- `--force` 在预检中沿用真实安装的冲突语义，但只报告意图，不执行覆盖或备份。

预检成功时，响应 `data` 至少包含以下稳定字段：

```json
{
  "dry_run": true,
  "package_sha256": "<64-character lowercase sha256>",
  "domain": "example.com",
  "version": "1.2.3",
  "files": ["commands.py", "metadata.json"],
  "would_replace": false,
  "would_create_backup": false
}
```

字段含义：

- `package_sha256`：实际归档文件的 SHA-256，供用户与发布记录核对。
- `domain`、`version`、`files`：来自通过校验的包清单与提取目录。`files` 使用适配器包内的相对路径，顺序稳定。
- `would_replace`：目标 domain 的已安装适配器目录是否存在。
- `would_create_backup`：真实安装在当前参数下是否会创建备份。仅当目标存在且传入 `--force` 时为 `true`。

预检成功使用现有 `success_response` 外层信封；此迭代不迁移市场命令的响应格式。

## 实现边界与架构

在 `marketplace.py` 提取一个内部、上下文管理的“已验证适配器包”读取边界，例如 `_validated_adapter_package(pack_path)`：

1. 打开本地归档。
2. 按现有规则拒绝不安全的 tar 成员路径。
3. 读取并解析 manifest。
4. 解压到 `TemporaryDirectory`。
5. 调用现有 `_validate_extracted_adapter_package`，复用 manifest、文件哈希和包结构校验。
6. 在上下文有效期内向调用方提供已验证的 manifest、提取目录和归档 SHA-256。

真实 `install_adapter` 与新增的只读检查函数（建议名为 `inspect_adapter_package`）都必须通过这一边界。这样可以避免预检与真实安装因校验逻辑漂移而得出不同结论。

`inspect_adapter_package` 负责：基于验证后的 manifest 计算目标 adapter 目录，判断现有目录与 `force` 参数形成的安装计划，整理上述稳定输出字段。它不得调用复制、移动、删除、备份或创建 adapter 目录的代码。

`market install` 命令在解析参数后分支：

- 含 `--dry-run`：调用 `inspect_adapter_package`，以成功响应返回预检数据。
- 不含 `--dry-run`：维持现有 `install_adapter` 调用及其输出，兼容已有脚本。

## 数据流与副作用

预检数据流：

```text
归档文件 -> 安全路径校验 -> manifest/哈希/结构校验 -> 冲突计划 -> JSON 或人类可读响应
```

预检允许在系统临时目录中解压并在上下文结束后清理；它不得写入 `~/.cliany-site/adapters/`、`~/.cliany-site/backups/`、session、snapshot 或仓库目录。无论预检成功或失败，适配器安装目录和备份目录均保持逐字节不变。

冲突规则与真实安装对齐：

- 目标不存在：预检成功，`would_replace=false`，`would_create_backup=false`。
- 目标存在且没有 `--force`：预检失败，行为与真实安装相同。
- 目标存在且带 `--force`：预检成功，`would_replace=true`，`would_create_backup=true`，但不修改目标或备份。

## 错误语义

预检沿用安装路径的错误分类，不新增错误码：

- 归档不存在、无法读取、tar 成员路径不安全、manifest 不合法、文件缺失或哈希不匹配，均以现有 `INSTALL_FAILED` 错误信封返回。
- 目标已存在且未传 `--force`，同样以 `INSTALL_FAILED` 返回。
- 命令层继续使用 `_install_fix_hint` 生成与真实安装一致的修复提示。

新增内部函数可以抛出既有的 `FileNotFoundError`、`FileExistsError`、`ValueError` 或 `OSError`；CLI 是唯一负责将它们映射为用户响应的边界。预检不会伪造成功结果，也不会吞掉安全校验错误。

## 测试策略

在现有 `tests/test_marketplace.py` 和市场 CLI 测试中覆盖以下场景：

1. 有效新包的预检返回 `dry_run=true`、SHA-256、domain、version、稳定文件列表和两个 `false` 意图字段；适配器及备份目录均不存在或保持不变。
2. 已安装目标与 `--force` 的预检返回 `would_replace=true`、`would_create_backup=true`；现有 `commands.py` 内容、目录条目和备份列表保持不变。
3. 已安装目标但未提供 `--force` 时，预检以现有 `INSTALL_FAILED` 语义失败，并保持零副作用。
4. 哈希不匹配的包和包含恶意 tar 路径的包都以现有失败语义拒绝，并保持零副作用。
5. 普通安装路径的现有测试继续通过，证明不带 `--dry-run` 的输出与安装行为没有回归。

测试必须使用既有的临时 home 机制，不能在仓库或真实 `~/.cliany-site/` 产生运行时状态。

## 文档与发布

更新 `docs/adapter-lifecycle.md`，在安装步骤前加入预检命令、字段含义和覆盖确认示例；README 的市场命令索引如已有对应位置则同步新增 `--dry-run` 示例。不要宣称支持远程下载或自动修复。

完成实现后按项目发布流程执行：更新版本和变更记录，运行聚焦测试、完整离线 QA、候选预检与发布就绪检查；随后创建 GitHub Release、发布 PyPI 包、部署官网并执行生产检查。此版本不依赖真实浏览器或 LLM 可用性，发布验证保持 `CLIANY_QA_OFFLINE=1` 的确定性路径。

## 非目标

- 不新增远程市场、注册表查询或包下载能力。
- 不在 `--dry-run` 中实际安装、删除、覆盖或创建备份。
- 不在本迭代实现安装事务、失败恢复或新的 rollback 体验。
- 不迁移市场命令的既有响应信封。
- 不修改 CDP、Chrome、LLM 探索或生成适配器流程。
