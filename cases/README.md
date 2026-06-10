# cliany-site 案例库

**状态：** 起步维护中  
**索引文件：** [manifest.json](manifest.json)  
**目标：** 用真实案例说明 cliany-site 适合做什么、不适合过度承诺什么，并把案例沉淀成可验证资产。

## 案例分层

| 层级 | 用途 | 是否进入默认 CI |
|------|------|----------------|
| 离线结构校验 | 校验案例索引、命令、文档链接不腐烂 | 是 |
| adapter metadata 校验 | 校验 demo adapter 包结构和 schema | 计划中 |
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

## 下一步

- 为 4 个 active demo adapter 增加离线 metadata 校验。
- 在 release notes 中链接案例库，说明每个版本新增或修复了哪些真实场景。
- 将 `search-extraction-gap` 拆成抽取能力设计任务：列表检测、字段映射、任务级验收。

