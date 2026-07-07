# 更新日志

本项目的所有显著更改都将记录在此文件中。

本文件的格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
并且本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- `scripts/plan_next_iteration.py --doctor-json <path> --issues-dir ...` now embeds saved `cliany-site doctor --llm-live --json` evidence into candidate issue artifacts, including `doctor_preflight_state`, extracted values, source path, and doctor-json-aware issue/evidence bundle commands.
- `scripts/plan_next_iteration.py --doctor-json <path> --handoff-json` now exposes the primary candidate `doctor_preflight_state` plus direct status, ready, and primary-reason aliases, so release automation can stop before `explore` without expanding full issue artifacts.
- Planner-generated candidate issue bodies now render a `Current Doctor Preflight State` section when `--doctor-json` is provided, so maintainers can file blocker-ready PyPI candidate issues without hand-splicing live LLM/CDP evidence.
- Planner-generated `create-issues.sh` scripts now preflight required GitHub labels before running `gh issue create`, listing missing labels such as `case-proposal` so candidate issue publication fails before any partial issue creation.

### Fixed
- The `v0.16.260` release draft now describes the daily release cap as a projected `3/3` to `4/3` target-tag blocker, avoiding ambiguous wording that implied the current `3/3` state was already over the limit.
- README and README.zh now spell out the `doctor_preflight_state_fields` values and the `ready` / `blocked` / `missing_fields` state set, so maintainers can apply the doctor-backed candidate blocker contract without cross-reading release drafts or source code.
- The `v0.16.260` release draft now tracks the README/README.zh doctor preflight state contract and the related documentation checks, keeping release notes aligned with the current candidate blocker handoff.
- The Candidate Promotion Runbook now documents the same `doctor_preflight_state_fields` and `doctor_preflight_state_statuses` contract, including when to continue to real `explore` versus attaching blocker evidence to the candidate issue.
- Good First Issues now asks candidate-promotion issues to carry the same doctor preflight state fields and `ready` / `blocked` / `missing_fields` status contract, keeping first-contributor handoffs aligned with the runbook.
- The contributor starter map now mirrors the same doctor preflight state contract, so first-time contributors who enter through the starter guide see when to continue real `explore` versus attaching blocker evidence.
- The case catalog README now documents the same doctor preflight state fields and `ready` / `blocked` / `missing_fields` status contract beside candidate evidence bundle handoffs, keeping case promotion guidance aligned with the runbook and contributor docs.
- The public website maintainer entrypoints now spell out the same `preflight_state.*` field list and `ready` / `blocked` / `missing_fields` gate, so website-only readers can apply candidate blocker evidence without opening source docs.
- The GitHub case proposal and pull request templates now ask candidate promotion contributors to include the same doctor preflight state fields and status contract, and release readiness now blocks those templates if the contract drifts.
- Planner-generated candidate issue bodies now always render the doctor preflight state contract, including the `preflight_state.*` fields, `ready` / `blocked` / `missing_fields` statuses, and the exact gate for continuing `adapter_package`.
- Release readiness now blocks planner issue-body drift when `scripts/plan_next_iteration.py` stops rendering the doctor preflight state contract or the exact `adapter_package` continuation gate.
- Candidate issue artifact READMEs now include an `Issue Body State Contract` section, so maintainers can verify the generated issue-body preflight gate before opening or copying individual issue files.

## [0.16.259] - 2026-07-07

### Added
- `cliany-site cases --case-id <id> --evidence-bundle --doctor-json <path>` now reads a saved `cliany-site doctor --llm-live --json` result and attaches actual doctor preflight values, hashes, missing-field counts, and `doctor_preflight_state` to the evidence bundle and primary `adapter_package` task.
- Candidate issue templates also accept `--doctor-json`, rendering copy-ready blocker evidence directly in the issue body when live LLM/CDP preflight blocks adapter generation.

## [0.16.258] - 2026-07-07

### Added
- Candidate promotion handoffs now expose a stable doctor preflight state contract: `doctor_preflight_state_fields`, `doctor_preflight_state_fields_sha256`, `doctor_preflight_state_statuses`, and `doctor_preflight_state_statuses_sha256`.
- Cases evidence bundles, promotion summaries, case validation summaries, planner candidate metadata, issue metadata, and compact planner handoffs now surface the same `preflight_state.*` contract so automation can read `ready`, `blocked`, and `missing_fields` semantics without opening the extractor source.

## [0.16.257] - 2026-07-07

### Added
- Added a maintainer-facing Candidate Promotion Runbook that turns the `pypi-project-search/adapter_package` handoff into a concrete preflight, adapter package, metadata validation, and online smoke checklist, and linked it from the good-first-issue docs, weekly maintainer docs, and public website docs.
- Added `python scripts/plan_next_iteration.py --handoff-json`, a compact planner output for release automation that needs the primary next action, publication summary, primary candidate task, issue/evidence bundle commands, validation commands, and a stable `handoff_sha256` without expanding full planner JSON.
- Candidate issue artifacts generated by `python scripts/plan_next_iteration.py --issues-dir ...` now include `planner-handoff.json`, the same compact handoff payload used by `--handoff-json`, and list it in artifact files, review order, and README handoff guidance.
- Candidate promotion evidence now exposes `doctor_preflight_evidence_selectors` beside the existing doctor evidence field names, and the human evidence bundle renders the same selector mapping so maintainers can locate `checks[name="llm_live"]` entries in the actual `doctor --llm-live --json` checks list.
- Compact planner handoffs now include primary candidate `doctor_preflight_evidence_fields`, `doctor_preflight_evidence_selectors`, selector count, and selector SHA-256, so automation using only `--handoff-json` can attach live LLM blocker evidence without opening full issue artifacts.
- Candidate issue artifact READMEs now show the compact planner handoff's doctor preflight selector count, selector SHA-256, and LLM error selector in the Planner Handoff section, so human artifact review can verify the same blocker-evidence mapping without opening JSON files.
- Added `python scripts/extract_doctor_preflight_evidence.py <doctor.json>`, which converts `cliany-site doctor --llm-live --json` output into a compact values/selectors evidence JSON for candidate promotion blocker comments.
- `scripts/extract_doctor_preflight_evidence.py` now supports `--markdown`, producing a copy-ready blocker evidence table for candidate promotion issues.
- Doctor preflight evidence extraction now classifies candidate promotion preflight as `ready`, `blocked`, or `missing_fields`, with stable reason codes and next actions for the PyPI candidate adapter-package gate.
- Cases evidence bundles, promotion plans, candidate issue bodies, and compact planner handoffs now expose the doctor preflight evidence extractor JSON/Markdown commands directly, so maintainers and bots do not need to reconstruct the script path from docs before attaching blocker evidence.
- Case validation JSON, Markdown reports, and plain text output now expose the same doctor preflight evidence extractor JSON/Markdown commands on the primary candidate task, so validation-only automation can attach blocker evidence without opening cases or planner artifacts.
- Compact planner handoffs now include `daily_release_resume_date_sha256` beside `daily_release_resume_date`, so daily-cap automation can verify the resume date without expanding the full planner JSON.

## [0.16.256] - 2026-07-03

### Changed
- Next-iteration planner JSON, text/Markdown reports, and candidate issue artifact summaries now expose primary candidate `issue_template` and `evidence_bundle` commands as top-level aliases, so automation can jump directly from the selected `adapter_package` task to reproducible issue and evidence handoffs.

## [0.16.255] - 2026-07-03

### Changed
- Next-iteration planner JSON, Markdown reports, plain text output, and candidate issue artifact summaries now expose primary candidate evidence aliases for `expected_adapter_package`, `acceptance_criteria`, `priority_rank`, and `priority_reason`, so release automation can act on the selected `adapter_package` task without expanding the nested primary task object.

## [0.16.254] - 2026-07-03

### Changed
- Next-iteration planner JSON and candidate issue artifacts now include issue template handoff commands (`candidate_promotions[*].issue_template_command`, `candidate_promotions[*].issue_template_json_command`, matching `issue-metadata.json` fields, and artifacts README Issue Template columns), so maintainers can regenerate candidate promotion issue bodies without deriving commands from case ids.
- Candidate issue bodies now include a `Doctor Preflight Evidence Template` with paste-ready `cliany-site doctor --llm-live --json` placeholders for every doctor preflight field, so LLM/CDP blockers can be attached consistently.
- Cases JSON, planner candidate promotion JSON, and candidate issue metadata now expose the same placeholders as `doctor_preflight_evidence_template`, so bots do not need to parse Markdown to attach doctor blocker evidence.
- Cases evidence bundles, planner JSON, candidate issue metadata, Markdown reports, and artifact README summaries now expose `doctor_preflight_evidence_template_field_count` / `doctor_preflight_evidence_template_sha256` plus primary and overall planner aliases, so bots can compare doctor evidence template drift without expanding Markdown.
- Cases promotion plan JSON now mirrors doctor template drift aliases onto `promotion_plan.primary_doctor_preflight_evidence_template_sha256`, each candidate primary task, and each incomplete `task_queue` item, so queue-only bots can compare evidence template drift without opening a full evidence bundle.
- Case validation JSON and Markdown reports now expose doctor template drift aliases on `promotion_evidence_summary.primary_next_task` and the `Candidate Promotion Evidence Summary` table, so validation-only tooling can compare the same preflight evidence contract.
- Case validation plain text output now also prints `promotion_evidence_primary_doctor_preflight_evidence_template_field_count` and `promotion_evidence_primary_doctor_preflight_evidence_template_sha256`, so stdout-only `scripts/validate_cases.py --strict` logs can detect doctor template drift.
- Candidate promotion handoffs now expose `llm_live_preflight_command_sha256` and planner alias `case_promotion_evidence_primary_llm_live_preflight_command_sha256`, so bots can detect drift in the required doctor preflight command without parsing runbooks.
- Candidate promotion issue bodies now render the live LLM preflight `Command SHA-256`, so copied GitHub issues preserve the command drift signal for human review.
- Candidate `promotion_command_plan` entries now expose `command_sha256`, so explore, metadata validation, and online smoke command drift can be checked without parsing natural-language handoffs.
- Candidate promotion issue bodies now render `command_sha256` under each `Promotion Command Plan` entry, so copied issues keep the per-command drift signal without requiring a separate evidence bundle.
- Candidate promotion issue bodies now also render `source` and `missing` under each `Promotion Command Plan` entry, so copied issues preserve where each command came from and whether a required command is absent.
- Candidate promotion issue bodies now include a `Promotion Command Plan Summary`, so copied issues show command count, missing command count, and all-declared status before the detailed command list.
- Cases detail JSON, evidence bundles, direct issue-template JSON, planner candidate promotions, and `issue-metadata.json` now expose `promotion_command_plan_summary` / `issue_template_promotion_command_plan_summary`, so bots can read command count, missing command count, and all-declared status without parsing Markdown.
- Candidate issue artifacts README now renders `promotion_command_plan_summary` in the `Candidate Summary` table, so maintainers can see command count, missing command count, and all-declared status before opening JSON metadata.
- Next-iteration Markdown reports now render `promotion_command_plan_summary` in the `Candidate Issue Metadata` table, so report-only reviews can see command count, missing command count, and all-declared status without generating issue artifacts.
- Candidate issue body inventory now carries `promotion_command_plan_summary` in JSON and README output, so maintainers can verify each body file hash alongside the command-plan completeness signal.
- Candidate issue gates now de-duplicate `required_actions` while preserving order, so overlapping publication and release-readiness blockers do not repeat the same maintainer action.
- Planner publication handoffs now de-duplicate `publication_next_actions` while preserving order, so repeated publication audit actions do not inflate action counts or drift hashes.
- Planner publication handoffs now de-duplicate `publication_publish_commands` while preserving order, so repeated publish commands do not inflate command counts or drift hashes.
- Release draft handoffs now de-duplicate `release_draft_required_actions` while preserving the original issue list, so repeated draft validation messages do not inflate action counts or drift hashes.
- Release readiness now de-duplicates publication handoff `next_actions` and `publish_commands` before exporting JSON/text/Markdown aliases, so direct release automation sees the same stable counts and hashes as the planner.
- Release readiness publication handoffs now suppress create-tag next actions while the target tag is blocked by the daily release cap, so direct publication automation receives the same pause signal as the top-level standard release flow.
- Release readiness target-tag publication decisions now mark daily-cap pauses as `blocked_by_daily_release_cap` and reuse the pause required action, so nested decision readers no longer see a stale create-tag instruction.
- Release readiness standard release flow summaries now expose primary blocked/pending step `command` / `action` aliases and SHA-256 digests, so automation can execute or display the first gate without traversing the full `steps` array.
- Next-iteration planner target-tag publication decisions now mirror the same `blocked_by_daily_release_cap` pause state, keeping planner artifacts aligned with release readiness for daily-cap pauses.
- Next-iteration planner standard release flow summaries now mirror primary blocked/pending step `command` / `action` aliases and SHA-256 digests across JSON, text/Markdown reports, publication handoffs, artifact manifests, bundle summaries, and artifact READMEs.
- Release readiness and next-iteration planner primary blocked/pending step handoffs now also expose exact `status` aliases and SHA-256 digests, so automation can distinguish `blocked`, `pending`, and more specific gate states without reopening `standard_release_flow.steps`.
- Next-iteration planner `publication_next_actions` now uses the same target-aware daily-cap filtering as top-level `next_actions`, so planner artifacts no longer expose create-tag actions while the target tag is paused.
- Next-iteration planner JSON, text output, and Markdown reports now expose the same `publication_handoff_*` schema, boundary, preview/tail, and SHA-256 aliases as candidate issue artifact summaries, so automation can audit `publication-handoff.json` shape without generating issue artifacts first.
- Next-iteration planner JSON, text output, Markdown reports, and artifact bundle summaries now share `release_draft_handoff_*`, required-action window, and issue window aliases, so automation can audit `release-draft-handoff.json` shape without generating candidate issue artifacts first.
- Planner candidate preflight aliases now use the same raw command SHA-256 as cases CLI and generated issue bodies, so `llm_live_preflight_command_sha256` fields no longer drift from the displayed preflight command hash.
- Cases promotion plan output now includes issue template handoff commands (`issue_template_command`, `issue_template_json_command`, and primary aliases), so maintainers can jump from the candidate queue directly to a copyable promotion issue body.
- Cases issue template output now reuses the evidence-bundle primary task, so `cliany-site cases --case-id <id> --issue-template` renders a `Primary Runbook`, standard LLM/doctor blocker comments, and `Doctor Preflight Evidence Fields`; `--json` exposes the same acceptance, runbook, and preflight fields on `issue_template_primary_task`.
- Cases evidence bundle JSON now exposes `doctor_preflight_evidence_fields` at the bundle level and on the `adapter_package` task, so direct `cliany-site cases --case-id <id> --evidence-bundle --json` handoffs can capture CDP and LLM blocker fields without going through planner artifacts.
- Next-iteration planner JSON, Markdown reports, and candidate issue artifact README summaries now expose `case_promotion_evidence_primary_llm_live_preflight_required`, `case_promotion_evidence_primary_llm_live_preflight_command`, `case_promotion_evidence_primary_llm_live_preflight_blocker_note`, `case_promotion_evidence_primary_llm_live_preflight_blocker_comment`, `case_promotion_evidence_primary_doctor_preflight_blocker_comment`, and candidate-level `doctor_preflight_evidence_fields`, so summary-only tools can detect the primary candidate live preflight gate and copy a standard CDP/LLM blocker comment without expanding the task object.
- Candidate human handoffs now render `preflight_required`, `preflight_blocker`, and `runbook_first` in the `Candidate 下一步` section, so non-JSON users see the live LLM gate before starting a real `explore`.
- Candidate promotion task objects now expose `llm_live_preflight_required`, `llm_live_preflight_command`, `llm_live_preflight_blocker_note`, and `llm_live_preflight_evidence_fields`, so summary-only tools can record live LLM blockers without expanding runbooks.
- Candidate promotion handoffs now expose `expected_adapter_package` across the cases CLI issue templates, evidence bundles, promotion plans, case validation summaries, next-iteration planner metadata, and generated issue bodies.
- Release readiness and next-iteration planning now expose `daily_release_cap_blocked`, `daily_release_resume_date`, and `daily_release_resume_date_sha256` when the target tag would exceed the daily release cap, so maintainers can see the exact next eligible release date instead of inferring it from prose.
- Release readiness and next-iteration text/Markdown reports now render the daily release cap status, resume date, and resume-date hash beside the existing JSON fields.
- Candidate issue artifacts now carry the same daily release cap handoff through `artifact-manifest.json`, `artifact_bundle_summary`, `publication-handoff.json`, and artifact README summaries.
- README, README.zh, website maintainer copy, and weekly maintainer docs now surface the daily-cap resume fields and the `CLIANY_CREATE_ISSUES_ACK_REVIEW=1` issue creation acknowledgment handoff.
- Added the `v0.16.254` release draft, documenting the 2026-07-02 daily-cap pause and the 2026-07-03 resume target without creating a new tag, GitHub Release, PyPI upload, or website deployment.

### Fixed
- Candidate issue creation scripts now default to `python3` through an overridable `PYTHON_BIN`, so generated issue handoff artifacts run on systems without a bare `python` executable.
- Candidate issue creation scripts now require `CLIANY_CREATE_ISSUES_ACK_REVIEW=1` before creating public GitHub issues when the candidate issue gate reports `requires_maintainer_review=true`, and generated artifact READMEs/manifests expose that acknowledgment contract.

## [0.16.253] - 2026-07-02

### Changed
- Release readiness standard release flows now include a `website_inspect` step after production website deployment, using `cd site && vercel inspect www.cliany.site --wait --timeout 90s` to verify the public cliany.site alias target before the final distribution audit.
- Release readiness and next-iteration planning now expose `standard_release_flow_has_website_inspect`, `standard_release_flow_website_inspect_command`, and `standard_release_flow_website_inspect_command_sha256` across JSON, text/Markdown reports, candidate issue manifests, publication handoff, bundle summaries, and artifact READMEs.
- Weekly maintainer docs, public roadmaps, and the website maintainer entrypoint now document the website inspect checkpoint and update the maintained baseline to the v0.16.253 release train.

## [0.16.252] - 2026-07-02

### Changed
- Release publication audits now fall back to PyPI's version-specific JSON endpoint when the project-level latest-version cache still reports the previous release, so a freshly uploaded version can be verified without waiting for `info.version` cache expiry.
- Distribution audit JSON, text, and Markdown reports now expose `pypi_latest_version` and `pypi_release_version` alongside the backward-compatible `pypi_version`, making PyPI cache-lag windows visible instead of ambiguous.
- README、README.zh、release cadence docs、weekly maintainer docs、public roadmap 和官网维护者入口 now document the stronger post-release PyPI audit fields and update the maintained baseline to the v0.16.252 release train.

## [0.16.251] - 2026-07-02

### Changed
- Candidate promotion plan and release planning evidence now prioritize candidate cases with more completed promotion evidence and fewer blockers before falling back to manifest order, so maintainers can keep pushing the closest case toward `active`.
- Candidate promotion plan output now includes stable `priority_rank` and `priority_reason` fields in JSON and human markdown, making the candidate queue ordering auditable for maintainers and issue handoffs.
- Case validation and next-iteration planning evidence summaries now carry the same `priority_rank` and `priority_reason` on candidate promotion tasks, so release artifacts explain candidate ordering without requiring the cases CLI.
- Candidate promotion issue artifacts now carry `priority_rank` and `priority_reason` through issue metadata, primary evidence tasks, and generated issue bodies, so candidate handoffs preserve the same ordering explanation as the planner summary.
- Candidate issue artifact README summaries now show promotion priority rank and reason beside each candidate, so maintainers can review ordering without opening JSON metadata.
- Next-iteration Markdown reports now show candidate issue priority rank and reason in the Candidate Issue Metadata table, so maintainers can review queue order without generating issue artifacts.
- Next-iteration validation commands and candidate issue artifacts now preserve remote audit arguments for `check_release_publication.py`, so copied validation steps re-check the same remote refs as the planner run.
- Release readiness and next-iteration standard release flow commands now preserve `--remote-name` on strict readiness checks, remote publication audits, and publish-script generation commands.
- Release readiness and next-iteration standard release flow remote publication audits now include `--distribution`, so the structured release checklist verifies GitHub Release and PyPI visibility after the tag workflow.
- Release readiness standard release flow commands now include the production website deployment command `cd site && vercel link --yes --project cliany.site && vercel --prod --yes`, so GitHub Release, PyPI, and website sync stay in the same checklist.
- Release readiness now exposes `standard_release_flow_has_website_deploy`, `standard_release_flow_website_deploy_command`, and `standard_release_flow_website_deploy_command_sha256`, so summary readers can verify the website deploy handoff without expanding the full standard release flow.
- Next-iteration planning and candidate issue artifacts now carry the same website deploy aliases through planner JSON, text/Markdown reports, `artifact-manifest.json`, `publication-handoff.json`, `artifact_bundle_summary`, and artifact README handoffs.
- Release readiness now exposes `standard_release_flow_has_distribution_audit`, `standard_release_flow_distribution_audit_command`, and `standard_release_flow_distribution_audit_command_sha256`, so summary readers can verify the final GitHub Release/PyPI audit without expanding the full standard release flow.
- Next-iteration planning and candidate issue artifacts now carry the same distribution audit aliases through planner JSON, text/Markdown reports, `artifact-manifest.json`, `publication-handoff.json`, `artifact_bundle_summary`, and artifact README handoffs.
- Next-iteration planner fallback standard release flows now include structured `steps`, keeping strict readiness, release notes, version bump, offline validation, branch publish, target tag, website deploy, and remote audit ordering available even when the planner cannot reuse release readiness' prebuilt flow.
- Release readiness and next-iteration planning now expose compact standard release flow step summaries (`standard_release_flow_step_count`, `standard_release_flow_step_names`, `standard_release_flow_step_names_sha256`, and `standard_release_flow_steps_sha256`) across JSON, text/Markdown reports, candidate issue manifests, publication handoff, bundle summaries, and artifact READMEs.
- Standard release flow summaries now also expose `standard_release_flow_first_step_name`, `standard_release_flow_last_step_name`, and `standard_release_flow_step_boundary_sha256`, so summary-only tools can verify the flow starts with strict readiness and ends with remote publication audit.
- Standard release flow summaries now include `standard_release_flow_step_status_counts`, `standard_release_flow_step_status_counts_sha256`, `standard_release_flow_primary_blocked_step_name`, and `standard_release_flow_primary_pending_step_name`, so summary-only tools can see the current gate shape before expanding full steps.
- Candidate evidence bundles and promotion plans now expose `primary_next_task_runbook` / `primary_runbook`, giving maintainers an ordered preflight-first checklist for the current candidate task.
- Next-iteration candidate issue artifacts now carry the primary candidate runbook through planner JSON, issue metadata, generated issue bodies, and artifact README summaries.
- Case validation and release readiness Markdown reports now render the same primary candidate runbook, so maintainers see the live LLM preflight, current evidence command, and acceptance step without opening the cases CLI.
- Release readiness and next-iteration planner JSON now expose compact primary runbook aliases, step counts, step lists, and SHA-256 hashes, and issue artifact bundle summaries render the same fields for tools that only read summary surfaces.
- Case validation, cases CLI, release readiness, next-iteration planning, and candidate issue artifact summaries now expose the primary runbook first step, first command, and first-command hash, so bots can run the live LLM preflight without expanding the full runbook.
- Cases CLI evidence bundles, candidate issue metadata, artifact README summaries, and generated candidate issue bodies now list the exact `cliany-site doctor --llm-live --json` fields to attach when live LLM preflight blocks candidate promotion.
- Live LLM preflight evidence handoffs now include `checks[llm_live].details.retryable` and `checks[llm_live].details.status_code`, so candidate promotion issues can distinguish retryable provider outages from configuration failures.
- `doctor --llm-live --json` now exposes `summary.llm_live_preflight`, a compact checked/ready/status/action object with provider and error details, so preflight automation can detect blocked adapter generation without walking the raw checks list.
- Candidate evidence bundles, planner issue metadata, generated issue bodies, and artifact README summaries now include `summary.llm_live_preflight` in `llm_live_preflight_evidence_fields`, so maintainers can attach the compact doctor preflight object as blocker evidence.
- Case validation and release readiness JSON/Markdown reports now expose the same `llm_live_preflight_evidence_fields` list, field count, and hash, so CI artifacts and release gates can preserve doctor preflight blocker evidence without expanding cases CLI bundles.
- Next-iteration planner JSON, Markdown reports, candidate issue manifests, artifact bundle summaries, and artifact READMEs now expose `case_promotion_llm_live_preflight_evidence_fields` plus count/hash aliases, matching release readiness for summary-only maintainer tools.
- README / README.zh now document the compact candidate runbook aliases that appear in planner and issue artifact summaries, and release readiness now gates the PyPI long-description entrypoints on those aliases.
- Contributor starter and good-first-issue docs now explain how to use `primary_next_task_runbook` and compact runbook aliases when creating candidate promotion issues, and release readiness gates those contributor entrypoints.
- Website quickstart and docs now surface the same candidate runbook handoff fields, and release readiness gates the static site on those public entrypoint snippets.
- The Real Demo Case Proposal issue template now prompts candidate promotion authors to include `primary_next_task_runbook` and compact runbook drift checks, with release readiness guarding that GitHub-native entrypoint.
- The pull request template now asks candidate promotion PRs to attach the same runbook and compact alias drift evidence, and release readiness gates that review checklist.
- `cliany-site doctor` now treats a sentinel-free root `AGENTS.md` as a manual agent knowledge base instead of a broken generated `AGENT.md`, keeping first-run diagnostics focused on actionable managed-file repairs.

### Fixed
- LLM retry classification now treats provider connection errors such as `Connection error.` as retryable `E_LLM_UNAVAILABLE`, so `doctor --llm-live` and `explore --json` no longer bury upstream connectivity failures under `E_UNKNOWN`.
- Release readiness now projects whether creating the target tag today would exceed the daily release cap, so planning `v0.16.251` after `v0.16.248`、`v0.16.249` 和 `v0.16.250` 已发布时会明确暂停 tag，而不是继续给出第四个同日 release 命令。
- Next-iteration planning now carries release readiness next actions such as the daily release cap pause into top-level `next_actions`, while avoiding a duplicate shorter weekly cadence action when readiness already provides the richer guidance.
- Release readiness and next-iteration planning now suppress target tag commands while the projected daily release cap blocks that target, so automation cannot mistake the pause gate for an executable tag handoff.
- Daily-cap pause guidance now takes precedence over generic "create a new release tag" wording in release readiness and next-iteration planner `next_actions`, keeping the first action aligned with the active blocker.
- Candidate issue gate now surfaces non-draft release readiness blockers such as the daily release cap as `release_readiness_blockers`, so issue artifacts are marked review-required instead of silently ready while the target release cannot be tagged.
- Candidate issue artifacts now promote release readiness blocker aliases into `publication-handoff.json` and the README quick summary, so maintainers can see why tagging is paused without expanding nested gate evidence.
- Candidate issue creation scripts now preflight against `candidate_issue_gate.can_create_issues` instead of strict publication visibility alone, so issue artifacts remain runnable in the normal "latest release published, HEAD preparing next version" state.
- Weekly maintainer loop docs now document the hard publication preflight command, temp JSON path, and failure handling used by candidate issue scripts.
- Release publication audits now distinguish `git ls-remote` network failures from genuinely missing remote refs, keeping branch/tag publish decisions on the safe rerun path instead of suggesting unnecessary pushes.

