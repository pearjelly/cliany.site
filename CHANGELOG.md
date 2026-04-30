# 更新日志

本项目的所有显著更改都将记录在此文件中。

本文件的格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
并且本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

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

[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.9.3...HEAD
[0.9.3]: https://github.com/pearjelly/cliany.site/compare/v0.9.2...v0.9.3
[0.9.2]: https://github.com/pearjelly/cliany.site/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/pearjelly/cliany.site/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/pearjelly/cliany.site/compare/v0.8.3...v0.9.0
[0.8.3]: https://github.com/pearjelly/cliany.site/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/pearjelly/cliany.site/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/pearjelly/cliany.site/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/pearjelly/cliany.site/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/pearjelly/cliany.site/compare/v0.7.0...v0.7.1
[0.6.2]: https://github.com/pearjelly/cliany.site/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/pearjelly/cliany.site/compare/v0.5.1...v0.6.1
[0.5.1]: https://github.com/pearjelly/cliany.site/releases/tag/v0.5.1
