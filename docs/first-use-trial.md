# 独立用户首次试用

**试用基线：** 2026-10-13 已发布的 `cliany-site==0.16.385`。两条路径都不需要 LLM key，不运行模型探索，不登录账号，也不写入第三方业务数据。请按顺序逐步运行，不要整段执行后只报告最后一次结果。

## 开始前

需要 Python 3.11+，以及访问 PyPI、GitHub 发布资产和对应公开站点的网络。先记下开始时间。遇到首次失败或看不懂的指令时先停止，把阶段、退出码和脱敏错误码/提示留下，再决定是否求助；失败也是有效反馈。不要为了成功先换版本、反复重装或删除原记录。

首次试用不要求读源码、提交 PR 或调试 LLM。可以只完成路径 A；路径 B 额外需要 Chrome，目前自动启动步骤面向 macOS/Linux，Windows 用户可先完成 A。Windows 的浏览器首跑另需独立的手动 CDP 配置，不能把 A 的成功计为 B 的成功。

### macOS / Linux

在普通终端运行，每条成功后再继续：

```bash
trial_dir=$(mktemp -d "${TMPDIR:-/tmp}/cliany-first-use.XXXXXX")
cd "$trial_dir"
python3 -m venv .venv
. .venv/bin/activate
export CLIANY_RUNTIME_HOME="$trial_dir/runtime"
python -m pip install --index-url https://pypi.org/simple cliany-site==0.16.385
cliany-site --version
```

### Windows PowerShell

每条成功后再继续；不需要改变 PowerShell 执行策略或激活脚本：

```powershell
$trialDir = Join-Path $env:TEMP ("cliany-first-use-" + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $trialDir | Out-Null
Set-Location $trialDir
py -3 -m venv .venv
$env:Path = "$(Join-Path $trialDir '.venv\Scripts');$env:Path"
$env:CLIANY_RUNTIME_HOME = Join-Path $trialDir 'runtime'
python -m pip install --index-url https://pypi.org/simple cliany-site==0.16.385
cliany-site --version
```

预期版本为 `0.16.385`。保留正常 OS `HOME` / `USERPROFILE`，新建运行目录只隔离 cliany 文件，不隔离 XDG 配置、系统凭据或浏览器。后续在同一终端继续；退出后保留试用目录，不覆盖原有 adapter，不上传完整目录。

## 路径 A：无需浏览器的 Jira 首个结果

```bash
cliany-site cases --status active --json
cliany-site demo --case-id apache-jira-issues --json
```

预期 `ok=true`、`data.installed_now=true`、`data.row_count >= 1`，并且 `data.result.data.issues` 中有非空的 key 和 summary。只看到案例列表或安装成功不算业务成功。独立打开至少一条结果对应的正常公开 Jira issue 页面，对照 key 与 summary；如页面打不开，记为独立核对未完成，不靠 `ok=true` 补分。

成功后继续：

```bash
cliany-site verify issues.apache.org --strict --json
cliany-site demo --case-id apache-jira-issues --json
```

严格验证应为 `verdict=ok`；第二次 demo 应为 `installed_now=false` 且仍有真实结果，表示复用而非替换。任何一步失败都保留该次结果，不能将后续重试当成首次成功。

记录从安装开始到独立核对结果的**墙钟**耗时；`meta.duration_ms` 不是完整首跑时间，只有 `meta.duration_measured=true` 时才可另记为单次调用的计时快照。

`doctor` 不是这条无需浏览器路径的放行门禁。愿意评价环境提示时，可在 B 的端口检查通过后运行 `cliany-site --headless --cdp-url http://127.0.0.1:19223 doctor`；它可能启动独立 Chrome，但不调用 LLM。仅浏览器/模型缺失提示不推翻已独立核对的 Jira 结果。不要公开原始 doctor 输出。

## 路径 B：Python 文档浏览器候选命令

只在愿意试浏览器且已安装 Chrome 的 macOS/Linux 上继续。这个历史公开 adapter 仍是 candidate，不是新生成命令，也不晋级为 active。使用正常 OS HOME 和不含私密账号状态的测试环境。

先确认专用端口可用；下面命令若失败，先停止，不连接已有端口，也不结束不属于你的浏览器。需要换端口时，记录为一次设置帮助，并替换后续命令中的同一个端口：

