# Obscura 实验性功能操作指南

> **⚠️ 注意: EXPERIMENTAL**  
> Obscura 提供商目前处于实验性阶段。在使用过程中请注意备份数据，并随时准备回退到 Chrome。

## 简介

Obscura 是 cliany-site 引入的全新轻量级浏览器驱动。相比于 Chrome，它在特定场景下拥有更好的启动速度和资源占用表现。

## 安装

使用内置命令下载并安装特定版本的 Obscura 二进制文件：

```bash
cliany-site obscura install 0.1.0 --json
```

## 使用与切换

可以通过环境变量在提供商之间快速切换：

```bash
# 切换到 Obscura
export CLIANY_BROWSER_PROVIDER=obscura

# 回退到默认的 Chrome (只需取消设置)
unset CLIANY_BROWSER_PROVIDER
```

## 支持能力矩阵

| 能力 | 是否支持 | 说明 |
|------|:---:|------|
| Navigation | ✅ | 支持跳转、后退、刷新 |
| Screenshot | ✅ | 支持全屏截图 |
| Cookies | ✅ | 支持读取与持久化 |
| Network Events | ✅ | 支持网络请求监控 |
| Console Events | ✅ | 支持捕获浏览器控制台日志 |
| Explore (AXTree) | ❌ | **暂不支持**，无法使用 `explore` 命令生成新适配器 |

## 诊断与故障排查

如果遇到问题，请运行以下诊断命令：

```bash
# 检查二进制状态
cliany-site obscura doctor --json

# 查看当前版本和活跃状态
cliany-site obscura status --json
```

## 回退

如果 Obscura 运行不稳定，可以使用回退命令恢复到之前的可用版本，或者直接切换回 Chrome：

```bash
cliany-site obscura rollback --json
```

## 错误代码

- `E_UNSUPPORTED_PLATFORM`: 当前操作系统或架构暂不支持。
- `E_MISSING_CAPABILITY`: 尝试调用了 Obscura 暂不支持的功能（如 `explore`）。
- `E_BINARY_NOT_FOUND`: 未找到 Obscura 可执行文件，请重新执行 `install`。
