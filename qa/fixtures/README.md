# qa/fixtures/

离线 QA fixture 站点，为 `e2e_real_site.sh` 的 `CLIANY_QA_OFFLINE=1` 模式提供本地 HTTP 服务器。

## 端口

默认端口：`18080`（可通过 `FIXTURE_PORT` 环境变量覆盖）

## 启停

前台运行（Ctrl+C 停止）：
```bash
bash qa/fixtures/serve.sh
```

后台运行：
```bash
bash qa/fixtures/serve.sh &
```

停止后台服务：
```bash
kill %1   # 或 kill $(lsof -ti:18080)
```

## 内容

- `site/index.html`：搜索演示页（含 `<input id="search-input">` + `<button id="search-btn">` + `<ul id="results">`）
- `site/results.html`：搜索结果页（含 5 个 `<li>` 结果）

## 断网运行

启动后无需网络，所有 fixture 资源均来自本地。