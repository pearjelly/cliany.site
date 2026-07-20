# First-success conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the README and static marketing site lead visitors to a quick, verifiable first success and present clear feedback paths.

**Architecture:** Keep the product and site static. A shell regression check protects the conversion contract: concise README start paths, valid site anchors, bilingual translation keys, copyable commands, and the three GitHub issue forms. The READMEs own onboarding copy; the HTML, translation map, and stylesheet own the equivalent site presentation.

**Tech Stack:** Markdown, static HTML, CSS, vanilla JavaScript, Bash, Python 3 standard library.

## Global Constraints

- Do not change adapter execution, package release automation, the case catalogue, or generated adapter code. The `doctor` onboarding summary may add a release-agnostic case-discovery route.
- Keep English and Simplified Chinese user-facing copy equivalent.
- Use `pip install cliany-site`, `cliany-site doctor`, and `cliany-site cases` as the release-agnostic first-success route.
- Do not place version-pinned adapter archive filenames in the first-success path.
- Use only the tracked GitHub issue forms: `bug_report.yml`, `feature_request.yml`, and `case_proposal.yml`.
- Add no runtime dependencies, analytics, forms, authentication, or backend services.
- Use shell QA rather than adding pytest-only documentation tests.
- Do not publish the Vercel site without an explicit user request.

### v0.16.266 alignment

The follow-up preserves the `demo_adapter_quickstart` JSON field for compatibility, but makes `case_catalog_quickstart` the recommended first-success route because no referenced release asset is currently published. It keeps the first-success path honest while users review maintained cases and their validation paths.

---

### Task 1: Turn both READMEs into an onboarding funnel

**Files:**

- Create: `qa/test_site_conversion.sh`
- Modify: `qa/run_all.sh`
- Modify: `README.md:1-23`
- Modify: `README.zh.md:1-24`

**Interfaces:**

- Consumes: `.github/ISSUE_TEMPLATE/{bug_report,feature_request,case_proposal}.yml` and `docs/quickstart-10min.md`.
- Produces: matching English/Chinese first-success paths and a focused shell regression check.

- [ ] **Step 1: Write the failing README conversion check**

Create `qa/test_site_conversion.sh` with this exact initial contract. It follows the existing QA counter convention and finds the repository root independently of the caller's current directory.

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0

pass() { printf '[PASS] %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf '[FAIL] %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }

assert_contains() {
  local file="$1" text="$2" label="$3"
  if grep -Fq -- "$text" "$file"; then pass "$label"; else fail "$label"; fi
}

assert_before() {
  local file="$1" first="$2" second="$3" label="$4"
  local first_line second_line
  first_line="$(grep -n -F -- "$first" "$file" | head -n 1 | cut -d: -f1 || true)"
  second_line="$(grep -n -F -- "$second" "$file" | head -n 1 | cut -d: -f1 || true)"
  if [ -n "$first_line" ] && [ -n "$second_line" ] && [ "$first_line" -lt "$second_line" ]; then
    pass "$label"
  else
    fail "$label"
  fi
}

assert_not_in_first_lines() {
  local file="$1" text="$2" label="$3"
  if head -n 35 "$file" | grep -Fq -- "$text"; then fail "$label"; else pass "$label"; fi
}

for template in bug_report.yml feature_request.yml case_proposal.yml; do
  if [ -f "$ROOT_DIR/.github/ISSUE_TEMPLATE/$template" ]; then
    pass "tracked issue template: $template"
  else
    fail "tracked issue template: $template"
  fi
done

for readme in README.md README.zh.md; do
  path="$ROOT_DIR/$readme"
  feature_heading="## Features"
  if [ "$readme" = "README.zh.md" ]; then feature_heading="## 特性"; fi
  assert_contains "$path" "pip install cliany-site" "$readme installs from PyPI"
  assert_contains "$path" "cliany-site doctor" "$readme explains doctor"
  assert_contains "$path" "cliany-site cases" "$readme explains maintained cases"
  assert_before "$path" "## Start here" "$feature_heading" "$readme puts onboarding before features"
  assert_not_in_first_lines "$path" "v0.14" "$readme removes old v0.14 notices from its opening"
