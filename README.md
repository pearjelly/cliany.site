# cliany-site

[![PyPI version](https://img.shields.io/pypi/v/cliany-site)](https://pypi.org/project/cliany-site/)
[![Python](https://img.shields.io/pypi/pyversions/cliany-site)](https://pypi.org/project/cliany-site/)
[![CI](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml/badge.svg)](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/pearjelly/cliany.site)](LICENSE)

> 🌐 Languages: [English](README.md) | [简体中文](README.zh.md)

> **🧪 v0.14.4 Quality Gates**: Structured extraction now reports `data.quality`, `browser extract --strict-quality` can fail empty or partially missing results with `E_EMPTY_RESULT`, generated `list-` / `search-` commands expose extraction quality, and `scripts/release_readiness.py` checks case catalog, CI gates, release draft, changelog, and weekly commit cadence before release. See [v0.14.4 release draft](docs/releases/v0.14.4-draft.md).
> **🧭 v0.14.3 Open-Source Readiness**: Added the Q3 roadmap, 10-minute quickstart, structured real-demo case index, human-readable `doctor` summary, contributor starter map, and local release cadence checks. See [CHANGELOG.md](CHANGELOG.md).
> **🤖 v0.14.2 自主改进闭环**：新增 5 维度自主改进脚手架——确定性 benchmark 回归测试、headless Chrome 具身验证、Dependabot 依赖哨兵、运行时反馈闭环、Agent 守则文档，使 OpenCode 可触发自主演进循环，详见 [CHANGELOG.md](CHANGELOG.md)。  
> **🔧 v0.14.1 修复与增强**：新增 `E_PAGE_NOT_READY` / `E_PARSE_FAILED` / `E_EMPTY_RESULT` 错误码、修复 navigate/extract/action_runtime 失败语义、doctor 同时识别 `AGENT.md` / `AGENTS.md`、Obscura 能力声明修正（navigation/cookies）、list-/search- 命令空结果 opt-in 检测、Obscura 友好错误提示，详见 [CHANGELOG.md](CHANGELOG.md)。  
> **✨ v0.14.0 Real-World Demos**: Case 2 (Enterprise CRM) & Case 3 (Team Toolbox) on the website now use real public demo sites — SuiteCRM Demo, ASF Jira, ASF Confluence, ASF Jenkins. See [Try Real Demos](#try-real-demos).
> **✨ v0.13.0 开发者体验加固**：修复 loader RuntimeError bug、稳定 test_session_lock 测试、补全 ERROR_FIX_HINTS 27 条提示、新增 SuccessEnvelope/ErrorEnvelope TypedDict、核心模块 pyright strict（0 errors）、doctor 命令增强（versions + adapter_stats），详见 [CHANGELOG.md](CHANGELOG.md)。  
> **🔒 v0.12.0 稳定性与质量加固**：新增文件锁保护（manifest/session 并发写安全）、tar 路径穿越防护、Obscura 下载重试、统一错误码体系，详见 [CHANGELOG.md](CHANGELOG.md)。  
> **🚀 v0.11.0**: Added experimental Obscura browser provider, multi-platform binaries, and lifecycle management.  
> ⚠️ **v0.10.0 BREAKING**: metadata schema v3 hardcut. Use `cliany-site migrate` to upgrade legacy adapters.

> Automate any web workflow into callable CLI commands

cliany-site is built on browser-use and Large Language Models (LLMs), enabling full-process automation from web exploration to code generation and replay via the Chrome CDP protocol. Explore with one command, execute with another—turning complex web workflows into repeatable CLI tools.

## Features

### Core Capabilities

- **Zero-Intrusion Exploration** — Chrome CDP captures page AXTree without script injection.
- **LLM-Driven Code Generation** — Claude / GPT-4o understands page semantics and generates Python CLI commands automatically.
- **LLM Call Retry Mechanism** — Automatic retries during network fluctuations to improve exploration success rates.
- **Retryable LLM Outage Signal** — `explore --json` reports gateway, rate-limit, or service outages as `E_LLM_UNAVAILABLE` with sanitized retry details instead of raw upstream HTML.
- **Unified JSON Envelope** — All commands support `--json`, outputting a machine-readable `{ok, data, error, meta}` envelope (v1).
- **Persistent Sessions** — Maintains Cookie / LocalStorage login states across commands.
- **Dynamic Adapter Loading** — Automatically registers CLI subcommands by domain, allowing for easy expansion.
- **Automatic Browser Management** — Manages Chrome debugging instances or experimental Obscura binaries automatically.
- **Data Extraction with Quality Signals** — Extracts structured page data, saves Markdown reports, and reports empty/partial results through `data.quality` or `E_EMPTY_RESULT` when strict quality is enabled.

### Developer Experience

- **Incremental Adapter Merging** — Intelligently merges when exploring the same site repeatedly, preserving existing commands.
- **Atomic Command System** — Automatically extracts reusable atomic operations shared across adapters.
- **Real-Time Progress Feedback** — Displays Rich progress bars and NDJSON streaming events during explore/execute.
- **Smart Healing** — AXTree snapshot comparison and selector hot-fixes without re-exploring.
- **CSS Selector Candidate Pre-computation** — Pre-generates multiple selector candidates to improve element matching resilience.
- **Breakpoint Resumption** — Records breakpoints after adapter command failures; resume via `cliany-site <domain> <command> --resume`.
- **Conversational Exploration** — `--interactive` for step-by-step confirmation, `--extend <domain>` for incremental expansion, and automatic exploration recording (`~/.cliany-site/recordings/`).

### Enterprise Features

- **Headless & Remote Browsers** — Supports `--headless` and `--cdp-url ws://host:port` for running in servers or Docker.
- **Obscura Lifecycle Management** — Dedicated `obscura` command group for binary installation, rollback, and health checks.
- **YAML Workflow Orchestration** — Declarative multi-step workflows with data passing, conditional logic, and retry strategies.
- **Data-Driven Batch Execution** — CSV/JSON batch parameters with concurrency control and summary reports.
- **Encrypted Session Storage** — Fernet symmetric encryption with system Keychain integration for key management.
- **Sandbox Execution Mode** — `--sandbox` limits cross-origin navigation and dangerous operations, currently prioritized for CLI adapter paths.
- **Generated Code Security Audit** — AST static analysis detects dangerous patterns like eval/exec/os.system.

### Ecosystem Integration

- **Python SDK** — `from cliany_site import explore, execute` for programmatic calls.
- **HTTP API** — `cliany-site serve --port 8080` starts a REST API service.
- **Adapter Marketplace** — Pack, install, uninstall, and rollback adapters to share automation capabilities within teams.
- **TUI Management Interface** — A Textual-based terminal UI for visual adapter management.
- **iframe/Shadow DOM** — Recursive AXTree collection with cross-origin iframe and Shadow DOM penetration.

### New in v0.11.0

- **Obscura Experimental Provider** — Integration of the Obscura lightweight browser backend. Enable via `CLIANY_BROWSER_PROVIDER=obscura`.
- **Obscura Command Group** — New `cliany-site obscura` commands: `install/use/status/clean/rollback/upgrade/doctor`.
- **Multi-Platform Support** — Pre-built binaries for `darwin-arm64`, `darwin-x86_64`, `linux-x86_64`, and `windows-x86_64`.
- **Capability Snapshot & Feature Gates** — Abstraction layer for browser providers with explicit capability routing.
- **Note**: `explore` is currently gated/unsupported under Obscura. Chrome remains the default provider for exploration.

### New in v0.10.0 (BREAKING)

> ⚠️ **BREAKING**: metadata schema v3 hardcut. v2 adapters must be migrated.  
> Run `cliany-site migrate --json` to upgrade all legacy adapters.

- **DOM Pruning & Compound Controls** — 4-layer AXTree pruning (depth/count/role/compress) + automatic extraction of `<select>` / `<input type=date>` / `<input type=file>` option metadata. Reduces prompt tokens by 30-50%.
- **Lazy Adapter Registry** — `discover()` reads only `metadata.json`; `get(domain, cmd)` loads on demand. CLI startup 2-5x faster.
- **Repair Cache** — Heal results cached in `~/.cliany-site/adapters/{domain}/repair-cache.json` (LRU 100/domain). Repeated failures skip LLM calls.
- **Network + Console Capture** — Explore phase auto-captures Network requests (stops at 1MB) and Console logs (500-entry ring), stored in StepRecord.
- **Capability Routing** — Sniffs API endpoints during explore; replay routes browser/API automatically. Override with `--force-browser`.
- **`migrate` command** — `cliany-site migrate [--json] [--dry-run]` scans and upgrades all legacy adapters to schema v3 with `.bak` backups.
- **Diagnostic Mode** — `cliany-site --diagnose --json <domain> <cmd>` triggers LLM diagnosis on failure, outputs `root_cause` + `suggested_fix`. Built into generated adapter templates via `diagnose_if_enabled()`.

### New in v0.9.x

- **Metadata Schema v2 Hardcut** — Mandatory schema_version=2; legacy adapters are rejected with a prompt to regenerate via `cliany-site explore <url> "<workflow>"`.
- **Smart Healing (`--heal`)** — AXTree snapshot diff + selector hot-fixes without re-exploring; supports healing caps and sidecar recording.
- **Static Verification (`verify`)** — Checks adapter schema, signatures, and dependency integrity without opening a browser; `cliany-site verify <domain> --json`.
- **Self-Describing Endpoints (`--explain`)** — `cliany-site --json --explain` outputs a machine-readable Agent contract for easier automation integration.
- **AGENT.md Auto-Rewrite** — AGENT.md includes sentinels and hashes; automatically updates with new features to keep the agent contract current.
- **Atomic Command System** — Generated commands call reusable atom commands instead of inlining CDP operations, shared across adapters.
- **Unified Envelope (`ok()`)** — All built-in commands use the unified `{ok, data, error, meta}` output format.
- **Extended Doctor Health Check** — Covers registry / legacy adapter detection / agent-md consistency validation.
- **Breakpoint Resumption (`--resume`)** — Records breakpoints after adapter command failures, supporting recovery from the point of failure.

## Quick Start (v0.11.0+)

For a guided first run, see [10-minute success path](docs/quickstart-10min.md). It starts with a real demo adapter before requiring LLM setup, then points successful users toward the `Real Demo Case Proposal` path for contributing new public read-only cases.

For upcoming work, see the user-facing [public roadmap](docs/public-roadmap.md) and the maintainer [Q3 roadmap](docs/roadmap-2026-q3.md).

### Installation

```bash
# Install via PyPI
pip install cliany-site

# Or install from source
git clone https://github.com/pearjelly/cliany.site.git
cd cliany.site
pip install -e .
```

### Basic Workflow

```bash
# Check environment
cliany-site doctor --json

# Optional live provider preflight before explore
cliany-site doctor --llm-live --json

# Discover maintained real demo cases
cliany-site cases --json
cliany-site cases --status candidate --promotion-plan
cliany-site cases --json --status candidate --promotion-plan
cliany-site cases --case-id pypi-project-search --json
cliany-site cases --case-id pypi-project-search --issue-template
cliany-site cases --case-id pypi-project-search --evidence-bundle
cliany-site cases --case-id pypi-project-search --evidence-bundle --json

# Explore web workflow (requires LLM)
cliany-site explore "https://github.com" "Search and view results" --json

# List generated commands
cliany-site list --json

# Execute generated commands (zero LLM)
cliany-site github.com search --query "cliany-site" --json

# Static verification
cliany-site verify github.com --json

# Query Agent contract
cliany-site --json --explain
```

### Configuration

```bash
# LLM Provider (choose one)
export CLIANY_LLM_PROVIDER=anthropic
export CLIANY_ANTHROPIC_API_KEY="sk-ant-..."

# Or OpenAI
export CLIANY_LLM_PROVIDER=openai
export CLIANY_OPENAI_API_KEY="sk-..."

# Experimental: Obscura Browser Provider
# export CLIANY_BROWSER_PROVIDER=obscura
```

Also supports `.env` file configuration. Search order: `~/.config/cliany-site/.env` → `~/.cliany-site/.env` → project directory `.env` → environment variables.

If `explore --json` returns `E_LLM_UNAVAILABLE`, the LLM provider returned a retryable upstream outage such as `502 Bad Gateway`, rate limiting, or service unavailable. The JSON envelope includes `details.retryable`, `details.status_code`, and `details.phase`; retry later or switch `CLIANY_LLM_PROVIDER` / `CLIANY_OPENAI_BASE_URL`. This does not mean the generated adapter or AXTree selector map is broken.

### Experimental: Obscura Browser Provider

Obscura is a lightweight browser provider currently in **experimental** status. Chrome remains the default provider for exploration.

> **Note**: Obscura does **not** support `explore` (AXTree/Accessibility) yet. Use it for executing existing adapters or lightweight navigation tasks.

#### Setup and Usage
```bash
# 1. Install Obscura binary (version >= 0.1.0)
cliany-site obscura install 0.1.0 --json

# 2. Enable Obscura as provider
export CLIANY_BROWSER_PROVIDER=obscura

# 3. Check status
cliany-site obscura status --json

# 4. Revert to Chrome
unset CLIANY_BROWSER_PROVIDER
```

For more details, see the [Obscura Experimental Guide](docs/walkthroughs/obscura-experimental-guide.md).

### Verify Environment

```bash
cliany-site doctor --json
cliany-site doctor --llm-live --json
```

By default, `doctor` checks local configuration, CDP, directories, and keys without calling the LLM provider. Add `--llm-live` when you want a real provider preflight before a longer `explore`; retryable gateway, rate-limit, or service outages appear as a `llm_live` warning with `details.error_code=E_LLM_UNAVAILABLE`.

## Usage Examples

### Basic Flow

```bash
# 1. Explore workflow
cliany-site explore "https://github.com" "Search repository and view README" --json

# 2. List generated commands
cliany-site list --json

# 3. Execute generated command
cliany-site github.com search --query "browser-use" --json
```

### Structured Extraction Quality

```bash
# Extract visible card data from the current browser page
cliany-site browser extract \
  --selector ".result-card" \
  --mode list \
  --fields-json '{"title": ".title", "url": "a@href"}' \
  --json

# Fail fast if all rows are empty or required fields are blank
cliany-site browser extract \
  --selector ".result-card" \
  --mode list \
  --fields-json '{"title": ".title", "url": "a@href"}' \
  --strict-quality \
  --json
```

Structured extraction responses include `data.quality`. Generated `list-` and `search-` adapter commands also include that summary and return `E_EMPTY_RESULT` when extraction quality is empty or partially missing required fields, so automation can distinguish "command ran" from "useful data was found".

### Conversational Exploration (v0.8)

```bash
# Interactive exploration (confirm each step)
cliany-site explore "https://github.com" "搜索仓库" --interactive

# Incrementally extend an existing adapter
cliany-site explore "https://github.com" "查看 Issues 列表" --extend github.com

# Replay exploration recording
cliany-site replay github.com --step
```

### Python SDK

```python
from cliany_site.sdk import ClanySite

async with ClanySite() as cs:
    result = await cs.explore("https://github.com", "搜索仓库")
    adapters = await cs.list_adapters()
```

## Try Real Demos

The following adapters are available as downloadable assets on [GitHub Release v0.14.1](https://github.com/pearjelly/cliany.site/releases/tag/v0.14.1).
The maintained case index lives in [cases/README.md](cases/README.md) and [cases/manifest.json](cases/manifest.json).
Use `cliany-site cases --json` to inspect active demos, candidate workflows, offline validation commands, and candidate promotion next actions from the CLI; `promotion_evidence_summary.primary_next_task` points automation at the first candidate task to advance, while `promotion_evidence_summary.primary_next_task_acceptance_criteria` states the proof required for that task. Add `--promotion-plan` to print the candidate promotion queue across all matched candidates; combine it with `--json` to read `promotion_plan.primary_next_item`, per-candidate primary tasks, and the incomplete `task_queue`. Use `cliany-site cases --case-id pypi-project-search --json` to open one case with validation and promotion details; omit `--json` for a copy-friendly human handoff with Promotion Tasks. Add `--issue-template` to print a GitHub issue body for a candidate promotion task, including Acceptance Criteria for each evidence task; combine it with `--json` to also read `issue_template_primary_task` without parsing Markdown. Add `--evidence-bundle` to print a structured local evidence checklist; combine it with `--json` for a machine-readable evidence bundle, including a `promotion_command_plan` that starts with `llm_live_preflight` before adapter package, metadata validation, and online smoke commands, plus `acceptance_criteria` for the proof each evidence task must attach. Use `python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues` to generate reviewable candidate issue artifacts; the artifacts README shows `Primary Evidence Status`, `Primary Acceptance Criteria`, and `primary_next_task_acceptance_criteria` before maintainers create issues.

### SuiteCRM Demo (Enterprise CRM)
```bash
# 1. Install adapter
cliany-site market install ./demo.suiteondemand.com.cliany-adapter-v0.14.0.tar.gz

# 2. Login (opens browser — use demo account from https://demo.suiteondemand.com/)
cliany-site login https://demo.suiteondemand.com/

# 3. Query accounts (no browser needed after login)
cliany-site demo.suiteondemand.com list-accounts --limit 5 --json
```

### ASF Jira (Issue Tracker)
```bash
cliany-site market install ./issues.apache.org.cliany-adapter-v0.14.0.tar.gz
cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json
```

### ASF Confluence (Wiki)
```bash
cliany-site market install ./cwiki.apache.org.cliany-adapter-v0.14.0.tar.gz
cliany-site cwiki.apache.org search-pages --space SPARK --query "release" --json
```

### ASF Jenkins (Build Status)
```bash
cliany-site market install ./builds.apache.org.cliany-adapter-v0.14.0.tar.gz
cliany-site builds.apache.org list-jobs --json
```

> **Disclaimer**: These demo sites are operated by third parties and may be temporarily unavailable. cliany-site only provides the CLI shim; we do not control the demo data or uptime.


### HTTP API

```bash
# Start service
cliany-site serve --port 8080

# Call API
curl http://localhost:8080/doctor
curl http://localhost:8080/adapters
curl -X POST http://localhost:8080/explore \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com", "workflow": "搜索仓库"}'
```

### YAML Workflow Orchestration

```yaml
# workflow.yaml
name: GitHub Search Process
steps:
  - name: Search Repository
    adapter: github.com
    command: search
    params:
      query: "cliany-site"
  - name: View Details
    adapter: github.com
    command: view
    params:
      repo: "$prev.data.results[0].name"
```

```bash
cliany-site workflow run workflow.yaml --json
cliany-site workflow validate workflow.yaml --json
```

### Batch Execution

```bash
# Batch execution from CSV
cliany-site workflow batch github.com search data.csv --concurrency 3 --json
```

### Adapter Marketplace

See [Adapter lifecycle and package format](docs/adapter-lifecycle.md) for the runtime layout, `.cliany-adapter.tar.gz` package contract, compatibility rules, and rollback workflow.

```bash
# Pack adapter
cliany-site market publish github.com --version 1.0.0

# Install adapter
cliany-site market install ~/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz

# Rollback
cliany-site market rollback github.com
```

## Command Reference

| Command | Arguments | Description |
|------|------|------|
| `doctor` | `[--json]` | Check environment (CDP, LLM Key, directory structure). |
| `login <url>` | `[--json]` | Open URL to wait for login and save session. |
| `explore <url> <workflow>` | `[--json] [--interactive] [--extend <domain>] [--record]` | Explore workflow and generate adapter. |
| `list` | `[--json]` | List generated adapters. |
| `cases` | `[--case-id <id>] [--status <status>] [--detail] [--issue-template] [--evidence-bundle] [--promotion-plan] [--json]` | List maintained real demo cases and candidate workflows. |
| `verify <domain>` | `[--json]` | Statically verify adapter schema, signatures, and dependency integrity. |
| `migrate` | `[--json] [--dry-run]` | Migrate all legacy adapters to schema v3. |
| `replay <domain>` | `[--session <id>] [--step]` | Replay exploration recording with screenshots and actions. |
| `check <domain>` | `[--json] [--fix]` | Check adapter health status. |
| `obscura <subcommand>` | `install/use/status/clean/rollback/upgrade/doctor` | Manage experimental Obscura browser provider. |
| `tui` | | Start TUI management interface. |
| `serve` | `[--host] [--port]` | Start HTTP API service. |
| `market publish <domain>` | `[--version] [--json]` | Pack and export adapter. |
| `market install <path>` | `[--force] [--json]` | Install adapter package. |
| `market uninstall <domain>` | `[--json]` | Uninstall adapter. |
| `market rollback <domain>` | `[--index] [--json]` | Rollback to a backup version. |
| `workflow run <file>` | `[--json] [--dry-run]` | Execute YAML workflow. |
| `workflow validate <file>` | `[--json]` | Validate workflow file. |
| `workflow batch <adapter> <cmd> <data>` | `[--concurrency] [--json]` | Batch execution. |
| `report list` | `[--domain] [--json]` | List execution reports. |
| `report show <id>` | `[--json]` | View report details. |
| `<domain> <command>` | `[--json] [args...]` | Execute a command from an adapter. |

**Global Options:** `--json` `--verbose` `--debug` `--cdp-url <ws://host:port>` `--headless` `--sandbox` `--explain` `--force-browser` `--diagnose`

## Architecture Overview

```
cliany-site/src/cliany_site/
├── cli.py              # Main entry point, SafeGroup global exception capture
├── config.py           # Unified configuration center (env + .env)
├── errors.py           # Exception hierarchy + error codes
├── response.py         # JSON envelope {ok, data, error, meta} (v1)
├── logging_config.py   # Structured logging (JSON format + masking)
├── sdk.py              # Python SDK (sync + async)
├── server.py           # HTTP API service (aiohttp)
├── security.py         # Session encryption (Fernet + Keychain)
├── sandbox.py          # Sandbox policy execution
├── audit.py            # Code security audit (AST analysis)
├── marketplace.py      # Adapter marketplace (pack/install/rollback)
├── browser/            # CDP connection + AXTree + Chrome start + iframe
├── explorer/           # LLM workflow exploration + atom extraction + verification
├── codegen/            # Code generation (template/param inference/deduplication/merge)
├── workflow/           # YAML orchestration + batch execution
├── commands/           # Built-in CLI commands
└── tui/                # Textual terminal UI
```

## Security Features

- **Session Encryption**: Fernet symmetric encryption with keys stored in system Keychain (macOS Keychain / Linux Secret Service); falls back to file keys if Keychain is unavailable.
- **Sandbox Mode**: `--sandbox` limits navigation to the same origin, forbids `javascript:` / `file://` / `data:` URLs, and prevents file downloads.
- **Code Audit**: Automatic AST scanning of codegen output to detect dangerous calls like `eval` / `exec`.

## Roadmap

The current iteration plan is tracked in [docs/roadmap-2026-q3.md](docs/roadmap-2026-q3.md). Release and commit cadence is defined in [docs/release-cadence.md](docs/release-cadence.md): one to three verified versions per day, with commits on at least three days each week. Maintainers can use the [weekly maintainer loop](docs/weekly-maintainer-loop.md), plus `next_actions`, `primary_next_action`, `release_count_today`, `max_daily_releases`, and `daily_release_limit_ok` from `scripts/release_readiness.py --json`, `scripts/check_release_cadence.py --json`, or `scripts/check_release_publication.py --json`, to choose the next small verified release slice and confirm whether the latest local tag is publicly visible. After the tag workflow completes, `scripts/check_release_publication.py --remote --distribution --json` also verifies that GitHub Release and PyPI both expose the latest version. Automation can compare `next_actions_sha256`, `publication_blockers_sha256`, `publication_next_actions_sha256`, `publication_publish_commands_sha256`, `target_tag_commands_sha256`, and `distribution.next_actions_sha256` to detect release-action drift without parsing Markdown reports.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR workflow.
First-time contributors can start from the [contributor starter map](docs/contributor-starter.md) or the curated [Good First Issues](docs/good-first-issues.md) list; both paths avoid real LLM keys by default and include local validation commands.

## Limitations

- Requires Chrome/Chromium (auto-start or manual `--remote-debugging-port=9222`).
- Requires a valid LLM API Key (Anthropic or OpenAI).
- Generated commands depend on page DOM structure; major redesigns may require re-exploration (minor changes handled by fuzzy matching and self-healing).
- Sessions are not shared across browser profiles.
- Recursive collection for cross-origin iframes is enabled by default (configurable via `CLIANY_CROSS_ORIGIN_IFRAMES`).

## Changelog

See full changelog: [CHANGELOG.md](CHANGELOG.md)
