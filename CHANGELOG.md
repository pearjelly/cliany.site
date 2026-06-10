# 更新日志

本项目的所有显著更改都将记录在此文件中。

本文件的格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
并且本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 新增 `docs/roadmap-2026-q3.md`，基于 v0.2~v0.14 迭代轨迹制定 2026 Q3 路线图，聚焦新用户可用性、真实案例库、adapter 生命周期、贡献者入口与运行可靠性。
- 新增 `docs/release-cadence.md`，固化每周至少 1 个版本、每周至少 3 天提交记录的发布与提交节奏。
- 新增 `cases/manifest.json` 与 `cases/README.md`，把 v0.14 真实 demo 和搜索抽取短板复盘沉淀为可维护案例库，并新增离线结构校验测试。

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

[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.11.0...HEAD
[0.11.0]: https://github.com/pearjelly/cliany.site/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/pearjelly/cliany.site/compare/v0.9.3...v0.10.0
