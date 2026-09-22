# Docker 构建与启动验收

日期：2026-09-22。代码基线：`ceb644ce5cf4150db41bb6a7e714c4ad92fedf15`。
本地验证镜像：`cliany-site:verify-ceb644c`，短 ID `d02975e9dc31`。
这是含 Unreleased 修改的开发镜像，版本字段仍为 0.16.356，未发布到镜像仓库。

## 实际结果

- 使用本机已运行的 Colima ARM64 Docker 环境，没有切换默认 context 或停止其他容器。
- 原 Dockerfile 构建第一次在 Python 包下载阶段发生读取超时；一次原样重试成功。没有修改证书校验或镜像源。
- 基础镜像 `python:3.11-slim` 摘要为 `sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9`；安装 Chromium 153.0.8010.52，browser-use 0.13.10。
- 运行探针均使用临时容器、`--rm --network none`，没有挂载用户会话或传递密钥。
- `--version` 退出 0，显示 0.16.356。
- `cases --json` 退出 0，读取 `/app/cases/manifest.json`，共 8 个案例：2 active、3 candidate、2 degraded、1 known-gap。
- `doctor --json` 退出 1，返回 `E_CDP_UNAVAILABLE`；浏览器工作流能力为未就绪。默认容器运行条件没有通过验收。

## 浏览器故障定位

在同一构建的系统依赖层运行 `chromium --headless --dump-dom about:blank`，
浏览器拒绝以 root 且未禁用沙箱的方式运行。使用 UID/GID 65534、临时 HOME 和
临时浏览器资料目录的非 root 探针，也返回无可用沙箱，并提示缺少 chromium-sandbox。
未使用 `--no-sandbox`、特权容器或关闭宿主机隔离来绕过失败。

下一步需要验证非 root 镜像用户、沙箱依赖与宿主机隔离兼容性，并复测 doctor 和
真实页面操作。安装沙箱包本身不能视为该目标已完成。Compose 中默认 doctor 是
一次性命令，不是常驻服务；服务名是 `cliany-site`，不能使用历史文档中的 `cliany`。

包内资源的直接探针也曾因 editable 安装下资源位于 `/app/cases` 而失败；随后通过
真实 `cases --json` 验证项目支持的源码目录回退路径。没有将直接资源探针算作通过。

结论：打包输入缺失已修复，实际镜像可构建且非浏览器入口可用；浏览器容器运行仍未修复。