done

for readme in README.md README.zh.md; do
  path="$ROOT_DIR/$readme"
  for template in bug_report.yml feature_request.yml case_proposal.yml; do
    assert_contains "$path" "issues/new?template=$template" "$readme links $template"
  done
done

printf '\nSite conversion checks: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
```

Add this line immediately after `run_script "$SCRIPT_DIR/doctor_check.sh"` in `qa/run_all.sh` and make the new file executable:

```bash
run_script "$SCRIPT_DIR/test_site_conversion.sh"
chmod +x qa/test_site_conversion.sh
```

- [ ] **Step 2: Run the check to verify the current README fails**

Run:

```bash
bash qa/test_site_conversion.sh
```

Expected: non-zero exit with failures for the missing `## Start here` section, feedback links, and old v0.14 notices in the opening block.

- [ ] **Step 3: Replace the README openings with the conversion copy**

In `README.md`, retain badges and the language line, remove the historical release-announcement block, and replace the text through the existing `## Features` heading with:

```markdown
> Turn repeated browser workflows into reusable CLI commands.

cliany-site observes a browser workflow through Chrome CDP, uses an LLM to turn it into a site-specific command, and replays that command as structured JSON. Start with a quick readiness check, then choose a maintained demo or automate a workflow of your own.

**Start here:** [10-minute success path](docs/quickstart-10min.md) · [Release history](CHANGELOG.md)

## Start here

```bash
pip install cliany-site
cliany-site doctor
cliany-site cases
```

`doctor` gives you a human-readable next step. `cases` lists maintained public demos and their verification paths, so you can explore a real example before configuring an LLM. Follow the [10-minute success path](docs/quickstart-10min.md) to run a demo, or configure Chrome/CDP and an LLM when you are ready to generate a command for your own site.

### Tell us what happened

- [Report a bug](https://github.com/pearjelly/cliany.site/issues/new?template=bug_report.yml) if installation, exploration, or replay did not behave as expected.
- [Request a feature or automation](https://github.com/pearjelly/cliany.site/issues/new?template=feature_request.yml) if a capability or workflow would make the tool more useful.
- [Propose a public read-only workflow](https://github.com/pearjelly/cliany.site/issues/new?template=case_proposal.yml) if you have a safe scenario others can try.

## Features
```

In `README.zh.md`, make the same replacement with:

```markdown
> 把重复的浏览器操作，变成可复用的 CLI 命令。

cliany-site 通过 Chrome CDP 观察浏览器工作流，用 LLM 将其转成站点专属命令，并以结构化 JSON 回放。先完成一次快速就绪检查，再选择维护中的 demo，或自动化你自己的工作流。

**从这里开始：** [10 分钟成功路径](docs/quickstart-10min.md) · [发布记录](CHANGELOG.md)

## Start here

```bash
pip install cliany-site
cliany-site doctor
cliany-site cases
```

`doctor` 会给出适合人的下一步建议；`cases` 会列出维护中的公开 demo 及其验证路径，让你在配置 LLM 前先了解真实案例。想运行 demo，请继续阅读 [10 分钟成功路径](docs/quickstart-10min.md)；准备自动化自己的站点时，再配置 Chrome/CDP 与 LLM。

### 告诉我们结果

- 安装、探索或回放不符合预期？请[提交 Bug](https://github.com/pearjelly/cliany.site/issues/new?template=bug_report.yml)。
- 想要某项能力或自动化流程？请[提交功能建议](https://github.com/pearjelly/cliany.site/issues/new?template=feature_request.yml)。
- 有其他人也能安全运行的公开只读流程？请[提交案例建议](https://github.com/pearjelly/cliany.site/issues/new?template=case_proposal.yml)。

## 特性
```

Keep the existing detailed reference material below the feature heading; do not remove API, marketplace, or maintainer documentation.

- [ ] **Step 4: Run the README check to verify it passes**

Run:

```bash
bash qa/test_site_conversion.sh
```

