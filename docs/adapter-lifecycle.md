# Adapter 生命周期与包格式

这份指南面向维护者和贡献者，用来说明一个 adapter 从生成、验证、打包、安装到回滚的完整闭环。目标是让团队共享真实站点自动化能力时，有稳定的文件格式、验证路径和安全边界。

## 生命周期总览

1. 生成或扩展 adapter：

   ```bash
   cliany-site explore "https://github.com" "搜索 cliany.site 仓库并查看 README" --json
   cliany-site explore "https://github.com" "新增一个查看 issue 的命令" --extend github.com --json
   ```

2. 静态验证：

   ```bash
   cliany-site verify github.com --json
   cliany-site list --json
   ```

3. 打包发布到本机 packages 目录：

   ```bash
   cliany-site market publish github.com --version 1.0.0 --author "team" --json
   ```

4. 在目标环境安装并检查：

   ```bash
   cliany-site market install ~/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz --json
   cliany-site market info github.com --json
   cliany-site check github.com --json
   ```

5. 出现回归时查看备份并回滚：

   ```bash
   cliany-site market backups github.com --json
   cliany-site market rollback github.com --index 0 --json
   ```

## 运行时位置

运行时状态不写入仓库，统一隔离在 `~/.cliany-site/`：

| 路径 | 用途 |
|------|------|
| `~/.cliany-site/adapters/<domain>/` | 已安装 adapter 目录 |
| `~/.cliany-site/adapters/<domain>/commands.py` | Click 命令入口，由 codegen 生成 |
| `~/.cliany-site/adapters/<domain>/metadata.json` | adapter 元数据，当前要求 `schema_version: 3` |
| `~/.cliany-site/adapters/<domain>/manifest.json` | market 安装后的分发 manifest |
| `~/.cliany-site/packages/` | `market publish` 生成的包 |
| `~/.cliany-site/backups/<domain>/` | 覆盖安装或回滚前的备份 |
| `~/.cliany-site/sessions/` | 登录态 cookies |

测试或复现脚本应使用临时 HOME，避免污染真实 `~/.cliany-site/`。

## 包格式

adapter 分发包后缀为 `.cliany-adapter.tar.gz`，由 `src/cliany_site/marketplace.py` 中的 `PACK_EXTENSION` 定义。tarball 根目录包含：

| 文件 | 必需 | 说明 |
|------|------|------|
| `manifest.json` | 是 | 分发 manifest，当前 `manifest_version: "1"` |
| `commands.py` | 是 | adapter 的 Click 命令代码 |
| `metadata.json` | 是 | codegen 元数据，当前 `schema_version: 3` |
| 其他快照文件 | 否 | 未来可用于诊断或回放，必须是普通文件，并列入 `files` 与 `file_hashes` |

`manifest.json` 的关键字段：

```json
{
  "manifest_version": "1",
  "domain": "github.com",
  "version": "1.0.0",
  "description": "搜索仓库并查看 README",
  "source_url": "https://github.com",
  "author": "team",
  "created_at": "2026-06-10T00:00:00+00:00",
  "cliany_site_min_version": "0.2.0",
  "files": ["commands.py", "metadata.json"],
  "file_hashes": {
    "commands.py": "<sha256>",
    "metadata.json": "<sha256>"
  },
  "checksum": ""
}
```

当前实现会要求包内载荷文件与 `files` / `file_hashes` 完全一致，并校验所有声明文件的内容哈希。`checksum` 字段保留在 manifest 数据结构中，尚未作为安装门禁。

## 兼容性矩阵

| 维度 | 当前约束 |
|------|----------|
| Python | 生成代码兼容 Python 3.11+ |
| metadata | `schema_version: 3`；旧版 adapter 需通过 `cliany-site migrate --json` 或重新 `explore` |
| manifest | `manifest_version: "1"` |
| 浏览器 provider | Chrome/CDP 支持 `explore`、`login`、执行 adapter；Obscura 当前主要用于执行既有 adapter 和轻量导航，不支持 AXTree explore |
| 命令输出 | 内置命令和生成命令应尊重 root `--json` |

## 安全边界

- 禁止把 adapter、session、snapshot 等运行时状态写进仓库。
- 禁止在生成的 adapter 代码中使用 `eval`、`exec`、`os.system` 等危险调用。
- 安装 tarball 时拒绝绝对路径和 `..` 路径穿越成员。
- 安装时按 `manifest.file_hashes` 校验文件哈希，哈希不匹配直接失败。
- 安装时拒绝缺失声明文件、缺失哈希和未在 manifest 中声明的额外文件。
- adapter 动作回放必须基于 AXTree 语义信息和 `selector_map` 做模糊匹配，不能新增脆弱 CSS selector 兜底。
- 分发包不应包含真实账号 cookies、API key、私有截图或业务数据。

## 安装故障排查

`market install --json` 失败时会返回 `INSTALL_FAILED`，并在 `error.fix` 中给出下一步建议：

| 失败信息 | 典型原因 | 修复路径 |
|----------|----------|----------|
| `adapter '<domain>' 已安装` | 目标环境已有同域 adapter | 确认版本后加 `--force` 覆盖，或先 `cliany-site market uninstall <domain>` |
| `文件校验失败` | 包内容与 `manifest.file_hashes` 不一致 | 重新下载包，或在来源环境重新运行 `cliany-site market publish <domain>` |
| `缺少声明文件` / `缺少文件哈希` | `manifest.files` 与 `file_hashes` 不完整 | 使用 `market publish` 重新打包，不要手工拼 tarball |
| `未声明文件` | tarball 中夹带了 manifest 未列出的文件 | 移除额外文件后重新打包，确认不会分发私密数据 |
| `不安全路径` | tarball 包含绝对路径或 `..` 路径穿越 | 丢弃该包，从可信来源重新获取 |

## 维护流程

一次高质量 adapter 更新建议按这个顺序提交：

1. 用真实站点或 demo 站点生成/扩展 adapter。
2. 运行 `cliany-site verify <domain> --json`，确认 metadata schema、签名和依赖完整性。
3. 运行最小业务命令，保留失败时的 `doctor --json`、`check --json` 或执行报告。
4. 用 `market publish` 生成包，并在临时 HOME 中执行 `market install` 回归安装流程。
5. 更新 `cases/manifest.json` 或相关文档，说明适用站点、能力边界和验证命令。
6. 如果覆盖安装已有版本，先确认 `market backups` 中存在可回滚备份。

## 贡献入口

优先贡献这些小而实用的改进：

- 给真实站点 adapter 增加最小可复现案例，记录在 `cases/manifest.json`。
- 为 `market publish/install/rollback` 补充离线 roundtrip 测试。
- 改进 `verify` 对 metadata v3、manifest v1 和包哈希错误的提示。
- 将常见 adapter 失效场景沉淀到 `docs/walkthroughs/`。

相关入口：

- `src/cliany_site/marketplace.py`
- `src/cliany_site/commands/market.py`
- `src/cliany_site/metadata.py`
- `src/cliany_site/codegen/generator.py`
- `tests/test_marketplace.py`
- `docs/contributor-starter.md`
