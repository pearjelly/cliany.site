# 自主修复协议（AUTONOMOUS FIX PROTOCOL）

> **本文档是给 OpenCode/Sisyphus agent 的自主修复协议。**
> CI workflow 仅负责触发与收集上下文，真正的修复由 agent 读取本文档后执行。
> 禁止将本文档当作可执行脚本——这是给 agent 读的协议约束文档。

---

## 总览

当自动化 CI 检测到以下情形时，agent 应读取本文档并按对应维度的修复协议执行：

| 触发来源 | 维度 | 修复章节 |
|----------|------|---------|
| `pytest tests/benchmarks/` 失败 | 维度1 | [回归修复](#维度1-promptadapter-生成回归修复) |
| Issue 打上 `auto-reproduce` label | 维度2 | [复现修复](#维度2-运行时反馈复现修复) |
| Dependabot PR 测试失败 | 维度4 | [依赖升级修复](#维度4-依赖升级修复) |

---

## 维度1：prompt/adapter 生成回归修复

### 触发条件
`tests/benchmarks/test_generation_regression.py` 或 `test_sentinel_effectiveness.py` 失败（PR 门禁 `benchmark-regression` job 红）。

### 定位失败原因
```bash
uv run pytest tests/benchmarks/ -v --no-cov 2>&1 | head -50
# 查看失败的 assert diff
```

### 修复策略

**若 `_parse_llm_response` 输出不符预期**（第1层失败）：
- 修复目标：`src/cliany_site/explorer/prompts.py`（SYSTEM_PROMPT JSON 合约）
- 检查：LLM 响应格式是否发生变化？prompt 约束是否够严格？
- 修复后：重新生成 `tests/benchmarks/data/*/expected_parsed.json` 基线（如确认是预期变更）

**若 `AdapterGenerator.generate` 输出不符预期**（第2层失败）：
- 修复目标：`src/cliany_site/codegen/generator.py`
- 检查：生成的 Click 代码结构、命令名称、参数是否发生非预期变化？
- 修复后：重新生成 `tests/benchmarks/data/*/expected_adapter/` 基线

### 修复边界约束
- **禁止**：放宽基线（修改 expected_*.json 来让测试通过而非修复真正问题）。
- **禁止**：引入 CSS 选择器兜底（必须基于 AXTree 语义）。
- **禁止**：修改 `tests/conftest.py`、`src/cliany_site/testing/snapshot.py` 等基础设施。
- **必须**：修复后 `pytest tests/benchmarks/ -v --no-cov` 全绿。

---

## 维度2：运行时反馈复现修复

### 触发条件
Issue 被打上 `auto-reproduce` label，`auto-reproduce.yml` workflow 将 issue 上下文保存为 `/tmp/repro/context.json`。

### 复现步骤
1. 读取 issue body，提取字段（来自 `.github/ISSUE_TEMPLATE/bug_report.yml`）：
   - `target_url`：触发 bug 的目标 URL
   - `error_code`：错误码
   - `axtree_snapshot`：AXTree JSON 快照
   - `cliany_version`：版本号
   - `doctor_output`：doctor 诊断输出

2. 根据 `error_code` 分诊修复目标（见 `src/cliany_site/errors.py`）：
   - `E_PARSE_FAILED`：检查 `src/cliany_site/explorer/prompts.py` SYSTEM_PROMPT 合约
   - `E_EMPTY_RESULT`：检查 `src/cliany_site/explorer/engine.py` 探索循环与结果累积逻辑
   - `E_PAGE_NOT_READY`：检查 `src/cliany_site/browser/cdp.py` 页面就绪检测逻辑

3. 用 AXTree 快照 mock 本地语义环境复现问题：
   ```bash
   CLIANY_QA_OFFLINE=1 \
   CLIANY_QA_FAKE_LLM_RESPONSES=<响应文件路径> \
   uv run python3 -c "
   from cliany_site.explorer.engine import _parse_llm_response, _sanitize_actions_data
   # 用 axtree_snapshot 数据测试解析路径
   "
   ```

4. 修复代码，提交 PR，确保 `pytest tests/ -v --no-cov` 全绿。

### 修复边界约束
- **迭代上限**：最多 3 轮修复循环，超出则 `gh issue comment` 请求人工介入。
- **禁止**：引入 CSS 选择器兜底。
- **必须**：修复须过完整测试套件。

---

## 维度4：依赖升级修复

### 触发条件
Dependabot 开 PR 后，`dep-upgrade-verify.yml` workflow 检测到测试失败，打上 `needs-autonomous-fix` label。

### 修复步骤（Agent 执行）
1. 读取失败的 PR 评论，识别失败的测试名称和错误信息。
2. 用 `cliany-site doctor --json` 确认环境健康。
3. 定位破坏性 API 变化：
   ```bash
   # 查阅上游新版文档（librarian/web search）
   # 示例：browser-use 升级后 AXTree 结构变化
   # 示例：langchain 升级后模型调用 API 变化
   ```
4. 在 Dependabot PR 分支上修复：
   - 更新 `src/cliany_site/` 中受影响的调用方式
   - 更新 `tests/benchmarks/data/` 中受影响的基线数据（如 AXTree 结构变化）
5. 验证：`pytest tests/ -v --no-cov` 全绿后推送到同一 PR 分支。

### 边界约束
- **迭代上限**：最多 3 轮修复循环，超出则在 PR 留评论请求人工介入。
- **禁止**：修改测试逻辑来绕过失败、引入 `# type: ignore` 掩盖类型错误。
- **禁止**：自动 merge PR（合并由人工或 CI 全绿后决策）。
- **必须**：修复须过完整测试套件（`pytest tests/`）。

---

## 共通护栏

以下约束适用于所有维度的自主修复：

1. **迭代上限**：每次触发最多 3 轮修复循环，超出则停止并请求人工介入。
2. **禁止破坏现有基础设施**：不重写 `.github/workflows/ci.yml` 现有 jobs、`tests/conftest.py`、`src/cliany_site/testing/snapshot.py`。
3. **禁止在 PR 门禁注入真实 LLM 密钥**：所有 CI 修复验证一律使用 `CLIANY_QA_OFFLINE=1`。
4. **所有修复须过完整测试**：`pytest tests/ -v` 全绿才可提交/推送。
5. **禁止引入脆弱 CSS 选择器**：必须基于 AXTree 语义模糊匹配（`selector_map` role/name）。
6. **禁止编辑生成的 adapter 代码**（标记 `# 自动生成 — DO NOT EDIT`）。