## [0.16.250] - 2026-07-01

### Added
- 新增 `v0.16.250` 发布草案，记录 live LLM preflight 返回 `E_UNKNOWN` connection error 时的 candidate 晋级阻塞边界。

### Changed
- Candidate promotion 的 issue template、evidence bundle、promotion plan、planner artifacts、case report、README 和官网说明现在把 `llm_live` warning/error（包括 `E_LLM_UNAVAILABLE` 与 `E_UNKNOWN` connection error）统一视为停止真实 `explore` 的 blocker 证据。

## [0.16.249] - 2026-07-01

### Added
- 新增 `v0.16.249` 发布草案，并将公开 / 维护者路线图与官网维护者循环基线校准到 `v0.16.248`；本轮继续记录 `pypi-project-search` live LLM preflight 阻塞，不伪造 candidate adapter package 证据。

## [0.16.248] - 2026-07-01

### Added
- 新增 `v0.16.248` 发布草案，将下一版继续聚焦 `pypi-project-search` candidate 晋级证据、live LLM preflight 门禁和 release cadence 累积。
- `scripts/check_release_publication.py` 新增显式 `--distribution` 发布后审计，可核对最新本地 tag 对应的 GitHub Release 与 PyPI 版本是否已经公开可见。
- `scripts/check_release_cadence.py` 和 release readiness 现在把周提交天数作为 `weekly_commit_cadence_ok` 节奏提醒，而不是阻塞当天合格 release tag 的硬门禁。

## [0.16.247] - 2026-06-28

### Added
- 新增 `v0.16.247` 发布草案，将下一版聚焦到 `pypi-project-search` candidate 晋级证据与 live LLM preflight 门禁。

## [0.16.246] - 2026-06-25

### Added
- 新增用户公开路线图，并将维护者 Q3 路线图校准到 v0.16.245 后的真实案例晋级、adapter 生命周期、抽取质量和 1.0 alpha readiness 重点。

## [0.16.245] - 2026-06-21

### Fixed
- `explore --json` now reports missing QA offline fake LLM configuration before CDP preflight, keeping deterministic offline tests independent of whether Chrome is available.
- CI Obscura smoke now reuses the already installed test environment instead of `uv run`, avoiding a fresh environment without the configured pytest coverage plugin.
- Windows CI now runs pytest in UTF-8 mode and keeps `tmp_home` isolated through Windows home environment variables, avoiding encoding failures and adapter-state leakage.
- Candidate issue artifact files now use stable LF newlines, and POSIX mode-bit assertions no longer run on Windows where those bits are not meaningful.
- Windows CI now skips the stdout-heavy current-repo planner JSON test that is already covered by the Linux Python matrix.
- Windows CI now runs an explicit cross-platform smoke suite instead of duplicating the full Linux pytest matrix, avoiding console-interactive test interruptions on the Windows runner.
- Windows CI invokes the smoke suite with `python -m pytest` to avoid an anomalous non-zero exit from the `pytest` console script after passing tests.
- Windows CI now checks the smoke suite JUnit XML before accepting that anomalous non-zero exit, so real Windows test failures still fail the job.
- Windows CI disables PowerShell native-command fail-fast around pytest so the JUnit-based result check can run.
- Windows CI now runs the smoke suite under `cmd`, logs the native pytest exit code plus JUnit status, and treats a zero-failure smoke report as authoritative.

## [0.16.244] - 2026-06-20

### Fixed
- Restored the main CI quality gates by applying the current ruff cleanup and mypy type-narrowing fixes across `src/`.
- Generic pytest jobs now skip the embodied Playwright test module when Playwright is not installed, avoiding collection-time failures outside the dedicated embodied workflow.
- The embodied CI workflow now installs the Playwright Python package before installing Chromium, so its headless CDP/AXTree test runs in the intended job.

## [0.16.243] - 2026-06-19

### Security
- `save_adapter()` now audits generated adapter code before writing `commands.py`; critical findings such as `eval()` abort generation with `SecurityError`.
- Added a regression test that proves unsafe generated adapter code is blocked before any adapter file is written.

### Fixed
- Release readiness tests now initialize fixture repositories with an explicit `master` branch, avoiding host `init.defaultBranch` drift.

## [0.16.242] - 2026-06-18

### Added
- `scripts/check_release_cadence.py --json` now reports `release_tags_today`, `release_count_today`, `max_daily_releases`, and `daily_release_limit_ok` so maintainers can enforce the 1-3 releases/day rule before tagging.
- `scripts/release_readiness.py` now treats an exceeded daily release cap as a cadence blocker and surfaces the pause-release next action in text and Markdown reports.
- `scripts/release_readiness.py` and `scripts/plan_next_iteration.py` now accept `--max-daily-releases` so the daily cap can be audited consistently from the cadence, readiness, and planning entrypoints.
- `scripts/release_readiness.py` and `scripts/plan_next_iteration.py` now accept `--remote` / `--remote-name` to include live remote branch and tag refs in release publication audits.
- `scripts/plan_next_iteration.py` now carries the daily release cap fields into `commit_cadence`, issue artifact summaries, and artifact README handoff sections.
- `scripts/plan_next_iteration.py` now distinguishes a published prior release plus unreleased HEAD commits from an unpublished release, so candidate planning is not mislabeled after `master` has moved past the latest tag.
- README、README.zh、路线图、发布节奏文档和官网源码现在同步说明每天 1~3 个可验证版本的发布纪律。
- 新增 `docs/releases/v0.16.242-draft.md`，把下一版聚焦到每日发布上限的机器可读门禁。

## [0.16.241] - 2026-06-17

### Added
- `scripts/plan_next_iteration.py --json` candidate promotion records now expose `llm_live_preflight_command` and `llm_live_preflight_blocker_note` without requiring automation to parse issue body Markdown.
- Generated candidate issue artifacts now include the same LLM preflight fields in `issue-metadata.json` and metadata summaries.
- Candidate issue artifact README tables and review checklists now surface the live LLM blocker contract before maintainers create promotion issues.
- Planner tests now lock the machine-readable `E_LLM_UNAVAILABLE` handoff for issue artifacts and candidate promotion JSON.
- 新增 `docs/releases/v0.16.241-draft.md`，记录本版在 live LLM 仍返回 502 时对 planner / issue artifact 交接面的加固。

## [0.16.240] - 2026-06-17

### Added
- `cliany-site cases --promotion-plan --json` now exposes the live LLM preflight command and blocker handling note at the plan, candidate, primary task, and task queue levels.
- Human promotion plan output now prints the live LLM preflight gate and `E_LLM_UNAVAILABLE` blocker handling before maintainers run candidate `explore`.
- Promotion plan tests now lock the queue-level LLM blocker contract so candidate adapters are not generated while live preflight is unavailable.
- 新增 `docs/releases/v0.16.240-draft.md`，记录本版将 live LLM 阻断规则提升到 candidate promotion queue 总入口。

## [0.16.239] - 2026-06-17

### Added
- Candidate promotion issue templates now include an explicit `LLM Preflight Gate` that tells maintainers to run `cliany-site doctor --llm-live --json` before any real `explore`.
- `cliany-site cases --case-id <id> --evidence-bundle --json` now exposes `llm_live_preflight_blocker_note`, and the human evidence bundle prints the same blocker handling guidance.
- `scripts/plan_next_iteration.py` generated candidate issue bodies and `scripts/validate_cases.py --report` issue templates now share the same preflight failure contract.
- [cases/README.md](cases/README.md) documents that `generate_adapters.ready=false` or `E_LLM_UNAVAILABLE` should stop candidate promotion and be attached as blocker evidence instead of being treated as adapter package evidence.
- 新增 `docs/releases/v0.16.239-draft.md`，记录本版在 live LLM 仍返回 502 时对 candidate handoff 的阻塞证据边界加固。

## [0.16.238] - 2026-06-17

### Added
- 所有 GitHub Actions workflow 现在声明 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`，提前切到 Node 24 runtime，避免每日发布链路继续产生 Node 20 deprecation annotations。
- `scripts/release_readiness.py` 现在把 CI 和 release workflow 的 Node 24 opt-in 纳入门禁；缺失该环境变量时会阻塞发版预检。
- release readiness 测试新增 CI / release workflow 缺少 Node 24 opt-in 的回归覆盖，确保发布基础设施不会静默退回 Node 20。
- Dependabot 的 GitHub Actions 注释现在也列出 `actions/download-artifact@v4`，与 release workflow 的实际 action surface 对齐。
- 新增 `docs/releases/v0.16.238-draft.md`，记录本版从 v0.16.237 GitHub Actions annotation 中提炼出的发布链路加固。

## [0.16.237] - 2026-06-17

### Added
- Candidate 晋级命令计划现在以 `llm_live_preflight` 开头，统一提示先运行 `cliany-site doctor --llm-live --json`，再进入真实 `explore`、package validation 和 online smoke。
- `cliany-site cases --promotion-plan`、`--case-id ... --evidence-bundle --json`、`scripts/validate_cases.py --json/report` 和 `scripts/plan_next_iteration.py` 的 candidate handoff 现在共享包含 live preflight 的四步命令计划。
- Candidate evidence contract 仍只把 `adapter_package`、`metadata_validation` 和 `online_smoke` 作为晋级证据任务；本版不改变任何 candidate 状态，也不伪造 adapter package 证据。
- README、README.zh、cases README、周维护手册、good-first-issues 和官网 quickstart 现在同步说明 candidate promotion command plan 的 live preflight 边界。
- 新增 `docs/releases/v0.16.237-draft.md`，记录本版从 live LLM 502 阻塞中提炼出的 candidate promotion handoff 改进。

## [0.16.236] - 2026-06-17

### Added
- `doctor --llm-live` 现在可选择性发起一次真实 LLM provider 预检，在 `explore` 前暴露上游网关、限流或服务不可用故障。
- `doctor --llm-live --json` 会在 `checks` 中输出 `llm_live`，并在上游不可用时返回 `details.error_code=E_LLM_UNAVAILABLE`、`retryable`、`status_code` 和 `phase=llm_preflight`。
- `doctor` 的 `summary.ready_for_explore` 和 `capabilities.generate_adapters` 现在会把失败的 live preflight 作为 `llm_live` should-fix blocker，但默认 `doctor` 仍只做离线 key/config/CDP/目录检查。
- README、README.zh、官网 quickstart 和官网文档现在说明如何用 `doctor --llm-live` 在长时间 `explore` 前确认 provider 真实可用。
- 新增 `docs/releases/v0.16.236-draft.md`，记录本版从真实 PyPI candidate 探索 502 阻塞中提炼出的 LLM live preflight。

## [0.16.235] - 2026-06-17

### Added
- `explore --json` 现在会把可重试的 LLM 上游网关、限流和服务不可用故障归类为 `E_LLM_UNAVAILABLE`，并在 `details` 中返回 `retryable`、`status_code` 和 `phase`，方便维护自动化决定是否稍后重试或切换 provider。
- LLM 重试日志和最终错误信封现在会清洗上游 HTML 网关页，只保留 `502 Bad Gateway` 等简短原因，避免 JSON 输出和日志被原始 HTML 污染。
- README、README.zh 和官网文档现在说明 `E_LLM_UNAVAILABLE` 是 `explore` 阶段的可重试 LLM 上游故障，不代表 adapter 或 AXTree selector 失效。
- 新增 `docs/releases/v0.16.235-draft.md`，记录本版从真实 PyPI candidate 探索 502 故障中提炼出的错误信封加固。

## [0.16.234] - 2026-06-17

### Added
- `cliany-site cases --promotion-plan` 现在输出 candidate 晋级队列，汇总每个候选案例的首要 evidence task、执行命令、handoff、验收标准和 evidence bundle 命令，维护者不用逐个展开单案例 bundle 也能安排真实案例晋级工作。
- `cliany-site cases --json --promotion-plan` 新增机器可读 `promotion_plan`，包含全局 `primary_next_item`、每个 candidate 的 primary task 摘要，以及所有未完成 promotion task 的 `task_queue`。
- README、README.zh、cases README 和官网 quickstart 现在同步说明 `--promotion-plan` 可作为 candidate 晋级队列入口。
- 新增 `docs/releases/v0.16.234-draft.md`，把本版 patch 聚焦到 candidate promotion queue 的可执行交接。

## [0.16.233] - 2026-06-17

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在在 `Candidate Summary` 中展示 `Primary Evidence Status` 和 `Primary Acceptance Criteria`，维护者创建 candidate issue 前即可看到首要 evidence task 的状态和验收标准。
- Candidate issue artifacts README 的 `Candidate Promotion Evidence Summary` 现在展示 `primary_next_task_acceptance_criteria`，任务表也新增 `Acceptance Criteria` 列，让 issue artifacts 与 cases CLI / case report 使用同一套 proof contract。
- README、README.zh、cases README、good first issues 指南和官网 quickstart 现在同步说明 `--issues-dir` 生成的候选 issue artifacts 会暴露 primary evidence status / acceptance criteria。
- 新增 `docs/releases/v0.16.233-draft.md`，把本版 patch 聚焦到 candidate issue artifacts 的验收标准可见性。

## [0.16.232] - 2026-06-17

### Added
- `cliany-site cases --json` 的 `promotion_evidence_summary.primary_next_task` 现在包含 `acceptance_criteria`，并新增顶层 `primary_next_task_acceptance_criteria`，让自动化不用展开单案例 evidence bundle 就能读取首要 candidate 任务的完成证据要求。
- `cliany-site cases` 的人类输出现在在 Candidate 下一步和单案例 Promotion Tasks 中显示 acceptance，维护者查看 CLI 文本输出时也能直接看到 proof contract。
- `scripts/validate_cases.py` 的文本输出、JSON summary 和 Markdown report 现在同步展示 primary acceptance criteria，并在 Candidate Promotion Evidence Summary 表格中为每个任务列出 Acceptance Criteria。
- `scripts/plan_next_iteration.py` 的 candidate promotion 摘要现在也会在 primary task 中携带 `acceptance_criteria`，让计划产物和 case/report 产物使用同一套 proof contract。
- README、README.zh、cases README 和官网 quickstart 现在同步说明全局 candidate summary 的 `primary_next_task_acceptance_criteria` 字段。
- 新增 `docs/releases/v0.16.232-draft.md`，把本版 patch 聚焦到 candidate promotion summary 的验收标准可见性。

## [0.16.231] - 2026-06-17

### Added
- `cliany-site cases --case-id <id> --issue-template` 现在把首要 evidence task 和每个 promotion task 的 Acceptance Criteria 直接写入 GitHub issue body，让 candidate 晋级 issue 能同时交接命令、当前状态和完成证据要求。
- `scripts/plan_next_iteration.py` 生成的 candidate issue body 现在与 cases CLI 使用同一套验收标准，计划器输出、issue artifacts 和手工 CLI 入口不再需要分别维护 proof 文案。
- `scripts/validate_cases.py --report` 的 Candidate Promotion Tasks / Issue Body Template 现在同步展示 `Acceptance Criteria`，让离线案例报告也能作为可复制的 candidate promotion issue 来源。
- README、README.zh、cases README 和官网 quickstart 现在同步说明 candidate issue template 也包含 evidence task 的验收标准。
- 新增 `docs/releases/v0.16.231-draft.md`，把本版 patch 聚焦到 candidate promotion issue 模板的可验收交接。

## [0.16.230] - 2026-06-17

### Added
- `cliany-site cases --case-id <id> --evidence-bundle --json` 现在输出任务级和顶层 `acceptance_criteria`，并新增 `primary_next_task_acceptance_criteria`，让 candidate 晋级自动化能同时读取下一步命令和完成证据要求。
- `cliany-site cases --case-id <id> --evidence-bundle` 的人类 Markdown 输出新增 Acceptance criteria 小节，并在首要任务摘要中展示 primary acceptance。
- README、README.zh、cases README 和官网 quickstart 现在同步说明 evidence bundle 的验收条件字段。
- 新增 `docs/releases/v0.16.230-draft.md`，把本版 patch 聚焦到 candidate promotion 证据验收合同。

## [0.16.229] - 2026-06-17

### Added
- Q3 路线图和发布节奏文档现在明确采用“每天至少一个可验证版本”的 release train，同时保留每周至少三天提交记录作为健康度门禁。
- 新增 `docs/releases/v0.16.229-draft.md`，把下一版 patch 聚焦到每日发布节奏固化和 candidate 案例晋级路线。

## [0.16.228] - 2026-06-17

### Fixed
- 调整 tag 触发的 release workflow：发布链路现在从严格 release readiness 开始，再执行 build、`twine check`、GitHub Release 和 PyPI 发布，避免历史完整 CI lint/type 债阻塞已经通过发版预检的 distribution 发布。
- 保留 `.github/workflows/ci.yml` 作为 PR/push 的质量信号，本版本不重写现有 CI jobs。

## [0.16.227] - 2026-06-16

### Added
- 新增内置 `cliany-site cases` 命令，可离线列出维护中的真实 demo、candidate 工作流、离线验证命令和 candidate 晋级下一步，并把 `cases/` 案例索引纳入 wheel 资源。
- `cliany-site cases --case-id <id>` 现在可精确展开单个案例的命令、validation 和 promotion 详情，找不到案例时会返回可用 case id 列表。
- `cliany-site cases --case-id <id>` 的人类输出现在展示目标 URL、文档、样例、validation 和 Promotion Tasks，方便贡献者直接复制执行下一步。
- `cliany-site cases --case-id <id> --issue-template` 现在可为 candidate 案例输出可复制的 GitHub issue body，并预填 human / JSON evidence bundle 命令。
- `cliany-site cases --case-id <id> --evidence-bundle` 现在可为 candidate 案例输出结构化本地证据清单，列出待补 promotion tasks、命令和离线验证步骤。
- `cliany-site cases --case-id <id> --evidence-bundle` 的 JSON 现在输出 `status_counts`、`blocked_tasks`、`complete_tasks` 和 `incomplete_tasks`，让维护工具能直接区分待办、阻塞与已完成晋级任务。
- `cliany-site cases --case-id <id> --evidence-bundle` 的 JSON 现在输出 `primary_pending_task`、`primary_blocked_task` 和 `primary_incomplete_task`，让 issue bot 与计划器能直接展示首要跟进项。
- `scripts/validate_cases.py --report` 现在输出 `Candidate Evidence Bundle Commands` 小节，直接链接每个 candidate 的 evidence bundle CLI 命令。
- `scripts/validate_cases.py --report` 的 `Issue Body Template` 现在包含 `Reproduction Context` 和 `Evidence Bundle` 小节，让 case report 复制出的 issue body 与 CLI/计划器模板一致。
- `scripts/plan_next_iteration.py --issues-dir` 生成的 candidate issue artifacts 现在在 `candidate_promotions`、`issue-metadata.json`、issue metadata summary 和 artifacts `README.md` 中输出 `evidence_bundle_command` / `evidence_bundle_json_command`，让维护者能直接复制案例证据包命令。
- `scripts/plan_next_iteration.py` 的 candidate promotion JSON 和 issue artifacts 现在输出 `promotion_evidence_primary_task`，并在 artifacts `README.md` 的 `Candidate Summary` 中展示首要 evidence task。
- `scripts/plan_next_iteration.py` 的 candidate promotion JSON、`issue-metadata.json` 和 artifacts `README.md` 现在也输出 `evidence_bundle_primary_next_task`，让 evidence bundle 的首要下一步字段贯穿周计划与 issue artifacts。
- `scripts/plan_next_iteration.py` 的默认文本输出和 Markdown report 现在也展示 `evidence_bundle_primary_next_task`，维护者不用生成 artifacts 就能看到 evidence bundle 首要下一步。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 现在同步说明 `promotion_evidence_primary_task` 与 `Primary Evidence Task`，让周维护手册和 candidate issue artifacts 字段保持一致。
- `scripts/plan_next_iteration.py` 生成的 candidate issue body 现在也包含 `Evidence Bundle` 小节，与 `cliany-site cases --case-id <id> --issue-template` 保持一致。
- `cliany-site cases --case-id <id> --issue-template` 和 `scripts/plan_next_iteration.py` 生成的 candidate issue body 现在会把已有 evidence 的 `complete` promotion task 输出为 `- [x]`，避免贡献者重复处理已完成证据项。
- `cliany-site cases --case-id <id> --issue-template` 和 `scripts/plan_next_iteration.py` 生成的 candidate issue body 现在包含 `Primary Evidence Task` 小节，直接指出当前首要待补证据任务。
- `cliany-site cases --case-id <id> --issue-template --json` 现在输出 `issue_template_primary_task`，让自动化不用解析 Markdown 就能读取首要待补证据任务。
- `cliany-site cases --json` 的 `promotion_evidence_summary` 现在输出 `primary_task_detail`，让维护脚本能直接读取首要 candidate 晋级任务的 case、task、status、evidence 和 next action。
- `scripts/validate_cases.py` 的 `promotion_evidence_summary` 现在也输出 `primary_task_detail`，并在 Markdown report 中展示同源字段，保持 case catalog 两个入口一致。
- `scripts/plan_next_iteration.py` 在回退构造 `case_promotion_evidence_summary` 时也保留 `primary_task_detail`，让周计划输入来自 validate report 或内存 case 对象时字段一致。
- `cliany-site cases --json`、`scripts/validate_cases.py` 和 `scripts/plan_next_iteration.py` 的 promotion evidence summary 现在输出 `primary_next_task`，让全局 candidate summary 与单案例 evidence bundle 使用同一首要下一步字段名。
- `scripts/plan_next_iteration.py` 的顶层 JSON、默认文本输出和 Markdown report 现在直接展示 `case_promotion_evidence_primary_next_task` 与 `case_promotion_evidence_primary_next_action`，让自动化不用展开 summary 也能定位首要 candidate 任务。
- `scripts/plan_next_iteration.py` 的顶层 JSON、默认文本输出和 Markdown report 现在也展示 `case_promotion_evidence_summary_sha256` 与 `case_promotion_command_plan_summary_sha256`，让周计划消费者不用生成 artifacts 也能检测 candidate evidence / command plan 摘要漂移。
- `scripts/plan_next_iteration.py` 现在输出 `plan_report_command`，把生成 `/tmp/cliany-next-iteration.md` 的 Markdown 周计划命令与 `issue_artifacts_command` 一样结构化交给维护工具。
- Candidate issue artifacts 的 `validation_commands` 现在包含 `plan_report_command`，让 artifacts README 和 manifest 都能直接复现 Markdown 周计划报告。
- Candidate issue artifacts 的 `artifact-manifest.json` 现在带顶层 `plan_report_command`，`artifact_bundle_summary` 也输出 `plan_report_command_sha256`，让工具不用展开 validation commands 就能复现并检测周计划报告命令漂移。
- Candidate issue artifacts 的 `publication-handoff.json` 和 README `Publication Handoff` 现在也展示 `plan_report_command`，让处理发布门禁的维护工具能直接跳回同一份 Markdown 周计划报告。
- Candidate issue artifacts 的 `release-draft-handoff.json` 和 README `Release Draft Handoff` 现在也展示 `plan_report_command`，让处理草案门禁的维护工具能直接复现同一份 Markdown 周计划报告。
- Candidate issue artifacts 的 `publication-handoff.json`、`release-draft-handoff.json` 和对应 README handoff 小节现在也展示 `issue_artifacts_command`，让只读取 handoff 的维护工具能直接重新生成整包候选任务 artifacts。
- Candidate issue artifacts 的 `publication-handoff.json`、`release-draft-handoff.json` 和对应 README handoff 小节现在也展示 `plan_report_command_sha256` 与 `issue_artifacts_command_sha256`，让只读取 handoff 的维护工具能检测复现命令漂移。
- `cliany-site cases --case-id <id> --evidence-bundle --json`、candidate issue body 和 candidate issue artifacts 的 `issue-metadata.json` 现在输出 `promotion_command_plan`，把 adapter package、metadata validation 和 online smoke 映射到可执行命令。
- `scripts/validate_cases.py --report` 的 `Candidate Promotion Tasks` / `Issue Body Template` 现在也输出 `Promotion Command Plan`，让 case catalog report、cases CLI 和 candidate issue artifacts 使用同一组三步执行命令。
- `scripts/validate_cases.py --json` 的 candidate case 条目现在输出 `promotion_command_plan`、`promotion_command_plan_count` 和 `promotion_command_plan_missing_tasks`，让自动化不用解析 Markdown report 就能读取三步晋级命令。
- `scripts/validate_cases.py --json` 和 Markdown report 现在输出顶层 `promotion_command_plan_summary` / `Candidate Promotion Command Plan Summary`，汇总 candidate 晋级命令总数、缺失命令数、缺失 case/task 和 `all_declared` 状态。
- `scripts/plan_next_iteration.py` 现在把 `promotion_command_plan_summary` 透传为 `case_promotion_command_plan_summary`，并写入默认文本输出、Markdown report、candidate issue artifacts manifest 和 `artifact_bundle_summary` compact 字段。
- `scripts/release_readiness.py` 的默认文本输出和 Markdown report 现在也展示 candidate promotion command plan summary，让发版预检 artifact 直接显示 candidate 晋级命令是否完整。
- `scripts/release_readiness.py` 现在把 publication audit 和 `publication_publish_commands` 写入 JSON、默认文本输出和 Markdown report，维护者查看发版预检 artifact 时可直接复制发布可见性复核命令。
- `scripts/release_readiness.py` 现在也把 `publication_tag_publish_decision` 提升到顶层 JSON、默认文本输出和 Markdown report，维护者无需展开 publication audit 就能看到 tag 是否可推和人工决策动作。
- `scripts/release_readiness.py` 现在也把 `publication_next_actions` 和 `publication_next_action_count` 提升到顶层 JSON、默认文本输出和 Markdown report，让发版预检 artifact 直接列出发布可见性待办。
- `scripts/release_readiness.py` 现在也把 `publication_ref_context` 提升到顶层 JSON、默认文本输出和 Markdown report，让维护者直接看到发布待办对应的 branch、upstream、HEAD、tag 和 ahead/behind refs。
- `scripts/release_readiness.py` 现在也把 `publication_worktree_clean`、`publication_worktree_status_count` 和 `publication_worktree_status` 提升到顶层 JSON、默认文本输出和 Markdown report，让维护者在发版预检 artifact 里直接判断本地改动是否阻塞发布命令。
- `scripts/release_readiness.py` 现在也输出 `publication_primary_next_action` 和 `publication_primary_publish_command`，让只读发版预检摘要的工具可以直接展示首要发布待办与首条发布命令。
- `scripts/release_readiness.py` 现在也输出 `publication_next_actions_sha256` 和 `publication_publish_commands_sha256`，让发版预检 artifact 能直接检测 publication action/command 列表是否漂移。
- `scripts/release_readiness.py` 现在输出顶层 `publication_summary`，把发布状态、worktree、branch/tag、ahead/behind、tag 决策、首要动作和首条发布命令压缩成一个机器可读摘要。
- `scripts/release_readiness.py` 现在输出 `publication_summary_sha256`，让只读发版预检 artifact 的工具能检测 publication summary 是否漂移。
- `scripts/release_readiness.py` 现在也输出 `publication_summary_primary_next_action` 和 `publication_summary_primary_publish_command` 顶层别名，让只读摘要字段族的工具不用展开 nested summary。
- `scripts/release_readiness.py` 的 `publication_tag_publish_decision` 和 `publication_summary` 现在也附带目标 release tag、目标 tag 状态、创建命令和命令 hash，让发版预检入口与周计划入口给出同一套 target tag 交接。
- `scripts/release_readiness.py` 的 `publication_tag_publish_decision` 和 `publication_summary` 现在也输出 `target_tag_release_gate_*` 字段；当提交日、草案或其他 readiness blocker 未清除时，目标 tag 会明确标记为 `blocked_by_readiness`，避免维护者把 `git tag v...` 命令误当成立刻可执行。
- `scripts/release_readiness.py --json` 的顶层 `next_actions` 现在会在 publication 未公开时先展示 `publication_summary.primary_next_action`，再展示 cadence/readiness 修复动作，避免发版预检只提示提交日而漏掉发布同步。
- `scripts/release_readiness.py --json` 的顶层 `next_actions` 现在也会在 publication 首项后展示目标 release tag 动作，让只读发版预检的工具不用展开 `publication_tag_publish_decision` 就能看到 `git tag v...` / `git push origin v...` 链路。
- README / README.zh 和周维护手册现在说明自动化可比对 `target_tag_commands_sha256`，并优先读取 `publication_summary.target_tag*` 字段确认目标 release tag 命令是否漂移。
- `scripts/release_readiness.py --json` 现在输出 `publication_blockers`、`publication_primary_blocker` 和 `publication_blockers_sha256`，让发版预检 artifact 顶层直接展示发布可见性阻塞原因。
- `scripts/release_readiness.py --json` 顶层现在也展示 `next_action_count`、`primary_next_action` 和 `next_actions_sha256`，让维护工具不用展开 `next_actions` 就能显示首要发版预检动作并检测漂移。
- `scripts/check_release_cadence.py` 的 JSON `next_actions` 现在保持纯文本，并输出 `primary_next_action` 与 `next_actions_sha256`，让 cadence audit 与 publication audit 的 action contract 保持一致。
- `scripts/check_release_publication.py` 的 JSON `next_actions` 现在保持纯文本，不再混入 Markdown bullet，文本和 Markdown report 仍由渲染层输出列表符号。
- `scripts/check_release_publication.py` 现在也输出 `primary_next_action`、`next_actions_sha256`、`primary_publish_command` 和 `publish_commands_sha256`，让 publication audit 自身能直接展示首项并检测 action/command 列表漂移。
- `scripts/check_release_publication.py --publish-script` 生成的可审阅发布脚本现在在注释头中展示 next/publish 的 count、SHA-256 和 primary 字段，维护者执行前即可确认脚本对应的发布动作集。
- `scripts/check_release_publication.py --publish-script` 生成的可审阅发布脚本现在执行前会重新运行 publication audit，并在 next/publish hash 已漂移时退出，避免继续执行过期发布命令。
- `scripts/plan_next_iteration.py` 现在也在顶层 JSON、默认文本输出和 Markdown report 展示 `next_action_count`、`primary_next_action` 与 `next_actions_sha256`，让周计划自身和 cadence/publication action contract 对齐。
- `scripts/plan_next_iteration.py --issues-dir` 的 `artifact-manifest.json` 顶层现在也展示 `next_action_count`、`primary_next_action` 与 `next_actions_sha256`，让只读 manifest 的维护工具无需重算周计划 action 摘要。
- `scripts/plan_next_iteration.py` 现在把 publication next actions / publish commands 的 primary 和 SHA-256 摘要提升到顶层 JSON、默认文本输出和 Markdown report。
- `scripts/plan_next_iteration.py` 现在也透传 `publication_blockers`、`publication_primary_blocker` 和 `publication_blockers_sha256` 到顶层 JSON、默认文本输出、Markdown report 与 candidate issue artifacts，帮助维护者先看发布阻塞原因再执行同步命令。
- `scripts/plan_next_iteration.py` 的 `publication_tag_publish_decision` 现在附带目标 release tag 建议、`git tag v...` / `git push origin v...` 命令和命令 hash，让维护者在 latest tag 不指向 HEAD 时也能直接看到应该创建哪个新 tag。
- `scripts/plan_next_iteration.py` 现在也把 `target_tag_release_gate_*` 字段透传到周计划、candidate issue gate evidence 和 artifacts compact summary；只读周计划/artifacts 的维护工具可以直接识别目标 tag 是否仍 `blocked_by_readiness`。
- `scripts/plan_next_iteration.py` 的顶层 `next_actions` 现在会在 tag mismatch 时用目标 release tag 动作替换旧 tag 推送提示，避免维护者误把不在 HEAD 的旧 tag 当作下一步发布对象。
- `scripts/plan_next_iteration.py` 现在也透传 `standard_release_flow`、`standard_release_flow_status`、`standard_release_flow_primary_next_action`、`standard_release_flow_command_count`、`standard_release_flow_commands_sha256` 和 `standard_release_flow_sha256`，并在标准发版流程阻塞时优先把 `standard_release_flow.primary_next_action` 放到顶层 `next_actions[0]`。
- Candidate issue artifacts 的 `artifact-manifest.json`、`publication-handoff.json`、artifacts `README.md` 和 `artifact_bundle_summary` 现在也展示 standard release flow 摘要，让只读候选任务交接包的维护工具不会漏掉提交后的标准发版 gate。
- Candidate issue artifacts 的 `artifact_bundle_summary` 现在输出 `publication_target_tag*` 摘要字段，维护工具只读整包摘要也能展示目标 release tag、创建命令和命令 hash。
- `candidate_issue_gate.evidence` 现在也输出 `publication_target_tag*` 字段，维护工具只读 gate evidence 就能看到目标 release tag 交接状态。
- `scripts/release_readiness.py` 现在输出 `standard_release_flow`、`standard_release_flow_status`、`standard_release_flow_primary_next_action` 和命令 hash，让提交后的标准发版流程可被 JSON、文本和 Markdown report 直接审阅。
- README / README.zh 的路线图入口现在说明维护者可读取 `primary_next_action`，自动化可比对 `next_actions_sha256`、`publication_next_actions_sha256` 和 `publication_publish_commands_sha256` 检测发布动作漂移。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 现在说明维护者如何先读 `publication_summary`、`publication_summary_sha256`、首要发布动作和首条发布命令，再决定是否展开发布详情。
- `artifact_bundle_summary` 现在输出 `case_promotion_evidence_primary_detail_sha256`，让只读整包摘要的工具能检测首要 candidate 晋级任务对象是否漂移。
- `artifact_bundle_summary` 现在也输出 `case_promotion_evidence_primary_next_task_sha256`，让只读整包摘要的工具能单独检测 `primary_next_task` 漂移。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 现在同步说明 `case_promotion_evidence_primary_next_task_sha256`，让周维护手册覆盖最新 artifact bundle summary 字段。
- `cliany-site cases --status candidate` 的人类输出现在会在 `Candidate 下一步` 中展示首要任务状态和当前 evidence，并从 `primary_next_task` 读取首要任务，维护者不用切到 JSON 也能判断证据是否已附加。
- `scripts/validate_cases.py` 的默认文本输出现在展示 `promotion_evidence_primary_next_task`，让快速校验入口也使用同一首要下一步字段名。
- `scripts/validate_cases.py` 的默认文本输出现在展示 `promotion_evidence_primary` 和 `promotion_evidence_evidence`，让维护者不用打开 Markdown report 也能看到首要 candidate 晋级任务状态与证据。
- `scripts/release_readiness.py --report` 现在输出 `Candidate Primary Next Task` 小节，直接展示 `promotion_evidence_summary.primary_next_task` 的 case、task、status、evidence 和 next action。
- `scripts/release_readiness.py --report --packages-dir ...` 现在输出 `Case Package Checks` 小节，直接列出每个 case adapter 包的状态、路径、问题和修复动作。
- `scripts/release_readiness.py --json --packages-dir ...` 的 `next_actions` 现在会透传失败 case package 的修复动作，让自动化不用解析 Markdown 也能提示缺失或无效包的下一步。
- `scripts/release_readiness.py --json` 的 `package_gate` 现在输出 `failed_count`、`missing_count`、`invalid_count`、`repair_action_count` 和 `primary_repair_action`，让维护工具不用遍历 case 列表也能判断包资产修复规模。
- `scripts/release_readiness.py` 的默认文本输出现在展示 `package_gate_summary` 和 `package_gate_primary_repair_action`，维护者不生成 JSON/Markdown 也能看到包资产修复规模和首要动作。
- `scripts/release_readiness.py --require-packages` 现在会在已检查包但存在失败项时让 `package_gate.ok=false`，并输出 `case package validation failed` blocker，避免正式发版预检把无效包只归到通用 case catalog 失败。
- `scripts/release_readiness.py` 的 package repair `next_actions` 现在会把多个 case 共用的修复动作合并为一条 `Package checks` 动作，避免空 packages 目录下重复输出同一条 rerun 命令。
- `scripts/plan_next_iteration.py` 现在支持 `--packages-dir` 和 `--require-packages`，会把包门禁参数透传给 release readiness，并写入 validation commands 与 issue artifacts 复现命令。
- `scripts/validate_cases.py --include-candidate-packages` 现在可显式校验 candidate adapter 包，按 `adapter_domain-<version>.cliany-adapter.tar.gz` 约定定位包文件，方便给 `pypi-project-search` 等候选案例补齐 adapter package evidence。
- `scripts/plan_next_iteration.py --packages-dir ... --json` 的 validation commands 现在会包含 `python scripts/validate_cases.py --packages-dir ... --include-candidate-packages --strict`，让周初计划直接给出 candidate 包 evidence 的复现命令。
- Candidate 案例的 `metadata_validation` 和 `promotion_evidence.metadata_validation.next_action` 现在统一使用 `--include-candidate-packages`，避免维护者照着 evidence 清单运行默认 active 包校验而漏掉候选包。
- `cliany-site cases --case-id <id> --evidence-bundle --json` 现在输出 `candidate_package_validation_command`，人类 evidence bundle 也展示 `Candidate package validation` 小节，让候选包 evidence 命令无需从自然语言里解析。
- `scripts/plan_next_iteration.py` 的 `candidate_promotions`、`issue-metadata.json` 和 artifacts `README.md` 现在也输出 `candidate_package_validation_command`，让候选包 evidence 命令贯穿周计划和 issue artifacts。
- Candidate issue body 和 `cliany-site cases --case-id <id> --issue-template` 现在在 `Validation Evidence` 中直接展示 candidate package validation command，减少创建 issue 后的命令查找。
- `cliany-site cases --case-id <id> --evidence-bundle --json` 现在把每个 promotion task 和对应可执行命令绑定到 `tasks` / `task_handoffs`，并输出 `primary_next_task_command*` 与 `primary_next_task_handoff`，让贡献者和自动化不用重新拼接 evidence、command plan 与下一步说明。
- Candidate issue artifacts 的 review checklist 现在要求核对 `issue-metadata.json` 中的 `candidate_package_validation_command`，避免创建 issue 前漏审候选包验证命令。
- README / README.zh 现在用 `promotion_evidence_summary.primary_next_task` 指引自动化读取首要 candidate 任务，避免新用户继续参考旧的 `primary_task_detail` 字段。
- `cliany-site cases --case-id <id> --evidence-bundle --json` 现在输出 `primary_next_task`，并在人类证据包里展示 `Primary next task`，让脚本和维护者无需重建 pending/blocked/incomplete 优先级规则。
- [cases/README.md](cases/README.md) 现在说明 `Candidate Promotion Evidence Summary` 会展示 `primary_next_task`，帮助贡献者直接定位首要 candidate case/task/status/evidence。
- [docs/good-first-issues.md](docs/good-first-issues.md) 和 [docs/contributor-starter.md](docs/contributor-starter.md) 现在要求 candidate promotion issue 引用 evidence bundle 的 `primary_next_task`，让 good-first issue 指向首要 case/task/status/evidence。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 现在同步说明 candidate issue artifacts 的 evidence bundle 字段和 `Candidate Summary` 复制入口。
- [docs/good-first-issues.md](docs/good-first-issues.md) 和 [docs/contributor-starter.md](docs/contributor-starter.md) 现在明确 candidate promotion 的 Issue Body Template 自带 `Reproduction Context` 与 `Evidence Bundle`。
- README / README.zh 现在展示 `cliany-site cases --case-id pypi-project-search --evidence-bundle --json`，让维护者知道证据包也可机器读取。
- 官网首页的贡献者路径现在展示 candidate evidence bundle JSON 命令，方便首次成功后的用户提交可复现案例证据。
- [docs/good-first-issues.md](docs/good-first-issues.md) 现在要求 candidate promotion issue 附上 evidence bundle JSON，保持 issue、case report 和 `promotion_evidence` 同步。
- [cases/README.md](cases/README.md) 现在明确 candidate promotion issue 应复制 `--issue-template`，并附上 `--evidence-bundle --json` 的机器可读证据包。
- 新增 `docs/releases/v0.16.227-draft.md`，把下一版 patch release 聚焦到 `v0.16.226` 本地 release 的发布可见性交接。
- `v0.16.227` 草案明确记录 `publication_visibility`、`candidate_issue_gate`、`publication-handoff.json` 和 `release-draft-handoff.json` 在本地 release 未公开时的审阅路径。

### Fixed
- `scripts/release_readiness.py --json` 顶层 `next_actions` 现在保持纯文本，不再混入 Markdown bullet 前缀；默认文本输出和 Markdown report 仍由渲染层添加列表符号。
- `plan_next_iteration.py` 现在把 `tag_points_at_head=false` 的发布审计动作透传到顶层 `next_actions` 和 `publication_visibility.summary`，避免把 tag mismatch 误写成“直接推 tag”。
- `check_release_publication.py --publish-script` 现在在最新 tag 不指向 HEAD 时写入审阅注释，明确脚本不会自动推送旧 tag。
- `check_release_publication.py --json` / `--report` 现在输出 `tag_publish_decision`，用稳定字段标记 `manual_decision_required`、`ready_to_push`、`published` 等 tag 发布状态。
- `plan_next_iteration.py` 现在把 `tag_publish_decision` 透传为 `publication_tag_publish_decision`，并写入 Markdown report、`artifact-manifest.json`、`publication-handoff.json` 和 artifacts `README.md`。
- `artifact_bundle_summary` 现在输出 `publication_tag_publish_decision_*` 摘要字段，让只读整包摘要的维护工具也能判断 tag 是否可推，并检测该对象字段漂移。
- `candidate_issue_gate.evidence` 现在包含 tag 发布决策状态、是否可推和 required action，artifacts `README.md` 的 `Publication Handoff` 也会展示同一组 gate evidence。
- `candidate_issue_gate` 现在直接输出 `primary_reason_code`、`primary_reason_description` 和 `primary_required_action`，artifacts `README.md` 的 `Publication Handoff` 也会展示这组首要 gate 字段。
- `publication-handoff.json` 现在把 `candidate_issue_gate_primary_reason_code`、`candidate_issue_gate_primary_reason_description` 和 `candidate_issue_gate_primary_required_action` 提升为顶层别名，方便只读 handoff 的工具展示首要 gate 状态。
- `artifact_bundle_summary` 现在输出 `publication_handoff_candidate_issue_gate_primary_*` 字段，让只读整包摘要的工具也能确认 publication handoff 顶层 gate primary 别名。
- `plan_next_iteration.py` 现在输出结构化 `commit_cadence`，并在 Markdown report、`artifact-manifest.json` 和 `artifact_bundle_summary` 中展示提交天数状态、缺口和摘要 hash。
- `publication-handoff.json` 和 artifacts `README.md` 的 `Publication Handoff` 现在展示 `commit_cadence` 状态、缺口和首要 cadence next action，帮助维护者先看到本周提交天数阻塞。
- Candidate issue artifacts `README.md` 现在新增 `Commit Cadence` 小节，集中展示本周提交天数、缺口、已有提交日期和 cadence next actions。
- `artifact_bundle_summary` 现在输出 `commit_cadence_next_action_count` 和 `commit_cadence_primary_next_action`，让只读整包摘要的工具能直接展示提交节奏下一步。

## [0.16.226] - 2026-06-15

### Added
- 新增 `docs/releases/v0.16.226-draft.md`，把下一版 patch release 聚焦到 `v0.16.225` 本地 release 的发布可见性交接。
- `v0.16.226` 草案明确记录 `publication_visibility`、`candidate_issue_gate`、`publication-handoff.json` 和 `release-draft-handoff.json` 在本地 release 未公开时的审阅路径。

## [0.16.225] - 2026-06-15

### Added
- 新增 `docs/releases/v0.16.225-draft.md`，把下一版 patch release 聚焦到发布可见性优先的维护路径。
- `v0.16.225` 草案明确记录 `publication_visibility`、`candidate_issue_gate`、`publication-handoff.json` 和 `release-draft-handoff.json` 的交接关系，让下一轮计划不再被缺失草案阻塞。

### Fixed
- `plan_next_iteration.py` 现在只在 release draft 真的存在校验问题时提示 `Draft and verify`，避免草案已通过后仍重复提示已完成动作。

## [0.16.224] - 2026-06-15

### Added
- `artifact_bundle_summary` 现在输出 `case_promotion_evidence_primary_case_id`、`case_promotion_evidence_primary_task` 和 `case_promotion_evidence_primary_status`，让只读整包摘要的工具能直接定位首要 candidate 晋级任务。
- `artifact_bundle_summary` 现在输出 `case_promotion_evidence_primary_evidence_sha256`，让维护工具能检测首要任务当前 evidence 是否漂移。
- 新增 `docs/releases/v0.16.224-draft.md`，把下一版 patch release 聚焦到 candidate promotion primary task 的 bundle-level 可定位性。

## [0.16.223] - 2026-06-15

### Added
- `artifact_bundle_summary` 现在输出 `case_promotion_evidence_summary_*` key count/hash/preview/tail/boundary 字段，让只读整包摘要的工具能检测 candidate 晋级证据摘要字段漂移。
- `artifact_bundle_summary` 现在输出 `case_promotion_evidence_candidate_count`、`case_promotion_evidence_task_count`、pending/blocked/complete 计数和 `case_promotion_evidence_primary_next_action`，方便维护工具不展开完整 manifest 也能展示首要晋级动作。
- 新增 `docs/releases/v0.16.223-draft.md`，把下一版 patch release 聚焦到 candidate promotion evidence summary 的 bundle-level 可审计性。

## [0.16.222] - 2026-06-15

### Added
- Candidate issue artifacts 的 `artifact-manifest.json` 现在带顶层 `case_promotion_evidence_summary`，让只读 manifest 的维护工具能直接看到 candidate 晋级证据摘要。
- Candidate issue artifacts `README.md` 现在展示 `Candidate Promotion Evidence Summary` 小节，把 pending/blocked/complete 数量、primary next action 和任务明细放进人工审阅入口。
- 新增 `docs/releases/v0.16.222-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的证据摘要可见性。

