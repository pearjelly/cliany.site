# Candidate Promotion Runbook

**适用版本：** v0.16.258+
**默认首要案例：** `pypi-project-search`
**目标：** 把 candidate 案例晋级所需的 adapter package、metadata validation 和 online smoke 证据整理成可复制的维护流程。

这份 runbook 面向维护者和贡献者。它不要求默认 PR 检查访问真实第三方站点，也不要求在证据未齐时把 candidate 标记为 active。所有真实运行产生的 adapter、session、snapshot 和 package 资产都应保留在 `~/.cliany-site/` 或 release asset 中，不写入仓库。

## 什么时候使用

使用场景：

- 计划器提示 `case_promotion_evidence_primary_case_id=pypi-project-search`。
- `promotion_evidence_summary.primary_next_task` 指向 `adapter_package`。
- 需要创建或更新 candidate promotion issue。
- 需要在下一个 release 中附上 adapter package 或 blocker evidence。

先运行：

```bash
python scripts/plan_next_iteration.py --target-version 0.16.258 --remote --json
cliany-site cases --status candidate --promotion-plan --json
cliany-site cases --case-id pypi-project-search --evidence-bundle --json
```

确认这些字段：

- `daily_release_cap_blocked`：如果为 `true`，只准备证据，不创建 tag。
- `daily_release_resume_date`：下一次允许尝试 tag 的日期。
- `case_promotion_evidence_primary_case_id`：应为 `pypi-project-search`。
- `case_promotion_evidence_primary_task`：应为 `adapter_package`。
- `case_promotion_evidence_primary_expected_adapter_package`：应为 `pypi.org-<version>.cliany-adapter.tar.gz`。
- `case_promotion_evidence_primary_issue_template_command`：应能直接生成 issue body。
- `case_promotion_evidence_primary_evidence_bundle_json_command`：应能直接生成机器可读证据包。

## Step 1: Live LLM Preflight

真实 `explore` 前必须先跑 live LLM preflight：

```bash
cliany-site doctor --llm-live --json > /tmp/cliany-doctor-preflight.json
cliany-site cases --case-id pypi-project-search --evidence-bundle --doctor-json /tmp/cliany-doctor-preflight.json --json
cliany-site cases --case-id pypi-project-search --issue-template --doctor-json /tmp/cliany-doctor-preflight.json
python scripts/plan_next_iteration.py --target-version 0.16.260 --doctor-json /tmp/cliany-doctor-preflight.json --issues-dir /tmp/cliany-candidate-issues
python scripts/extract_doctor_preflight_evidence.py /tmp/cliany-doctor-preflight.json
python scripts/extract_doctor_preflight_evidence.py /tmp/cliany-doctor-preflight.json --markdown
```

如果输出中任一条件不满足，停止真实探索，把 doctor JSON 摘要贴回 candidate issue，并保持 `adapter_package` 为 `pending` 或 `blocked`：

- `summary.ready_for_explore=true`
- `summary.llm_live_preflight.ready=true`
- `summary.capabilities.generate_adapters.ready=true`
- `checks[llm_live].status` 不是 warning/error

常见 blocker evidence 字段：

- `summary.ready_for_explore`
- `summary.llm_live_preflight`
- `summary.capabilities.generate_adapters.ready`
- `checks[llm_live].status`
- `checks[llm_live].details.error_code`
- `checks[llm_live].details.retryable`
- `checks[llm_live].details.status_code`
- `checks[llm_live].details.phase`
- `checks[llm_live].details.message`

`cliany-site cases --doctor-json` 会按 `doctor_preflight_evidence_selectors` 从 doctor JSON 的 `data.checks[name="..."]` 列表中提取这些字段，并把 `doctor_preflight_evidence_values`、`doctor_preflight_evidence_ok`、`doctor_preflight_evidence_missing_count`、`doctor_preflight_evidence_null_count`、`doctor_preflight_evidence_null_fields` 和 `doctor_preflight_state` 附加到 evidence bundle、primary `adapter_package` task 或 issue body。`doctor_preflight_state_fields` 固定为 `preflight_state.status`、`preflight_state.ready_for_adapter_package`、`preflight_state.primary_reason`、`preflight_state.reason_codes` 和 `preflight_state.next_action`；`doctor_preflight_state_statuses` 固定为 `ready`、`blocked`、`missing_fields`。只有 `preflight_state.status=ready` 且 `preflight_state.ready_for_adapter_package=true` 时，才继续真实 `explore`；`blocked` 或 `missing_fields` 时先把 state、reason codes 和 doctor evidence 贴回 issue。`scripts/plan_next_iteration.py --doctor-json ... --issues-dir ...` 会把同一份 evidence 写进批量 candidate issue artifacts 的 `issue-metadata.json` 和 issue body，并让 issue/evidence bundle commands 保留 `--doctor-json <path>`，适合 live LLM 仍 blocked 时生成 blocker-ready issue 草稿。`scripts/extract_doctor_preflight_evidence.py` 仍可作为低层备用；它会输出 `values`、`missing_fields`、`null_fields`、`selectors_sha256` 和 `values_sha256`，加 `--markdown` 可生成直接粘贴到 candidate issue 的 blocker evidence 表格。`null_fields` 表示 selector 已解析且值为 JSON `null`；如果 `missing_count>0`，则先贴回真正缺失的字段和原始 doctor JSON 摘要，不继续运行真实 `explore`。

