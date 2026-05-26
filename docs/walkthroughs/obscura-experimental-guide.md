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

## Why Obscura cannot explore yet

目前 Obscura 提供商的 `supports_axtree` 属性为 `False`。正如 **ADR-0005** 和 **ADR-0009** 中所述，`explore` 命令的核心依赖于浏览器提供的 **AXTree (Accessibility Tree)** 数据来进行页面语义理解和 Click 适配器代码生成。

由于 Obscura 目前尚无法导出完整的 AXTree，它无法为 LLM 提供必要的结构化信息。因此，`explore` 功能目前被门禁系统拦截，以避免产生无效的探索结果。

## Recommended workflow

虽然 Obscura 暂不支持探索，但你依然可以结合 Chrome 的能力来完成完整的自动化流程。推荐的工作流如下：

1. **使用 Chrome 进行探索并生成适配器**：
   ```bash
   # 确保处于 Chrome 模式（默认模式）
   unset CLIANY_BROWSER_PROVIDER
   
   # 执行探索
   cliany-site explore "https://example.com" "点击登录并搜索产品" --json
   ```

2. **切换到 Obscura 进行快速重放 (Replay)**：
   ```bash
   # 切换到 Obscura 提供商
   export CLIANY_BROWSER_PROVIDER=obscura
   
   # 执行生成的适配器命令
   cliany-site example.com search --query "test" --json
   ```

这种工作流利用了 Chrome 强大的页面解析能力来生成代码，同时利用了 Obscura 的轻量化特性来执行重复性的自动化任务。

## Troubleshooting

如果你在运行 `explore` 命令时遇到 `E_MISSING_CAPABILITY` 错误，这是由于当前活跃的浏览器提供商（如 Obscura）不支持探索功能。

**错误示例：**
```json
{
  "ok": false,
  "error": {
    "code": "E_MISSING_CAPABILITY",
    "message": "当前浏览器提供商不支持 explore (AXTree) 功能。",
    "details": {
      "suggested_action": "unset CLIANY_BROWSER_PROVIDER",
      "doc_url": "docs/walkthroughs/obscura-experimental-guide.md"
    }
  }
}
```

**应对步骤：**
1. 检查环境变量 `CLIANY_BROWSER_PROVIDER` 是否已设置为 `obscura`。
2. 如果你需要执行探索任务，请取消设置该环境变量：
   ```bash
   unset CLIANY_BROWSER_PROVIDER
   ```
3. 再次尝试运行 `explore` 命令。
4. 更多信息请参考：[Obscura 实验性功能操作指南](docs/walkthroughs/obscura-experimental-guide.md)