## [0.16.221] - 2026-06-13

### Added
- `scripts/plan_next_iteration.py` 的 JSON、默认文本输出和 Markdown report 现在输出 `case_promotion_evidence_summary`，让周初计划直接展示 candidate 晋级任务的状态汇总。
- Next iteration Markdown report 新增 `Candidate Promotion Evidence Summary` 小节，展示 candidate/task 数量、pending/blocked/complete 数量、primary next action 和任务明细。
- 新增 `docs/releases/v0.16.221-draft.md`，把下一版 patch release 聚焦到周初计划中的 candidate promotion evidence summary。

## [0.16.220] - 2026-06-13

### Added
- `scripts/validate_cases.py` 的 JSON 现在输出 `promotion_evidence_summary`，汇总 candidate 数量、任务数量、pending/blocked/complete 状态计数和 primary next action。
- `scripts/validate_cases.py --report` 新增 `Candidate Promotion Evidence Summary` 小节，让维护者不用展开每个 candidate 也能看到下一项该推进的晋级证据。
- `scripts/validate_cases.py` 默认文本输出现在展示 `promotion_evidence_pending`、`promotion_evidence_blocked`、`promotion_evidence_complete` 和 `promotion_evidence_next`。
- 新增 `docs/releases/v0.16.220-draft.md`，把下一版 patch release 聚焦到 candidate promotion evidence summary。

## [0.16.219] - 2026-06-13

### Added
- Candidate 案例现在声明 `promotion_evidence`，为 `adapter_package`、`metadata_validation` 和 `online_smoke` 记录 `pending` / `complete` / `blocked` 状态、证据和下一步动作。
- `scripts/validate_cases.py` 现在校验 candidate `promotion_evidence`，并在文本、JSON 和 Markdown report 中输出结构化晋级证据。
- `scripts/plan_next_iteration.py` 现在把 `promotion_evidence` 透传到 candidate promotion JSON、issue body、`issue-metadata.json` 和 issue metadata summary，方便维护者按证据状态拆分任务。
- 新增 `docs/releases/v0.16.219-draft.md`，把下一版 patch release 聚焦到 candidate promotion evidence 的可交接性。

## [0.16.218] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_next_action_preview_count`、`publication_next_action_preview` 和 `publication_next_action_preview_sha256`，让只读取整包摘要的维护工具能检查 publication next actions 前窗口。
- `artifact_bundle_summary` 现在输出 `publication_next_action_tail_count`、`publication_next_action_tail` 和 `publication_next_action_tail_sha256`，让 publication next actions 尾部窗口也可审计。
- 新增 `docs/releases/v0.16.218-draft.md`，把下一版 patch release 聚焦到 publication next action preview/tail 可见性。

## [0.16.217] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_handoff_key_preview_count`、`publication_handoff_key_preview` 和 `publication_handoff_key_preview_sha256`，让只读取整包摘要的维护工具能检查 `publication-handoff.json` 字段清单前窗口。
- `artifact_bundle_summary` 现在输出 `publication_handoff_key_tail_count`、`publication_handoff_key_tail` 和 `publication_handoff_key_tail_sha256`，让 publication handoff 字段清单尾部窗口也可审计。
- 新增 `docs/releases/v0.16.217-draft.md`，把下一版 patch release 聚焦到 publication handoff key preview/tail 可见性。

## [0.16.216] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_ref_context_key_preview_count`、`publication_ref_context_key_preview` 和 `publication_ref_context_key_preview_sha256`，让只读取整包摘要的维护工具能检查 publication ref context 字段清单前窗口。
- `artifact_bundle_summary` 现在输出 `publication_ref_context_key_tail_count`、`publication_ref_context_key_tail` 和 `publication_ref_context_key_tail_sha256`，让 publication ref context 字段清单尾部窗口也可审计。
- 新增 `docs/releases/v0.16.216-draft.md`，把下一版 patch release 聚焦到 publication ref context key preview/tail 可见性。

## [0.16.215] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_key_preview_count`、`release_draft_handoff_key_preview` 和 `release_draft_handoff_key_preview_sha256`，让只读取整包摘要的维护工具能检查 `release-draft-handoff.json` 字段清单前窗口。
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_key_tail_count`、`release_draft_handoff_key_tail` 和 `release_draft_handoff_key_tail_sha256`，让 release draft handoff 字段清单尾部窗口也可审计。
- 新增 `docs/releases/v0.16.215-draft.md`，把下一版 patch release 聚焦到 release draft handoff key preview/tail 可见性。

## [0.16.214] - 2026-06-13

### Added
- `release_readiness.py` 的 JSON 和 Markdown report 现在输出 `release_mode` 与 `release_tag`，让维护者和自动化能区分普通 target-version readiness 与 tagged release preflight。
- `Weekly Review` 的发布已验证 tag 文案现在只在显式 `--release-tag` 模式通过时出现；普通 `--target-version` readiness 继续提示准备打 tag。
- 新增 `docs/releases/v0.16.214-draft.md`，把下一版 patch release 聚焦到 release readiness mode 可见性。

## [0.16.213] - 2026-06-13

### Added
- `release_readiness.py --report` 的 `Weekly Review` 在 tagged release preflight 通过且 tag 已指向 HEAD 时，现在把下一步显示为发布已验证 tag。
- 新增测试覆盖 tagged release mode 的 Weekly Review 文案，避免 tag 已存在时继续提示维护者“Ready to tag”。
- 新增 `docs/releases/v0.16.213-draft.md`，把下一版 patch release 聚焦到 tagged release preflight 的下一步可读性。

## [0.16.212] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_issue_gate_evidence_first_key`、`candidate_issue_gate_evidence_last_key` 和 `candidate_issue_gate_evidence_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue gate evidence key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 gate evidence key boundary，并继续展示 evidence key count 和 evidence hash。
- 新增 `docs/releases/v0.16.212-draft.md`，把下一版 patch release 聚焦到 candidate issue gate evidence key boundary 可见性。

## [0.16.211] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `create_issues_safety_contract_key_preview_count`、`create_issues_safety_contract_key_preview` 和 `create_issues_safety_contract_key_preview_sha256`，让只读取整包摘要的维护工具能检查 create issues safety contract key 前窗口。
- `artifact_bundle_summary` 现在输出 `create_issues_safety_contract_key_tail_count`、`create_issues_safety_contract_key_tail` 和 `create_issues_safety_contract_key_tail_sha256`，让 create issues safety contract keys 的尾部窗口与 review checklist、validation commands 和 blockers 的可见性保持一致。
- 新增 `docs/releases/v0.16.211-draft.md`，把下一版 patch release 聚焦到 create issues safety contract key preview/tail 可见性。

## [0.16.210] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_checklist_preview_count`、`review_checklist_preview` 和 `review_checklist_preview_sha256`，让只读取整包摘要的维护工具能检查 review checklist 前窗口。
- `artifact_bundle_summary` 现在输出 `review_checklist_tail_count`、`review_checklist_tail` 和 `review_checklist_tail_sha256`，让 review checklist 的尾部窗口与 validation commands、blockers 和 next actions 的可见性保持一致。
- 新增 `docs/releases/v0.16.210-draft.md`，把下一版 patch release 聚焦到 review checklist preview/tail 可见性。

## [0.16.209] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `validation_command_preview_count`、`validation_command_preview` 和 `validation_command_preview_sha256`，让只读取整包摘要的维护工具能检查 validation commands 前窗口。
- `artifact_bundle_summary` 现在输出 `validation_command_tail_count`、`validation_command_tail` 和 `validation_command_tail_sha256`，让 validation commands 的尾部窗口与 blockers、next actions 和 release draft windows 的可见性保持一致。
- 新增 `docs/releases/v0.16.209-draft.md`，把下一版 patch release 聚焦到 validation command preview/tail 可见性。

## [0.16.208] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_required_action_preview_count`、`release_draft_required_action_preview`、`release_draft_required_action_preview_sha256`、`release_draft_required_action_tail_count`、`release_draft_required_action_tail` 和 `release_draft_required_action_tail_sha256`，让只读取整包摘要的维护工具能检查 release draft required actions 前后窗口。
- `artifact_bundle_summary` 现在输出 `release_draft_issue_preview_count`、`release_draft_issue_preview`、`release_draft_issue_preview_sha256`、`release_draft_issue_tail_count`、`release_draft_issue_tail` 和 `release_draft_issue_tail_sha256`，让 release draft issues 的窗口摘要与 blockers/next actions 的可见性保持一致。
- 新增 `docs/releases/v0.16.208-draft.md`，把下一版 patch release 聚焦到 release draft issue/action preview 与 tail 可见性。

