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

## 非 root 沙箱复验

在上述镜像上建立仅用于本机验证的 `cliany-site:sandbox-probe`（短 ID
`38da0a718d63`），安装与 Chromium 匹配的 `chromium-sandbox`，创建 UID 10001
的非 root 用户及其 HOME。正式 Dockerfile 和 Compose 没有因此改动。

以 `--rm --network none` 运行 Chromium 的 `about:blank` dump-dom 探针，未增加
capabilities、未指定特权模式或自定义安全策略，结果退出码 133。错误为创建新
命名空间时 `Operation not permitted`，随后 Zygote 进程退出。Docker 报告当前
启用 AppArmor、内置 seccomp 与 cgroup namespace；仅凭错误不能确定是哪一层
策略阻止该操作，不能宣称添加沙箱包即可修复，也不能宣称所有 Docker 主机都会失败。

后续需要在受支持的宿主环境验证最小必要的命名空间策略及浏览器沙箱是否实际启用，
或验证应用容器连接独立、已安全运行的浏览器。禁止用 `--no-sandbox`、
`--privileged` 或关闭全部 seccomp/AppArmor 的方式充当成功证据。
