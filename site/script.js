const I18N = {
  'nav.features': { zh: '功能', en: 'Features' },
  'nav.how': { zh: '工作原理', en: 'How It Works' },
  'nav.quickstart': { zh: '快速开始', en: 'Get Started' },
  'nav.cta': { zh: '开始使用', en: 'Get Started' },

  'hero.title': { zh: '将浏览器操作，变成命令行指令', en: 'Turn Browser Actions into CLI Commands' },
  'hero.subtitle': {
    zh: '基于 LLM 与 Chrome CDP 协议，cliany-site 自动探索网页工作流，生成可复用的 CLI 命令。像调用脚本一样操控任何网站。',
    en: 'Powered by LLM and Chrome CDP, cliany-site automatically explores web workflows and generates reusable CLI commands. Control any website like calling a script.'
  },
  'hero.cta': { zh: '开始使用', en: 'Get Started' },
  'hero.github': { zh: '查看 GitHub →', en: 'View on GitHub →' },

  'terminal.connecting': { zh: '✓ 正在连接 Chrome CDP...', en: '✓ Connecting to Chrome CDP...' },
  'terminal.analyzing': { zh: '✓ 正在分析页面结构...', en: '✓ Analyzing page structure...' },
  'terminal.planning': { zh: '✓ LLM 规划工作流...', en: '✓ LLM planning workflow...' },
  'terminal.generated': {
    zh: '✓ 生成 CLI 命令至 ~/.cliany-site/adapters/github.com/',
    en: '✓ CLI commands generated to ~/.cliany-site/adapters/github.com/'
  },

  'features.title': { zh: '核心特性', en: 'Core Features' },
  'features.subtitle': { zh: '4 个核心能力 + 12 个扩展能力', en: '4 core capabilities + 12 extended capabilities' },
  'features.focus.badge': { zh: '核心', en: 'CORE' },
  'features.more.title': { zh: '扩展能力（12）', en: 'Extended Capabilities (12)' },
  'features.more.subtitle': { zh: '默认隐藏复杂度，需要时再打开。', en: 'Hide complexity by default, unlock it when needed.' },
  'features.value.text': { zh: '先用核心 4 项打通路径，再按需启用扩展能力。', en: 'Start with the core four, then enable advanced capabilities on demand.' },
  'features.focus.explore.desc': { zh: 'AXTree 无注入探索，快速定位可自动化路径。', en: 'Injection-free AXTree exploration to quickly locate automatable paths.' },
  'features.focus.llm.desc': { zh: '把页面语义直接转成可执行 CLI 命令。', en: 'Turn page semantics directly into executable CLI commands.' },
  'features.focus.json.desc': { zh: '统一 {success,data,error}，自动化易集成。', en: 'Unified {success,data,error} output for easy automation integration.' },
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
    zh: '所有命令支持 --json 选项，输出统一 {success, data, error} 信封格式，方便管道和自动化集成。',
    en: 'All commands support --json, outputting a unified {success, data, error} envelope for easy piping and automation.'
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

  'qs.title': { zh: '快速开始', en: 'Quick Start' },
  'qs.subtitle': { zh: '五分钟完成安装与配置', en: 'Set up in five minutes' },
  'qs.step1': { zh: 'Step 1: 安装', en: 'Step 1: Install' },
  'qs.step2': { zh: 'Step 2: 配置 LLM', en: 'Step 2: Configure LLM' },
  'qs.step3': { zh: 'Step 3: Chrome 配置', en: 'Step 3: Chrome Setup' },
  'qs.step4': { zh: 'Step 4: 开始探索', en: 'Step 4: Start Exploring' },

  'copy.btn': { zh: '复制', en: 'Copy' },
  'copy.done': { zh: '已复制 ✓', en: 'Copied ✓' },

  'footer.desc': { zh: '将任意网页操作自动化为 CLI 命令', en: 'Automate any web action into CLI commands' },
  'footer.docs': { zh: '文档', en: 'Docs' },
  'footer.quickstart': { zh: '快速开始', en: 'Quick Start' },
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
    zh: 'cliany-site | 将浏览器操作变成命令行指令',
    en: 'cliany-site | Turn Browser Actions into CLI Commands'
  },
  'meta.description': {
    zh: '基于 LLM 与 Chrome CDP 协议，cliany-site 自动探索网页工作流，生成可复用的 CLI 命令。像调用脚本一样操控任何网站。',
    en: 'Powered by LLM and Chrome CDP, cliany-site automatically explores web workflows and generates reusable CLI commands. Control any website like calling a script.'
  },
  'meta.og.description': {
    zh: '基于 LLM 与 Chrome CDP 协议，自动探索网页工作流，生成可复用的 CLI 命令。',
    en: 'Powered by LLM and Chrome CDP — automatically explore web workflows and generate reusable CLI commands.'
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
  'usecases.case2.title': { zh: '没有 API？自己造一个', en: 'No API? Build Your Own' },
  'usecases.case2.desc': {
    zh: '企业 CRM 没 API，查个客户要点 7 个页面？cliany-site 为任何网站生成专属 CLI。',
    en: 'Stuck with a legacy CRM with no API? Generate a dedicated CLI for any web portal in minutes.'
  },
  'usecases.case2.before': { zh: '登录 → 侧边栏 → 客户管理 → 搜索 → 点详情 → 切订单 → 筛选', en: 'Login → CRM → Search → Details → Orders → Filter' },
  'usecases.case2.before.steps': { zh: '7 步操作 · 约 2 分钟', en: '7 steps · ~2m' },
  'usecases.case2.after': { zh: '管道组合，直接抽取订单数据', en: 'Extract structured data with pipes' },
  'usecases.case2.after.steps': { zh: '1 条命令 · 秒级响应', en: '1 command · Instant' },

  // --- Case 3: Team Toolbox ---
  'usecases.case3.title': { zh: '团队工具箱：一人探索，全队受益', en: 'Team Toolbox' },
  'usecases.case3.desc': {
    zh: '团队有 10 个内部平台，新人入职学 2 周？资深工程师一次探索，全队永久受益。',
    en: 'Stop wasting time on internal portal onboarding. Explore once, share adapters, and level up the whole team.'
  },
  'usecases.case3.before': { zh: '10 份操作文档 + 每天问 5 次「这个功能在哪」', en: '10+ docs + constant "where is this?" questions' },
  'usecases.case3.before.steps': { zh: '碎片化知识 · 高依赖成本', en: 'Fragmented knowledge · High friction' },
  'usecases.case3.after': { zh: '安装团队工具箱，所有平台一键调用', en: 'Install shared adapters for instant access' },
  'usecases.case3.after.steps': { zh: '统一 CLI · 零学习成本', en: 'Unified CLI · Zero learning curve' },

  // --- Terminal Result Lines ---
  'usecases.case1.terminal.result': { zh: '✓ 适配器已生成至 ~/.cliany-site/adapters/github.com/', en: '✓ Adapter generated at ~/.cliany-site/adapters/github.com/' },
  'usecases.case3.terminal.result': { zh: '✓ 已安装: jira.company.com, confluence.company.com, jenkins.company.com', en: '✓ Installed: jira.company.com, confluence.company.com, jenkins.company.com' },

  // --- v0.9.x New Features ---
  'features.healer.title': { zh: '智能自愈', en: 'Smart Self-Healing' },
  'features.healer.desc': { zh: 'AXTree 快照对比，selector 热修复，无需重新 explore。', en: 'AXTree snapshot diffing, hot-patch selectors without re-exploring.' },
  'features.verify.title': { zh: '静态校验', en: 'Static Verification' },
  'features.verify.desc': { zh: '不打开浏览器，校验 adapter schema、签名、依赖完整性。', en: 'Verify adapter schema, signature, and dependency integrity without launching a browser.' },
  'features.explain.title': { zh: '自描述契约', en: 'Self-Describing Contract' },
  'features.explain.desc': { zh: '`--explain` 输出机器可读的 Agent 契约，便于自动化集成。', en: '`--explain` outputs a machine-readable Agent contract for automation integration.' },
  'features.atomCommands.title': { zh: '原子命令系统', en: 'Atom Commands System' },
  'features.atomCommands.desc': { zh: 'Generated commands 复用原子操作而非内嵌 CDP，跨适配器共享。', en: 'Generated commands reuse atomic operations instead of inlined CDP, shared across adapters.' },
  'features.metadata.title': { zh: 'Metadata Schema v2', en: 'Metadata Schema v2' },
  'features.metadata.desc': { zh: '强制使用 v2 metadata，旧 adapter 自动拒绝并提示重新探索。', en: 'Enforces v2 metadata; legacy adapters auto-rejected with re-explore hint.' }
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
    if (entry) el.textContent = entry[lang];
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