## Step 2: Generate Adapter Package Evidence

preflight 通过后，运行 candidate 的 explore 命令：

```bash
cliany-site explore "https://pypi.org" "search Python packages for cliany-site and list project names" --json
```

生成并发布 adapter package 后，证据中必须包含其中之一：

- 本地 package 路径，例如 `~/.cliany-site/packages/pypi.org-<version>.cliany-adapter.tar.gz`
- GitHub Release asset 名称，例如 `pypi.org-<version>.cliany-adapter.tar.gz`

验收标准：

```text
Attach the generated <domain>-<version>.cliany-adapter.tar.gz package path or GitHub Release asset name.
```

不要把 `~/.cliany-site/` 下的 package 文件提交进仓库。

## Step 3: Metadata Validation

adapter package 存在后，运行：

```bash
python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --include-candidate-packages --strict
```

验收证据应说明：

- `ok: True`
- candidate package schema 通过
- manifest hash 可读
- `adapter_domain` 与 case manifest 匹配
- package 名称匹配 `pypi.org-<version>.cliany-adapter.tar.gz`

如果 package 暂时只作为 GitHub Release asset 存在，应先下载到本地 packages dir 再跑同一条 validation 命令。

## Step 4: Online Smoke

安装或加载 adapter 后，运行只读 smoke 命令：

```bash
cliany-site pypi.org search-projects --query cliany-site --limit 5 --json
```

验收证据应包含：

- JSON envelope `ok=true`
- `data.quality.ok=true`
- `row_count>0`
- 至少一条结果能看出 PyPI project 名称

如果 PyPI 页面结构变化导致抽取为空，不要把 candidate 标为 active。把 JSON envelope、错误码、quality 字段和截图或页面摘要作为 blocker evidence。

## Step 5: Update Case Evidence

只有三段证据都齐全时，才更新 `cases/manifest.json` 中该 candidate 的 `promotion_evidence`：

- `adapter_package`
- `metadata_validation`
- `online_smoke`

然后运行：

```bash
python scripts/validate_cases.py --strict
python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md
```

如果三段证据都完整且可复核，下一步才考虑把 `pypi-project-search` 从 `candidate` 晋级为 `active`。晋级 PR 应同时说明 release asset、metadata validation 和 online smoke 的证据来源。

## Issue Handoff

生成可复制 issue body：

```bash
cliany-site cases --case-id pypi-project-search --issue-template
cliany-site cases --case-id pypi-project-search --issue-template --json
```

生成机器可读 evidence bundle：

```bash
cliany-site cases --case-id pypi-project-search --evidence-bundle
cliany-site cases --case-id pypi-project-search --evidence-bundle --json
```

批量生成 candidate issue artifacts：

```bash
python scripts/plan_next_iteration.py --target-version 0.16.260 --remote --issues-dir /tmp/cliany-candidate-issues
python scripts/plan_next_iteration.py --target-version 0.16.260 --remote --doctor-json /tmp/cliany-doctor-preflight.json --issues-dir /tmp/cliany-candidate-issues
```

创建公开 GitHub issue 前，先审阅：

- `candidate_issue_gate.status`
- `candidate_issue_gate.requires_maintainer_review`
- `publication_visibility.status`
- `release_draft_issue_count`
- `daily_release_cap_blocked`
- `case_promotion_evidence_primary_runbook_steps_sha256`
- `case_promotion_evidence_primary_llm_live_preflight_command_sha256`
- `case_promotion_evidence_primary_doctor_preflight_evidence_template_sha256`
- `doctor_preflight_state_fields`
- `doctor_preflight_state_statuses`

如果 gate 仍要求人工审阅，只有在审阅完成后才设置：

```bash
CLIANY_CREATE_ISSUES_ACK_REVIEW=1
```

## Non-goals

- 不在 PR 默认检查中依赖真实 LLM key。
- 不在仓库内提交 runtime adapter/session/snapshot/package 文件。
- 不用脆弱 CSS selector 作为 AXTree 语义匹配的兜底。
- 不把 candidate 提前标成 active。
- 不在 daily release cap 已满时创建新的 release tag。