Expected: zero exit and every README/issue-template assertion prints `[PASS]`.

- [ ] **Step 5: Commit the documentation onboarding slice**

```bash
git add README.md README.zh.md qa/test_site_conversion.sh qa/run_all.sh
git commit -m "docs: add first-success onboarding path"
```

### Task 2: Add the site’s first-success and feedback conversion surfaces

**Files:**

- Modify: `qa/test_site_conversion.sh`
- Modify: `site/index.html:6-61, after hero section, before footer`
- Modify: `site/script.js:1-22 and quickstart/footer translation entries`
- Modify: `site/style.css:263-360, 643-765, responsive rules`
- Modify: `site/sitemap.xml:5-6`

**Interfaces:**

- Consumes: the README's three commands, the existing `data-i18n` language switcher, existing `.copy-btn` click handler, and the three issue-form URLs.
- Produces: `#try-it` and `#feedback` anchors, copyable static commands, and translation keys used by `site/index.html`.

- [ ] **Step 1: Extend the check with the website contract**

Insert this block immediately before the final `printf` in `qa/test_site_conversion.sh`:

```bash
SITE_HTML="$ROOT_DIR/site/index.html"
SITE_JS="$ROOT_DIR/site/script.js"

assert_contains "$SITE_HTML" 'id="try-it"' "site exposes first-success anchor"
assert_contains "$SITE_HTML" 'id="feedback"' "site exposes feedback anchor"
assert_contains "$SITE_HTML" 'href="#try-it"' "site routes primary CTA to first success"
assert_contains "$SITE_HTML" 'href="#feedback"' "site navigation reaches feedback"
assert_contains "$SITE_HTML" 'data-clipboard="pip install cliany-site"' "site copies install command"
assert_contains "$SITE_HTML" 'data-clipboard="cliany-site doctor"' "site copies readiness command"
assert_contains "$SITE_HTML" 'data-clipboard="cliany-site cases"' "site copies case discovery command"

for template in bug_report.yml feature_request.yml case_proposal.yml; do
  assert_contains "$SITE_HTML" "issues/new?template=$template" "site links $template"
done

for key in nav.try nav.feedback hero.kicker try.title try.subtitle try.install.title try.install.body try.check.title try.check.body try.cases.title try.cases.body try.guide feedback.title feedback.subtitle feedback.bug.title feedback.bug.body feedback.bug.cta feedback.feature.title feedback.feature.body feedback.feature.cta feedback.case.title feedback.case.body feedback.case.cta footer.feedback; do
  if grep -F "'$key': { zh:" "$SITE_JS" | grep -Fq 'en:'; then
    pass "translation key $key has Chinese and English text"
  else
    fail "translation key $key has Chinese and English text"
  fi
done

if python3 - "$SITE_HTML" <<'PY'
from html.parser import HTMLParser
from pathlib import Path
import sys

class PageParser(HTMLParser):
    pass

PageParser().feed(Path(sys.argv[1]).read_text(encoding="utf-8"))
PY
then
  pass "site HTML parses with the standard library"
else
  fail "site HTML parses with the standard library"
fi
```

The `data-i18n` map entries introduced in this task must stay on one line so this check proves that each key has both values. Keep the counter and exit check below this inserted block.

- [ ] **Step 2: Run the expanded check to verify the site currently fails**

Run:

```bash
bash qa/test_site_conversion.sh
```

Expected: README assertions pass; site assertions fail because `#try-it`, `#feedback`, and the new translation keys do not yet exist.

- [ ] **Step 3: Update metadata, navigation, hero, and sections**

In `site/index.html`, replace its title and social description with:

```html
<title>cliany-site | Make browser work reusable</title>
<meta name="description" content="Turn repeated browser work into reusable CLI commands. Install cliany-site, check readiness, and automate your next workflow.">
<meta property="og:title" content="cliany-site | Make browser work reusable">
<meta property="og:description" content="Turn repeated browser work into reusable CLI commands — start with a quick readiness check.">
```

Replace the quick-start navigation target and add feedback:

```html
<a href="#try-it" class="nav-link" data-i18n="nav.try">Try it</a>
<a href="#feedback" class="nav-link" data-i18n="nav.feedback">Feedback</a>
<a href="#try-it" class="btn btn-primary nav-cta" data-i18n="nav.cta">Start your first workflow</a>
```

Replace the hero copy and primary link with:

```html
<p class="hero-kicker" data-i18n="hero.kicker">From repeated clicks to reusable commands</p>
<h1 class="hero-title" data-i18n="hero.title">Make browser work reusable</h1>
<p class="hero-subtitle" data-i18n="hero.subtitle">Turn a browser workflow into a site-specific CLI command you can run again, script, and inspect as JSON.</p>
<div class="hero-actions">
  <a href="#try-it" class="btn btn-primary" data-i18n="hero.cta">Start your first workflow</a>
  <a href="https://github.com/pearjelly/cliany.site" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" data-i18n="hero.github">View on GitHub →</a>
</div>
```

Insert this section immediately after the hero and before `#features`:

```html
<section id="try-it" class="first-success section-padding">
  <div class="container">
    <div class="section-header reveal">
      <h2 class="section-title" data-i18n="try.title">Try it in three commands</h2>
      <p class="section-subtitle" data-i18n="try.subtitle">Install, see the next safe step, then choose a maintained example before connecting an LLM.</p>
    </div>
    <div class="first-success-grid reveal">
      <article class="first-success-card"><span class="first-success-number">01</span><h3 data-i18n="try.install.title">Install</h3><p data-i18n="try.install.body">Get the CLI from PyPI.</p><div class="code-block-container"><pre class="code-block"><code>pip install cliany-site</code></pre><button class="copy-btn" data-clipboard="pip install cliany-site" aria-label="Copy to clipboard" data-i18n="copy.btn" data-i18n-aria="aria.copyBtn">Copy</button></div></article>
      <article class="first-success-card"><span class="first-success-number">02</span><h3 data-i18n="try.check.title">Check readiness</h3><p data-i18n="try.check.body">Read the human-friendly next step for your machine.</p><div class="code-block-container"><pre class="code-block"><code>cliany-site doctor</code></pre><button class="copy-btn" data-clipboard="cliany-site doctor" aria-label="Copy to clipboard" data-i18n="copy.btn" data-i18n-aria="aria.copyBtn">Copy</button></div></article>
      <article class="first-success-card"><span class="first-success-number">03</span><h3 data-i18n="try.cases.title">Choose a maintained example</h3><p data-i18n="try.cases.body">Browse public demos before you configure Chrome/CDP or an LLM for your own workflow.</p><div class="code-block-container"><pre class="code-block"><code>cliany-site cases</code></pre><button class="copy-btn" data-clipboard="cliany-site cases" aria-label="Copy to clipboard" data-i18n="copy.btn" data-i18n-aria="aria.copyBtn">Copy</button></div></article>
    </div>
    <p class="first-success-guide reveal"><a href="https://github.com/pearjelly/cliany.site/blob/master/docs/quickstart-10min.md" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" data-i18n="try.guide">Follow the 10-minute guide →</a></p>
  </div>
</section>
```

Insert this feedback section immediately before `</main>`:

```html
<section id="feedback" class="feedback section-padding">
  <div class="container">
    <div class="section-header reveal"><h2 class="section-title" data-i18n="feedback.title">Help shape the next workflow</h2><p class="section-subtitle" data-i18n="feedback.subtitle">A target URL, expected result, and reproducible steps are the most useful feedback.</p></div>
    <div class="feedback-grid reveal">
      <article class="feedback-card"><h3 data-i18n="feedback.bug.title">Something broke</h3><p data-i18n="feedback.bug.body">Tell us what you expected and what happened instead.</p><a href="https://github.com/pearjelly/cliany.site/issues/new?template=bug_report.yml" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" data-i18n="feedback.bug.cta">Report a bug</a></article>
      <article class="feedback-card"><h3 data-i18n="feedback.feature.title">Want an automation</h3><p data-i18n="feedback.feature.body">Describe the repeated browser task you want to turn into a command.</p><a href="https://github.com/pearjelly/cliany.site/issues/new?template=feature_request.yml" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" data-i18n="feedback.feature.cta">Request a feature</a></article>
      <article class="feedback-card"><h3 data-i18n="feedback.case.title">Have a public workflow</h3><p data-i18n="feedback.case.body">Share a safe, read-only scenario that other people can verify.</p><a href="https://github.com/pearjelly/cliany.site/issues/new?template=case_proposal.yml" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" data-i18n="feedback.case.cta">Propose a workflow</a></article>
    </div>
  </div>
</section>
```