## [0.16.207] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_next_action_first_item`、`publication_next_action_last_item` 和 `publication_next_action_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication next actions 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication next action first/last item 与 boundary hash，并继续展示 next action count、完整 hash 和 primary action。
- 新增 `docs/releases/v0.16.207-draft.md`，把下一版 patch release 聚焦到 publication next action boundary 可见性。

## [0.16.206] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_handoff_first_key`、`publication_handoff_last_key` 和 `publication_handoff_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication handoff key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication handoff first/last key 与 boundary hash，并继续展示 handoff key count、schema version 和完整 hash。
- 新增 `docs/releases/v0.16.206-draft.md`，把下一版 patch release 聚焦到 publication handoff boundary 可见性。

## [0.16.205] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_first_key`、`release_draft_handoff_last_key` 和 `release_draft_handoff_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 release draft handoff key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft handoff first/last key 与 boundary hash，并继续展示 handoff key count、schema version、primary issue/action 和完整 hash。
- 新增 `docs/releases/v0.16.205-draft.md`，把下一版 patch release 聚焦到 release draft handoff boundary 可见性。

## [0.16.204] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_worktree_status_first_item`、`publication_worktree_status_last_item` 和 `publication_worktree_status_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication worktree status 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication worktree status first/last item 与 boundary hash，并继续展示 status count 和完整 hash。
- 新增 `docs/releases/v0.16.204-draft.md`，把下一版 patch release 聚焦到 publication worktree status boundary 可见性。

## [0.16.203] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_publish_first_command`、`publication_publish_last_command` 和 `publication_publish_command_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication publish commands 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication publish command first/last command 与 boundary hash，并继续展示 publish command count、完整 hash 和 primary command。
- 新增 `docs/releases/v0.16.203-draft.md`，把下一版 patch release 聚焦到 publication publish command boundary 可见性。

## [0.16.202] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_ref_context_first_key`、`publication_ref_context_last_key` 和 `publication_ref_context_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 publication ref context 的 key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication ref context first/last key 与 boundary hash，并继续展示 ref context key count 和完整 hash。
- 新增 `docs/releases/v0.16.202-draft.md`，把下一版 patch release 聚焦到 publication ref context boundary 可见性。

## [0.16.201] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `create_issues_safety_contract_first_key`、`create_issues_safety_contract_last_key` 和 `create_issues_safety_contract_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 create issues safety contract 的 key 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 create issues safety contract first/last key 与 boundary hash，并继续展示 contract key count 和完整 hash。
- 新增 `docs/releases/v0.16.201-draft.md`，把下一版 patch release 聚焦到 create issues safety contract boundary 可见性。

## [0.16.200] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_checklist_first_item`、`review_checklist_last_item` 和 `review_checklist_boundary_sha256`，让只读取整包摘要的维护工具能检查 review checklist 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 review checklist first/last item 与 boundary hash，并继续展示 checklist count 和完整 hash。
- 新增 `docs/releases/v0.16.200-draft.md`，把下一版 patch release 聚焦到 review checklist boundary 可见性。

## [0.16.199] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `validation_first_command`、`validation_last_command` 和 `validation_command_boundary_sha256`，让只读取整包摘要的维护工具能检查 validation commands 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 validation command first/last command 与 boundary hash，并继续展示 validation command count 和完整 hash。
- 新增 `docs/releases/v0.16.199-draft.md`，把下一版 patch release 聚焦到 validation command boundary 可见性。

## [0.16.198] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_first_required_action`、`release_draft_last_required_action` 和 `release_draft_required_action_boundary_sha256`，让只读取整包摘要的维护工具能检查 release draft required actions 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft required action first/last action 与 boundary hash，并继续展示 required action count、完整 hash 和 primary action。
- 新增 `docs/releases/v0.16.198-draft.md`，把下一版 patch release 聚焦到 release draft required action boundary 可见性。

## [0.16.197] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_first_issue`、`release_draft_last_issue` 和 `release_draft_issue_boundary_sha256`，让只读取整包摘要的维护工具能检查 release draft issues 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft issue first/last item 与 boundary hash，并继续展示 issue count、primary issue 和完整 hash。
- 新增 `docs/releases/v0.16.197-draft.md`，把下一版 patch release 聚焦到 release draft issue boundary 可见性。

## [0.16.196] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_issue_gate_first_required_action`、`candidate_issue_gate_last_required_action` 和 `candidate_issue_gate_required_action_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue gate required action 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate issue gate required action first/last action 与 boundary hash，并继续展示 required action count、完整 hash 和 primary action。
- 新增 `docs/releases/v0.16.196-draft.md`，把下一版 patch release 聚焦到 candidate issue gate required action boundary 可见性。

## [0.16.195] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_issue_gate_first_reason_code`、`candidate_issue_gate_last_reason_code` 和 `candidate_issue_gate_reason_code_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue gate reason code 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate issue gate reason code first/last code 与 boundary hash，并继续展示 reason code count、完整 hash 和 primary reason。
- 新增 `docs/releases/v0.16.195-draft.md`，把下一版 patch release 聚焦到 candidate issue gate reason code boundary 可见性。

## [0.16.194] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `next_action_first_item`、`next_action_last_item` 和 `next_action_boundary_sha256`，让只读取整包摘要的维护工具能检查 next actions 列表首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 next action first/last item 与 boundary hash，并继续展示 next action preview、next action tail、next action count 与完整 hash。
- 新增 `docs/releases/v0.16.194-draft.md`，把下一版 patch release 聚焦到 next action boundary 可见性。

## [0.16.193] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `next_action_tail_count`、`next_action_tail` 和 `next_action_tail_sha256`，让只读取整包摘要的维护工具能看到 next actions 列表末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 next action tail count/list/hash，并继续展示 next action preview、next action count 与完整 hash。
- 新增 `docs/releases/v0.16.193-draft.md`，把下一版 patch release 聚焦到 next action tail 可见性。

## [0.16.192] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `next_action_preview_count`、`next_action_preview` 和 `next_action_preview_sha256`，让只读取整包摘要的维护工具能看到 next actions 列表入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 next action preview count/list/hash，并继续展示 next action count 与完整 hash。
- 新增 `docs/releases/v0.16.192-draft.md`，把下一版 patch release 聚焦到 next action preview 可见性。

## [0.16.191] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `blocker_first_item`、`blocker_last_item` 和 `blocker_boundary_sha256`，让只读取整包摘要的维护工具能检查 blockers 列表首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 blocker first/last item 与 boundary hash，并继续展示 blocker preview、blocker tail、blocker count 与完整 hash。
- 新增 `docs/releases/v0.16.191-draft.md`，把下一版 patch release 聚焦到 blocker boundary 可见性。

## [0.16.190] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `blocker_tail_count`、`blocker_tail` 和 `blocker_tail_sha256`，让只读取整包摘要的维护工具能看到 blockers 列表末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 blocker tail count/list/hash，并继续展示 blocker preview、blocker count 与完整 hash。
- 新增 `docs/releases/v0.16.190-draft.md`，把下一版 patch release 聚焦到 blocker tail 可见性。

## [0.16.189] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `blocker_preview_count`、`blocker_preview` 和 `blocker_preview_sha256`，让只读取整包摘要的维护工具能看到 blockers 列表入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 blocker preview count/list/hash，并继续展示 blocker count 与完整 hash。
- 新增 `docs/releases/v0.16.189-draft.md`，把下一版 patch release 聚焦到 blocker preview 可见性。

## [0.16.188] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_visibility_key_tail_count`、`publication_visibility_key_tail` 和 `publication_visibility_key_tail_sha256`，让只读取整包摘要的维护工具能看到发布可见性对象末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication visibility key tail count/list/hash，并继续展示 preview、first/last key、boundary hash、key count、visibility hash 与 summary hash。
- 新增 `docs/releases/v0.16.188-draft.md`，把下一版 patch release 聚焦到 publication visibility key tail 可见性。

## [0.16.187] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_visibility_key_preview_count`、`publication_visibility_key_preview` 和 `publication_visibility_key_preview_sha256`，让只读取整包摘要的维护工具能看到发布可见性对象字段入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication visibility key preview count/list/hash，并继续展示 first/last key、boundary hash、key count、visibility hash 与 summary hash。
- 新增 `docs/releases/v0.16.187-draft.md`，把下一版 patch release 聚焦到 publication visibility key preview 可见性。

## [0.16.186] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_visibility_first_key`、`publication_visibility_last_key` 和 `publication_visibility_key_boundary_sha256`，让只读取整包摘要的维护工具能检查发布可见性对象首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 publication visibility first/last key 与 boundary hash，并继续展示 key count、visibility hash 与 summary hash。
- 新增 `docs/releases/v0.16.186-draft.md`，把下一版 patch release 聚焦到 publication visibility key boundary 可见性。

## [0.16.185] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_files_first_key`、`artifact_files_last_key` 和 `artifact_files_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue artifacts 文件映射首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact files first/last key 与 boundary hash，并继续展示 artifact files key preview、tail、key count 与完整 hash。
- 新增 `docs/releases/v0.16.185-draft.md`，把下一版 patch release 聚焦到 artifact files key boundary 可见性。

## [0.16.184] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_files_key_tail_count`、`artifact_files_key_tail` 和 `artifact_files_key_tail_sha256`，让只读取整包摘要的维护工具能看到 candidate issue artifacts 文件映射末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact files key tail count/list/hash，并继续展示 artifact files key preview、key count 与完整 hash。
- 新增 `docs/releases/v0.16.184-draft.md`，把下一版 patch release 聚焦到 artifact files key tail 可见性。

## [0.16.183] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_files_key_preview_count`、`artifact_files_key_preview` 和 `artifact_files_key_preview_sha256`，让只读取整包摘要的维护工具能看到 candidate issue artifacts 文件映射入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact files key preview count/list/hash，并继续展示 artifact files key count 与完整 hash。
- 新增 `docs/releases/v0.16.183-draft.md`，把下一版 patch release 聚焦到 artifact files key preview 可见性。

## [0.16.182] - 2026-06-13

### Added
- `issue_metadata_summary` 现在输出 `metadata_first_item`、`metadata_last_item` 和 `metadata_boundary_sha256`，让候选 issue metadata 的首尾边界可被机器审阅。
- `artifact_bundle_summary` 现在输出 `issue_metadata_first_item`、`issue_metadata_last_item` 和 `issue_metadata_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue metadata 首尾边界。
- 新增 `docs/releases/v0.16.182-draft.md`，把下一版 patch release 聚焦到 issue metadata boundary 可见性。

## [0.16.181] - 2026-06-13

### Added
- `issue_metadata_summary` 现在输出 `metadata_tail_count`、`metadata_tail` 和 `metadata_tail_sha256`，让候选 issue metadata 的稳定末尾入口可被机器审阅。
- `artifact_bundle_summary` 现在输出 `issue_metadata_tail_count`、`issue_metadata_tail` 和 `issue_metadata_tail_sha256`，让只读取整包摘要的维护工具能检查 candidate issue metadata 末尾入口。
- 新增 `docs/releases/v0.16.181-draft.md`，把下一版 patch release 聚焦到 issue metadata tail 可见性。

## [0.16.180] - 2026-06-13

### Added
- `issue_metadata_summary` 现在输出 `metadata_preview_count`、`metadata_preview` 和 `metadata_preview_sha256`，让候选 issue metadata 的稳定入口可被机器审阅。
- `artifact_bundle_summary` 现在输出 `issue_metadata_preview_count`、`issue_metadata_preview` 和 `issue_metadata_preview_sha256`，让只读取整包摘要的维护工具能检查 candidate issue metadata 入口。
- 新增 `docs/releases/v0.16.180-draft.md`，把下一版 patch release 聚焦到 issue metadata preview 可见性。

## [0.16.179] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_order_first_item`、`review_order_last_item` 和 `review_order_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate issue artifacts 审阅顺序首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 review order first/last item 与 boundary hash，并继续展示 review order preview、tail 和完整 hash。
- 新增 `docs/releases/v0.16.179-draft.md`，把下一版 patch release 聚焦到 review order boundary 可见性。

## [0.16.178] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_order_tail_count`、`review_order_tail` 和 `review_order_tail_sha256`，让只读取整包摘要的维护工具能检查 candidate issue artifacts 审阅顺序末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 review order tail count/list/hash，并继续展示 review order preview 与完整 hash。
- 新增 `docs/releases/v0.16.178-draft.md`，把下一版 patch release 聚焦到 review order tail 可见性。

## [0.16.177] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `review_order_preview_count`、`review_order_preview` 和 `review_order_preview_sha256`，让只读取整包摘要的维护工具能看到 candidate issue artifacts 审阅顺序入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 review order preview count/list/hash，并继续展示 review order hash。
- 新增 `docs/releases/v0.16.177-draft.md`，把下一版 patch release 聚焦到 review order preview 可见性。

## [0.16.176] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_summary_key_tail_count`、`issue_body_summary_key_tail` 和 `issue_body_summary_key_tail_sha256`，让只读取整包摘要的维护工具能检查 issue body summary 字段集合末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body summary key tail count/list/hash，并继续展示 key preview 与完整 summary hash。
- 新增 `docs/releases/v0.16.176-draft.md`，把下一版 patch release 聚焦到 issue body summary key tail 可见性。

## [0.16.175] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_summary_key_preview_count`、`issue_body_summary_key_preview` 和 `issue_body_summary_key_preview_sha256`，让只读取整包摘要的维护工具能看到 issue body summary 字段集合入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body summary key preview count/list/hash，并继续展示 key boundary 与完整 summary hash。
- 新增 `docs/releases/v0.16.175-draft.md`，把下一版 patch release 聚焦到 issue body summary key preview 可见性。

## [0.16.174] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_summary_first_key`、`issue_body_summary_last_key` 和 `issue_body_summary_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 issue body summary 字段集合首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body summary first/last key 和 boundary hash，并继续展示 issue body summary key count/hash。
- 新增 `docs/releases/v0.16.174-draft.md`，把下一版 patch release 聚焦到 issue body summary key boundary 可见性。

## [0.16.173] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_summary_key_count` 和 `issue_body_summary_keys_sha256`，让只读取整包摘要的维护工具能检查 issue body summary 字段集合。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body summary key count/hash，并继续展示 issue body summary hash。
- 新增 `docs/releases/v0.16.173-draft.md`，把下一版 patch release 聚焦到 issue body summary schema 可见性。

## [0.16.172] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_inventory_first_entry`、`issue_body_inventory_last_entry` 和 `issue_body_inventory_boundary_sha256`，让只读取整包摘要的维护工具能检查 issue body inventory 首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body inventory first/last entry 和 boundary hash，并继续展示 preview/tail 与完整 inventory hash。
- 新增 `docs/releases/v0.16.172-draft.md`，把下一版 patch release 聚焦到 issue body inventory 首尾边界可见性。

## [0.16.171] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_inventory_tail_count`、`issue_body_inventory_tail` 和 `issue_body_inventory_tail_sha256`，让只读取整包摘要的维护工具能检查 issue body inventory 末尾入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body inventory tail count/list/hash，并继续展示 preview 与完整 inventory hash。
- 新增 `docs/releases/v0.16.171-draft.md`，把下一版 patch release 聚焦到 issue body inventory 末尾预览可见性。

## [0.16.170] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `issue_body_inventory_preview_count`、`issue_body_inventory_preview` 和 `issue_body_inventory_preview_sha256`，让只读取整包摘要的维护工具能看到 issue body inventory 入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 issue body inventory preview count/list/hash，并继续展示完整 inventory hash。
- 新增 `docs/releases/v0.16.170-draft.md`，把下一版 patch release 聚焦到 issue body inventory 预览可见性。

## [0.16.169] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_cases_first_case`、`candidate_cases_last_case` 和 `candidate_cases_boundary_sha256`，让只读取整包摘要的维护工具能检查 candidate case 列表首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate cases first/last case 和 boundary hash，并继续展示 candidate cases preview/tail。
- 新增 `docs/releases/v0.16.169-draft.md`，把下一版 patch release 聚焦到 candidate case 列表边界可见性。

## [0.16.168] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_cases_tail_count`、`candidate_cases_tail` 和 `candidate_cases_tail_sha256`，让只读取整包摘要的维护工具能检查 candidate case 列表尾部入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate cases tail count/list/hash，并继续展示 candidate cases preview。
- 新增 `docs/releases/v0.16.168-draft.md`，把下一版 patch release 聚焦到 candidate case 列表尾部预览可见性。

## [0.16.167] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `candidate_cases_preview_count`、`candidate_cases_preview` 和 `candidate_cases_preview_sha256`，让只读取整包摘要的维护工具能直接看到 candidate case 列表入口。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 candidate cases preview count/list/hash，并继续展示完整 candidate cases hash。
- 新增 `docs/releases/v0.16.167-draft.md`，把下一版 patch release 聚焦到 candidate case 列表预览可见性。

## [0.16.166] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_payload_first_key`、`artifact_manifest_payload_last_key` 和 `artifact_manifest_payload_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` payload 字段首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest payload first/last key 和 boundary hash，并继续展示 payload key preview/tail。
- 新增 `docs/releases/v0.16.166-draft.md`，把下一版 patch release 聚焦到 artifact manifest payload 字段边界可见性。

## [0.16.165] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_payload_key_tail_count`、`artifact_manifest_payload_key_tail` 和 `artifact_manifest_payload_key_tail_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` payload 字段后缀。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest payload key tail count/list/hash，并继续展示 payload key preview。
- 新增 `docs/releases/v0.16.165-draft.md`，把下一版 patch release 聚焦到 artifact manifest payload 字段尾部预览可见性。

## [0.16.164] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_payload_key_preview_count`、`artifact_manifest_payload_key_preview` 和 `artifact_manifest_payload_key_preview_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` payload 字段前缀。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest payload key preview count/list/hash，并继续展示 payload hash。
- 新增 `docs/releases/v0.16.164-draft.md`，把下一版 patch release 聚焦到 artifact manifest payload 字段预览可见性。

## [0.16.163] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_key_tail_count`、`artifact_manifest_key_tail` 和 `artifact_manifest_key_tail_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` 顶层字段后缀。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest key tail count/list/hash，并继续展示 manifest key preview。
- 新增 `docs/releases/v0.16.163-draft.md`，把下一版 patch release 聚焦到 artifact manifest 顶层字段尾部预览可见性。

## [0.16.162] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_key_preview_count`、`artifact_manifest_key_preview` 和 `artifact_manifest_key_preview_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` 顶层字段前缀。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest key preview count/list/hash，并继续展示 manifest key boundary。
- 新增 `docs/releases/v0.16.162-draft.md`，把下一版 patch release 聚焦到 artifact manifest 顶层字段预览可见性。

## [0.16.161] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_first_key`、`artifact_manifest_last_key` 和 `artifact_manifest_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 `artifact-manifest.json` 顶层字段首尾边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest first/last key 和 boundary hash，并继续展示 manifest key count/hash。
- 新增 `docs/releases/v0.16.161-draft.md`，把下一版 patch release 聚焦到 artifact manifest 顶层字段边界可见性。

## [0.16.160] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_bundle_summary_first_key`、`artifact_bundle_summary_last_key` 和 `artifact_bundle_summary_key_boundary_sha256`，让只读取整包摘要的维护工具能检查 summary 首尾字段边界。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact bundle summary first/last key 和 boundary hash，并继续展示 key preview/tail。
- 新增 `docs/releases/v0.16.160-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 自身字段边界可见性。

## [0.16.159] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_bundle_summary_key_tail_count`、`artifact_bundle_summary_key_tail` 和 `artifact_bundle_summary_key_tail_sha256`，让只读取整包摘要的维护工具能检查 summary 末尾字段。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact bundle summary key tail count/list/hash，并继续展示 key preview。
- 新增 `docs/releases/v0.16.159-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 自身字段尾部预览可见性。

## [0.16.158] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_bundle_summary_key_preview_count`、`artifact_bundle_summary_key_preview` 和 `artifact_bundle_summary_key_preview_sha256`，让只读取整包摘要的维护工具能先检查 summary 前几个关键字段。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact bundle summary key preview count/list/hash，并继续展示完整 key count/hash。
- 新增 `docs/releases/v0.16.158-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 自身字段预览可见性。

## [0.16.157] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_bundle_summary_key_count` 和 `artifact_bundle_summary_keys_sha256`，让只读取整包摘要的维护工具能判断 summary 自身字段规模和字段清单是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact bundle summary key count/hash，并继续展示 manifest payload hash。
- 新增 `docs/releases/v0.16.157-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 自身字段清单摘要可见性。

## [0.16.156] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_payload_key_count` 和 `artifact_manifest_payload_sha256`，让只读取整包摘要的维护工具能判断除 summary 自身之外的 manifest payload 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在复用 manifest 中预先计算的 bundle summary，确保 README 与 `artifact-manifest.json` 的 payload hash 同源。
- 新增 `docs/releases/v0.16.156-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifact manifest payload summary 可见性。

## [0.16.155] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_key_count` 和 `artifact_manifest_keys_sha256`，让只读取整包摘要的维护工具能判断 `artifact-manifest.json` 顶层字段规模和字段清单是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 artifact manifest key count/hash，并继续展示 manifest schema version。
- 新增 `docs/releases/v0.16.155-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifact manifest key summary 可见性。

## [0.16.154] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `artifact_manifest_schema_version`，让只读取整包摘要的维护工具能先判断 `artifact-manifest.json` 字段语义版本。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `artifact_manifest_schema_version`，并与 manifest 顶层 `schema_version` 保持同源。
- 新增 `docs/releases/v0.16.154-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifact manifest schema version 可见性。

## [0.16.153] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_primary_issue` 和 `release_draft_handoff_primary_required_action`，让只读取整包摘要的维护工具能用 handoff primary alias 展示首要草案问题和处理动作。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft handoff primary alias，并继续展示 schema version、key count 与 hash。
- 新增 `docs/releases/v0.16.153-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft handoff primary alias 可见性。

## [0.16.152] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_handoff_schema_version`，让只读取整包摘要的维护工具能先判断 release draft handoff 字段语义版本。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `release_draft_handoff_schema_version`，并继续展示 handoff key count 与 hash。
- 新增 `docs/releases/v0.16.152-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft handoff schema version 可见性。

## [0.16.151] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_handoff_schema_version`，让只读取整包摘要的维护工具能先判断 publication handoff 字段语义版本。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `publication_handoff_schema_version`，并继续展示 handoff key count 与 hash。
- 新增 `docs/releases/v0.16.151-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication handoff schema version 可见性。

## [0.16.150] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `schema_version: 1`，让只读取 publication handoff 的维护工具能先判断字段语义版本。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示 `schema_version`，并让 `publication_handoff_key_count` 与 hash 反映该字段变化。
- 新增 `docs/releases/v0.16.150-draft.md`，把下一版 patch release 聚焦到 publication handoff schema version 可见性。

## [0.16.149] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `primary_issue` 和 `primary_required_action`，让工具能用和 publication handoff 一致的 primary 字段模型读取首要草案问题。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `primary_issue` 和 `primary_required_action`，并在无 release draft issue 时使用 `(none)`。
- 新增 `docs/releases/v0.16.149-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 primary 字段别名可见性。

## [0.16.148] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `primary_next_action`，让只读取 publication handoff 的维护工具也能直接展示第一条发布同步待办。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示 `primary_next_action`，并在无 publication next action 时使用 `(none)`。
- 新增 `docs/releases/v0.16.148-draft.md`，把下一版 patch release 聚焦到 publication handoff 的 primary next action 可见性。

## [0.16.147] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `primary_publish_command`，让只读取 publication handoff 的维护工具也能直接展示第一条发布同步命令。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示 `primary_publish_command`，并在无 publish command 时使用 `(none)`。
- 新增 `docs/releases/v0.16.147-draft.md`，把下一版 patch release 聚焦到 publication handoff 的 primary publish command 可见性。

## [0.16.146] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_primary_publish_command`，让只读取整包摘要的维护工具也能直接展示第一条发布同步命令。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `publication_primary_publish_command`，并在无 publish command 时使用 `(none)`。
- 新增 `docs/releases/v0.16.146-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication primary publish command 可见性。

## [0.16.145] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `publication_primary_next_action`，让只读取整包摘要的维护工具也能直接展示第一条发布同步待办。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `publication_primary_next_action`，并在无 publication next action 时使用 `(none)`。
- 新增 `docs/releases/v0.16.145-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication primary next action 可见性。

## [0.16.144] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_primary_issue`，让只读取整包摘要的维护工具也能直接展示第一条 release draft 阻塞原因。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `release_draft_primary_issue`，并在无阻塞原因时使用 `(none)`。
- 新增 `docs/releases/v0.16.144-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft primary issue 可见性。

## [0.16.143] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_primary_required_action`，让只读取整包摘要的维护工具也能直接展示第一条 release draft 修复动作。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 `release_draft_primary_required_action`，并在无动作时使用 `(none)`。
- 新增 `docs/releases/v0.16.143-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft primary required action 可见性。

## [0.16.142] - 2026-06-13

### Added
- `artifact_bundle_summary` 现在输出 `release_draft_required_action_count` 和 `release_draft_required_actions_sha256`，让只读取整包摘要的维护工具也能判断 release draft required actions 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 段落现在展示 release draft required actions 的数量和 hash。
- 新增 `docs/releases/v0.16.142-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft required actions 可见性。

## [0.16.141] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_required_action_count`、`release_draft_required_actions_sha256` 和 `release_draft_required_actions`，让只读取 handoff 的维护工具也能直接拿到完整草案处理动作列表。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 release draft required actions 的数量、hash 和列表。
- 新增 `docs/releases/v0.16.141-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的完整 required actions 可见性。

## [0.16.140] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_primary_required_action`，让只读取 handoff 的维护工具也能直接拿到第一条草案处理动作。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_primary_required_action`。
- 新增 `docs/releases/v0.16.140-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 primary required action 可见性。

## [0.16.139] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `schema_version`，让只读取 handoff 的维护工具也能先判断字段语义版本。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `schema_version`。
- 新增 `docs/releases/v0.16.139-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 schema version 可见性。

## [0.16.138] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_primary_issue`，让只读取 handoff 的维护工具也能直接看到第一条草案阻塞原因。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_primary_issue`。
- 新增 `docs/releases/v0.16.138-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 primary issue 可见性。

## [0.16.137] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_issues_sha256`，让只读取 handoff 的维护工具也能检测草案问题列表漂移。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_issues_sha256`。
- 新增 `docs/releases/v0.16.137-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的问题列表摘要可见性。

## [0.16.136] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_path_sha256`，让只读取 handoff 的维护工具也能检测草案路径漂移。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_path_sha256`。
- 新增 `docs/releases/v0.16.136-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的路径摘要可见性。

