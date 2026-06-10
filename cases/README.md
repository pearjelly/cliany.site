# cliany-site 案例库

**状态：** 起步维护中  
**索引文件：** [manifest.json](manifest.json)  
**目标：** 用真实案例说明 cliany-site 适合做什么、不适合过度承诺什么，并把案例沉淀成可验证资产。

## 案例分层

| 层级 | 用途 | 是否进入默认 CI |
|------|------|----------------|
| 离线结构校验 | 校验案例索引、命令、文档链接不腐烂 | 是 |
| adapter metadata 校验 | 校验本地 demo adapter 包结构、哈希和 metadata schema v3 | 可选，本地 release asset 存在时 |
| 在线 smoke | 访问第三方 demo 站点并执行只读命令 | 否，第三方站点不稳定 |
| 完整 explore 回归 | Chrome + LLM 从头探索生成 adapter | 手动或受保护 workflow |

## 当前案例

| ID | 场景 | 状态 | 价值 |
|----|------|------|------|
| `suitecrm-accounts` | SuiteCRM demo 账户列表 | active | 企业 CRM 查询，无 API 后台操作 CLI 化 |
| `apache-jira-issues` | ASF Jira issue 列表 | active | DevOps/项目管理列表读取 |
| `apache-confluence-search` | ASF Confluence 页面搜索 | active | 团队知识库搜索 |
| `apache-jenkins-jobs` | ASF Jenkins job 列表 | active | 构建状态查询 |
| `search-extraction-gap` | 搜索结果抽取复盘 | known-gap | 明确「页面交互强、列表抽取弱」的产品边界 |

## 维护规则

- 新增真实 demo 时，先更新 `manifest.json`，再补充 README/官网展示。
- 第三方站点不可用时，将 `status` 标记为 `degraded`，不要直接删除案例。
- 每个 active 案例至少要有一个 `commands` 示例和一种 `validation` 方式。
- 已知短板用 `known-gap` 记录，作为路线图输入，而不是藏在聊天记录里。
- 案例运行产生的 adapter/session/snapshot 仍必须保存在 `~/.cliany-site/`，不能写入 repo。

## 离线验收

默认验收只检查索引结构、文档链接、状态、命令和验证说明，不访问第三方站点：

```bash
python scripts/validate_cases.py
python scripts/validate_cases.py --json
python scripts/validate_cases.py --strict
pytest tests/test_search_extraction_gap_fixture.py -q --no-cov
```

`search-extraction-gap` 的最小复现页面固定在 [tests/fixtures/search_extraction_gap.html](../tests/fixtures/search_extraction_gap.html)，用于离线验证搜索结果列表中链接或摘要缺失时应被判为 `partial` 质量问题。

如果本地有从 GitHub Release 下载的 demo adapter 包，可以额外检查 active 案例声明的安装包是否存在、tarball 是否安全可读、`manifest.json` 是否与 `adapter_domain` 匹配、声明文件哈希是否一致，以及 `metadata.json` 是否为 schema v3：

```bash
python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict
python scripts/release_readiness.py --packages-dir ~/.cliany-site/packages --require-packages --strict
```

## 下一步

- 在正式发版前，把 GitHub Release 候选 demo adapter 包下载到 `~/.cliany-site/packages`，再运行 `scripts/release_readiness.py --packages-dir ~/.cliany-site/packages --require-packages --strict`。
- 在 release notes 中链接案例库，说明每个版本新增或修复了哪些真实场景。
- 将 `search-extraction-gap` 继续拆成更细的抽取能力设计任务：列表检测、字段映射、任务级验收。当前已用最小 HTML fixture 固定 partial 字段缺失语义，并让 `browser extract --strict-quality` 与生成的 `list-` / `search-` 数据命令都能把空结果或字段缺失判为 `E_EMPTY_RESULT`。
