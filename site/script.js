const I18N = {
  'nav.features': { zh: '功能', en: 'Features' },
  'nav.how': { zh: '工作原理', en: 'How It Works' },
  'nav.quickstart': { zh: '快速开始', en: 'Get Started' },
  'nav.try': { zh: '立即试用', en: 'Try it' },
  'nav.feedback': { zh: '反馈', en: 'Feedback' },
  'nav.cta': { zh: '开始第一个工作流', en: 'Start your first workflow' },

  'hero.kicker': { zh: '从重复点击，到可复用命令', en: 'From repeated clicks to reusable commands' },
  'hero.title': { zh: '让浏览器工作流可以复用', en: 'Make browser work reusable' },
  'hero.subtitle': { zh: '把浏览器工作流转成站点专属 CLI 命令，重复执行、写入脚本，并以 JSON 查看结果。', en: 'Turn a browser workflow into a site-specific CLI command you can run again, script, and inspect as JSON.' },
  'hero.cta': { zh: '开始第一个工作流', en: 'Start your first workflow' },
  'hero.github': { zh: '查看 GitHub →', en: 'View on GitHub →' },

  'try.title': { zh: '三条命令开始试用', en: 'Try it in three commands' },
  'try.subtitle': { zh: '安装后让 doctor 给出已发布 demo 或案例目录的安全下一步，再决定是否连接 LLM。', en: 'Install, let doctor offer a published demo or case catalog as the safe next step, then decide whether to connect an LLM.' },
  'try.install.title': { zh: '安装', en: 'Install' },
  'try.install.body': { zh: '从 PyPI 获取 CLI。', en: 'Get the CLI from PyPI.' },
  'try.check.title': { zh: '检查就绪状态', en: 'Check readiness' },
  'try.check.body': { zh: '查看适合你当前机器的下一步建议。', en: 'Read the human-friendly next step for your machine.' },
  'try.cases.title': { zh: '选择维护中的案例', en: 'Choose a maintained example' },
  'try.cases.body': { zh: '当 doctor 报告 ready_for_demo_adapters=true 时，按 demo_adapter_quickstart.commands 安装、verify 并执行只读 active demo；否则浏览公开案例及其验证路径。', en: 'When doctor reports ready_for_demo_adapters=true, follow demo_adapter_quickstart.commands to install, verify, and run a read-only active demo; otherwise browse public cases and their validation paths.' },
  'try.guide': { zh: '查看 10 分钟指南 →', en: 'Follow the 10-minute guide →' },

  'terminal.connecting': { zh: '✓ 正在连接 Chrome CDP...', en: '✓ Connecting to Chrome CDP...' },
  'terminal.analyzing': { zh: '✓ 正在分析页面结构...', en: '✓ Analyzing page structure...' },
  'terminal.planning': { zh: '✓ LLM 规划工作流...', en: '✓ LLM planning workflow...' },
  'terminal.generated': {
    zh: '✓ 生成 CLI 命令至 ~/.cliany-site/adapters/github.com/',
    en: '✓ CLI commands generated to ~/.cliany-site/adapters/github.com/'
  },
  'demo.quality.contract': {
    zh: '生成的 list/search/read/extract 命令及包含 extract action 的命令默认 expects_nonempty=true；零条数据、缺失字段或 partial 结果都会失败。只有零匹配本来合法时才声明 expects_nonempty=false；已安装的旧 adapter 不会被静默改写。',
    en: 'Generated list/search/read/extract commands, and any command with an extract action, default to expects_nonempty=true; empty, missing, or partial data fails. Declare expects_nonempty=false only when zero matches are valid; installed adapters are not silently rewritten.'
  },

  'features.title': { zh: '核心特性', en: 'Core Features' },
  'features.subtitle': { zh: '4 个核心能力 + 12 个扩展能力', en: '4 core capabilities + 12 extended capabilities' },
  'features.focus.badge': { zh: '核心', en: 'CORE' },
  'features.more.title': { zh: '扩展能力（12）', en: 'Extended Capabilities (12)' },
  'features.more.subtitle': { zh: '默认隐藏复杂度，需要时再打开。', en: 'Hide complexity by default, unlock it when needed.' },
  'features.value.text': { zh: '先用核心 4 项打通路径，再按需启用扩展能力。', en: 'Start with the core four, then enable advanced capabilities on demand.' },
  'features.focus.explore.desc': { zh: 'AXTree 无注入探索，快速定位可自动化路径。', en: 'Injection-free AXTree exploration to quickly locate automatable paths.' },
  'features.focus.llm.desc': { zh: '把页面语义直接转成可执行 CLI 命令。', en: 'Turn page semantics directly into executable CLI commands.' },
  'features.focus.json.desc': { zh: '统一 {ok,data,error}，自动化易集成。', en: 'Unified {ok,data,error} output for easy automation integration.' },
  'features.focus.session.desc': { zh: '一次登录跨命令复用，减少重复操作。', en: 'Reuse one login across commands to eliminate repetitive operations.' },
  'features.explore.title': { zh: '零侵入探索', en: 'Zero-Intrusion Exploration' },
  'features.explore.desc': {
    zh: '通过 Chrome CDP 协议捕获页面无障碍树（AXTree），无需注入脚本，零侵入分析网页结构。',
    en: 'Capture the page accessibility tree (AXTree) via Chrome CDP — no script injection, zero-intrusion page analysis.'
  },
  'features.llm.title': { zh: 'LLM 驱动代码生成', en: 'LLM-Driven Code Generation' },
  'features.llm.desc': {
    zh: '调用 Claude / GPT-4o 理解页面语义，自动将复杂工作流转化为结构化的 Python CLI 命令。',
    en: 'Leverage Claude / GPT-4o to understand page semantics and automatically transform complex workflows into structured Python CLI commands.'
  },
  'features.json.title': { zh: '标准 JSON 输出', en: 'Standard JSON Output' },
  'features.json.desc': {
    zh: '所有命令支持 --json 选项，输出统一 {ok, data, error} 信封格式，方便管道和自动化集成。',
    en: 'All commands support --json, outputting a unified {ok, data, error} envelope for easy piping and automation.'
  },
  'features.session.title': { zh: '持久化 Session', en: 'Persistent Sessions' },
  'features.session.desc': {
    zh: '跨命令保持 Cookie 和 LocalStorage 登录状态，一次登录，多次复用。',
    en: 'Maintain Cookie and LocalStorage login state across commands — log in once, reuse many times.'
  },
  'features.adapter.title': { zh: '动态适配器加载', en: 'Dynamic Adapter Loading' },
  'features.adapter.desc': {
    zh: '每个网站自动生成独立适配器，按域名动态注册为 CLI 子命令。随时扩展，按需加载。',
    en: 'Each website generates its own adapter, dynamically registered as a CLI subcommand by domain. Extend anytime, load on demand.'
  },
  'features.chrome.title': { zh: 'Chrome 自动管理', en: 'Chrome Auto-Management' },
  'features.chrome.desc': {
    zh: '自动检测并启动 Chrome 调试实例，支持 macOS 和 Linux，无需手动配置 CDP。',
    en: 'Automatically detect and launch Chrome debug instances. Supports macOS and Linux — no manual CDP setup needed.'
  },
  'features.merge.title': { zh: '适配器增量合并', en: 'Incremental Adapter Merge' },
  'features.merge.desc': {
    zh: '重复探索同一网站时智能合并新旧适配器，保留已有命令，自动处理冲突。',
    en: 'Smart-merge new and existing adapters when re-exploring the same site. Preserves existing commands with automatic conflict resolution.'
  },
  'features.atoms.title': { zh: '原子命令系统', en: 'Atomic Command System' },
  'features.atoms.desc': {
    zh: '从工作流中自动提取可复用的原子操作，跨适配器共享登录、搜索等通用步骤，参数化复用。',
    en: 'Auto-extract reusable atomic actions from workflows. Share common steps like login and search across adapters with parameterized reuse.'
  },
  'features.validator.title': { zh: '智能录制验证', en: 'Smart Recording Validation' },
  'features.validator.desc': {
    zh: '纯逻辑验证器校验操作步骤完整性，结构化错误报告，可由调用方集成至工作流。',
    en: 'Pure-logic validator checks action step integrity. Structured error reports, ready for caller integration into workflows.'
  },
  'features.tui.title': { zh: 'TUI 管理界面', en: 'TUI Management Interface' },
  'features.tui.desc': {
    zh: '基于 Textual 的终端 UI，可视化管理适配器、查看操作日志、导入导出配置，全键盘操作。',
    en: 'Textual-based terminal UI for visual adapter management, activity logs, config import/export — fully keyboard-driven.'
  },
  'features.headless.title': { zh: 'Headless & 远程浏览器', en: 'Headless & Remote Browser' },
  'features.headless.desc': {
    zh: '支持 Headless Chrome 和远程 CDP 连接，可在服务器和 Docker 容器中运行，突破本地 GUI 限制。',
    en: 'Support Headless Chrome and remote CDP connections. Run on servers and Docker containers, beyond local GUI limitations.'
  },
  'features.workflow.title': { zh: 'YAML 工作流编排', en: 'YAML Workflow Orchestration' },
  'features.workflow.desc': {
    zh: '通过 YAML 声明式编排多步骤工作流，支持步骤间数据传递、条件判断和重试策略。',
    en: 'Declaratively orchestrate multi-step workflows via YAML, with inter-step data passing, conditional logic, and retry policies.'
  },
  'features.batch.title': { zh: '数据驱动批量执行', en: 'Data-Driven Batch Execution' },
  'features.batch.desc': {
    zh: '从 CSV/JSON 读取参数列表批量执行，支持并发控制，自动生成汇总报告。',
    en: 'Batch execute from CSV/JSON parameter lists with concurrency control and automatic summary reports.'
  },
  'features.sdk.title': { zh: 'Python SDK & HTTP API', en: 'Python SDK & HTTP API' },
  'features.sdk.desc': {
    zh: '程序化调用 from cliany_site import explore，或启动 REST API 服务，集成到任意系统。',
    en: 'Programmatic calls via from cliany_site import explore, or launch a REST API server for integration into any system.'
  },
  'features.security.title': { zh: '安全加固', en: 'Security Hardening' },
  'features.security.desc': {
    zh: 'Session 加密存储、沙箱执行模式、生成代码自动 AST 安全审计，全方位安全保障。',
    en: 'Encrypted session storage, sandbox execution mode, and automatic AST security auditing of generated code.'
  },
  'features.marketplace.title': { zh: '适配器市场', en: 'Adapter Marketplace' },
  'features.marketplace.desc': {
    zh: '打包、发布、安装、回滚适配器，团队间共享自动化能力，版本化管理。',
    en: 'Package, publish, install, and rollback adapters. Share automation capabilities across teams with version management.'
  },

  'how.title': { zh: '工作原理', en: 'How It Works' },
  'how.subtitle': { zh: '三步完成从网页到命令行的转化', en: 'Three steps from web pages to CLI commands' },
  'how.explore.title': { zh: '探索 (Explore)', en: 'Explore' },
  'how.explore.desc': {
    zh: '指定目标 URL 和任务描述，LLM 自动分析页面结构并规划操作路径。',
    en: 'Specify a target URL and task description — the LLM automatically analyzes page structure and plans the action path.'
  },
  'how.generate.title': { zh: '生成 (Generate)', en: 'Generate' },
  'how.generate.desc': {
    zh: '将探索结果转化为 Python/Click 命令行工具，自动保存至本地适配器目录。',
    en: 'Transform exploration results into Python/Click CLI tools, automatically saved to the local adapter directory.'
  },
  'how.run.title': { zh: '执行 (Run)', en: 'Run' },
  'how.run.desc': {
    zh: '通过生成的 CLI 命令一键回放工作流。模糊匹配技术确保页面微调后依然稳定运行。',
    en: 'Replay workflows with generated CLI commands. Fuzzy matching ensures stable execution even after minor page changes.'
  },

  'demo.title': { zh: '命令行参考', en: 'CLI Reference' },
  'demo.login.waiting': { zh: '✓ 等待浏览器完成登录...', en: '✓ Waiting for browser login...' },
  'demo.login.saved': { zh: '✓ Session 已保存至 ~/.cliany-site/sessions/', en: '✓ Session saved to ~/.cliany-site/sessions/' },
  'demo.explore.done': { zh: '✓ 探索完成，已生成适配器', en: '✓ Exploration complete, adapter generated' },

  'qs.title': { zh: '10 分钟成功路径', en: '10-Minute Success Path' },
  'qs.subtitle': { zh: '先运行 doctor 指向的 active demo 或案例目录，再为自己的命令配置 LLM', en: 'Follow doctor to an active demo or case catalog before configuring an LLM for your own commands' },
  'qs.step1': { zh: 'Step 1: 安装', en: 'Step 1: Install' },
  'qs.step2': { zh: 'Step 2: 检查就绪状态', en: 'Step 2: Check Readiness' },
  'qs.step3': { zh: 'Step 3: 运行 active demo 或浏览案例', en: 'Step 3: Run an Active Demo or Browse Cases' },
  'qs.step4': { zh: 'Step 4: 生成你的命令', en: 'Step 4: Generate Your Own' },
  'qs.contribute.title': { zh: '首次成功之后', en: 'After Your First Success' },
  'qs.contribute.desc': {
    zh: '跑通公开只读工作流后，可以通过 Real Demo Case Proposal 路径提交候选场景，让它沉淀为带离线 JSON 样例的可验证案例。',
    en: 'Ran a real public workflow? Propose it through the Real Demo Case Proposal path so it can become a validated case with an offline JSON example.'
  },
  'qs.contribute.case': {
    zh: '使用 <code>Real Demo Case Proposal</code> issue 模板提交公开、只读工作流；candidate 晋级 issue 可由 <code>cliany-site cases --case-id pypi-project-search --issue-template</code> 生成，并包含 <code>Acceptance Criteria</code>、<code>Primary Runbook</code>、<code>Command SHA-256</code>、<code>Promotion Command Plan Summary</code>、JSON <code>promotion_command_plan_summary</code> / <code>issue_template_promotion_command_plan_summary</code>、<code>Promotion Command Plan</code> <code>command_sha256</code> 子行、<code>source</code> / <code>missing</code> 元数据、<code>Doctor Preflight Evidence Fields</code>、<code>Doctor Preflight Evidence Template</code>、JSON <code>doctor_preflight_evidence_template</code>、<code>doctor_preflight_evidence_template_field_count</code>、<code>doctor_preflight_evidence_template_sha256</code>、<code>doctor_preflight_state_fields</code> 与 <code>doctor_preflight_state_statuses</code>。state 字段固定为 <code>preflight_state.status</code>、<code>preflight_state.ready_for_adapter_package</code>、<code>preflight_state.primary_reason</code>、<code>preflight_state.reason_codes</code>、<code>preflight_state.next_action</code>，状态只允许 <code>ready</code>、<code>blocked</code>、<code>missing_fields</code>。',
    en: 'Use the <code>Real Demo Case Proposal</code> issue template for public, read-only workflows; generate candidate promotion issues with <code>cliany-site cases --case-id pypi-project-search --issue-template</code>, including <code>Acceptance Criteria</code>, <code>Primary Runbook</code>, <code>Command SHA-256</code>, <code>Promotion Command Plan Summary</code>, JSON <code>promotion_command_plan_summary</code> / <code>issue_template_promotion_command_plan_summary</code>, <code>Promotion Command Plan</code> <code>command_sha256</code> lines, <code>source</code> / <code>missing</code> metadata, <code>Doctor Preflight Evidence Fields</code>, <code>Doctor Preflight Evidence Template</code>, JSON <code>doctor_preflight_evidence_template</code>, <code>doctor_preflight_evidence_template_field_count</code>, <code>doctor_preflight_evidence_template_sha256</code>, <code>doctor_preflight_state_fields</code>, and <code>doctor_preflight_state_statuses</code>. The state fields are <code>preflight_state.status</code>, <code>preflight_state.ready_for_adapter_package</code>, <code>preflight_state.primary_reason</code>, <code>preflight_state.reason_codes</code>, and <code>preflight_state.next_action</code>; statuses are limited to <code>ready</code>, <code>blocked</code>, and <code>missing_fields</code>.'
  },
  'qs.contribute.validate': {
    zh: '候选案例应关联 <code>cases/manifest.json</code>、<code>cases/examples/</code>、<code>python scripts/validate_cases.py --strict</code>、带 <code>llm_live_preflight</code>、<code>llm_live_preflight_command_sha256</code>、<code>primary_issue_template_command</code> 与 <code>issue_template_json_command</code> 的 <code>cliany-site cases --status candidate --promotion-plan</code>、带 <code>preflight_required</code> / <code>preflight_blocker</code> / <code>runbook_first</code> 的 human <code>cliany-site cases --status candidate</code> 输出、带 <code>summary.llm_live_preflight</code> 与 CDP 阻塞证据的 doctor JSON、基础 <code>cliany-site cases --case-id &lt;id&gt; --evidence-bundle --json</code> 输出、带 <code>primary_next_task_runbook</code>、<code>primary_next_task_acceptance_criteria</code>、<code>promotion_command_plan_summary</code>、<code>promotion_command_plan[*].command_sha256</code>、<code>doctor_preflight_evidence_fields</code>、<code>doctor_preflight_evidence_values</code>、<code>doctor_preflight_evidence_ok</code>、<code>doctor_preflight_evidence_missing_count</code>、<code>doctor_preflight_evidence_null_count</code>、<code>doctor_preflight_evidence_null_fields</code> 与 <code>doctor_preflight_state</code> 的 <code>cliany-site cases --case-id &lt;id&gt; --evidence-bundle --doctor-json /tmp/cliany-doctor-preflight.json --json</code>，以及带 <code>candidate_promotions[*].issue_template_command</code>、<code>candidate_promotions[*].issue_template_json_command</code>、<code>candidate_promotions[*].promotion_command_plan_summary</code>、<code>issue-metadata.json</code>、<code>Primary Acceptance Criteria</code>、<code>case_promotion_evidence_primary_llm_live_preflight_required</code>、<code>case_promotion_evidence_primary_llm_live_preflight_command_sha256</code>、<code>case_promotion_evidence_primary_llm_live_preflight_blocker_comment</code>、<code>case_promotion_evidence_primary_doctor_preflight_blocker_comment</code>、<code>case_promotion_evidence_primary_doctor_preflight_evidence_template_sha256</code>、<code>case_promotion_doctor_preflight_evidence_template_sha256</code>、<code>doctor_preflight_evidence_fields</code>、<code>doctor_preflight_state_fields</code>、<code>doctor_preflight_state_statuses</code>、<code>required_labels</code>、<code>required_label_count</code>、<code>required_labels_sha256</code> 与 <code>case_promotion_evidence_primary_runbook_steps</code> / hash 漂移检查的 <code>python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues</code>。',
    en: 'Candidate cases should point to <code>cases/manifest.json</code>, <code>cases/examples/</code>, <code>python scripts/validate_cases.py --strict</code>, <code>cliany-site cases --status candidate --promotion-plan</code> with <code>llm_live_preflight</code>, <code>llm_live_preflight_command_sha256</code>, <code>primary_issue_template_command</code>, and <code>issue_template_json_command</code>, human <code>cliany-site cases --status candidate</code> output with <code>preflight_required</code>, <code>preflight_blocker</code>, and <code>runbook_first</code>, doctor JSON with <code>summary.llm_live_preflight</code> and CDP blocker evidence, base <code>cliany-site cases --case-id &lt;id&gt; --evidence-bundle --json</code> output plus <code>cliany-site cases --case-id &lt;id&gt; --evidence-bundle --doctor-json /tmp/cliany-doctor-preflight.json --json</code> with <code>primary_next_task_runbook</code>, <code>primary_next_task_acceptance_criteria</code>, <code>promotion_command_plan_summary</code>, <code>promotion_command_plan[*].command_sha256</code>, <code>doctor_preflight_evidence_fields</code>, <code>doctor_preflight_evidence_values</code>, <code>doctor_preflight_evidence_ok</code>, <code>doctor_preflight_evidence_missing_count</code>, <code>doctor_preflight_evidence_null_count</code>, <code>doctor_preflight_evidence_null_fields</code>, and <code>doctor_preflight_state</code>, and <code>python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues</code> / <code>issue-metadata.json</code> with <code>candidate_promotions[*].issue_template_command</code>, <code>candidate_promotions[*].issue_template_json_command</code>, <code>candidate_promotions[*].promotion_command_plan_summary</code>, <code>Primary Acceptance Criteria</code>, <code>case_promotion_evidence_primary_llm_live_preflight_required</code>, <code>case_promotion_evidence_primary_llm_live_preflight_command_sha256</code>, <code>case_promotion_evidence_primary_llm_live_preflight_blocker_comment</code>, <code>case_promotion_evidence_primary_doctor_preflight_blocker_comment</code>, <code>case_promotion_evidence_primary_doctor_preflight_evidence_template_sha256</code>, <code>case_promotion_doctor_preflight_evidence_template_sha256</code>, <code>doctor_preflight_evidence_fields</code>, <code>doctor_preflight_state_fields</code>, <code>doctor_preflight_state_statuses</code>, <code>required_labels</code>, <code>required_label_count</code>, <code>required_labels_sha256</code>, and <code>case_promotion_evidence_primary_runbook_steps</code> / hash drift checks.'
  },
  'qs.contribute.queue': {
    zh: '只读取队列的自动化可以通过 <code>promotion_plan.primary_doctor_preflight_evidence_template_sha256</code>、<code>promotion_plan.primary_llm_live_preflight_command_sha256</code>、candidate <code>primary_doctor_preflight_evidence_template_sha256</code>、<code>task_queue[*].doctor_preflight_evidence_template_sha256</code> 和 <code>task_queue[*].llm_live_preflight_command_sha256</code> 比对 doctor 证据模板与 preflight 命令漂移，不必展开完整 evidence bundle。',
    en: 'Queue-only automation can compare doctor evidence and preflight-command drift from <code>promotion_plan.primary_doctor_preflight_evidence_template_sha256</code>, <code>promotion_plan.primary_llm_live_preflight_command_sha256</code>, candidate <code>primary_doctor_preflight_evidence_template_sha256</code>, <code>task_queue[*].doctor_preflight_evidence_template_sha256</code>, and <code>task_queue[*].llm_live_preflight_command_sha256</code> without opening a full evidence bundle.'
  },
  'qs.contribute.validation': {
    zh: '只读取 validation 的自动化可以从 <code>scripts/validate_cases.py --json</code> 的 <code>promotion_evidence_summary.primary_next_task.doctor_preflight_evidence_template_sha256</code>、<code>scripts/validate_cases.py --report</code> 的 <code>primary_doctor_preflight_evidence_template_sha256</code>，或纯文本 <code>scripts/validate_cases.py --strict</code> stdout 的 <code>promotion_evidence_primary_doctor_preflight_evidence_template_sha256</code> / <code>promotion_evidence_primary_llm_live_preflight_command_sha256</code> 读取同源漂移信号。Evidence bundle 还会暴露 <code>doctor_preflight_evidence_selectors</code>，把 <code>checks[llm_live].details.error_code</code> 这类语义字段映射到实际 doctor JSON selector <code>data.checks[name=&quot;llm_live&quot;].details.error_code</code>。',
    en: 'Validation-only automation can read <code>promotion_evidence_summary.primary_next_task.doctor_preflight_evidence_template_sha256</code> from <code>scripts/validate_cases.py --json</code>, <code>primary_doctor_preflight_evidence_template_sha256</code> from <code>scripts/validate_cases.py --report</code>, or <code>promotion_evidence_primary_doctor_preflight_evidence_template_sha256</code> / <code>promotion_evidence_primary_llm_live_preflight_command_sha256</code> from plain <code>scripts/validate_cases.py --strict</code> stdout. Evidence bundles also expose <code>doctor_preflight_evidence_selectors</code>, mapping semantic fields such as <code>checks[llm_live].details.error_code</code> to actual doctor JSON selectors such as <code>data.checks[name=&quot;llm_live&quot;].details.error_code</code>.'
  },
  'qs.contribute.runbook': {
    zh: '推进 PyPI candidate 前，先按 <code>docs/candidate-promotion-runbook.md</code> 的 <code>Candidate Promotion Runbook</code> 跑 <code>cliany-site doctor --llm-live --json</code>、adapter package、metadata validation 和 online smoke；目标包名保持 <code>pypi.org-&lt;version&gt;.cliany-adapter.tar.gz</code>。',
    en: 'Before advancing the PyPI candidate, use the <code>Candidate Promotion Runbook</code> in <code>docs/candidate-promotion-runbook.md</code> for <code>cliany-site doctor --llm-live --json</code>, adapter package, metadata validation, and online smoke; keep the target package name <code>pypi.org-&lt;version&gt;.cliany-adapter.tar.gz</code>.'
  },
  'qs.contribute.goodfirst': {
    zh: '首次贡献者可以从 <code>docs/good-first-issues.md</code> 开始，选择默认离线、可本地验证的任务。',
    en: 'First-time contributors can start from <code>docs/good-first-issues.md</code> for offline, locally verifiable tasks.'
  },
  'qs.maintainer.title': { zh: '维护者循环', en: 'Maintainer Loop' },
  'qs.maintainer.desc': {
    zh: '当前基线：v0.16.275。candidate 晋级输出现在把必需的 live-LLM 预检作为可执行的下一条命令，并将通过预检后的任务命令单独保留，避免在 gate 通过前把 candidate 表述为已就绪。使用每天 1~3 个版本的发布循环、每周维护者循环、release readiness 的 next_actions、官网 alias inspect 和 PyPI 版本专属发布审计，把路线图拆成小而可验证的发布切片。doctor 现在会从打包的 active 案例目录选择无需登录的已发布 demo，并提供固定 GitHub Release URL、SHA-256 安装、verify 和只读命令；它不把 candidate 或第三方在线成功伪装成已验证事实。运行 <code>cliany-site market publish github.com --version 1.0.0 --json</code>；成功输出的 <code>data.package_sha256</code> 是完成归档的 64 个字符小写十六进制 SHA-256 摘要，应交接给安装方。将该值用于通用直接 HTTPS URL 的 <code>--sha256 &lt;64-hex-sha256&gt;</code>，或使用 <code>cliany-site market install &lt;package&gt; --dry-run --json</code> 预检本地包。',
    en: 'Current baseline: v0.16.275. Candidate promotion output now gives the required live-LLM preflight as the executable next command and preserves the post-preflight task command separately, so a candidate is not presented as ready before its gate passes. Use the 1-3 releases/day loop, weekly maintainer loop, release readiness next_actions, website alias inspect, and PyPI version-specific publication audit to turn the roadmap into small verified releases. Doctor now selects a published no-login demo from the packaged active case catalog and provides a pinned GitHub Release URL, SHA-256 install, verify, and read-only command; it does not present a candidate or third-party online success as verified fact. Use <code>cliany-site market publish github.com --version 1.0.0 --json</code>; its successful <code>data.package_sha256</code> is the lowercase 64-character hexadecimal SHA-256 of the completed archive to hand to the installer. Use that value with the generic direct HTTPS URL and <code>--sha256 &lt;64-hex-sha256&gt;</code>, or run <code>cliany-site market install &lt;package&gt; --dry-run --json</code> for a local preflight.'
  },
  'qs.maintainer.loop': {
    zh: '选择下一块发布切片时，从 <code>docs/weekly-maintainer-loop.md</code> 开始。',
    en: 'Start from <code>docs/weekly-maintainer-loop.md</code> when choosing the next release slice.'
  },
  'qs.maintainer.actions': {
    zh: '读取 <code>python scripts/release_readiness.py --json</code> 或 <code>python scripts/check_release_cadence.py --json</code> 输出的 <code>next_actions</code>、<code>weekly_commit_cadence_ok</code>、<code>release_count_today</code>、<code>max_daily_releases</code>、<code>daily_release_limit_ok</code>、<code>daily_release_cap_blocked</code> 和 <code>daily_release_resume_date</code>；daily cap 暂停时，<code>release_readiness.py --json</code> 还会输出 <code>daily_release_resume_command</code> 和 <code>daily_release_resume_command_sha256</code>。发布后用 <code>python scripts/check_release_publication.py --remote --distribution --json</code> 核对 GitHub Release、<code>pypi_version</code>、<code>pypi_latest_version</code> 与 <code>pypi_release_version</code>。',
    en: 'Read <code>next_actions</code>, <code>weekly_commit_cadence_ok</code>, <code>release_count_today</code>, <code>max_daily_releases</code>, <code>daily_release_limit_ok</code>, <code>daily_release_cap_blocked</code>, and <code>daily_release_resume_date</code> from <code>python scripts/release_readiness.py --json</code> or <code>python scripts/check_release_cadence.py --json</code>; when the daily cap pauses a tag, <code>release_readiness.py --json</code> also exposes <code>daily_release_resume_command</code> and <code>daily_release_resume_command_sha256</code>. After release, confirm GitHub Release plus <code>pypi_version</code>, <code>pypi_latest_version</code>, and <code>pypi_release_version</code> with <code>python scripts/check_release_publication.py --remote --distribution --json</code>.'
  },

  'obscura.title': { zh: '实验性功能：Obscura Browser Provider', en: 'Experimental: Obscura Browser Provider' },
  'obscura.desc': { zh: 'Obscura 是一个轻量级的浏览器替代方案，目前处于实验阶段。Chrome 仍然是默认 provider。', en: 'Obscura is a lightweight alternative to Chrome, currently in experimental status. Chrome remains the default provider.' },
  'obscura.limitation': { zh: '<strong>探索不支持：</strong>Obscura 尚未支持 AXTree 探索功能。请仅用于执行已有的适配器。', en: '<strong>Explore Not Supported:</strong> Obscura does not yet support AXTree exploration. Use it for executing existing adapters.' },
  'obscura.platforms': { zh: '<strong>支持平台：</strong> <code>darwin-arm64</code>, <code>darwin-x86_64</code>, <code>linux-x86_64</code>, <code>windows-x86_64</code>', en: '<strong>Platforms:</strong> <code>darwin-arm64</code>, <code>darwin-x86_64</code>, <code>linux-x86_64</code>, <code>windows-x86_64</code>' },
  'obscura.lifecycle': { zh: '<strong>生命周期命令：</strong> <code>install / use / status / clean / rollback / upgrade / doctor</code>', en: '<strong>Lifecycle Commands:</strong> <code>install / use / status / clean / rollback / upgrade / doctor</code>' },

  'feedback.title': { zh: '一起完善下一个工作流', en: 'Help shape the next workflow' },
  'feedback.subtitle': { zh: '目标 URL、预期结果和可复现步骤，是最有价值的反馈。', en: 'A target URL, expected result, and reproducible steps are the most useful feedback.' },
  'feedback.bug.title': { zh: '遇到问题了', en: 'Something broke' },
  'feedback.bug.body': { zh: '告诉我们你的预期，以及实际发生了什么。', en: 'Tell us what you expected and what happened instead.' },
  'feedback.bug.cta': { zh: '提交 Bug', en: 'Report a bug' },
  'feedback.feature.title': { zh: '想自动化一个流程', en: 'Want an automation' },
  'feedback.feature.body': { zh: '描述你想变成命令的重复浏览器任务。', en: 'Describe the repeated browser task you want to turn into a command.' },
  'feedback.feature.cta': { zh: '提交功能建议', en: 'Request a feature' },
  'feedback.case.title': { zh: '有公开工作流可分享', en: 'Have a public workflow' },
  'feedback.case.body': { zh: '分享其他人也能验证的安全、只读场景。', en: 'Share a safe, read-only scenario that other people can verify.' },
  'feedback.case.cta': { zh: '提交案例建议', en: 'Propose a workflow' },

  'copy.btn': { zh: '复制', en: 'Copy' },
  'copy.done': { zh: '已复制 ✓', en: 'Copied ✓' },

  'footer.desc': { zh: '将任意网页操作自动化为 CLI 命令', en: 'Automate any web action into CLI commands' },
  'footer.docs': { zh: '文档', en: 'Docs' },
  'footer.quickstart': { zh: '快速开始', en: 'Quick Start' },
  'footer.feedback': { zh: '反馈', en: 'Feedback' },
  'footer.github': { zh: 'GitHub', en: 'GitHub' },
  'footer.built': { zh: '基于 Python、Chrome CDP 和 LLM 构建', en: 'Built with Python, Chrome CDP & LLM' },
  'footer.copyright': { zh: '© 2024-2026 cliany-site', en: '© 2024-2026 cliany-site' },

  'aria.menuToggle': { zh: '切换导航', en: 'Toggle navigation' },
  'aria.langToggle': { zh: '语言切换', en: 'Language' },
  'aria.copyBtn': { zh: '复制到剪贴板', en: 'Copy to clipboard' },
  'aria.github': { zh: 'GitHub', en: 'GitHub' },

  'terminal.cmd1': {
    zh: '$ cliany-site explore "https://github.com" "搜索仓库并查看 README"',
    en: '$ cliany-site explore "https://github.com" "Search repos and view README"'
  },
  'terminal.cmd2': {
    zh: '$ cliany-site github.com search --query "cliany-site" --json',
    en: '$ cliany-site github.com search --query "cliany-site" --json'
  },

  'meta.title': {
    zh: 'cliany-site | 让浏览器工作流可以复用',
    en: 'cliany-site | Make browser work reusable'
  },
  'meta.description': {
    zh: '把重复的浏览器工作转成可复用的 CLI 命令。安装 cliany-site、检查就绪状态，然后自动化你的下一个工作流。',
    en: 'Turn repeated browser work into reusable CLI commands. Install cliany-site, check readiness, and automate your next workflow.'
  },
  'meta.og.description': {
    zh: '把重复的浏览器工作转成可复用的 CLI 命令，从快速就绪检查开始。',
    en: 'Turn repeated browser work into reusable CLI commands — start with a quick readiness check.'
  },

  // --- Nav: Use Cases ---
  'nav.usecases': { zh: '案例', en: 'Use Cases' },

  // --- Use Cases Section ---
  'usecases.title': { zh: '真实场景', en: 'Real-World Use Cases' },
  'usecases.subtitle': { zh: '一次探索，永久拥有你的专属 CLI', en: 'Explore once, own your CLI forever' },
  'usecases.badge.conceptual': { zh: '概念展示', en: 'CONCEPT' },

  // --- Shared Tab Labels ---
  'usecases.tab.before': { zh: '之前', en: 'BEFORE' },
  'usecases.tab.after': { zh: '之后', en: 'AFTER' },

  // --- Case 1: GitHub ---
  'usecases.case1.title': { zh: 'GitHub 变成你的命令行', en: 'GitHub as Your CLI' },
  'usecases.case1.desc': {
    zh: '还在手动点击 GitHub 搜索仓库、查看 README？现在，一行命令搞定一切。',
    en: 'Tired of repetitive clicks on GitHub? Search repos and view READMEs directly from your terminal.'
  },
  'usecases.case1.before': { zh: '打开浏览器 → 输入网址 → 搜索关键词 → 点击仓库 → 查看 README', en: 'Browser → Search → Click repo → View README' },
  'usecases.case1.before.steps': { zh: '5 步操作 · 约 30 秒', en: '5 steps · ~30s' },
  'usecases.case1.after': { zh: '一行命令，结构化 JSON 输出，可管道组合', en: 'Single command, structured JSON, pipe-friendly' },
  'usecases.case1.after.steps': { zh: '1 条命令 · 秒级响应', en: '1 command · Instant' },

  // --- Case 2: CRM ---
  'usecases.case2.title': { zh: '企业 CRM：登录后只读查询', en: 'Enterprise CRM: Login & Query' },
  'usecases.case2.desc': {
    zh: '公开 SuiteCRM demo 演示：先 login 保存 session，后续查询无需打开浏览器。',
    en: 'SuiteCRM public demo: login once to save session, then query without a browser.'
  },
  'usecases.case2.before': { zh: '登录 CRM → 找 Accounts → 翻页查 5 条客户', en: 'Login → CRM → Search → View 5 accounts' },
  'usecases.case2.before.steps': { zh: '5 步 · 约 1 分钟', en: '5 steps · ~1m' },
  'usecases.case2.after': { zh: '一次 login，后续 `list-accounts --json`', en: 'Login once, then `list-accounts --json`' },
  'usecases.case2.after.steps': { zh: '1 条命令 · 秒级', en: '1 command · Instant' },

  // --- Case 3: Team Toolbox ---
  'usecases.case3.title': { zh: 'Apache 开源工具聚合：Jira / Wiki / Jenkins', en: 'Apache OSS Tools: Jira / Wiki / Jenkins Aggregated' },
  'usecases.case3.desc': {
    zh: '同一 CLI 风格，覆盖三个公开开源项目工具站，跨平台聚合查询。',
    en: 'Same CLI style across three open-source project tools — cross-platform aggregated queries.'
  },
  'usecases.case3.before': { zh: '在 3 个 Web UI 切换、搜索、复制', en: 'Switch & search across 3 web UIs' },
  'usecases.case3.before.steps': { zh: '多窗口切换 · 上下文丢失', en: 'Multi-tab · Context loss' },
  'usecases.case3.after': { zh: 'shell 脚本三命令聚合查询', en: 'Three CLI commands aggregate the data' },
  'usecases.case3.after.steps': { zh: '统一 JSON · 可管道', en: 'Unified JSON · Pipe-friendly' },

  // --- Terminal Result Lines ---
  'usecases.case1.terminal.result': { zh: '✓ 适配器已生成至 ~/.cliany-site/adapters/github.com/', en: '✓ Adapter generated at ~/.cliany-site/adapters/github.com/' },
  'usecases.case2.terminal.result': { zh: '✓ Session 已保存：demo.suiteondemand.com', en: '✓ Session saved for demo.suiteondemand.com' },
  'usecases.case3.terminal.result': { zh: '{"ok": true, "data": {"jobs": [...] }}', en: '{"ok": true, "data": {"jobs": [...]}}' },

  // --- v0.11.0 / v0.10.x Features ---
  'features.healer.title': { zh: '智能自愈', en: 'Smart Self-Healing' },
  'features.healer.desc': { zh: 'AXTree 快照对比，selector 热修复，无需重新 explore。', en: 'AXTree snapshot diffing, hot-patch selectors without re-exploring.' },
  'features.domPruning.title': { zh: '智能 DOM 剪枝', en: 'Smart DOM Pruning' },
  'features.domPruning.desc': { zh: '4 层 AXTree 剪枝，大幅降低复杂页面的 LLM Token 消耗。', en: '4-layer AXTree pruning reduces LLM token usage by up to 50% for complex pages.' },
  'features.lazyLoad.title': { zh: '延迟加载 Registry', en: 'Lazy Adapter Registry' },
  'features.lazyLoad.desc': { zh: '按需加载适配器，CLI 启动速度提升 2-5 倍。', en: 'On-demand adapter loading accelerates CLI startup times significantly.' },
  'features.diagnostic.title': { zh: '诊断模式', en: 'Diagnostic Mode' },
  'features.diagnostic.desc': { zh: 'AI 驱动的根本原因分析，快速定位命令执行失败原因。', en: 'AI-powered root cause analysis for command execution failures.' },
  'features.metadata.title': { zh: 'Metadata Schema v3', en: 'Metadata Schema v3' },
  'features.metadata.desc': { zh: '强制使用 v3 metadata，提供 migrate 工具自动升级旧适配器。', en: 'Enforces v3 metadata with `migrate` utility to auto-upgrade legacy adapters.' }
};