## [0.16.135] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_ok`，让只读取 handoff 的维护工具也能直接判断草案门禁是否通过。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_ok`。
- 新增 `docs/releases/v0.16.135-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 ok 状态可见性。

## [0.16.134] - 2026-06-13

### Added
- `release-draft-handoff.json` 现在输出 `release_draft_issue_count`，让只读取 handoff 的维护工具也能先判断草案门禁规模。
- Candidate issue artifacts `README.md` 的 `Release Draft Handoff` 段落现在展示 `release_draft_issue_count`。
- 新增 `docs/releases/v0.16.134-draft.md`，把下一版 patch release 聚焦到 release draft handoff 的 issue 数量可见性。

## [0.16.133] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `publish_command_count`，让只读取 handoff 的维护工具也能先判断发布命令规模。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示 `publish_command_count`。
- 新增 `docs/releases/v0.16.133-draft.md`，把下一版 patch release 聚焦到 publication handoff 的发布命令数量可见性。

## [0.16.132] - 2026-06-13

### Added
- `publication-handoff.json` 现在输出 `publish_script_path_sha256` 和 `publish_script_command_sha256`，让只读取 handoff 的维护工具也能检测发布脚本路径或命令漂移。
- Candidate issue artifacts `README.md` 的 `Publication Handoff` 段落现在展示同一组发布脚本摘要字段。
- 新增 `docs/releases/v0.16.132-draft.md`，把下一版 patch release 聚焦到 publication handoff 的发布脚本摘要可见性。

## [0.16.131] - 2026-06-13

### Added
- `scripts/plan_next_iteration.py` 现在输出 `publication_publish_script_command_sha256`，让计划 JSON、文本输出和 Markdown report 不生成 artifacts 也能检测发布脚本生成命令漂移。
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 和 `artifact-manifest.json` 现在展示 `publication_publish_script_command_sha256`。
- 新增 `docs/releases/v0.16.131-draft.md`，把下一版 patch release 聚焦到 publication publish script command hash 的 plan 级可见性。

## [0.16.130] - 2026-06-13

### Added
- `scripts/plan_next_iteration.py` 现在输出 `publication_publish_script_path_sha256`，让计划 JSON、文本输出和 Markdown report 不生成 artifacts 也能检测发布脚本路径漂移。
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 和 `artifact-manifest.json` 现在展示 `publication_publish_script_path_sha256`。
- 新增 `docs/releases/v0.16.130-draft.md`，把下一版 patch release 聚焦到 publication publish script path hash 的 plan 级可见性。

## [0.16.129] - 2026-06-13

### Added
- `scripts/plan_next_iteration.py` 现在输出 `publication_publish_script_path`，让计划 JSON、文本输出和 Markdown report 直接展示可审阅发布脚本的默认路径。
- Candidate issue artifacts `README.md`、`artifact-manifest.json` 和 `publication-handoff.json` 现在保留发布脚本路径；`artifact_bundle_summary` 新增 `publication_publish_script_path_sha256` 便于检测路径漂移。
- 新增 `docs/releases/v0.16.129-draft.md`，把下一版 patch release 聚焦到 publication publish script path 的结构化可见性。

## [0.16.128] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_publish_script_command`，方便维护者第一屏就能看到生成可审阅发布脚本的命令。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication publish script command。
- 新增 `docs/releases/v0.16.128-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布脚本生成命令可见性。

## [0.16.127] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_publish_command_count`，方便维护者先判断发布命令规模。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication publish command 数量。
- 新增 `docs/releases/v0.16.127-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布命令数量可见性。

## [0.16.126] - 2026-06-12

### Fixed
- `Candidate Issue Gate Quick Summary` 的 inline code helper 现在会用带空格的双反引号包裹包含反引号的 summary，避免 `visibility_summary` 以反引号开头时生成含混的 Markdown。
- `tests/test_plan_next_iteration.py` 覆盖 summary 以反引号开头的格式化边界。
- 新增 `docs/releases/v0.16.126-draft.md`，把下一版 patch release 聚焦到 quick summary inline code fence 稳定性。

## [0.16.125] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `visibility_summary`，方便维护者先读到发布可见性的可读解释。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 visibility summary。
- 新增 `docs/releases/v0.16.125-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的 visibility summary 可见性。

## [0.16.124] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `blocker_count`、`next_action_count` 和 `publication_next_action_count`，方便维护者先判断本轮待办规模。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 blocker/next action 数量。
- 新增 `docs/releases/v0.16.124-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的待办规模可见性。

## [0.16.123] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_ok` 和 `release_draft_ok`，方便维护者先区分发布阻塞和草案阻塞。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication/release draft ok。
- 新增 `docs/releases/v0.16.123-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的 ok 布尔值可见性。

## [0.16.122] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_upstream_head`、`publication_tag_points_at_head`、`publication_tag_commit_in_upstream`、`publication_branch_published`、`publication_tag_published`、`publication_remote_branch_head` 和 `publication_remote_tag_commit`。
- `tests/test_plan_next_iteration.py` 覆盖 quick summary 的 upstream HEAD、tag state、published state 和 remote refs。
- 新增 `docs/releases/v0.16.122-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布状态字段落地。

## [0.16.121] - 2026-06-12

### Added
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 现在明确说明 `Candidate Issue Gate Quick Summary` 会展示 publication upstream HEAD、tag state、published state 和 remote refs。
- `tests/test_weekly_maintainer_loop_docs.py` 固定 quick summary 文档契约，避免维护者循环说明遗漏现有发布状态字段。
- 新增 `docs/releases/v0.16.121-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的文档契约完整性。

## [0.16.120] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_tag_commit`，方便维护者先核对最新 tag 指向的提交。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication local HEAD/tag commit。
- 新增 `docs/releases/v0.16.120-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的 tag commit 可见性。

## [0.16.119] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_local_head`，方便维护者先核对本地发布提交。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication local HEAD。
- 新增 `docs/releases/v0.16.119-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的本地 HEAD 可见性。

## [0.16.118] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_remote`，方便维护者先确认发布命令对应的远端名称。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication branch/upstream/remote。
- 新增 `docs/releases/v0.16.118-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的远端名称可见性。

## [0.16.117] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_upstream`，方便维护者先确认本地分支对应的上游引用。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication branch/upstream。
- 新增 `docs/releases/v0.16.117-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的上游引用可见性。

## [0.16.116] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_branch`，方便维护者先确认待发布分支。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication branch。
- 新增 `docs/releases/v0.16.116-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布分支可见性。

## [0.16.115] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_worktree_clean`，方便维护者先判断是否需要清理本地改动再发布。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication worktree clean。
- 新增 `docs/releases/v0.16.115-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的工作区清洁状态可见性。

## [0.16.114] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_behind_count`，方便维护者先判断本地分支是否落后远端。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication ahead/behind 数。
- 新增 `docs/releases/v0.16.114-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的 behind 同步风险可见性。

## [0.16.113] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_remote_checked`，方便维护者先判断发布可见性结论是否做过远端复核。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication remote checked。
- 新增 `docs/releases/v0.16.113-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的远端复核状态可见性。

## [0.16.112] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `release_draft_path`，方便维护者直接定位需要审阅的草案文件。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 release draft path。
- 新增 `docs/releases/v0.16.112-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的草案路径可见性。

## [0.16.111] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `publication_ahead_count` 和 `release_draft_issue_count`，方便维护者先判断本地 release 发布规模和草案剩余问题数量。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 publication ahead 数和 release draft issue 数。
- 新增 `docs/releases/v0.16.111-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 的发布/草案规模可见性。

## [0.16.110] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 的 `Candidate Issue Gate Quick Summary` 现在展示 `reason_code_count` 和 `required_action_count`，方便维护者先判断 gate 是否还有更多细节需要展开。
- [docs/weekly-maintainer-loop.md](docs/weekly-maintainer-loop.md) 说明 quick summary 会展示 reason/action 数量。
- 新增 `docs/releases/v0.16.110-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 数量可见性。

## [0.16.109] - 2026-06-12

### Added
- Candidate issue artifacts `README.md` 现在会在 `Artifact Bundle Summary` 前展示 `Candidate Issue Gate Quick Summary`，让维护者先看到 gate status、首要 reason/action、latest tag 和 visibility。
- README quick summary 会复用已有 primary reason code、reason description 和 required action，让人工审阅不必先展开完整 artifact bundle summary。
- 新增 `docs/releases/v0.16.109-draft.md`，把下一版 patch release 聚焦到 candidate issue gate quick summary 可读性。

## [0.16.108] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_primary_reason_description`，方便工具只读整包摘要就展示首要 gate reason 的可读说明。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 会展示 gate primary reason description，并保持 primary reason code/action 字段不变。
- 新增 `docs/releases/v0.16.108-draft.md`，把下一版 patch release 聚焦到 candidate issue gate primary reason description 可见性。

## [0.16.107] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_primary_reason_code` 和 `candidate_issue_gate_primary_required_action`，方便工具只读整包摘要就展示首要 gate 阻塞原因和首个维护动作。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 会展示 gate primary reason/action，并对包含反引号的动作文本使用更宽的 Markdown code span。
- 新增 `docs/releases/v0.16.107-draft.md`，把下一版 patch release 聚焦到 candidate issue gate primary summary 可见性。

## [0.16.106] - 2026-06-12

### Added
- `publication_ref_context` 现在包含 `remote_branch_head` 和 `remote_tag_commit`，方便候选 issue artifacts 保留远端 ref 实际指向。
- `artifact_bundle_summary` 现在包含 `publication_remote_branch_head` 和 `publication_remote_tag_commit`，方便工具只读整包摘要就判断 remote check 看到的远端分支和 tag commit。
- 新增 `docs/releases/v0.16.106-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication remote ref 可见性。

## [0.16.105] - 2026-06-12

### Added
- `publication_ref_context` 现在包含 `branch_published` 和 `tag_published`，方便候选 issue artifacts 保留分支/tag 是否公开可见的判断。
- `artifact_bundle_summary` 现在包含 `publication_branch_published` 和 `publication_tag_published`，方便工具只读整包摘要就判断发布 refs 是否公开。
- 新增 `docs/releases/v0.16.105-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication published state 可见性。

## [0.16.104] - 2026-06-12

### Added
- `publication_ref_context` 现在包含 `tag_points_at_head` 和 `tag_commit_in_upstream`，方便候选 issue artifacts 保留 tag 状态判断。
- `artifact_bundle_summary` 现在包含 `publication_tag_points_at_head` 和 `publication_tag_commit_in_upstream`，方便工具只读整包摘要就判断最新本地 tag 是否指向 HEAD 以及 tag commit 是否在上游。
- 新增 `docs/releases/v0.16.104-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication tag state 可见性。

## [0.16.103] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_local_head` 和 `publication_upstream_head`，方便工具只读候选 issue artifacts 整包摘要就定位本地 HEAD 与上游 HEAD。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication local/upstream HEAD。
- 新增 `docs/releases/v0.16.103-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication head 可见性。

## [0.16.102] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_latest_tag` 和 `publication_tag_commit`，方便工具只读候选 issue artifacts 整包摘要就定位最新本地 tag 及其提交。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication latest tag/tag commit。
- 新增 `docs/releases/v0.16.102-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication tag 可见性。

## [0.16.101] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_branch`、`publication_upstream` 和 `publication_remote`，方便工具只读候选 issue artifacts 整包摘要就定位发布分支、上游和远端。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication branch/upstream/remote。
- 新增 `docs/releases/v0.16.101-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication ref names 可见性。

## [0.16.100] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_behind_count`，方便工具只读候选 issue artifacts 整包摘要就判断本地分支是否落后远端。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication behind count。
- 新增 `docs/releases/v0.16.100-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication behind 可见性。

## [0.16.99] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_remote_checked` 和 `publication_ahead_count`，方便工具只读候选 issue artifacts 整包摘要就判断 publication audit 是否做过远端复核及本地领先规模。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication remote checked 与 ahead count。
- 新增 `docs/releases/v0.16.99-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication remote 可见性。

## [0.16.98] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `release_draft_ok`，方便工具只读候选 issue artifacts 整包摘要就判断 release draft gate 是否通过。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 release draft ok 布尔值。
- 新增 `docs/releases/v0.16.98-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft gate 可见性。

## [0.16.97] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `release_draft_path` 和 `release_draft_path_sha256`，方便工具只读候选 issue artifacts 整包摘要就判断目标 release draft 路径是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 release draft path 与 path hash。
- 新增 `docs/releases/v0.16.97-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft path 可见性。

## [0.16.96] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `release_draft_issues_sha256`，方便工具只读候选 issue artifacts 整包摘要就判断 release draft issues 列表是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 release draft issues hash。
- 新增 `docs/releases/v0.16.96-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft issues 可见性。

## [0.16.95] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_visibility_key_count`，方便工具只读候选 issue artifacts 整包摘要就判断 publication visibility 结构规模。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication visibility key count。
- 新增 `docs/releases/v0.16.95-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication visibility 结构可见性。

## [0.16.94] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_ref_context_key_count`，方便工具只读候选 issue artifacts 整包摘要就判断 publication ref context 结构规模。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication ref context key count。
- 新增 `docs/releases/v0.16.94-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication ref context 结构可见性。

## [0.16.93] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_publish_command_count`，方便工具只读候选 issue artifacts 整包摘要就判断发布命令数量。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication publish command count。
- 新增 `docs/releases/v0.16.93-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的发布命令数量可见性。

## [0.16.92] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 JSON、默认文本输出和 Markdown report 现在包含 `publication_next_action_count` 与 `publication_publish_command_count`，方便维护者在周初计划里先判断发布待办规模。
- 新增 `docs/releases/v0.16.92-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的发布待办数量可见性。

## [0.16.91] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 的 JSON、默认文本输出和 Markdown report 现在包含 `next_action_count` 与 `publish_command_count`，方便维护者先判断发布待办规模再展开具体列表。
- 新增 `docs/releases/v0.16.91-draft.md`，把下一版 patch release 聚焦到 publication audit 的待办数量可见性。

## [0.16.90] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_publish_script_command_sha256`，方便工具只读整包摘要就检测发布脚本生成命令是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication publish script command hash。
- 新增 `docs/releases/v0.16.90-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的发布脚本生成入口漂移检测。

## [0.16.89] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_visibility_sha256` 和 `publication_visibility_summary_sha256`，方便工具只读整包摘要就检测发布可见性对象或 summary 文本是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication visibility hash 和 summary hash。
- 新增 `docs/releases/v0.16.89-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的发布可见性漂移检测。

## [0.16.88] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `issue_artifacts_command_sha256`，方便工具只读整包摘要就检测 candidate issue artifacts 复现命令是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 issue artifacts command hash。
- 新增 `docs/releases/v0.16.88-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifacts 复现命令漂移检测。

## [0.16.87] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `artifact_files_key_count` 和 `artifact_files_sha256`，方便工具只读整包摘要就检测 candidate issue artifacts 文件映射是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 artifact files key count 和 hash。
- 新增 `docs/releases/v0.16.87-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 artifacts 文件映射漂移检测。

## [0.16.86] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_key_count` 和 `candidate_issue_gate_sha256`，方便工具只读整包摘要就检测整个 candidate issue gate 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate issue gate key count 和 hash。
- 新增 `docs/releases/v0.16.86-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 candidate issue gate 整体漂移检测。

## [0.16.85] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `requires_maintainer_review`，方便工具只读整包摘要就判断候选 issue gate 是否仍需人工审阅。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 maintainer review flag。
- 新增 `docs/releases/v0.16.85-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的人工审阅标记。

## [0.16.84] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_summary_sha256`，方便工具只读整包摘要就检测 gate summary 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate issue gate summary hash。
- 新增 `docs/releases/v0.16.84-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 gate summary 漂移检测。

## [0.16.83] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_reason_description_count` 和 `candidate_issue_gate_reason_descriptions_sha256`，方便工具只读整包摘要就检测 gate reason descriptions 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate issue gate reason descriptions count 和 hash。
- 新增 `docs/releases/v0.16.83-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 gate reason descriptions 漂移检测。

## [0.16.82] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_issue_gate_evidence_key_count` 和 `candidate_issue_gate_evidence_sha256`，方便工具只读整包摘要就检测 gate evidence 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate issue gate evidence key count 和 hash。
- 新增 `docs/releases/v0.16.82-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 gate evidence 漂移检测。

## [0.16.81] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_handoff_key_count` 和 `publication_handoff_sha256`，方便工具只读整包摘要就检测 publication handoff 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 publication handoff key count 和 hash。
- 新增 `docs/releases/v0.16.81-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 publication handoff 漂移检测。

## [0.16.80] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `release_draft_handoff_key_count` 和 `release_draft_handoff_sha256`，方便工具只读整包摘要就检测 release draft handoff 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 release draft handoff key count 和 hash。
- 新增 `docs/releases/v0.16.80-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 release draft handoff 漂移检测。

## [0.16.79] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `issue_body_summary_sha256`，方便工具只读整包摘要就检测 issue body summary 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 issue body summary hash。
- 新增 `docs/releases/v0.16.79-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 issue body summary 漂移检测。

## [0.16.78] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `candidate_cases_sha256`，方便工具只读整包摘要就检测候选 case 列表是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 candidate cases hash。
- 新增 `docs/releases/v0.16.78-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 candidate cases 漂移检测。

## [0.16.77] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `issue_metadata_count` 和 `issue_metadata_sha256`，方便工具只读整包摘要就检测候选 issue metadata 是否漂移。
- `artifact-manifest.json` 新增 `issue_metadata_summary`，记录稳定 issue metadata 字段的数量和 SHA-256。
- 新增 `docs/releases/v0.16.77-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 issue metadata 漂移检测。

## [0.16.76] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `create_issues_safety_contract_key_count` 和 `create_issues_safety_contract_sha256`，方便工具只读整包摘要就检测候选 issue 创建安全契约是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 create issues safety contract 摘要字段。
- 新增 `docs/releases/v0.16.76-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 create issues safety contract 漂移检测。

## [0.16.75] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `review_checklist_count` 和 `review_checklist_sha256`，方便工具只读整包摘要就检测候选 issue 审阅清单是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 review checklist 摘要字段。
- 新增 `docs/releases/v0.16.75-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 review checklist 漂移检测。

## [0.16.74] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `validation_command_count` 和 `validation_commands_sha256`，方便工具只读整包摘要就检测验证命令集合是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 validation commands 摘要字段。
- 新增 `docs/releases/v0.16.74-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 validation commands 漂移检测。

## [0.16.73] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_worktree_status_count` 和 `publication_worktree_status_sha256`，方便工具只读整包摘要就检测发布前工作树证据是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 publication worktree status 摘要字段。
- 新增 `docs/releases/v0.16.73-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 worktree status 漂移检测。

## [0.16.72] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_ref_context_sha256` 和 `publication_publish_commands_sha256`，方便工具只读整包摘要就检测发布可见性证据是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 publication ref context / publish commands hash 字段。
- 新增 `docs/releases/v0.16.72-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的发布可见性漂移检测。

## [0.16.71] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `blockers_sha256`、`next_actions_sha256` 和 `publication_next_actions_sha256`，方便工具只读整包摘要就检测 blockers/action lists 是否漂移。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 blocker/action hash 字段。
- 新增 `docs/releases/v0.16.71-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的待办内容漂移检测。

## [0.16.70] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `blocker_count`、`next_action_count` 和 `publication_next_action_count`，方便工具只读整包摘要就判断本轮待办规模。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 blocker/action 计数字段。
- 新增 `docs/releases/v0.16.70-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的待办规模预筛。

## [0.16.69] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `publication_ok`、`publication_visibility_status` 和 `release_draft_issue_count`，方便工具只读整包摘要就区分 publication/release draft 阻塞来源。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示这些 publication/release draft 预筛字段。
- 新增 `docs/releases/v0.16.69-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的阻塞来源预筛。

## [0.16.68] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 candidate issue gate reason/action 的 count/hash，方便工具只读整包摘要就判断 gate 是否需要展开。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 gate reason/action 摘要字段。
- 新增 `docs/releases/v0.16.68-draft.md`，把下一版 patch release 聚焦到 artifact bundle summary 的 gate 摘要。

## [0.16.67] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `reason_code_count` 和 `reason_codes_sha256`，方便工具快速检测 gate reason set 是否变化。
- Next iteration Markdown report 与 candidate issue artifacts `README.md` 现在展示 reason code count/hash。
- 新增 `docs/releases/v0.16.67-draft.md`，把下一版 patch release 聚焦到 candidate issue gate reason codes 摘要。

## [0.16.66] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `required_action_count` 和 `required_actions_sha256`，方便工具快速检测 gate action set 是否变化。
- Next iteration Markdown report 与 candidate issue artifacts `README.md` 现在展示 required actions count/hash。
- 新增 `docs/releases/v0.16.66-draft.md`，把下一版 patch release 聚焦到 candidate issue gate required actions 摘要。

## [0.16.65] - 2026-06-12

### Changed
- `candidate_issue_gate.required_actions` 现在会在 publication 阻塞之外追加 release draft 修复动作，避免 `release_draft_issues` 只有原因码、没有可执行待办。
- Release draft 修复动作统一使用 `Resolve release draft issue: ...` 文案，方便维护者和自动化从 gate payload 直接执行下一步。
- 新增 `docs/releases/v0.16.65-draft.md`，把下一版 patch release 聚焦到 candidate issue gate required actions 的完整性。

## [0.16.64] - 2026-06-12

### Added
- `artifact_bundle_summary` 现在包含 `review_order_sha256`，让工具能快速检测 candidate issue artifacts 审阅顺序是否变化。
- Candidate issue artifacts `README.md` 的 `Artifact Bundle Summary` 现在展示 review order hash。
- 新增 `docs/releases/v0.16.64-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 审阅顺序摘要。

## [0.16.63] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `artifact_bundle_summary`，汇总 candidate/body/review item 数量、inventory hash、gate 状态和创建脚本安全布尔值。
- Candidate issue artifacts `README.md` 现在展示 `Artifact Bundle Summary` 小节，方便维护者先快速审阅整包状态。
- 新增 `docs/releases/v0.16.63-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 整包摘要。

## [0.16.62] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `issue_body_summary`，记录 candidate issue body 总数、总字节数和 inventory SHA-256。
- Candidate issue artifacts `README.md` 现在展示 `Issue Body Summary` 小节，方便维护者快速判断整批 body 文件是否变化。
- 新增 `docs/releases/v0.16.62-draft.md`，把下一版 patch release 聚焦到 candidate issue body 汇总的机器可读审计。

## [0.16.61] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `issue_body_inventory`，记录每个 candidate issue body 的文件名、字节数和 SHA-256。
- Candidate issue artifacts `README.md` 现在展示 `Issue Body Inventory` 表，方便维护者核对 body 文件完整性。
- 新增 `docs/releases/v0.16.61-draft.md`，把下一版 patch release 聚焦到 candidate issue body 清单的机器可读审计。

## [0.16.60] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `create_issues_safety`，结构化说明候选 issue 创建脚本的 dry-run 和 publication preflight 行为。
- Candidate issue artifacts `README.md` 现在展示 `Create Issues Safety` 小节，让维护者直接看到 dry-run、preflight command 和 preflight JSON 路径。
- 新增 `docs/releases/v0.16.60-draft.md`，把下一版 patch release 聚焦到 candidate issue 创建脚本安全语义的机器可读交接。

## [0.16.59] - 2026-06-12

### Added
- 生成的 candidate issue `create-issues.sh` 现在支持 `CLIANY_CREATE_ISSUES_DRY_RUN=1` 预览模式，只打印 `gh issue create` 命令，不运行 preflight 或创建 issue。
- `artifact-manifest.json` 现在包含 `create_issues_dry_run_command`，方便工具和维护者展示安全预览入口。
- 新增 `docs/releases/v0.16.59-draft.md`，把下一版 patch release 聚焦到 candidate issue 创建脚本的 dry-run 预览能力。

## [0.16.58] - 2026-06-12

### Changed
- Candidate issue artifacts `README.md` 的 `Validation Commands` 现在复用 `artifact-manifest.json.validation_commands` 的完整命令列表。
- Artifacts README 现在直接展示 release readiness 与 publication audit 复核命令，减少维护者只照 README 操作时漏跑门禁的风险。
- 新增 `docs/releases/v0.16.58-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 与 manifest 的验证命令对齐。

## [0.16.57] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `reason_descriptions`，为 `reason_codes` 提供同源可读说明。
- Next iteration Markdown report 和 candidate issue artifacts README 现在展示 gate reason descriptions，方便维护者无需查文档也能理解原因码。
- 新增 `docs/releases/v0.16.57-draft.md`，把下一版 patch release 聚焦到 candidate issue gate reason code descriptions。

## [0.16.56] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `reason_codes`，用 `publication_not_published`、`local_release_only`、`release_draft_issues` 等稳定原因码解释 gate 结论。
- Next iteration Markdown report 和 candidate issue artifacts README 现在展示 gate reason codes，方便维护者和自动化无需解析 summary。
- 新增 `docs/releases/v0.16.56-draft.md`，把下一版 patch release 聚焦到 candidate issue gate 的机器可读原因码。

## [0.16.55] - 2026-06-12

### Added
- `candidate_issue_gate.evidence` 现在包含 `publication_worktree_clean` 和 `release_draft_ok`，让维护者和自动化能直接审计 worktree 与 release draft 门禁状态。
- Next iteration Markdown report 和 candidate issue artifacts README 现在展示这两个布尔 gate evidence 字段。
- 新增 `docs/releases/v0.16.55-draft.md`，把下一版 patch release 聚焦到 candidate issue gate 的布尔判定证据。

## [0.16.54] - 2026-06-12

### Changed
- `candidate_issue_gate.evidence.release_draft_path` 现在使用 `docs/releases/v<version>-draft.md` 形式的仓库相对路径，避免 candidate issue artifacts 泄漏维护者本机绝对路径。
- 新增 `docs/releases/v0.16.54-draft.md`，把下一版 patch release 聚焦到 candidate issue gate evidence 的相对路径交接。

## [0.16.53] - 2026-06-12

### Added
- `plan_next_iteration.py` 的默认文本输出现在会把 `candidate_issue_gate.evidence` 展开为缩进列表，方便维护者在终端直接审阅 gate 判定依据。
- 新增 `docs/releases/v0.16.53-draft.md`，把下一版 patch release 聚焦到 candidate issue gate evidence 的文本输出可读性。

## [0.16.52] - 2026-06-12

### Added
- `candidate_issue_gate` 现在包含 `evidence`，记录 publication visibility、latest tag、ahead count 和 release draft issue count 等判定输入。
- Next iteration Markdown report 和 candidate issue artifacts README 现在展示 candidate issue gate evidence，方便维护者审计为什么候选 issue 创建被阻塞或需要人工审阅。
- 新增 `docs/releases/v0.16.52-draft.md`，把下一版 patch release 聚焦到 candidate issue gate 的机器可读判定证据。

## [0.16.51] - 2026-06-12

### Added
- `plan_next_iteration.py` 现在输出 `candidate_issue_gate`，用 `blocked_by_publication`、`review_required` 和 `ready` 区分候选 issue 创建前的硬性发布门控与人工审阅门控。
- Candidate issue artifacts 的 `artifact-manifest.json`、`publication-handoff.json` 和 `README.md` 现在同步展示 `candidate_issue_gate`、`can_create_issues` 和 required actions。
- 新增 `docs/releases/v0.16.51-draft.md`，把下一版 patch release 聚焦到 candidate issue 创建门控的机器可读交接。

## [0.16.50] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `review_checklist`，让候选任务产物包的放行审阅步骤也能被工具读取。
- 新增 `docs/releases/v0.16.50-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的机器可读审阅清单。

## [0.16.49] - 2026-06-12

### Added
- `artifact-manifest.json` 的 `validation_commands` 现在包含 `python scripts/release_readiness.py --target-version <version> --json`，让候选任务产物包直接给出 release gate 复核命令。
- 新增 `docs/releases/v0.16.49-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 release readiness 验证命令。

## [0.16.48] - 2026-06-12

### Added
- `artifact-manifest.json` 的 `validation_commands` 现在包含 `python scripts/check_release_publication.py --json`，让候选任务产物包直接给出发布可见性复核命令。
- 新增 `docs/releases/v0.16.48-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 publication audit 验证命令。

