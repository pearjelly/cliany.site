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
  'features.subtitle': { zh: '十大核心能力，从探索到执行', en: 'Ten core capabilities, from exploration to execution' },
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
    zh: '从工作流中自动提取可复用的原子操作，跨适配器共享登录、搜索等通用步骤，参数化执行。',
    en: 'Auto-extract reusable atomic actions from workflows. Share common steps like login and search across adapters with parameterized execution.'
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
  }
};

function getLang() {
  var saved;
  try { saved = localStorage.getItem('cliany-lang'); } catch(e) {}
  if (saved === 'en' || saved === 'zh') return saved;
  return navigator.language && navigator.language.startsWith('zh') ? 'zh' : 'en';
}

function setLang(lang) {
  if (lang !== 'en' && lang !== 'zh') lang = 'zh';

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
});