function getLang() {
  var saved;
  try { saved = localStorage.getItem('cliany-lang'); } catch(e) {}
  if (saved === 'en' || saved === 'zh') return saved;
  return navigator.language && navigator.language.startsWith('zh') ? 'zh' : 'en';
}

function setLang(lang) {
  if (lang !== 'en' && lang !== 'zh') lang = 'en';

  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.documentElement.dataset.lang = lang;
  try { localStorage.setItem('cliany-lang', lang); } catch(e) {}

  document.querySelectorAll('[data-i18n]').forEach(function(el) {
    var key = el.getAttribute('data-i18n');
    var entry = I18N[key];
    if (entry) {
      if (entry[lang].indexOf('<') !== -1) {
        el.innerHTML = entry[lang];
      } else {
        el.textContent = entry[lang];
      }
    }
  });

  if (window._terminalRestart) {
    window._terminalRestart(lang);
  } else {
    document.querySelectorAll('[data-i18n-text]').forEach(function(el) {
      var key = el.getAttribute('data-i18n-text');
      var entry = I18N[key];
      if (entry) {
        el.setAttribute('data-text', entry[lang]);
        if (el.classList.contains('done')) {
          el.textContent = entry[lang];
        }
      }
    });
  }

  document.querySelectorAll('[data-i18n-aria]').forEach(function(el) {
    var key = el.getAttribute('data-i18n-aria');
    var entry = I18N[key];
    if (entry) el.setAttribute('aria-label', entry[lang]);
  });

  var titleEntry = I18N['meta.title'];
  if (titleEntry) document.title = titleEntry[lang];

  var descMeta = document.querySelector('meta[name="description"]');
  var descEntry = I18N['meta.description'];
  if (descMeta && descEntry) descMeta.setAttribute('content', descEntry[lang]);

  var ogDescMeta = document.querySelector('meta[property="og:description"]');
  var ogDescEntry = I18N['meta.og.description'];
  if (ogDescMeta && ogDescEntry) ogDescMeta.setAttribute('content', ogDescEntry[lang]);

  var ogTitleMeta = document.querySelector('meta[property="og:title"]');
  if (ogTitleMeta && titleEntry) ogTitleMeta.setAttribute('content', titleEntry[lang]);

  var toggle = document.querySelector('.lang-toggle');
  if (toggle) {
    toggle.dataset.active = lang;
    toggle.querySelectorAll('.lang-option').forEach(function(btn) {
      var isActive = btn.dataset.lang === lang;
      btn.setAttribute('aria-checked', isActive ? 'true' : 'false');
      btn.setAttribute('tabindex', isActive ? '0' : '-1');
    });
  }
}