## [0.16.47] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `schema_version: 1`，让维护脚本能先识别 candidate issue artifacts manifest 的字段语义。
- 新增 `docs/releases/v0.16.47-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 schema version。

## [0.16.46] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `issue_artifacts_command`，让候选任务产物包的机器可读入口也能直接展示重新生成同一批 artifacts 的命令。
- 新增 `docs/releases/v0.16.46-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的复现命令。

## [0.16.45] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `release_draft_path` 和 `release_draft_issues`，让候选任务产物包的机器可读入口也能直接展示下一版 release draft handoff。
- 新增 `docs/releases/v0.16.45-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 release draft handoff 摘要。

## [0.16.44] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `publication_ref_context`、`publication_worktree_clean`、`publication_worktree_status` 和 `publication_publish_script_command`，让候选任务产物包的机器可读入口也能直接展示发布 refs、worktree 和发布脚本生成命令。
- 新增 `docs/releases/v0.16.44-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 publication context 摘要。

## [0.16.43] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `publication_ok`、`publication_visibility`、`publication_next_actions` 和 `publication_publish_commands`，让候选任务产物包的机器可读入口也能直接展示发布可见性与推送命令。
- 新增 `docs/releases/v0.16.43-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 publication 摘要。

## [0.16.42] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `blockers` 和 `next_actions`，让候选任务产物包有单文件可读的交接摘要。
- 新增 `docs/releases/v0.16.42-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的 blocker/next action 摘要。

## [0.16.41] - 2026-06-12

### Added
- `artifact-manifest.json` 现在包含 `candidate_count` 和 `candidate_cases`，让维护者和工具无需读取 issue metadata 也能快速识别本批 candidate artifacts 覆盖范围。
- 新增 `docs/releases/v0.16.41-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts manifest 的候选案例摘要。

## [0.16.40] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 现在会写出 `artifact-manifest.json`，列出 candidate issue artifacts 的文件名、review order 和 validation commands。
- 新增 `docs/releases/v0.16.40-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的结构化 manifest。

## [0.16.39] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 现在会写出 `release-draft-handoff.json`，把 target version、release draft path 和 release draft issues 作为结构化 artifact 交给维护者和工具读取。
- 新增 `docs/releases/v0.16.39-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的结构化 release draft handoff。

## [0.16.38] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会展示 `Release Draft Handoff`，包含下一版草案路径和 release draft issues。
- 新增 `docs/releases/v0.16.38-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 release draft handoff。

## [0.16.37] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会在 `Publication Handoff` 中展示 `visibility_summary`，维护者不用打开 `publication-handoff.json` 也能看到发布可见性原因。
- 新增 `docs/releases/v0.16.37-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 publication visibility summary。

## [0.16.36] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在会输出 `publication_visibility`，并在 Markdown plan、`publication-handoff.json` 和 candidate artifacts `README.md` 中展示发布可见性状态与 summary。
- 新增 `docs/releases/v0.16.36-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publication visibility 结论字段。

## [0.16.35] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在会输出 `publication_ref_context`，并在 Markdown plan、`publication-handoff.json` 和 artifacts `README.md` 中展示 publication latest tag、local HEAD 和 tag commit 等上下文。
- 新增 `docs/releases/v0.16.35-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publication ref context 交接。

## [0.16.34] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在会输出 `publication_worktree_clean` / `publication_worktree_status`，并在 Markdown plan、`publication-handoff.json` 和 artifacts `README.md` 中展示 publication worktree 状态。
- 新增 `docs/releases/v0.16.34-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publication worktree 状态交接。

## [0.16.33] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 的 JSON、文本和 Markdown report 现在会展示 `worktree_clean` / `worktree_status`，dirty worktree 时优先提示清理本地改动并收敛 `publish_commands`。
- 新增 `docs/releases/v0.16.33-draft.md`，把下一版 patch release 聚焦到 publication audit 的 worktree 状态可见性。

## [0.16.32] - 2026-06-12

### Added
- `scripts/check_release_publication.py --publish-script` 生成的发布脚本现在会在 push 前运行 `git status --porcelain`，当 worktree 有未提交改动时拒绝执行。
- 新增 `docs/releases/v0.16.32-draft.md`，把下一版 patch release 聚焦到 publish script 的 dirty worktree 保护。

## [0.16.31] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 的 publication report 现在包含 `repo_root`，生成的 publish script 会先进入该仓库根目录并校验 `git rev-parse --show-toplevel`，避免从错误目录执行时作用到错误工作区。
- 新增 `docs/releases/v0.16.31-draft.md`，把下一版 patch release 聚焦到 publish script 的 repo root 固定。

## [0.16.30] - 2026-06-12

### Added
- `scripts/check_release_publication.py --publish-script` 生成的发布脚本现在会在 push 前执行本地 stale preflight，确认 HEAD、latest tag 和 tag commit 仍与脚本生成时一致。
- 新增 `docs/releases/v0.16.30-draft.md`，把下一版 patch release 聚焦到 publish script 的过期脚本保护。

## [0.16.29] - 2026-06-12

### Added
- `scripts/check_release_publication.py --publish-script` 生成的发布脚本现在会带 `Publication context` 注释，展示 branch、tag、HEAD、ahead/behind 和 remote check 状态，方便维护者审阅脚本是否对应当前本地 release。
- 新增 `docs/releases/v0.16.29-draft.md`，把下一版 patch release 聚焦到 publish script 的发布上下文注释。

## [0.16.28] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 `issue-metadata.json` 现在为每个 candidate 增加 `issue_body_name`，方便下游工具不解析绝对路径也能定位 body 文件。
- 新增 `docs/releases/v0.16.28-draft.md`，把下一版 patch release 聚焦到 candidate issue metadata 的 body 文件名字段。

## [0.16.27] - 2026-06-12

### Changed
- `scripts/plan_next_iteration.py` 生成的 candidate issue body 现在会把 candidate commands 和 offline validation commands 渲染为 `Reproduction Context` 下的子列表，提升 GitHub issue 可读性。
- 新增 `docs/releases/v0.16.27-draft.md`，把下一版 patch release 聚焦到 candidate issue body 的复现命令层级。

## [0.16.26] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会在 `Publication Handoff` 中展示 `Publication Publish Script` 命令，方便维护者先生成并审阅发布脚本。
- 新增 `docs/releases/v0.16.26-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 publish script 入口。

## [0.16.25] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 审阅清单现在要求先确认 `Publication Next Actions` 已处理或明确延后，再运行 `create-issues.sh`。
- 新增 `docs/releases/v0.16.25-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 publication next actions 审阅门禁。

## [0.16.24] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会在 `Publication Handoff` 中展示 `Publication Next Actions`，让维护者不用打开 JSON 也能看到具体发布阻塞。
- 新增 `docs/releases/v0.16.24-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts README 的 publication next actions 可见性。

## [0.16.23] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 JSON、文本和 Markdown report 现在会输出 `publication_next_actions`，直接透传 publication audit 的具体发布待办。
- `scripts/plan_next_iteration.py --issues-dir` 写出的 `publication-handoff.json` 现在包含 `publication_next_actions`，方便候选 issue 派发前审阅发布阻塞。
- 新增 `docs/releases/v0.16.23-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publication audit 待办交接。

## [0.16.22] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 JSON、文本和 Markdown report 现在会输出 `release_draft_issues`，把下一版 release draft 缺失或 snippet 校验失败的具体原因直接带到周初计划里。
- 新增 `docs/releases/v0.16.22-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 release draft 诊断细节。

## [0.16.21] - 2026-06-12

### Changed
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 中，`Candidate Summary` 表现在包含每个 candidate 对应的 issue body 文件名。
- 新增 `docs/releases/v0.16.21-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 摘要表的 body 文件入口。

## [0.16.20] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在包含 `Candidate Summary` 表，展示每个 candidate 的 target URL、candidate commands 数量和 offline validation commands 数量。
- 新增 `docs/releases/v0.16.20-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的 README 候选摘要表。

## [0.16.19] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 artifacts `README.md` 现在会要求维护者审阅 `issue-metadata.json` 中的 target URL、candidate commands 和 offline validation commands。
- 新增 `docs/releases/v0.16.19-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的 metadata 复现字段审阅清单。

## [0.16.18] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 `issue-metadata.json` 现在包含 `target_url`、`commands` 和 `offline_commands`，方便维护者机器可读地审阅候选 issue 复现上下文。
- 新增 `docs/releases/v0.16.18-draft.md`，把下一版 patch release 聚焦到 candidate issue metadata 的结构化复现上下文。

## [0.16.17] - 2026-06-12

### Changed
- `scripts/plan_next_iteration.py --issues-dir` 生成的 `create-issues.sh` 在 publication preflight 失败时会把 `/tmp/cliany-issue-publication-check.json` 打印到 stderr 后退出。
- 新增 `docs/releases/v0.16.17-draft.md`，把下一版 patch release 聚焦到 candidate issue script 的 publication preflight 失败可读性。

## [0.16.16] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 现在写出 `publication-handoff.json`，把 publication 状态、next actions 和 publish commands 放进候选 issue artifacts。
- 新增 `docs/releases/v0.16.16-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的 publication handoff。

## [0.16.15] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 生成的 `create-issues.sh` 现在会先运行 `python scripts/check_release_publication.py --strict --json`，在最新本地 release 尚未公开可见时阻止继续创建候选 issue。
- 新增 `docs/releases/v0.16.15-draft.md`，把下一版 patch release 聚焦到 candidate issue artifacts 的 publication preflight。

## [0.16.14] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 生成的 candidate issue body 现在包含 `Reproduction Context`，带上 target URL、candidate commands 和 offline validation commands。
- 新增 `docs/releases/v0.16.14-draft.md`，把下一版 patch release 聚焦到 candidate issue body 的复现上下文。

## [0.16.13] - 2026-06-12

### Added
- `scripts/validate_cases.py --report` 现在输出 `Candidate Handoff Matrix`，把 candidate 的 target URL、推荐命令和离线验证命令集中成贡献者交接表。
- 新增 `docs/releases/v0.16.13-draft.md`，把下一版 patch release 聚焦到 candidate 案例 handoff matrix。

## [0.16.12] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在输出 `publication_publish_script_command`，周初计划可直接给出生成 `/tmp/cliany-publish-release.sh` 的命令。
- 新增 `docs/releases/v0.16.12-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的 publish script 生成命令。

## [0.16.11] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 新增 `--publish-script`，可把 `publish_commands` 写成可审阅的可执行 shell 脚本，便于维护者手动发布 branch/tag 后复核远端 refs。
- 新增 `docs/releases/v0.16.11-draft.md`，把下一版 patch release 聚焦到 release publication publish script artifact。

## [0.16.10] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 现在会把 publication audit 的 `publish_commands` 带入 `publication_publish_commands`，周初计划可直接展示 branch/tag push 和远端复核命令。
- 新增 `docs/releases/v0.16.10-draft.md`，把下一版 patch release 聚焦到 next iteration plan 的发布交接命令。

## [0.16.9] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 现在输出 `publish_commands`，把需要维护者审阅执行的 branch/tag push 和远端复核命令集中到 JSON、文本和 Markdown report。
- 新增 `docs/releases/v0.16.9-draft.md`，把下一版 patch release 聚焦到 release publication handoff 命令。

## [0.16.8] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --json` 现在输出 `issue_artifacts_command`，`--issues-dir` 生成的 `README.md` 也会展示同一条候选 issue artifacts 复现命令。
- 新增 `docs/releases/v0.16.8-draft.md`，把下一版 patch release 聚焦到候选 issue artifacts 可复现生成命令。

## [0.16.7] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --issues-dir` 现在会写出 `README.md`，说明 candidate issue artifacts 的文件用途、审阅清单、验证命令和 `create-issues.sh` 不会自动执行的边界。
- 新增 `docs/releases/v0.16.7-draft.md`，把下一版 patch release 聚焦到候选案例 issue artifact README。

## [0.16.6] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 新增 `--issues-dir`，可离线写出 candidate issue body 文件、`issue-metadata.json` 和可审阅的 `create-issues.sh`，帮助维护者批量创建候选案例晋级 issue。
- 新增 `docs/releases/v0.16.6-draft.md`，把下一版 patch release 聚焦到候选案例 issue artifacts 输出。

## [0.16.5] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 `candidate_promotions` 现在包含 `issue_title` 和 `issue_labels`，Markdown report 新增 `Candidate Issue Metadata` 表，便于维护者直接创建候选案例晋级 issue。
- 新增 `docs/releases/v0.16.5-draft.md`，把下一版 patch release 聚焦到计划器生成候选案例 issue 标题和标签。

## [0.16.4] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py` 的 `candidate_promotions` 现在包含可复制 `issue_body`，Markdown report 新增 `Candidate Issue Body Templates` 小节，帮助维护者把候选案例晋级拆成 GitHub issue。
- 新增 `docs/releases/v0.16.4-draft.md`，把下一版 patch release 聚焦到计划器生成候选案例 issue 模板。

## [0.16.3] - 2026-06-12

### Added
- `scripts/plan_next_iteration.py --json` 和 `--report` 现在输出 `candidate_promotions` / `Candidate Promotion Tasks`，直接列出 candidate 案例晋级所需的 `adapter_package`、`metadata_validation` 和 `online_smoke` 证据。
- 新增 `docs/releases/v0.16.3-draft.md`，把下一版 patch release 聚焦到计划器中的 candidate 晋级任务表。

## [0.16.2] - 2026-06-12

### Added
- 新增 `scripts/plan_next_iteration.py`，聚合 release readiness、publication audit、commit cadence 和 candidate cases，为下个版本输出可执行推荐切片、JSON 和 Markdown 报告。
- 新增 `docs/releases/v0.16.2-draft.md`，把下一版 patch release 聚焦到维护者下个迭代计划入口。

## [0.16.1] - 2026-06-12

### Changed
- `scripts/validate_cases.py --packages-dir ... --report` 的包校验失败现在会输出 `next_actions`，帮助维护者定位 domain、metadata schema、hash 或缺失文件问题。

## [0.16.0] - 2026-06-12

### Changed
- 案例库新增结构化 `validation.offline_commands`，`scripts/validate_cases.py --report` 会汇总每个案例的离线验证命令，便于 PR 和 release 复盘直接复制。

## [0.15.9] - 2026-06-12

### Changed
- `Real Demo Case Proposal` issue 模板现在包含 candidate 晋级证据字段，并指向 `Candidate Promotion Tasks` / `Issue Body Template`，让外部案例提案沿用后续 active 晋级结构。

## [0.15.8] - 2026-06-12

### Changed
- `scripts/validate_cases.py --report` 的 `Candidate Promotion Tasks` 现在会为每个 candidate 输出可复制的 `Issue Body Template`，包含任务、验收证据和非目标边界。

## [0.15.7] - 2026-06-12

### Changed
- `scripts/validate_cases.py --report` 现在会输出 `Candidate Promotion Tasks` 小节，把 candidate 案例的 `promotion` 清单转成可复制的 GitHub issue 任务。

## [0.15.6] - 2026-06-12

### Changed
- 候选案例文档和 Good First Issues 现在把 `adapter_package`、`metadata_validation`、`online_smoke` 拆成独立可验收子任务，帮助贡献者推进 candidate 案例晋级 active。

## [0.15.5] - 2026-06-12

### Changed
- `docs/module-ownership.md` 的 Release operations 行现在纳入 `scripts/check_release_publication.py` 和 `tests/test_release_publication.py`，让贡献者能从模块地图找到发布可见性检查。

## [0.15.4] - 2026-06-12

### Changed
- README 双语路线图入口现在会提示 `scripts/check_release_publication.py --json`，让维护者在选择下一块发布切片时同时确认最新本地 tag 是否公开可见。

## [0.15.3] - 2026-06-12

### Added
- `scripts/check_release_publication.py` 新增 `--report`，可生成 release publication Markdown 报告，保存 branch/tag 发布可见性、refs 和 next actions。
- 新增 `docs/releases/v0.15.3-draft.md`，把下一版 patch release 聚焦到发布可见性报告 artifact。

## [0.15.2] - 2026-06-12

### Added
- 新增 `scripts/check_release_publication.py`，用于检查最新本地 release commit/tag 是否已经被 upstream 或远端 refs 看见，并输出可执行 `next_actions`。
- 新增 `docs/releases/v0.15.2-draft.md`，把下一版 patch release 聚焦到发布可见性检查，避免本地 tag 与公开 GitHub/PyPI 发布状态脱节。

## [0.15.1] - 2026-06-12

### Added
- 新增 `docs/releases/v0.15.1-draft.md`，把下一版 patch release 聚焦到 candidate 案例晋级路径和包名提示去版本漂移。

### Changed
- candidate 案例的 `promotion.adapter_package` 现在要求使用 `<domain>-<version>.cliany-adapter.tar.gz` 占位格式，避免发布后继续保留上一轮固定版本提示。
- `cases/manifest.json` 中 PyPI、npm 和 crates.io 候选案例的晋级包名提示改为 `<version>` 占位，便于后续任意 release train 复用。

## [0.15.0] - 2026-06-12

### Added
- 新增 `docs/releases/v0.15.0-draft.md`，把下一版 minor release 聚焦到 10 分钟成功路径、doctor 下一步提示和 demo adapter 静态验证闭环。

### Changed
- `doctor --json` 的 `data.summary` 现在包含 `demo_adapter_quickstart` 命令清单，human 输出也会展示 demo adapter 安装、list、verify 和只读执行路径。
- 官网首页和文档页的 quickstart 现在明确展示 `10 分钟成功路径`，优先引导用户安装、验证并执行真实 demo adapter，而不是先配置 LLM 后 explore。
- `release_readiness.py` 的项目元数据 gate 现在会检查官网首页和官网 docs 是否保留 10 分钟成功路径，防止网站入口退回旧 quickstart。
- `release_readiness.py` 的项目元数据 gate 现在会检查 `docs/quickstart-10min.md` 是否保留 doctor、demo adapter install/verify/只读命令和无 LLM key 分叉提示。
- `docs/release-cadence.md` 现在说明 minor release 应使用 `release_readiness.py --target-version 0.15.0` 跟踪目标版本，避免默认下一 patch 草案与路线图目标脱节。
- `release_readiness.py --release-tag` 现在要求目标 tag 指向当前 HEAD，避免在 tag 后继续提交时误把后续工作区当作已打 tag 的发布状态。

## [0.14.4] - 2026-06-12

### Added
- 案例库新增 `candidate` 状态和 `pypi-project-search` 候选案例，用离线 JSON 样例承接真实公开只读工作流，待 adapter 包准备好后再晋级 active。
- 案例库新增 `npm-package-search` 候选案例，用离线 JSON 样例覆盖 JavaScript 包注册表搜索场景。
- 案例库新增 `crates-io-crate-search` 候选案例，用离线 JSON 样例覆盖 Rust 包注册表搜索场景，并把真实案例资产推进到 8 个。
- 新增 `docs/module-ownership.md`，把 owner area、主要路径、典型改动和最小验证命令整理成贡献者模块地图。
- 新增 `docs/weekly-maintainer-loop.md`，把路线图、release readiness、案例库验证和发布节奏串成每周选题、实现、复盘的维护者循环。
- 新增 `docs/good-first-issues.md`，把首次贡献任务整理成默认离线、带验证命令的候选池。
- 新增 GitHub `Real Demo Case Proposal` issue 模板，引导外部用户提交可验证、只读、带离线样例输出的真实案例候选。
- `scripts/release_readiness.py` 新增 `--report`，可生成下一版发布 readiness Markdown 摘要，便于发版复盘和 release notes 准备。
- `scripts/validate_cases.py` 新增 `--report`，可生成案例库离线验收 Markdown 报告；CI 会上传 `case-catalog-report` artifact。
- 新增 `cases/examples/*.json` 离线样例输出，让 active 真实案例在不访问第三方站点时也能展示 JSON envelope 形状和典型字段。
- 新增 `tests/fixtures/search_extraction_gap.html` 和离线回归测试，用最小 HTML 页面固定搜索结果抽取字段缺失应判为 `partial` 的 known-gap 语义。
- 新增 `docs/adapter-lifecycle.md`，固化 adapter 从生成、验证、打包、安装到回滚的生命周期，以及 `.cliany-adapter.tar.gz` 包格式和安全边界。
- 新增 `scripts/validate_cases.py`，为 `cases/manifest.json` 提供离线验收报告，并可选检查本地 demo adapter 包 manifest、声明文件哈希和 metadata schema v3 是否与案例声明匹配。
- 新增 `scripts/release_readiness.py`，聚合发布节奏、真实案例库和下一版发布草案检查，作为发版前统一本地门禁。
- 新增抽取结果质量评估，保存的 Markdown 报告会标记空结果、全空字段和部分缺字段，推进搜索/列表抽取 known-gap 的任务级验收。
- 新增 `docs/releases/v0.14.4-draft.md`，提前整理下一版 patch release 的用户价值、风险、验证命令和发版阻塞项。

### Changed
- `doctor` 的 summary 现在包含 `recommended_next_step`，human 输出会直接显示 `下一步`，帮助首次运行用户判断先跑 demo adapter、配置 LLM key 还是修复环境。
- `doctor` 的 summary 现在包含 `capabilities`，按管理已有 adapter、运行浏览器 workflow、生成新 adapter 三条路径展示 ready 状态和 blockers。
- `docs/adapter-lifecycle.md` 新增临时 HOME 的离线 roundtrip 验证流程，帮助维护者在不污染真实 `~/.cliany-site/` 的情况下检查 publish/install/verify/rollback。
- README 双语 marketplace 示例现在使用 `market publish` 实际生成的 `<domain>-<version>.cliany-adapter.tar.gz` 包名，避免复制旧包名失败。
- 案例库 candidate 状态现在要求 `promotion` 清单，明确 adapter 包、metadata 校验和在线只读 smoke 三个晋级 active 的条件。
- `scripts/validate_cases.py` 现在要求 candidate 案例声明 `example_output`，防止候选真实工作流缺少可离线展示的 JSON envelope 样例。
- `scripts/validate_cases.py` 现在会校验 `example_output.data.command` 是否匹配 manifest 中声明的业务命令，避免样例输出和案例命令漂移。
- `scripts/validate_cases.py` 现在会校验离线样例输出中的 `data.quality`，要求样例显式展示成功质量状态和正数 `row_count`。
- `scripts/validate_cases.py` 的终端输出、JSON 和 Markdown 报告现在会展示 candidate 案例的 `promotion` 晋级清单，维护者可直接从 CI artifact 判断候选案例下一步。
- `release_readiness.py` 的文本与 Markdown 报告现在会显示案例库 active/candidate/known-gap/total 汇总，发版复盘可直接看到候选案例管道。
- `release_readiness.py` 默认要求案例库至少保留 8 个 active/candidate/known-gap 资产，防止真实案例库目标在后续维护中无声回退。
- `release_readiness.py --report` 现在会输出 `Candidate Promotions` 小节，把候选案例晋级 active 的三项动作直接带入发版 readiness artifact。
- 官网 quickstart 现在暴露每周维护者循环和 `next_actions` 入口，让网站读者也能从 roadmap 进入可验证发布切片。
- README 双语路线图入口现在链接每周维护者循环，并说明 `release_readiness.py --json` / `check_release_cadence.py --json` 的 `next_actions` 可用于选择下一块可验证发布切片。
- `check_release_cadence.py --json` 现在输出 `missing_commit_days`，cadence/readiness 的 `next_actions` 会直接提示本周还差几个独立提交日。
- `check_release_cadence.py` 的 JSON 与默认文本输出现在包含 `next_actions`，单独检查每周提交节奏时也会提示下一步。
- `release_readiness.py --json` 现在会在顶层输出 `next_actions`，方便 CI、agent 或维护脚本自动读取下一步动作。
- `release_readiness.py` 的默认文本输出现在也会显示 `next_actions`，维护者不生成 Markdown 报告也能看到下一步动作。
- `release_readiness.py --report` 现在会输出 `Next Actions` 小节，把提交天数、案例库、发布草案、CI、发布 workflow、项目元数据和包校验阻塞映射为维护者下一步动作。
- `release_readiness.py --report` 现在会输出 `Weekly Review` 小节，把每周复盘问题和当前 gate 证据放在同一份 Markdown artifact 中。
- `release_readiness.py` 的项目元数据 gate 现在会校验每周维护者循环文档及 roadmap/release cadence 入口，防止持续发布机制在发版前漂移。
- `release_readiness.py` 的项目元数据 gate 现在会校验 `docs/good-first-issues.md`、README good-first-issue 入口和贡献者上手地图链接，防止首次贡献路径漂移。
- `release_readiness.py` 的项目元数据 gate 现在会校验 README 双语 marketplace 示例保留真实 `market publish` 包名，防止安装示例回退到旧格式。
- `docs/good-first-issues.md` 新增 `Issue 拆分清单`，并用文档测试要求每个候选任务保留具体文件和本地验证命令，方便维护者把任务池转成可复现的 `good first issue`。
- `docs/roadmap-2026-q3.md` 与 `docs/release-cadence.md` 现在链接每周维护者循环，帮助维护者把路线图切成可发布、可验证的小版本。
- 官网 quickstart 现在在首次成功路径后提示 `docs/good-first-issues.md`，把首次贡献者引导到默认离线、可本地验证的任务池。
- 官网 quickstart 现在在首次成功路径后提示 `Real Demo Case Proposal`，把公开只读真实工作流引导到案例库贡献和离线验收路径。
- `release_readiness.py` 的项目元数据 gate 现在会校验 README 双语首页是否保留 10 分钟成功路径、抽取质量、release readiness 和真实案例贡献入口。
- `README.md` / `README.zh.md` 的 quickstart 入口现在说明首次成功后可通过 `Real Demo Case Proposal` 贡献新的公开只读真实案例。
- `docs/quickstart-10min.md` 新增首次成功后的贡献路径，指向 `Real Demo Case Proposal`、`cases/manifest.json`、`cases/examples/` 和案例库离线验收命令。
- `docs/contributor-starter.md` 新增 Issue 与 PR 模板入口，说明 bug、feature、真实 demo 候选和 PR 提交分别应准备的可复现信息。
- `release_readiness.py` 的项目元数据 gate 现在会校验 GitHub PR 模板、issue 模板与 issue template config 是否存在且包含关键字段，避免关键开源协作入口和安全上报入口在发版前漂移。
- `.github/PULL_REQUEST_TEMPLATE.md` 更新为按改动类型提示案例库、release readiness 和零密钥 PR 门禁验证，减少贡献者跑错检查的概率。
- `docs/release-cadence.md` 新增 readiness 报告排障流程，要求维护者优先读取 `Gate Issues` 并逐项关闭 gate 失败原因。
- `docs/contributor-starter.md` 的发布脚本验证路径改为优先使用 `release_readiness.py` 总入口，并用测试固定贡献者文档不会退回单点 cadence 检查。
- `release_readiness.py --report` 现在会在 Markdown 报告中列出各 gate 的具体失败原因，CI artifact 可直接用于定位发版阻塞项。
- `release_readiness.py` 新增项目元数据 gate，发布前会校验 PyPI `description` / `readme` / project URLs，以及 LICENSE、贡献、安全和支持入口文件。
- `.github/workflows/release.yml` 在发布构建前清理 `dist/`，并在 `uv build` 后运行 `uvx twine check dist/*` 校验本次 wheel/sdist 元数据。
- `pyproject.toml` 新增 PyPI `description` 和 `readme` 元数据，让发布包包含 README long description。
- `release_readiness.py --release-tag` 支持校验已打 tag 的发布状态，避免 tag workflow 把当前 tag 误判成“下一版”。
- `.github/workflows/release.yml` 在构建和发布前新增 `Release Preflight`，会运行 `release_readiness.py --strict --release-tag ... --report`，防止 tag 发布绕过 readiness 门禁。
- `scripts/release_readiness.py` 现在会校验 `.github/workflows/release.yml` 的 tag 触发、CI 复用、构建、GitHub Release 和 PyPI 发布链路，避免正式发版 workflow 漂移。
- CI 新增 `Release Readiness Report` job，在 PR/主分支生成并上传 `release-readiness-report` artifact，便于持续观察下一版发版阻塞项。
- `scripts/validate_cases.py` 现在要求 active 案例声明 `example_output`，并校验样例路径、JSON envelope、`meta.case_id` 和非空 `data.results`。
- `scripts/check_release_cadence.py` / `scripts/release_readiness.py` 现在会校验 `CHANGELOG.md` 的 `[Unreleased]` compare 链接是否从最新 tag 指向 `HEAD`，避免发布说明范围漂移。
- `scripts/validate_cases.py` 现在会检查 `cases/manifest.json` 中 `docs` 的 Markdown 锚点和 active 案例命令域名一致性，避免真实案例链接或命令漂移。
- `docs/releases/v0.14.4-draft.md` 新增案例库映射，release notes 会链接 `cases/README.md`、`cases/manifest.json` 和 `search-extraction-gap` 离线复现。
- `scripts/release_readiness.py` 新增 `--require-packages`，正式发版前可强制要求 `--packages-dir` 完成 demo adapter 包离线校验。
- `README.md` / `README.zh.md` 同步 v0.14.4 抽取质量与 release readiness 入口，说明 `data.quality`、`--strict-quality` 和 `E_EMPTY_RESULT` 的用户含义。
- `scripts/release_readiness.py` 新增 CI release gate 检查，发布前会确认案例库和抽取质量回归 job 仍在默认 CI 中。
- CI 新增 `Extract Quality Regression` job，在零真实 LLM key 环境中显式运行抽取质量、结构化 `browser extract` 和生成数据命令回归。
- 生成 adapter 的 JSON 输出新增 `data.quality` 汇总，并修复 extract 步骤调用 `browser extract --mode` 时内置命令不识别该参数的问题。
- `browser extract --mode ... --json` 在结构化提取时新增 `data.quality`，便于手动调试 list/table/attribute 结果是否为空或字段缺失。
- `browser extract --mode ... --strict-quality` 可在结构化提取质量未通过时返回 `E_EMPTY_RESULT`，便于本地脚本和 CI 将空抽取或关键字段缺失判为失败。
- 生成的 `list-` / `search-` 数据命令现在会在抽取质量为 `empty` 或 `partial` 时返回 `E_EMPTY_RESULT`，避免“命令成功但字段为空或缺失”的误判。
- 官网 Quick Start 同步 v0.14.3 首次成功路径：先运行 `doctor` 摘要和真实 demo adapter，再配置 LLM 生成自定义命令。
- CI 新增 `Case Catalog Validation` job，在 PR/主分支默认离线运行 `scripts/validate_cases.py --strict` 与案例库结构测试，防止真实案例索引漂移。
- `market install` 收紧包内容校验：拒绝缺失声明文件、缺失哈希和未声明额外文件，并在覆盖安装前先完成完整校验，避免坏包产生无意义备份。
- `market install --json` 对安装失败返回 `INSTALL_FAILED` 和针对性 `error.fix`，覆盖重复安装、哈希不匹配、manifest 缺失字段、未声明文件与不安全路径场景。
- `verify --json` 在已安装 adapter 存在 `manifest.json` 时新增 manifest v1、domain、files/file_hashes 和已安装文件哈希诊断；无 market manifest 的本机 adapter 会标记为 `manifest.status = "missing"` 但不判定失败。

