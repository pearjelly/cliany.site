# Phase 4.1 适配器市场

**日期:** 2026-03-29
**Phase:** 4.1 (v0.5.0 生态建设)
**状态:** 已完成

## 概述

为 cliany-site 实现适配器打包/分发/安装/版本管理系统，支持离线分享和版本回滚。

## 变更清单

### 4.1.1 适配器打包格式

**文件:** `src/cliany_site/marketplace.py` (新增, ~360 行)

- `AdapterManifest` frozen dataclass: manifest_version、domain、version、author、file_hashes 等字段
- `pack_adapter(domain, version, author)` 将 adapter 目录打包为 `.cliany-adapter.tar.gz`
- tarball 内含 `manifest.json` + adapter 文件 (commands.py、metadata.json、可选快照)
- SHA-256 文件哈希校验，自动跳过隐藏文件和 .tmp 临时文件
- 输出路径：`~/.cliany-site/packages/<domain>-<version>.cliany-adapter.tar.gz`

### 4.1.2 适配器安装

- `install_adapter(pack_path, force)` 从 tarball 安装
- 安全检查：阻止路径穿越攻击 (`..` 和绝对路径)
- 文件哈希校验：逐文件对比 manifest 中记录的 SHA-256
- 重复安装保护：已存在时需 `--force` 才能覆盖
- 覆盖安装前自动创建备份

### 4.1.3 适配器卸载 / 信息查询

- `uninstall_adapter(domain)` 删除 adapter 目录
- `get_adapter_info(domain)` 返回版本、manifest、metadata、备份列表

### 4.1.4 版本管理 (备份/回滚)

- `_create_backup(domain)` 将当前版本复制到 `~/.cliany-site/backups/<domain>/<version>-<timestamp>/`
- `list_backups(domain)` 按时间倒序列出所有备份
- `rollback_adapter(domain, backup_index)` 回滚到指定备份，回滚前自动创建当前版本的备份

### 4.1.5 CLI 命令集

**文件:** `src/cliany_site/commands/market.py` (新增, ~135 行)

`cliany-site market` 命令组包含 6 个子命令：

| 命令 | 说明 |
|------|------|
| `market publish <domain>` | 打包适配器 |
| `market install <pack_path>` | 从分发包安装 |
| `market uninstall <domain>` | 卸载适配器 |
| `market info <domain>` | 查看详细信息 |
| `market rollback <domain>` | 回滚到备份 |
| `market backups <domain>` | 列出备份 |

所有命令遵循 root `--json` 继承和 `print_response` 错误处理约定。

### 4.1.6 CLI 注册

**文件:** `src/cliany_site/cli.py` (修改)

- 新增 `from cliany_site.commands.market import market_group`
- `cli.add_command(market_group)` 注册市场命令组

### 4.1.7 错误码

**文件:** `src/cliany_site/errors.py` (修改)

- 新增 `PACK_FAILED` 和 `INSTALL_FAILED` 错误码及修复提示

## Bug 修复

- **marketplace.py 中 `cfg.base_dir` 引用修复**: `ClanySiteConfig` 没有 `base_dir` 属性，应为 `cfg.home_dir`。涉及 packages 和 backups 路径 3 处。

## 测试

**文件:** `tests/test_marketplace.py` (新增, 44 个测试)

| 测试类 | 数量 | 覆盖 |
|--------|------|------|
| TestAdapterManifest | 5 | defaults、round-trip、missing fields、类型强制转换、frozen |
| TestSha256File | 2 | 确定性、不同内容 |
| TestPackAdapter | 7 | 创建 tarball、manifest 内容、哈希、缺失 adapter、版本/作者、输出路径、跳过隐藏文件 |
| TestInstallAdapter | 10 | 安装、manifest 写入、哈希校验失败、路径穿越拦截、缺少 manifest、重复拦截、强制覆盖、备份创建、缺少 domain |
| TestUninstallAdapter | 2 | 删除、不存在返回 False |
| TestListBackups | 2 | 空列表、倒序排列 |
| TestRollbackAdapter | 4 | 恢复、回滚前备份、无备份、索引越界 |
| TestGetAdapterInfo | 4 | 返回 dict、不存在返回 None、含 manifest、含 backups |
| TestPackInstallEndToEnd | 2 | 打包→卸载→安装、打包→升级 |
| TestMarketCLI | 6 | publish/uninstall/info/backups 的成功和失败路径 |

## 验证结果

- **ruff check:** 0 错误
- **mypy:** 0 错误
- **pytest:** 519 全部通过 (原有 475 + 新增 44)