```bash
python -c 'import socket; s=socket.socket(); s.bind(("", 19223)); s.close(); print("trial port available")'
```

随后逐条执行：

```bash
cliany-site market install https://github.com/pearjelly/cliany.site/releases/download/v0.16.373/docs.python.org-0.1.0.cliany-adapter.tar.gz --sha256 29f1ece48fd6749e53cf7384f5be0878c1617d1d8344641e284b6c37150f6592 --json
cliany-site verify docs.python.org --strict --json
cliany-site --headless --cdp-url http://127.0.0.1:19223 docs.python.org search-python-docs --query pathlib --json
```

只在严格验证退出码为零且 `verdict=ok` 后运行最后一条。显式 loopback 根地址避免配置指向私有调试浏览器；专用端口未占用时由工具启动独立 profile，不要在检查与执行之间启动别的浏览器。发生端口争用就停止，不保证该检查消除并发争用。

应返回非空标题/链接。独立打开 [Python 文档的 pathlib 搜索](https://docs.python.org/3/search.html?q=pathlib)，等页面完成搜索，再核对首条标题与链接；不是查看工具已打开的页面，也不是只相信 JSON。记下行数与 `data.quality.extracts[*].limit_reached`。最多返回 **100** 行，`limit_reached=true` 不代表完整收集。历史包没有父调用实测计时标记，使用外部墙钟耗时。无需修改生成文件。

成功后再用同一命令将 `--query pathlib` 改成 `--query asyncio`，重新核对正常站点对应搜索的首条结果，分别记录两次，不用第二次结果覆盖第一次。

## 留下结果或首次失败

在 [Jira 首跑 Issue #33](https://github.com/pearjelly/cliany.site/issues/33) 或 [浏览器试用 Issue #55](https://github.com/pearjelly/cliany.site/issues/55) 留言即可，不必等待成功。也可用 `First Use Trial` 反馈表（`first_use.yml`，合并到默认分支后可用）。两条路径的结果分别记录；不会把 Jira API 结果算成浏览器验证。

```text
日期、OS、Python、cliany-site 版本；浏览器路径另记 Chrome 版本：
是否参与开发/构建 adapter：是 / 否 / 不确定
是否获得帮助：无 / 首次尝试前 / 首次失败后（说明帮助内容）
路径 A 或 B；首次达到的阶段、所用公开命令：
首次失败的阶段、退出码、脱敏错误码/提示；没有失败写“无”：
墙钟耗时；未计时写“未测量”：
若成功：严格验证、返回行数、首条公开结果、独立页面核对是否一致；A 另记两次 installed_now，B 另记 limit_reached：
重试：日期、版本、改了什么、结果；未重试写“无”：
```

不要上传密钥、Cookie、环境变量清单、个人路径、全量终端/doctor/AXTree 日志或浏览器 profile。原始证据仅保留本地并先检查敏感内容；公开分享阶段、错误码和公开结果已经足够。无 GitHub 账号时可以把同样的脱敏反馈交给邀请人，并注明由试用者自报，不冒充维护者独立观察。

## 维护者验收规则

截至 2026-10-13，独立用户已记录 **0/2**；准备说明、自动化或维护者复测不算试用者，不先填成功率。需要至少两位未构建 adapter 的人提交首次尝试，且至少一位不经维护者介入完成公开包安装、严格校验及独立非空结果核对。A 与 B 分开统计，浏览器案例保持 candidate，直到其独立用户证据满足条件。

每个反馈保留原链接和首次尝试的版本/阶段，修复与复测必须**另增**记录，原失败不可重写或删除。第三方故障、安装/CLI 缺陷、说明不清和未完成独立核对分别标注；未复现就明确写“未复现”，不推测根因。仅脱敏后的记录进入公开证据文档，不提交用户数据。

优先复现最常见的首跑阻塞，补失败回归后修复。新版本仍走完整离线/静态/案例/分发检查、最终 SHA 普通与浏览器 CI、在线上海发布限额、tagged readiness、GitHub/PyPI 精确版本、生产官网与别名检查及远端分发审计。没有实际价值改动时不为凑每日版本发布。