## [0.14.3] - 2026-06-10

### Added
- 新增 `docs/roadmap-2026-q3.md`，基于 v0.2~v0.14 迭代轨迹制定 2026 Q3 路线图，聚焦新用户可用性、真实案例库、adapter 生命周期、贡献者入口与运行可靠性。
- 新增 `docs/release-cadence.md`，固化每周至少 1 个版本、每周至少 3 天提交记录的发布与提交节奏。
- 新增 `cases/manifest.json` 与 `cases/README.md`，把 v0.14 真实 demo 和搜索抽取短板复盘沉淀为可维护案例库，并新增离线结构校验测试。
- 新增 `docs/quickstart-10min.md`，提供不依赖 LLM key 的 demo adapter 首次成功路径，以及生成自定义 adapter 的后续路径。
- `doctor --json` 新增 `data.summary` 分层行动建议，并为每个 check 补充 `severity` 与 `action` 字段，帮助新用户区分必须修复、建议优化和诊断信息。
- `doctor` 非 JSON 输出新增面向人的摘要视图，按“必须修复 / 建议处理 / 诊断信息”展示行动项。
- 新增 `scripts/check_release_cadence.py`，本地检查版本 tag、本周提交天数、CHANGELOG Unreleased 和工作区状态；`scripts/publish.sh` 改为优先使用 `PYPI_TOKEN` 环境变量。
- 新增 `docs/contributor-starter.md`，提供 good-first-issue 清单、模块地图、复现问题最小包和按风险选择验证范围的贡献者入口。

### Verification
- `.venv/bin/python -m pytest tests/test_doctor.py tests/test_doctor_checks.py tests/test_doctor_v3.py tests/test_obscura_integration_entrypoints.py tests/test_cases_manifest.py tests/test_release_cadence.py tests/test_contributor_docs.py -q --no-cov`
- `.venv/bin/ruff check src/cliany_site/commands/doctor.py scripts/check_release_cadence.py tests/test_doctor_v3.py tests/test_cases_manifest.py tests/test_release_cadence.py tests/test_contributor_docs.py`

## [0.14.2] - 2026-06-10

### Added
- **自主改进闭环基础设施**：新增 5 个维度的自主改进脚手架，使 OpenCode 可触发自主演进循环。
  - **维度1 确定性回归**：`tests/benchmarks/` 基线数据集（2 场景）+ `_parse_llm_response` / `_sanitize_actions_data` / `AdapterGenerator.generate` 三层回归测试 + 哨兵有效性闭环验证，零真实 LLM。
  - **维度2 运行时反馈**：扩展 `bug_report.yml` 新增 5 个结构化字段（target_url / error_code / axtree_snapshot / cliany_version / doctor_output）+ `auto-reproduce` label 触发的复现 workflow。
  - **维度3 具身浏览器验证**：`tests/embodied/` headless Chromium + CDPConnection + AXTree 集成测试，配套独立 `embodied-ci.yml` CI job。
  - **维度4 依赖哨兵**：`.github/dependabot.yml`（pip + github-actions，weekly）+ `dep-upgrade-verify.yml` 依赖升级验证 workflow。
  - **维度5 Agent 守则**：根 `AGENTS.md` 与包级 `src/cliany_site/AGENTS.md` 新增「AUTONOMOUS IMPROVEMENT GUARDRAILS」章节 + `.github/AUTONOMOUS_FIX.md` 自主修复协议总文档。
- **benchmark 回归并入 PR 门禁**：`ci.yml` 新增 `benchmark-regression` job（零密钥，`CLIANY_QA_OFFLINE=1`，`timeout-minutes: 10`）。

## [0.14.1] - 2026-05-28

### Added
- **3 个新错误码**：`E_PAGE_NOT_READY`（页面未就绪超时）、`E_PARSE_FAILED`（解析异常）、`E_EMPTY_RESULT`（空结果，list-/search- opt-in），统一"空结果 vs 显式失败"语义。
- **list-/search- 命令空结果检测**：生成器模板新增 opt-in 空结果 guard，防止静默空返回。
- **Obscura 友好错误提示**：explore/login 在 Obscura provider 下返回结构化友好提示，包含 `suggested_action` 和文档链接。
- **ADR-0008**：`docs/decisions/0008-failure-semantics.md` — 失败语义决策记录。
- **ADR-0009**：`docs/decisions/0009-provider-capability-matrix.md` — Provider 能力矩阵决策记录。
- **3 个新 qa 脚本**：`test_failure_semantics.sh`（4 场景）、`test_doctor_agent_md.sh`（2 场景）、`test_obscura_explore_friendly.sh`（2 场景）。

### Fixed
- **navigate/extract/action_runtime 失败语义**：readiness timeout 和解析异常统一返回 `ok=false` + 对应错误码，而非静默空结果。
- **doctor agent_md 双文件名检查**：同时识别 `AGENT.md` 和 `AGENTS.md`，sentinel 缺失时仅提示不重生成。
- **Obscura 能力声明修正**：`ObscuraProvider` 正确声明 `supports_navigation=False` / `supports_cookies=False`，与实际行为一致，修复 login feature gate 不拦截导致的挂起问题。
- **CDP 日志降噪**：`cdp_use.client` logger 设为 ERROR 级别，消除探索过程中的 WARNING 噪声。



### Added
- **4개 공개 데모 사이트 adapter 자산**: SuiteCRM Demo, ASF Jira, ASF Confluence, ASF Jenkins(builds.apache.org). GitHub Release v0.14.0 assets에 탑재.

### Changed
- **官网 "Real-World Use Cases" 섹션**: Case 2(기업 CRM) · Case 3(팀 도구함) 카드에서 CONCEPT 배지 제거, 실제 공개 데모 사이트 명령어 및 i18n 문案으로 교체.

### Docs
- **README.md / README.zh.md**: "Try Real Demos" 단락 추가, 제3자 유지 demo 사이트 disclaimer 포함.

## [0.13.0] - 2026-05-25

### Fixed
- **[Bug] loader.py::load_or_rebuild 未捕获 RuntimeError**：`build_manifest()` 调用现在被 `try/except` 包裹，异常时记录 `logger.warning` 并回退为空 manifest，不再向上传播
- **[Flaky] test_session_lock 不稳定测试修复**：改用 `patch.object(logger, "error")` 替代 caplog，测试确定性提升

### Added
- **doctor 命令增强**：新增 `versions` 检查项（Python 版本、cliany-site 版本、click/anthropic/openai 依赖版本）和 `adapter_stats` 检查项（adapter 数量、命令总数）
- **ERROR_FIX_HINTS 补全**：为 `ErrorCode` 类的所有 `E_*` 前缀常量（共 27 个）补充用户友好的修复提示

### Changed
- **envelope.py TypedDict 分离**：新增 `SuccessEnvelope`（`ok: Literal[True]`）和 `ErrorEnvelope`（`ok: Literal[False]`）分离 TypedDict；`Envelope` 保留为 Union 别名，向后兼容
- **核心模块 pyright strict**：`errors.py`、`response.py`、`atomic_io.py`、`envelope.py`、`loader.py` 进入 pyright strict 模式，0 errors

## [0.12.0] - 2026-05-21

### Fixed
- **[보안] tar 경로 순회 차단** (`tui/screens/adapter_list.py`): 악성 `.tar.gz` 임포트 시 경로 이탈 방지, `UnsafeArchiveError` 추가 (commit bbb13d6)
- **[안정성] binary/process.py PID 파일 경쟁 조건 수정**: portalocker 배타 락 + NamedTemporaryFile + os.replace()로 원자적 쓰기 보장 (commit 3924c00)
- **[안정성] loader.py manifest 경쟁 조건 수정**: portalocker.Lock + threading.RLock + 원자 쓰기로 동시 접근 안전성 확보 (commit e903f44)
- **[안정성] codegen/merger.py fsync 누락 수정**: flush + fsync + 디렉터리 fsync로 전력 이상 시 데이터 손실 방지 (commit 9b236cd)
- **[안정성] obscura 다운로드 재시도 없음 수정**: 지수 백오프 3회 재시도 구현, HTTPError/URLError 예외 계층 올바르게 처리 (commit 6e8c713)
- **[안정성] session.py / atomic_io.py 파일 락 및 로그 누락 수정**: portalocker + mkstemp + fdopen + fsync 패턴 적용, 파싱 실패 시 에러 로그 추가 (commit 74ee847)

### Changed
- **explorer/interactive.py 연쇄 except 세분화**: 브로드 Exception 블록을 구체적 예외 타입(AttributeError, RuntimeError, asyncio.TimeoutError 등)으로 분리, logger.extra 컨텍스트 필드 추가 (commit 60a9b59)
- **errors.py 에러 코드 통일**: `LOCK_TIMEOUT`, `UNSAFE_ARCHIVE` 2개 에러 코드 추가(후방 호환), ERROR_FIX_HINTS 힌트 메시지 보완 (commit 5bf36c4)

### Added
- **pytest-cov 및 portalocker 의존성 추가**: v0.12 가딩 작업 기반 인프라 (commit 5980712)
- **CI coverage 리포트**: GitHub Actions에 pytest-cov 플래그 + artifact 업로드 추가 (commit bff9074)
- **가관측성 단언 테스트 4종**: 로깅 마스킹, JSONFormatter, ERROR_FIX_HINTS 커버리지, envelope ok/success 호환성 (commit e4eb52c)
- **action_runtime.py 분기 커버리지 보완**: `_resolve_action_node`, `_attempt_adaptive_repair` 등 9개 분기 테스트 추가 (commit 74ee847)
- **성능 마이크로 벤치마크**: `tests/perf/` 디렉터리에 pytest-benchmark 기반 P95 회귀 임계값 테스트 추가 (commit 26ebc82)

### Internal
- **ADR-0007 안정성 가딩 결정 기록**: `docs/decisions/0007-v012-stability-hardening.md` 신규 작성 (commit 046cbcc)

## [0.11.0] - 2026-05-12

### Obscura 实验性浏览器后端集成
- **核心功能**：
  - 新增浏览器提供者抽象层（Browser Provider Abstraction），支持能力快照（Capability Snapshot）与特性门禁（Feature Gate）。
  - 新增 `ObscuraProvider` 与 `ChromeProvider` 包装层，Chrome 保持为默认提供者。
  - 显式启用方式：设置环境变量 `CLIANY_BROWSER_PROVIDER=obscura`。
  - **注意**：`explore` 命令在 Obscura 下已被门禁（Gated），目前不宣称完全支持。
- **Obscura 生命周期管理**：
  - 增加 `cliany-site obscura` 命令组：支持 `install/use/status/clean/rollback/upgrade/doctor`。
  - 实现二进制文件生命周期：包括 Manifest 管理、本地缓存、原子安装（Atomic Install）、Active 指针切换、回滚支持及进程管理器。
- **多平台支持**：
  - 支持 `darwin-arm64` (Apple Silicon), `darwin-x86_64` (Intel Mac), `linux-x86_64`, `windows-x86_64`。
- **测试与质量保证**：
  - 建立 Smoke（冒烟）、Compat（兼容性）、Benchmark（基准）三层测试体系。
  - 集成 CI Release Gates，确保发布质量。
- **文档与工程**：
  - 新增相关 ADR（决策记录）与 Obscura Experimental Guide 实验性指南。

## [0.10.0] - 2026-05-07

### BREAKING 变更
- **metadata schema v3 硬切换**：schema_version 2 及以下 adapter 标记为 legacy，需通过 `cliany-site migrate` 重新迁移或重新 explore 生成。

### 新功能（借鉴自 opencli）
- **DOM 剪枝 + 复合控件提取**（T02/T03）：AXTree 捕获时四层剪枝（深度/节点数/屏蔽角色/压缩序列），自动提取 `<select>` / `<input type=date>` / `<input type=file>` 的选项元数据，减少 prompt token 消耗 30%~50%。
- **Lazy Adapter Registry**（T05/T06）：`LazyAdapterRegistry` 替代全量 import，`discover()` 仅读 `metadata.json`，`get(domain, cmd)` 按需 `importlib.import_module()`，加快 CLI 启动 2~5x。
- **Repair Cache（修复缓存）**（T10）：heal 结果写入 `~/.cliany-site/adapters/{domain}/repair-cache.json`（LRU 100 条/domain），相同故障模式命中缓存可跳过 LLM 调用。
- **Network + Console Capture**（T11）：explore 阶段自动捕获 Network 请求（>1MB 停止）和 Console 日志（500 条滚动覆盖），存入 StepRecord，供诊断/回放使用。
- **Capability Routing**（T13）：探索时嗅探 API endpoints，replay 时自动路由 browser / api 双通道，`--force-browser` flag 强制走 browser 模式。
- **migrate 命令**（T12）：`cliany-site migrate [--json] [--dry-run]` 一键扫描并迁移所有 legacy adapter 到 schema_version 3，带 `.bak` 备份。
- **Diagnostic Mode**（T20/T22/T23）：`cliany-site --diagnose --json <domain> <cmd>` 在命令失败时触发 LLM 诊断，输出 `root_cause` + `suggested_fix`；生成的 adapter 模板已内置 `diagnose_if_enabled(ctx, failed)` hook。

### 新测试
- `tests/test_v010_integration.py`：10 项集成测试（CI 可跑，不依赖 Chrome/LLM key）
- `tests/fixtures/fake_llm.py`：`FakeChatModel` 用于离线 QA（`CLIANY_QA_OFFLINE=1`）
- `qa/test_v010_e2e.sh`：端到端 shell 测试套件

### 环境变量新增
- `CLIANY_QA_OFFLINE=1`：离线 QA 模式，配合 `CLIANY_QA_FAKE_LLM_RESPONSES` 使用
- `CLIANY_QA_FAKE_LLM_RESPONSES=<path>`：FakeChatModel 的 response 文件路径
- `--force-browser`：root flag，强制 replay 走 browser 通道
- `--diagnose`：root flag，命令失败时触发 LLM 诊断

## [0.9.3] - 2026-04-30

### 文档
- README.md 默认改为英文，新增 README.zh.md（中文完整版）
- 删除旧的 README.en.md
- 官网全面英文化：默认语言改为 en、style.css 注释翻译为英文、补齐 script.js 缺失英文翻译

### 官网
- 新增 5 张 v0.9.x 功能展示 cards（Smart Self-Healing、Static Verification、Self-Describing Contract、Atom Commands System、Metadata Schema v2）
- SEO meta 同步中英语言切换

## [0.9.2] - 2026-04-28

### 修复
- 录像 AXTree bytes 序列化 + explore 命令迁移到新 envelope 格式

## [0.9.1] - 2026-04-27

### 修复
- 修复 3 个运行时回归：根级 JSON 错误信封、legacy adapter 列表过滤、verify schema 资源打包

## [0.9.0] - 2026-04-26

### BREAKING CHANGES
- **metadata schema v2 hardcut**: `schema_version` 정수 필드 필수. 구 adapter 자동 거부 + `cliany-site explore <url>` 지침 출력.
- **envelope 통일**: 모든 명령 출력이 `{ok, version, command, data, error, meta}` 형식으로 전환. `success` 키는 하위 호환 alias.

### Added
- `cliany-site browser state/navigate/find/click/type/extract/wait/screenshot/eval` — 9개 atom 명령 (zero LLM)
- `cliany-site verify [domain]` — 정적(jsonschema+AST) + `--smoke` CDP 냉간 테스트
- `cliany-site --json --explain` — Agent 자기설명 엔드포인트
- `cliany-site adapter accept-heal <domain>` — healer sidecar 적용
- `cliany-site list --legacy` — 거부된 구 adapter 목록 표시
- `cliany-site doctor` — registry/legacy/agent_md/healed_pending 체크 추가
- `./AGENT.md` 자동 생성/갱신 (sentinel+hash 이중 보호)
- `--heal` 자가치유 플래그 (LLM 비용 cap: max_calls=3, max_tokens=4000)
- `CLIANY_HEAL_DISABLE`, `CLIANY_HEAL_MAX_CALLS`, `CLIANY_HEAL_MAX_TOKENS` 환경변수
- `CLIANY_NO_AGENT_MD=1` 환경변수로 AGENT.md 자동 재작성 억제

### Changed
- `explore` 성공 시 v2 metadata 원자 쓰기 + AGENT.md 자동 재작성
- `loader` — 구 adapter 하드 거부 (이전: 경고 후 로드)
- `codegen` — generated 명령이 run_atom() 통해 atom 명령을 호출 (직접 CDP 미사용)

### Removed
- 구 metadata (`schema_version` 없거나 문자열 "1") 자동 로드 지원 종료

### Migration
구 adapter → 재생성: `cliany-site explore <url> "<workflow>"`  
자세한 마이그레이션 절차: [docs/migration-0.9.md](docs/migration-0.9.md)

## [0.8.3] - 2026-04-13

### 新增
- **sandbox 执行预检**：为适配器命令接通 `--sandbox` 执行预检流程，限制跨域导航和危险操作

### 文档
- 添加 sandbox CLI 闭环设计与计划文档
- 官网新增「真实场景」Use Cases 展示模块（案例内容打磨与精简）

### 其他
- 更新 `.gitignore` 规则

## [0.8.2] - 2026-04-08

### 新增
- **adapter 命令级断点恢复**：为生成的站点命令补齐 `--resume`，可通过 `cliany-site <domain> <command> --resume` 从最近断点继续执行

### 变更
- 生成命令会先汇总完整动作序列，再统一传入执行引擎，避免断点恢复时出现分段索引错位
- README 中的断点续执行说明已对齐到真实 CLI 入口

### 修复
- 修复 `explorer` 包级导出导致的循环导入问题，避免 codegen 相关测试在收集阶段失败
- 修复 CLI 版本测试对旧版本号的硬编码断言，改为读取包元数据

### 文档
- 添加 `--resume` 闭环设计与实现计划文档
- 添加规划差距评审与规划项对账文档

## [0.8.1] - 2026-04-03

### 新增
- **官网 Use Cases 展示模块**：在 Features 和 How It Works 之间新增「真实场景」案例展示
- 3 个案例卡片：GitHub CLI 化（真实）、企业 CRM 无 API（概念）、团队工具箱（概念）
- Before/After 标签页切换交互
- 案例 1 终端 CSS 打字动画（IntersectionObserver 触发，支持 prefers-reduced-motion）
- 完整中英双语支持，44 个 `usecases.*` i18n 键
- 响应式布局：375/900/1280px 三视口适配

### 文档
- 官网新增 Use Cases 模块完整实施 walkthrough 文档

## [0.8.0] - 2026-04-02

### 新增
- **会话式探索**：支持交互式探索 (`--interactive`)，每步 LLM 规划后暂停，支持 CONFIRM/SKIP/MODIFY/ROLLBACK
- **增量扩展探索**：支持 `--extend <domain>`，加载已有适配器 metadata 作为 LLM 上下文，实现精准补全
- **探索录像系统**：自动保存截图、AXTree 和动作序列到 `~/.cliany-site/recordings/`
- **录像回放命令**：新增 `replay <domain>` 命令，Rich 终端回放探索全过程，支持 `--step` 逐步回放
- **优雅中断保护**：Ctrl-C 中断后自动保存已探索的中间结果，支持后续合并

## [0.7.1] - 2026-04-02

### 文档
- 修复 README.md「更新日志」和「贡献指南」区块的中英双语格式

## [0.7.0] - 2026-03-31

### 新增
- **多模态感知系统**：截图 + Vision LLM 双通道感知，提升探索和元素定位成功率
- 新增 `browser/screenshot.py` 截图采集模块，支持 CDP 截图和 base64 编码
- 新增 SoM（Set-of-Mark）标注引擎，在截图上绘制带编号的元素标签
- 新增 `explorer/vision.py` 多模态消息构建模块，支持 LangChain 图文混合消息
- 新增 Vision 视觉定位能力，作为元素解析 L3 层兜底策略
- 新增 5 个 Vision 配置项：`CLIANY_VISION_ENABLED`、`CLIANY_SCREENSHOT_FORMAT`、`CLIANY_SCREENSHOT_QUALITY`、`CLIANY_VISION_MIN_CONFIDENCE`、`CLIANY_VISION_SOM_MAX_LABELS`
- 新增 `Pillow` 可选依赖组 `[vision]`，用于 SoM 图像标注
- 新增 17 个测试用例覆盖截图和 Vision 模块

### 变更
- `capture_axtree()` 在 vision_enabled 时同步采集截图数据
- `_invoke_llm_with_retry()` 支持 LangChain Message 对象（图文混合输入）
- 探索循环在 Vision 模式下自动构建多模态 prompt
- 元素解析策略扩展为 4 层：L0 直接匹配 → L1 模糊打分 → L2 自适应修复 → L3 Vision 定位

### 文档
- 添加 v0.7.0 多模态感知实施计划文档
- 添加 v0.7.0 实施 walkthrough 文档

## [0.6.2] - 2026-03-31

### 新增
- 添加完整的开源社区基础设施文件

### 文档
- 添加 MIT LICENSE（版权 pearjelly，2026）
- 添加 CONTRIBUTING.md 贡献者指南（中英双语）
- 添加 CODE_OF_CONDUCT.md 行为准则（Contributor Covenant v2.1）
- 添加 SECURITY.md 安全漏洞报告政策
- 添加 SUPPORT.md 用户支持指引
- 添加 CHANGELOG.md（Keep-a-Changelog 格式，迁移历史版本）
- 添加 .github/ISSUE_TEMPLATE/（bug report / feature request / config）
- 添加 .github/PULL_REQUEST_TEMPLATE.md
- 添加 .pre-commit-config.yaml（ruff + mypy 本地工具）
- 更新 README.md（更新日志/贡献指南改为链接外部文件）

## [0.6.1] - 2026-03-31

### 修复
- 修复 extract 在某些情况下 Page 对象获取失败的问题

## [0.5.1] - 2026-03-31

### 新增
- 添加 LLM 调用重试机制，提升网络不稳定时的探索成功率
- 新增 Extract 数据抽取动作类型，支持从页面提取结构化数据并保存为 Markdown

### 变更
- CSS Selector 候选预计算，自动生成多个 selector 候选增强元素匹配韧性
- 探索提示词注入 selector 候选，extract 空 selector 告警

### 修复
- 修复合并周期保留 selector/extract_mode/fields_map 的问题
- 修正 QA 测试断言与实际 API 对齐