document.addEventListener('DOMContentLoaded', function() {
  setLang(getLang());
  document.body.style.visibility = 'visible';

  var toggle = document.querySelector('.lang-toggle');
  if (toggle) {
    var langOptions = toggle.querySelectorAll('.lang-option');
    langOptions.forEach(function(btn) {
      btn.addEventListener('click', function() {
        var lang = btn.dataset.lang;
        if (!lang) return;
        setLang(lang);
      });

      btn.addEventListener('touchstart', function() {
        var lang = btn.dataset.lang;
        if (!lang) return;
        setLang(lang);
      }, { passive: true });
    });

    toggle.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        var newLang = toggle.dataset.active === 'zh' ? 'en' : 'zh';
        setLang(newLang);
        var target = toggle.querySelector('.lang-option[data-lang="' + newLang + '"]');
        if (target) target.focus();
      }
    });
  }

  var revealElements = document.querySelectorAll('.reveal');

  if ('IntersectionObserver' in window) {
    var revealOptions = {
      threshold: 0.1,
      rootMargin: "0px 0px -50px 0px"
    };

    var revealObserver = new IntersectionObserver(function(entries, observer) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');

          if (entry.target.classList.contains('features-grid') ||
              entry.target.classList.contains('steps-flow') ||
              entry.target.classList.contains('qs-grid')) {
            var children = entry.target.children;
            Array.from(children).forEach(function(child, index) {
              child.style.transitionDelay = index * 100 + 'ms';
            });
          }

          observer.unobserve(entry.target);
        }
      });
    }, revealOptions);

    revealElements.forEach(function(el) { revealObserver.observe(el); });
  } else {
    revealElements.forEach(function(el) { el.classList.add('visible'); });
  }

  var heroTerminal = document.getElementById('hero-terminal');
  if (heroTerminal) {
    var typeLines = heroTerminal.querySelectorAll('.type-line');
    var resultLines = heroTerminal.querySelectorAll('.result-lines');
    var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var terminalTimers = [];

    var clearTerminalTimers = function() {
      terminalTimers.forEach(function(id) { clearTimeout(id); });
      terminalTimers = [];
    };

    window._terminalRestart = function(lang) {
      clearTerminalTimers();
      typeLines.forEach(function(line) {
        var key = line.getAttribute('data-i18n-text');
        var entry = I18N[key];
        if (entry) {
          line.setAttribute('data-text', entry[lang]);
          if (line.classList.contains('done')) {
            line.textContent = entry[lang];
          }
        }
      });
    };

    if (prefersReducedMotion) {
      typeLines.forEach(function(line) {
        line.textContent = line.getAttribute('data-text');
        line.classList.add('done');
      });
      resultLines.forEach(function(res) { res.classList.add('visible'); });
    } else {
      var currentLineIndex = 0;
      var typingCancelled = false;

      var typeText = function(element, text, speed, callback) {
        var i = 0;
        element.textContent = '';
        typingCancelled = false;

        var typeChar = function() {
          if (typingCancelled) return;
          if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            var tid = setTimeout(typeChar, speed + (Math.random() * 20));
            terminalTimers.push(tid);
          } else {
            element.classList.add('done');
            if (callback) {
              var tid = setTimeout(callback, 200);
              terminalTimers.push(tid);
            }
          }
        };
        typeChar();
      };

      var animateTerminal = function() {
        if (typingCancelled) return;
        if (currentLineIndex < typeLines.length) {
          var currentLine = typeLines[currentLineIndex];
          var text = currentLine.getAttribute('data-text');

          typeText(currentLine, text, 30, function() {
            if (resultLines[currentLineIndex]) {
              resultLines[currentLineIndex].classList.add('visible');
            }
            currentLineIndex++;
            var tid = setTimeout(animateTerminal, 600);
            terminalTimers.push(tid);
          });
        }
      };

      window._terminalRestart = function(lang) {
        typingCancelled = true;
        clearTerminalTimers();
        currentLineIndex = 0;

        typeLines.forEach(function(line) {
          var key = line.getAttribute('data-i18n-text');
          var entry = I18N[key];
          if (entry) {
            line.setAttribute('data-text', entry[lang]);
          }
          if (line.classList.contains('done')) {
            if (entry) line.textContent = entry[lang];
          } else {
            line.textContent = '';
            line.classList.remove('done');
          }
        });
        resultLines.forEach(function(res) {
          if (!res.classList.contains('visible')) return;
          /* keep already-revealed results visible */
        });

        /* Restart animation from where incomplete lines begin */
        for (var idx = 0; idx < typeLines.length; idx++) {
          if (!typeLines[idx].classList.contains('done')) {
            currentLineIndex = idx;
            typingCancelled = false;
            var tid = setTimeout(animateTerminal, 300);
            terminalTimers.push(tid);
            return;
          }
        }
        /* All lines done — just update text, no restart needed */
      };

      var tid = setTimeout(animateTerminal, 1000);
      terminalTimers.push(tid);
    }
  }

  var copyButtons = document.querySelectorAll('.copy-btn');
  copyButtons.forEach(function(btn) {
    btn.addEventListener('click', function() {
      var textToCopy = btn.getAttribute('data-clipboard');

      navigator.clipboard.writeText(textToCopy).then(function() {
        var lang = document.documentElement.dataset.lang || 'zh';
        var doneEntry = I18N['copy.done'];
        btn.textContent = doneEntry ? doneEntry[lang] : '已复制 ✓';
        btn.style.backgroundColor = '#D97757';
        btn.style.color = '#FAFAF8';
        btn.style.borderColor = '#D97757';

        setTimeout(function() {
          var btnEntry = I18N['copy.btn'];
          btn.textContent = btnEntry ? btnEntry[lang] : '复制';
          btn.style.backgroundColor = '';
          btn.style.color = '';
          btn.style.borderColor = '';
        }, 2000);
      }).catch(function(err) {
        console.error('Failed to copy: ', err);
      });
    });
  });

  var menuToggle = document.querySelector('.menu-toggle');
  var navLinks = document.querySelector('.nav-links');
  var navLinksItems = document.querySelectorAll('.nav-link, .nav-cta');

  if (menuToggle && navLinks) {
    menuToggle.addEventListener('click', function() {
      var isOpen = navLinks.classList.toggle('active');
      menuToggle.setAttribute('aria-expanded', isOpen);
    });

    navLinksItems.forEach(function(item) {
      item.addEventListener('click', function() {
        navLinks.classList.remove('active');
        menuToggle.setAttribute('aria-expanded', 'false');
      });
    });

    document.addEventListener('click', function(e) {
      if (!e.target.closest('.navbar')) {
        navLinks.classList.remove('active');
        menuToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      var targetId = this.getAttribute('href');
      if (targetId === '#') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
      }

      var targetElement = document.querySelector(targetId);
      if (targetElement) {
        var headerOffset = 70;
        var elementPosition = targetElement.getBoundingClientRect().top;
        var offsetPosition = elementPosition + window.pageYOffset - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth'
        });
      }
    });
  });

  var useCasesSection = document.getElementById('use-cases');
  if (useCasesSection) {
    useCasesSection.addEventListener('click', function(e) {
      var tab = e.target.closest('.case-tab');
      if (!tab) return;
      
      var comparison = tab.closest('.case-comparison');
      if (!comparison) return;
      
      var tabs = comparison.querySelectorAll('.case-tab');
      for (var i = 0; i < tabs.length; i++) {
        tabs[i].classList.remove('active');
      }
      tab.classList.add('active');
      
      var panels = comparison.querySelectorAll('.case-panel');
      for (var j = 0; j < panels.length; j++) {
        panels[j].classList.remove('active');
      }
      
      var targetId = tab.getAttribute('data-target');
      if (targetId) {
        var targetPanel = document.getElementById(targetId);
        if (targetPanel) {
          targetPanel.classList.add('active');
        }
      }
    });
  }

  var case1Terminal = document.getElementById('case1-terminal');
  if (case1Terminal) {
    var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    var case1Observer = new IntersectionObserver(function(entries, observer) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          observer.unobserve(entry.target);
          
          var typeLines = entry.target.querySelectorAll('.case-type-line');
          
          function typeLine(index) {
            if (index >= typeLines.length) return;
            
            var line = typeLines[index];
            var text = line.getAttribute('data-text') || '';
            var resultDiv = line.nextElementSibling;
            
            line.classList.add('animated');
            
            if (prefersReducedMotion) {
              line.textContent = text;
              if (resultDiv && resultDiv.classList.contains('result-lines')) {
                resultDiv.classList.add('visible');
              }
              typeLine(index + 1);
              return;
            }
            
            line.textContent = '';
            var charIndex = 0;
            
            function typeChar() {
              if (charIndex < text.length) {
                line.textContent += text.charAt(charIndex);
                charIndex++;
                setTimeout(typeChar, 30 + Math.random() * 20);
              } else {
                if (resultDiv && resultDiv.classList.contains('result-lines')) {
                  resultDiv.classList.add('visible');
                }
                setTimeout(function() {
                  typeLine(index + 1);
                }, 600);
              }
            }
            
            typeChar();
          }
          
          typeLine(0);
        }
      });
    }, { threshold: 0.3 });
    
    case1Observer.observe(case1Terminal);
  }
});