Change the footer quick-start link to `#try-it` and add `<a href="#feedback" class="footer-link" data-i18n="footer.feedback">Feedback</a>`.

- [ ] **Step 4: Add matching translations, styles, and sitemap freshness**

Add these one-line entries to `site/script.js` next to the matching existing navigation, hero, and footer records. Do not leave the old `hero.title`, `hero.subtitle`, or `hero.cta` records alongside the replacements.

```javascript
'nav.try': { zh: '立即试用', en: 'Try it' },
'nav.feedback': { zh: '反馈', en: 'Feedback' },
'nav.cta': { zh: '开始第一个工作流', en: 'Start your first workflow' },
'hero.kicker': { zh: '从重复点击，到可复用命令', en: 'From repeated clicks to reusable commands' },
'hero.title': { zh: '让浏览器工作流可以复用', en: 'Make browser work reusable' },
'hero.subtitle': { zh: '把浏览器工作流转成站点专属 CLI 命令，重复执行、写入脚本，并以 JSON 查看结果。', en: 'Turn a browser workflow into a site-specific CLI command you can run again, script, and inspect as JSON.' },
'hero.cta': { zh: '开始第一个工作流', en: 'Start your first workflow' },
'try.title': { zh: '三条命令开始试用', en: 'Try it in three commands' },
'try.subtitle': { zh: '安装、查看安全的下一步，再在连接 LLM 前选择一个维护中的案例。', en: 'Install, see the next safe step, then choose a maintained example before connecting an LLM.' },
'try.install.title': { zh: '安装', en: 'Install' },
'try.install.body': { zh: '从 PyPI 获取 CLI。', en: 'Get the CLI from PyPI.' },
'try.check.title': { zh: '检查就绪状态', en: 'Check readiness' },
'try.check.body': { zh: '查看适合你当前机器的下一步建议。', en: 'Read the human-friendly next step for your machine.' },
'try.cases.title': { zh: '选择维护中的案例', en: 'Choose a maintained example' },
'try.cases.body': { zh: '在为自己的工作流配置 Chrome/CDP 或 LLM 前，先浏览公开 demo。', en: 'Browse public demos before you configure Chrome/CDP or an LLM for your own workflow.' },
'try.guide': { zh: '查看 10 分钟指南 →', en: 'Follow the 10-minute guide →' },
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
'footer.feedback': { zh: '反馈', en: 'Feedback' },
```

Add these CSS rules after the existing quick-start rules. Add the final media rule inside the existing `@media (max-width: 768px)` block.

```css
.hero-kicker {
  color: var(--color-accent);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  letter-spacing: 0.04em;
  margin-bottom: 1rem;
}

.first-success { background: var(--color-surface); }

.first-success-grid,
.feedback-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.5rem;
}

.first-success-card,
.feedback-card {
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  min-width: 0;
  padding: 2rem;
}

.first-success-number {
  color: var(--color-accent);
  display: block;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

.first-success-card h3,
.feedback-card h3 {
  font-family: var(--font-body);
  font-size: 1.2rem;
  margin-bottom: 0.75rem;
}

.first-success-card p,
.feedback-card p {
  color: var(--color-text-muted);
  margin-bottom: 1.25rem;
}

.first-success-guide { margin-top: 2rem; text-align: center; }

.feedback { background: var(--color-bg-dark); }
.feedback .section-title { color: var(--color-white); }
.feedback .section-subtitle { color: #D3C6AA; }
.feedback-card { background: rgba(255, 255, 255, 0.06); border-color: rgba(255, 255, 255, 0.18); }
.feedback-card h3 { color: var(--color-white); }
.feedback-card p { color: #D3C6AA; }
.feedback-card .btn-secondary { border-color: rgba(255, 255, 255, 0.35); color: var(--color-white); }
.feedback-card .btn-secondary:hover { background: rgba(255, 255, 255, 0.12); }

@media (max-width: 768px) {
  .first-success-grid,
  .feedback-grid { grid-template-columns: 1fr; }
}
```