[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.16.259...HEAD
[0.16.259]: https://github.com/pearjelly/cliany.site/compare/v0.16.258...v0.16.259
[0.16.258]: https://github.com/pearjelly/cliany.site/compare/v0.16.257...v0.16.258
[0.16.257]: https://github.com/pearjelly/cliany.site/compare/v0.16.256...v0.16.257
[0.16.256]: https://github.com/pearjelly/cliany.site/compare/v0.16.255...v0.16.256
[0.16.255]: https://github.com/pearjelly/cliany.site/compare/v0.16.254...v0.16.255
[0.16.254]: https://github.com/pearjelly/cliany.site/compare/v0.16.253...v0.16.254
[0.16.253]: https://github.com/pearjelly/cliany.site/compare/v0.16.252...v0.16.253
[0.16.252]: https://github.com/pearjelly/cliany.site/compare/v0.16.251...v0.16.252
[0.16.251]: https://github.com/pearjelly/cliany.site/compare/v0.16.250...v0.16.251
[0.16.250]: https://github.com/pearjelly/cliany.site/compare/v0.16.249...v0.16.250
[0.16.249]: https://github.com/pearjelly/cliany.site/compare/v0.16.248...v0.16.249
[0.16.248]: https://github.com/pearjelly/cliany.site/compare/v0.16.247...v0.16.248
[0.16.247]: https://github.com/pearjelly/cliany.site/compare/v0.16.246...v0.16.247
[0.16.246]: https://github.com/pearjelly/cliany.site/compare/v0.16.245...v0.16.246
[0.16.245]: https://github.com/pearjelly/cliany.site/compare/v0.16.244...v0.16.245
[0.16.244]: https://github.com/pearjelly/cliany.site/compare/v0.16.243...v0.16.244
[0.16.243]: https://github.com/pearjelly/cliany.site/compare/v0.16.242...v0.16.243
[0.16.242]: https://github.com/pearjelly/cliany.site/compare/v0.16.241...v0.16.242
[0.16.241]: https://github.com/pearjelly/cliany.site/compare/v0.16.240...v0.16.241
[0.16.240]: https://github.com/pearjelly/cliany.site/compare/v0.16.239...v0.16.240
[0.16.239]: https://github.com/pearjelly/cliany.site/compare/v0.16.238...v0.16.239
[0.16.238]: https://github.com/pearjelly/cliany.site/compare/v0.16.237...v0.16.238
[0.16.237]: https://github.com/pearjelly/cliany.site/compare/v0.16.236...v0.16.237
[0.16.236]: https://github.com/pearjelly/cliany.site/compare/v0.16.235...v0.16.236
[0.16.235]: https://github.com/pearjelly/cliany.site/compare/v0.16.234...v0.16.235
[0.16.234]: https://github.com/pearjelly/cliany.site/compare/v0.16.233...v0.16.234
[0.16.233]: https://github.com/pearjelly/cliany.site/compare/v0.16.232...v0.16.233
[0.16.232]: https://github.com/pearjelly/cliany.site/compare/v0.16.231...v0.16.232
[0.16.231]: https://github.com/pearjelly/cliany.site/compare/v0.16.230...v0.16.231
[0.16.230]: https://github.com/pearjelly/cliany.site/compare/v0.16.229...v0.16.230
[0.16.229]: https://github.com/pearjelly/cliany.site/compare/v0.16.228...v0.16.229
[0.16.228]: https://github.com/pearjelly/cliany.site/compare/v0.16.227...v0.16.228
[0.16.227]: https://github.com/pearjelly/cliany.site/compare/v0.16.226...v0.16.227
[0.16.226]: https://github.com/pearjelly/cliany.site/compare/v0.16.225...v0.16.226
[0.16.225]: https://github.com/pearjelly/cliany.site/compare/v0.16.224...v0.16.225
[0.16.224]: https://github.com/pearjelly/cliany.site/compare/v0.16.223...v0.16.224
[0.16.223]: https://github.com/pearjelly/cliany.site/compare/v0.16.222...v0.16.223
[0.16.222]: https://github.com/pearjelly/cliany.site/compare/v0.16.221...v0.16.222
[0.16.221]: https://github.com/pearjelly/cliany.site/compare/v0.16.220...v0.16.221
[0.16.220]: https://github.com/pearjelly/cliany.site/compare/v0.16.219...v0.16.220
[0.16.219]: https://github.com/pearjelly/cliany.site/compare/v0.16.218...v0.16.219
[0.16.218]: https://github.com/pearjelly/cliany.site/compare/v0.16.217...v0.16.218
[0.16.217]: https://github.com/pearjelly/cliany.site/compare/v0.16.216...v0.16.217
[0.16.216]: https://github.com/pearjelly/cliany.site/compare/v0.16.215...v0.16.216
[0.16.215]: https://github.com/pearjelly/cliany.site/compare/v0.16.214...v0.16.215
[0.16.214]: https://github.com/pearjelly/cliany.site/compare/v0.16.213...v0.16.214
[0.16.213]: https://github.com/pearjelly/cliany.site/compare/v0.16.212...v0.16.213
[0.16.212]: https://github.com/pearjelly/cliany.site/compare/v0.16.211...v0.16.212
[0.16.211]: https://github.com/pearjelly/cliany.site/compare/v0.16.210...v0.16.211
[0.16.210]: https://github.com/pearjelly/cliany.site/compare/v0.16.209...v0.16.210
[0.16.209]: https://github.com/pearjelly/cliany.site/compare/v0.16.208...v0.16.209
[0.16.208]: https://github.com/pearjelly/cliany.site/compare/v0.16.207...v0.16.208
[0.16.207]: https://github.com/pearjelly/cliany.site/compare/v0.16.206...v0.16.207
[0.16.206]: https://github.com/pearjelly/cliany.site/compare/v0.16.205...v0.16.206
[0.16.205]: https://github.com/pearjelly/cliany.site/compare/v0.16.204...v0.16.205
[0.16.204]: https://github.com/pearjelly/cliany.site/compare/v0.16.203...v0.16.204
[0.16.203]: https://github.com/pearjelly/cliany.site/compare/v0.16.202...v0.16.203
[0.16.202]: https://github.com/pearjelly/cliany.site/compare/v0.16.201...v0.16.202
[0.16.201]: https://github.com/pearjelly/cliany.site/compare/v0.16.200...v0.16.201
[0.16.200]: https://github.com/pearjelly/cliany.site/compare/v0.16.199...v0.16.200
[0.16.199]: https://github.com/pearjelly/cliany.site/compare/v0.16.198...v0.16.199
[0.16.198]: https://github.com/pearjelly/cliany.site/compare/v0.16.197...v0.16.198
[0.16.197]: https://github.com/pearjelly/cliany.site/compare/v0.16.196...v0.16.197
[0.16.196]: https://github.com/pearjelly/cliany.site/compare/v0.16.195...v0.16.196
[0.16.195]: https://github.com/pearjelly/cliany.site/compare/v0.16.194...v0.16.195
[0.16.194]: https://github.com/pearjelly/cliany.site/compare/v0.16.193...v0.16.194
[0.16.193]: https://github.com/pearjelly/cliany.site/compare/v0.16.192...v0.16.193
[0.16.192]: https://github.com/pearjelly/cliany.site/compare/v0.16.191...v0.16.192
[0.16.191]: https://github.com/pearjelly/cliany.site/compare/v0.16.190...v0.16.191
[0.16.190]: https://github.com/pearjelly/cliany.site/compare/v0.16.189...v0.16.190
[0.16.189]: https://github.com/pearjelly/cliany.site/compare/v0.16.188...v0.16.189
[0.16.188]: https://github.com/pearjelly/cliany.site/compare/v0.16.187...v0.16.188
[0.16.187]: https://github.com/pearjelly/cliany.site/compare/v0.16.186...v0.16.187
[0.16.186]: https://github.com/pearjelly/cliany.site/compare/v0.16.185...v0.16.186
[0.16.185]: https://github.com/pearjelly/cliany.site/compare/v0.16.184...v0.16.185
[0.16.184]: https://github.com/pearjelly/cliany.site/compare/v0.16.183...v0.16.184
[0.16.183]: https://github.com/pearjelly/cliany.site/compare/v0.16.182...v0.16.183
[0.16.182]: https://github.com/pearjelly/cliany.site/compare/v0.16.181...v0.16.182
[0.16.181]: https://github.com/pearjelly/cliany.site/compare/v0.16.180...v0.16.181
[0.16.180]: https://github.com/pearjelly/cliany.site/compare/v0.16.179...v0.16.180
[0.16.179]: https://github.com/pearjelly/cliany.site/compare/v0.16.178...v0.16.179
[0.16.178]: https://github.com/pearjelly/cliany.site/compare/v0.16.177...v0.16.178
[0.16.177]: https://github.com/pearjelly/cliany.site/compare/v0.16.176...v0.16.177
[0.16.176]: https://github.com/pearjelly/cliany.site/compare/v0.16.175...v0.16.176
[0.16.175]: https://github.com/pearjelly/cliany.site/compare/v0.16.174...v0.16.175
[0.16.174]: https://github.com/pearjelly/cliany.site/compare/v0.16.173...v0.16.174
[0.16.173]: https://github.com/pearjelly/cliany.site/compare/v0.16.172...v0.16.173
[0.16.172]: https://github.com/pearjelly/cliany.site/compare/v0.16.171...v0.16.172
[0.16.171]: https://github.com/pearjelly/cliany.site/compare/v0.16.170...v0.16.171
[0.16.170]: https://github.com/pearjelly/cliany.site/compare/v0.16.169...v0.16.170
[0.16.169]: https://github.com/pearjelly/cliany.site/compare/v0.16.168...v0.16.169
[0.16.168]: https://github.com/pearjelly/cliany.site/compare/v0.16.167...v0.16.168
[0.16.167]: https://github.com/pearjelly/cliany.site/compare/v0.16.166...v0.16.167
[0.16.166]: https://github.com/pearjelly/cliany.site/compare/v0.16.165...v0.16.166
[0.16.165]: https://github.com/pearjelly/cliany.site/compare/v0.16.164...v0.16.165
[0.16.164]: https://github.com/pearjelly/cliany.site/compare/v0.16.163...v0.16.164
[0.16.163]: https://github.com/pearjelly/cliany.site/compare/v0.16.162...v0.16.163
[0.16.162]: https://github.com/pearjelly/cliany.site/compare/v0.16.161...v0.16.162
[0.16.161]: https://github.com/pearjelly/cliany.site/compare/v0.16.160...v0.16.161
[0.16.160]: https://github.com/pearjelly/cliany.site/compare/v0.16.159...v0.16.160
[0.16.159]: https://github.com/pearjelly/cliany.site/compare/v0.16.158...v0.16.159
[0.16.158]: https://github.com/pearjelly/cliany.site/compare/v0.16.157...v0.16.158
[0.16.157]: https://github.com/pearjelly/cliany.site/compare/v0.16.156...v0.16.157
[0.16.156]: https://github.com/pearjelly/cliany.site/compare/v0.16.155...v0.16.156
[0.16.155]: https://github.com/pearjelly/cliany.site/compare/v0.16.154...v0.16.155
[0.16.154]: https://github.com/pearjelly/cliany.site/compare/v0.16.153...v0.16.154
[0.16.153]: https://github.com/pearjelly/cliany.site/compare/v0.16.152...v0.16.153
[0.16.152]: https://github.com/pearjelly/cliany.site/compare/v0.16.151...v0.16.152
[0.16.151]: https://github.com/pearjelly/cliany.site/compare/v0.16.150...v0.16.151
[0.16.150]: https://github.com/pearjelly/cliany.site/compare/v0.16.149...v0.16.150
[0.16.149]: https://github.com/pearjelly/cliany.site/compare/v0.16.148...v0.16.149
[0.16.148]: https://github.com/pearjelly/cliany.site/compare/v0.16.147...v0.16.148
[0.16.147]: https://github.com/pearjelly/cliany.site/compare/v0.16.146...v0.16.147
[0.16.146]: https://github.com/pearjelly/cliany.site/compare/v0.16.145...v0.16.146
[0.16.145]: https://github.com/pearjelly/cliany.site/compare/v0.16.144...v0.16.145
[0.16.144]: https://github.com/pearjelly/cliany.site/compare/v0.16.143...v0.16.144
[0.16.143]: https://github.com/pearjelly/cliany.site/compare/v0.16.142...v0.16.143
[0.16.142]: https://github.com/pearjelly/cliany.site/compare/v0.16.141...v0.16.142
[0.16.141]: https://github.com/pearjelly/cliany.site/compare/v0.16.140...v0.16.141
[0.16.140]: https://github.com/pearjelly/cliany.site/compare/v0.16.139...v0.16.140
[0.16.139]: https://github.com/pearjelly/cliany.site/compare/v0.16.138...v0.16.139
[0.16.138]: https://github.com/pearjelly/cliany.site/compare/v0.16.137...v0.16.138
[0.16.137]: https://github.com/pearjelly/cliany.site/compare/v0.16.136...v0.16.137
[0.16.136]: https://github.com/pearjelly/cliany.site/compare/v0.16.135...v0.16.136
[0.16.135]: https://github.com/pearjelly/cliany.site/compare/v0.16.134...v0.16.135
[0.16.134]: https://github.com/pearjelly/cliany.site/compare/v0.16.133...v0.16.134
[0.16.133]: https://github.com/pearjelly/cliany.site/compare/v0.16.132...v0.16.133
[0.16.132]: https://github.com/pearjelly/cliany.site/compare/v0.16.131...v0.16.132
[0.16.131]: https://github.com/pearjelly/cliany.site/compare/v0.16.130...v0.16.131
[0.16.130]: https://github.com/pearjelly/cliany.site/compare/v0.16.129...v0.16.130
[0.16.129]: https://github.com/pearjelly/cliany.site/compare/v0.16.128...v0.16.129
[0.16.128]: https://github.com/pearjelly/cliany.site/compare/v0.16.127...v0.16.128
[0.16.127]: https://github.com/pearjelly/cliany.site/compare/v0.16.126...v0.16.127
[0.16.126]: https://github.com/pearjelly/cliany.site/compare/v0.16.125...v0.16.126
[0.16.125]: https://github.com/pearjelly/cliany.site/compare/v0.16.124...v0.16.125
[0.16.124]: https://github.com/pearjelly/cliany.site/compare/v0.16.123...v0.16.124
[0.16.123]: https://github.com/pearjelly/cliany.site/compare/v0.16.122...v0.16.123
[0.16.122]: https://github.com/pearjelly/cliany.site/compare/v0.16.121...v0.16.122
[0.16.121]: https://github.com/pearjelly/cliany.site/compare/v0.16.120...v0.16.121
[0.16.120]: https://github.com/pearjelly/cliany.site/compare/v0.16.119...v0.16.120
[0.16.119]: https://github.com/pearjelly/cliany.site/compare/v0.16.118...v0.16.119
[0.16.118]: https://github.com/pearjelly/cliany.site/compare/v0.16.117...v0.16.118
[0.16.117]: https://github.com/pearjelly/cliany.site/compare/v0.16.116...v0.16.117
[0.16.116]: https://github.com/pearjelly/cliany.site/compare/v0.16.115...v0.16.116
[0.16.115]: https://github.com/pearjelly/cliany.site/compare/v0.16.114...v0.16.115
[0.16.114]: https://github.com/pearjelly/cliany.site/compare/v0.16.113...v0.16.114
[0.16.113]: https://github.com/pearjelly/cliany.site/compare/v0.16.112...v0.16.113
[0.16.112]: https://github.com/pearjelly/cliany.site/compare/v0.16.111...v0.16.112
[0.16.111]: https://github.com/pearjelly/cliany.site/compare/v0.16.110...v0.16.111
[0.16.110]: https://github.com/pearjelly/cliany.site/compare/v0.16.109...v0.16.110
[0.16.109]: https://github.com/pearjelly/cliany.site/compare/v0.16.108...v0.16.109
[0.16.108]: https://github.com/pearjelly/cliany.site/compare/v0.16.107...v0.16.108
[0.16.107]: https://github.com/pearjelly/cliany.site/compare/v0.16.106...v0.16.107
[0.16.106]: https://github.com/pearjelly/cliany.site/compare/v0.16.105...v0.16.106
[0.16.105]: https://github.com/pearjelly/cliany.site/compare/v0.16.104...v0.16.105
[0.16.104]: https://github.com/pearjelly/cliany.site/compare/v0.16.103...v0.16.104
[0.16.103]: https://github.com/pearjelly/cliany.site/compare/v0.16.102...v0.16.103
[0.16.102]: https://github.com/pearjelly/cliany.site/compare/v0.16.101...v0.16.102
[0.16.101]: https://github.com/pearjelly/cliany.site/compare/v0.16.100...v0.16.101
[0.16.100]: https://github.com/pearjelly/cliany.site/compare/v0.16.99...v0.16.100
[0.16.99]: https://github.com/pearjelly/cliany.site/compare/v0.16.98...v0.16.99
[0.16.98]: https://github.com/pearjelly/cliany.site/compare/v0.16.97...v0.16.98
[0.16.97]: https://github.com/pearjelly/cliany.site/compare/v0.16.96...v0.16.97
[0.16.96]: https://github.com/pearjelly/cliany.site/compare/v0.16.95...v0.16.96
[0.16.95]: https://github.com/pearjelly/cliany.site/compare/v0.16.94...v0.16.95
[0.16.94]: https://github.com/pearjelly/cliany.site/compare/v0.16.93...v0.16.94
[0.16.93]: https://github.com/pearjelly/cliany.site/compare/v0.16.92...v0.16.93
[0.16.92]: https://github.com/pearjelly/cliany.site/compare/v0.16.91...v0.16.92
[0.16.91]: https://github.com/pearjelly/cliany.site/compare/v0.16.90...v0.16.91
[0.16.90]: https://github.com/pearjelly/cliany.site/compare/v0.16.89...v0.16.90
[0.16.89]: https://github.com/pearjelly/cliany.site/compare/v0.16.88...v0.16.89
[0.16.88]: https://github.com/pearjelly/cliany.site/compare/v0.16.87...v0.16.88
[0.16.87]: https://github.com/pearjelly/cliany.site/compare/v0.16.86...v0.16.87
[0.16.86]: https://github.com/pearjelly/cliany.site/compare/v0.16.85...v0.16.86
[0.16.85]: https://github.com/pearjelly/cliany.site/compare/v0.16.84...v0.16.85
[0.16.84]: https://github.com/pearjelly/cliany.site/compare/v0.16.83...v0.16.84
[0.16.83]: https://github.com/pearjelly/cliany.site/compare/v0.16.82...v0.16.83
[0.16.82]: https://github.com/pearjelly/cliany.site/compare/v0.16.81...v0.16.82
[0.16.81]: https://github.com/pearjelly/cliany.site/compare/v0.16.80...v0.16.81
[0.16.80]: https://github.com/pearjelly/cliany.site/compare/v0.16.79...v0.16.80
[0.16.79]: https://github.com/pearjelly/cliany.site/compare/v0.16.78...v0.16.79
[0.16.78]: https://github.com/pearjelly/cliany.site/compare/v0.16.77...v0.16.78
[0.16.77]: https://github.com/pearjelly/cliany.site/compare/v0.16.76...v0.16.77
[0.16.76]: https://github.com/pearjelly/cliany.site/compare/v0.16.75...v0.16.76
[0.16.75]: https://github.com/pearjelly/cliany.site/compare/v0.16.74...v0.16.75
[0.16.74]: https://github.com/pearjelly/cliany.site/compare/v0.16.73...v0.16.74
[0.16.73]: https://github.com/pearjelly/cliany.site/compare/v0.16.72...v0.16.73
[0.16.72]: https://github.com/pearjelly/cliany.site/compare/v0.16.71...v0.16.72
[0.16.71]: https://github.com/pearjelly/cliany.site/compare/v0.16.70...v0.16.71
[0.16.70]: https://github.com/pearjelly/cliany.site/compare/v0.16.69...v0.16.70
[0.16.69]: https://github.com/pearjelly/cliany.site/compare/v0.16.68...v0.16.69
[0.16.68]: https://github.com/pearjelly/cliany.site/compare/v0.16.67...v0.16.68
[0.16.67]: https://github.com/pearjelly/cliany.site/compare/v0.16.66...v0.16.67
[0.16.66]: https://github.com/pearjelly/cliany.site/compare/v0.16.65...v0.16.66
[0.16.65]: https://github.com/pearjelly/cliany.site/compare/v0.16.64...v0.16.65
[0.16.64]: https://github.com/pearjelly/cliany.site/compare/v0.16.63...v0.16.64
[0.16.63]: https://github.com/pearjelly/cliany.site/compare/v0.16.62...v0.16.63
[0.16.62]: https://github.com/pearjelly/cliany.site/compare/v0.16.61...v0.16.62
[0.16.61]: https://github.com/pearjelly/cliany.site/compare/v0.16.60...v0.16.61
[0.16.60]: https://github.com/pearjelly/cliany.site/compare/v0.16.59...v0.16.60
[0.16.59]: https://github.com/pearjelly/cliany.site/compare/v0.16.58...v0.16.59
[0.16.58]: https://github.com/pearjelly/cliany.site/compare/v0.16.57...v0.16.58
[0.16.57]: https://github.com/pearjelly/cliany.site/compare/v0.16.56...v0.16.57
[0.16.56]: https://github.com/pearjelly/cliany.site/compare/v0.16.55...v0.16.56
[0.16.55]: https://github.com/pearjelly/cliany.site/compare/v0.16.54...v0.16.55
[0.16.54]: https://github.com/pearjelly/cliany.site/compare/v0.16.53...v0.16.54
[0.16.53]: https://github.com/pearjelly/cliany.site/compare/v0.16.52...v0.16.53
[0.16.52]: https://github.com/pearjelly/cliany.site/compare/v0.16.51...v0.16.52
[0.16.51]: https://github.com/pearjelly/cliany.site/compare/v0.16.50...v0.16.51
[0.16.50]: https://github.com/pearjelly/cliany.site/compare/v0.16.49...v0.16.50
[0.16.49]: https://github.com/pearjelly/cliany.site/compare/v0.16.48...v0.16.49
[0.16.48]: https://github.com/pearjelly/cliany.site/compare/v0.16.47...v0.16.48
[0.16.47]: https://github.com/pearjelly/cliany.site/compare/v0.16.46...v0.16.47
[0.16.46]: https://github.com/pearjelly/cliany.site/compare/v0.16.45...v0.16.46
[0.16.45]: https://github.com/pearjelly/cliany.site/compare/v0.16.44...v0.16.45
[0.16.44]: https://github.com/pearjelly/cliany.site/compare/v0.16.43...v0.16.44
[0.16.43]: https://github.com/pearjelly/cliany.site/compare/v0.16.42...v0.16.43
[0.16.42]: https://github.com/pearjelly/cliany.site/compare/v0.16.41...v0.16.42
[0.16.41]: https://github.com/pearjelly/cliany.site/compare/v0.16.40...v0.16.41
[0.16.40]: https://github.com/pearjelly/cliany.site/compare/v0.16.39...v0.16.40
[0.16.39]: https://github.com/pearjelly/cliany.site/compare/v0.16.38...v0.16.39
[0.16.38]: https://github.com/pearjelly/cliany.site/compare/v0.16.37...v0.16.38
[0.16.37]: https://github.com/pearjelly/cliany.site/compare/v0.16.36...v0.16.37
[0.16.36]: https://github.com/pearjelly/cliany.site/compare/v0.16.35...v0.16.36
[0.16.35]: https://github.com/pearjelly/cliany.site/compare/v0.16.34...v0.16.35
[0.16.34]: https://github.com/pearjelly/cliany.site/compare/v0.16.33...v0.16.34
[0.16.33]: https://github.com/pearjelly/cliany.site/compare/v0.16.32...v0.16.33
[0.16.32]: https://github.com/pearjelly/cliany.site/compare/v0.16.31...v0.16.32
[0.16.31]: https://github.com/pearjelly/cliany.site/compare/v0.16.30...v0.16.31
[0.16.30]: https://github.com/pearjelly/cliany.site/compare/v0.16.29...v0.16.30
[0.16.29]: https://github.com/pearjelly/cliany.site/compare/v0.16.28...v0.16.29
[0.16.28]: https://github.com/pearjelly/cliany.site/compare/v0.16.27...v0.16.28
[0.16.27]: https://github.com/pearjelly/cliany.site/compare/v0.16.26...v0.16.27
[0.16.26]: https://github.com/pearjelly/cliany.site/compare/v0.16.25...v0.16.26
[0.16.25]: https://github.com/pearjelly/cliany.site/compare/v0.16.24...v0.16.25
[0.16.24]: https://github.com/pearjelly/cliany.site/compare/v0.16.23...v0.16.24
[0.16.23]: https://github.com/pearjelly/cliany.site/compare/v0.16.22...v0.16.23
[0.16.22]: https://github.com/pearjelly/cliany.site/compare/v0.16.21...v0.16.22
[0.16.21]: https://github.com/pearjelly/cliany.site/compare/v0.16.20...v0.16.21
[0.16.20]: https://github.com/pearjelly/cliany.site/compare/v0.16.19...v0.16.20
[0.16.19]: https://github.com/pearjelly/cliany.site/compare/v0.16.18...v0.16.19
[0.16.18]: https://github.com/pearjelly/cliany.site/compare/v0.16.17...v0.16.18
[0.16.17]: https://github.com/pearjelly/cliany.site/compare/v0.16.16...v0.16.17
[0.16.16]: https://github.com/pearjelly/cliany.site/compare/v0.16.15...v0.16.16
[0.16.15]: https://github.com/pearjelly/cliany.site/compare/v0.16.14...v0.16.15
[0.16.14]: https://github.com/pearjelly/cliany.site/compare/v0.16.13...v0.16.14
[0.16.13]: https://github.com/pearjelly/cliany.site/compare/v0.16.12...v0.16.13
[0.16.12]: https://github.com/pearjelly/cliany.site/compare/v0.16.11...v0.16.12
[0.16.11]: https://github.com/pearjelly/cliany.site/compare/v0.16.10...v0.16.11
[0.16.10]: https://github.com/pearjelly/cliany.site/compare/v0.16.9...v0.16.10
[0.16.9]: https://github.com/pearjelly/cliany.site/compare/v0.16.8...v0.16.9
[0.16.8]: https://github.com/pearjelly/cliany.site/compare/v0.16.7...v0.16.8
[0.16.7]: https://github.com/pearjelly/cliany.site/compare/v0.16.6...v0.16.7
[0.16.6]: https://github.com/pearjelly/cliany.site/compare/v0.16.5...v0.16.6
[0.16.5]: https://github.com/pearjelly/cliany.site/compare/v0.16.4...v0.16.5
[0.16.4]: https://github.com/pearjelly/cliany.site/compare/v0.16.3...v0.16.4
[0.16.3]: https://github.com/pearjelly/cliany.site/compare/v0.16.2...v0.16.3
[0.16.2]: https://github.com/pearjelly/cliany.site/compare/v0.16.1...v0.16.2
[0.16.1]: https://github.com/pearjelly/cliany.site/compare/v0.16.0...v0.16.1
[0.16.0]: https://github.com/pearjelly/cliany.site/compare/v0.15.9...v0.16.0
[0.15.9]: https://github.com/pearjelly/cliany.site/compare/v0.15.8...v0.15.9
[0.15.8]: https://github.com/pearjelly/cliany.site/compare/v0.15.7...v0.15.8
[0.15.7]: https://github.com/pearjelly/cliany.site/compare/v0.15.6...v0.15.7
[0.15.6]: https://github.com/pearjelly/cliany.site/compare/v0.15.5...v0.15.6
[0.15.5]: https://github.com/pearjelly/cliany.site/compare/v0.15.4...v0.15.5
[0.15.4]: https://github.com/pearjelly/cliany.site/compare/v0.15.3...v0.15.4
[0.15.3]: https://github.com/pearjelly/cliany.site/compare/v0.15.2...v0.15.3
[0.15.2]: https://github.com/pearjelly/cliany.site/compare/v0.15.1...v0.15.2
[0.15.1]: https://github.com/pearjelly/cliany.site/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/pearjelly/cliany.site/compare/v0.14.4...v0.15.0
[0.14.4]: https://github.com/pearjelly/cliany.site/compare/v0.14.3...v0.14.4
[0.11.0]: https://github.com/pearjelly/cliany.site/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/pearjelly/cliany.site/compare/v0.9.3...v0.10.0