Update `site/index.html` cache-busting query strings to `style.css?v=20260717a` and `script.js?v=20260717a`. Change the homepage `<lastmod>` in `site/sitemap.xml` to `2026-07-17`.

- [ ] **Step 5: Run the full conversion check and inspect the implementation diff**

Run:

```bash
bash qa/test_site_conversion.sh
git diff --check
git diff -- site/index.html site/script.js site/style.css site/sitemap.xml qa/test_site_conversion.sh
```

Expected: zero exit from the QA script, no whitespace errors, all new i18n keys contain both languages, and the new `#try-it` section contains no `v0.14.0.tar.gz` filename.

- [ ] **Step 6: Commit the website conversion slice**

```bash
git add site/index.html site/script.js site/style.css site/sitemap.xml qa/test_site_conversion.sh
git commit -m "feat(site): guide visitors to first success"
```

### Task 3: Run focused regression and hand off publication safely

**Files:**

- Modify: no additional product files expected
- Test: `qa/test_site_conversion.sh`

**Interfaces:**

- Consumes: the committed README and static-site conversion surfaces.
- Produces: focused verification evidence and an explicitly user-authorized production deployment handoff.

- [ ] **Step 1: Run the focused regression suite from a clean checkout state**

Run:

```bash
git status --short
bash qa/test_site_conversion.sh
```

Expected: the status is empty before testing, and the conversion suite exits zero with no `[FAIL]` lines.

- [ ] **Step 2: Verify every conversion acceptance criterion directly**

Run:

```bash
rg -n '## Start here|## (Features|特性)|issues/new\?template=(bug_report|feature_request|case_proposal)\.yml' README.md README.zh.md
rg -n 'id="try-it"|id="feedback"|href="#try-it"|href="#feedback"|data-clipboard="cliany-site (doctor|cases)"' site/index.html
rg -n "'nav.try'|'nav.feedback'|'try.title'|'feedback.title'|'footer.feedback'" site/script.js
git diff --check HEAD~2..HEAD
```

Expected: both READMEs contain the start path and all three form links; the site exposes both anchors and the three copyable commands; each required bilingual key exists; and Git reports no whitespace errors.

- [ ] **Step 3: Commit only if validation exposes a correction**

If a check reveals a defect, make the smallest correction, rerun Steps 1–2, then commit only the correction:

```bash
git add README.md README.zh.md site/index.html site/script.js site/style.css site/sitemap.xml qa/test_site_conversion.sh
git commit -m "fix(site): complete first-success conversion checks"
```

If all checks pass without a correction, do not create an empty commit.

- [ ] **Step 4: Publish only after explicit user approval**

Do not publish automatically. If the user explicitly asks to publish, run the project-prescribed commands from `site/`:

```bash
vercel link --yes --project cliany.site
vercel --prod --yes
```

After a successful publish, report the production URL and exact deployed commit.

## Plan self-review

- **Spec coverage:** Task 1 implements the concise bilingual README path and three feedback links. Task 2 implements hero/metadata, primary CTA, navigation, bilingual three-step site path, three feedback options, responsive styling, stale-version avoidance, and sitemap freshness. Task 3 verifies every acceptance criterion and preserves user control over publication.
- **Placeholder scan:** No incomplete implementation markers or unscoped validation steps remain.
- **Interface consistency:** HTML `data-i18n` keys are declared in `site/script.js`; `data-clipboard` commands match the README; and every external feedback link maps to a tracked issue template.
