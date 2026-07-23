# cliany-site

[![PyPI version](https://img.shields.io/pypi/v/cliany-site)](https://pypi.org/project/cliany-site/)
[![Python](https://img.shields.io/pypi/pyversions/cliany-site)](https://pypi.org/project/cliany-site/)
[![CI](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml/badge.svg)](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/pearjelly/cliany.site)](LICENSE)

> 🌐 Languages: [English](README.md) | [简体中文](README.zh.md)

> Turn repeated browser workflows into reusable CLI commands.

cliany-site observes a browser workflow through Chrome CDP, uses an LLM to turn it into a site-specific command, and replays that command as structured JSON. Start with a quick readiness check, then review a maintained case or automate a workflow of your own.

**Start here:** [10-minute success path](docs/quickstart-10min.md) · [Release history](CHANGELOG.md)

## Start here

```bash
pip install cliany-site
cliany-site doctor
cliany-site cases
```

`doctor` gives you a human-readable next step. `cases` lists maintained public cases and their current verification paths, so you can understand a real example before configuring an LLM. Follow the [10-minute success path](docs/quickstart-10min.md) to review a case, or configure Chrome/CDP and an LLM when you are ready to generate a command for your own site.

### Tell us what happened

- [Report a bug](https://github.com/pearjelly/cliany.site/issues/new?template=bug_report.yml) if installation, exploration, or replay did not behave as expected.
- [Request a feature or automation](https://github.com/pearjelly/cliany.site/issues/new?template=feature_request.yml) if a capability or workflow would make the tool more useful.
- [Propose a public read-only workflow](https://github.com/pearjelly/cliany.site/issues/new?template=case_proposal.yml) if you have a safe scenario others can try.

## Features

### Core Capabilities

- **Zero-Intrusion Exploration** — Chrome CDP captures page AXTree without script injection.
- **LLM-Driven Code Generation** — Claude / GPT-4o understands page semantics and generates Python CLI commands automatically.
- **LLM Call Retry Mechanism** — Automatic retries during network fluctuations to improve exploration success rates.
- **Retryable LLM Outage Signal** — `explore --json` reports gateway, rate-limit, provider connection, or service outages as `E_LLM_UNAVAILABLE` with sanitized retry details instead of raw upstream HTML.
- **Unified JSON Envelope** — All commands support `--json`, outputting a machine-readable `{ok, data, error, meta}` envelope (v1).
- **Persistent Sessions** — Maintains Cookie / LocalStorage login states across commands.
- **Dynamic Adapter Loading** — Automatically registers CLI subcommands by domain, allowing for easy expansion.
- **Automatic Browser Management** — Manages Chrome debugging instances or experimental Obscura binaries automatically.
- **Data Extraction with Quality Signals** — Extracts structured page data, saves Markdown reports, and keeps empty/partial results visible through `data.quality`; generated data commands require actual extracted results unless they explicitly model a legitimate zero-match result.

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

For a guided first run, see [10-minute success path](docs/quickstart-10min.md). It guides you from installation through `doctor` to maintained cases, then points successful users toward the `Real Demo Case Proposal` path for contributing new public read-only cases.

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

If `explore --json` returns `E_LLM_UNAVAILABLE`, the LLM provider returned a retryable upstream outage such as `502 Bad Gateway`, rate limiting, provider connection failure, or service unavailable. The JSON envelope includes `details.retryable`, `details.status_code`, and `details.phase`; retry later or switch `CLIANY_LLM_PROVIDER` / `CLIANY_OPENAI_BASE_URL`. This does not mean the generated adapter or AXTree selector map is broken.

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

By default, `doctor` checks local configuration, CDP, directories, and keys without calling the LLM provider. Add `--llm-live` when you want a real provider preflight before a longer `explore`; retryable gateway, rate-limit, provider connection, or service outages appear as a `llm_live` warning with `details.error_code=E_LLM_UNAVAILABLE`.

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

Structured extraction responses include `data.quality`. Generated `list-`, `search-`, `read-`, and `extract-` adapter commands, plus any command containing an `extract` action, enforce that summary. Their `expects_nonempty` contract defaults to `true`: zero data, missing required fields, and partial rows return `E_EMPTY_RESULT`. A command may declare `expects_nonempty=false` only when zero matches are a valid outcome; it then returns `ok=true` for that outcome while retaining `data.quality` as the machine-readable row-count and data-quality signal. Re-running `explore` for a command applies this rule to its newly generated code, but existing installed adapters are not silently rewritten. Missing required fields and partial results, including partially missing required fields, remain failures even when zero matches are permitted, so automation can distinguish "command ran", "no matching data was expected", and "data needs review".

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
The install commands below use the published HTTPS asset and its release SHA-256. Add `--dry-run --json` first when you want to verify a package without installing it.
Use `cliany-site cases --json` to inspect active demos, candidate workflows, offline validation commands, and candidate promotion next actions from the CLI; `promotion_evidence_summary.primary_next_task` points automation at the first candidate task to advance, while `promotion_evidence_summary.primary_next_task_acceptance_criteria` states the proof required for that task. Add `--promotion-plan` to print the candidate promotion queue across all matched candidates; combine it with `--json` to read `promotion_plan.primary_next_item`, `promotion_plan.primary_runbook`, `promotion_plan.primary_issue_template_command`, per-candidate primary tasks, the expected release asset name in `expected_adapter_package`, per-candidate `issue_template_json_command`, and the incomplete `task_queue`. Use `cliany-site cases --case-id pypi-project-search --json` to open one case with validation and promotion details, including `promotion_command_plan_summary`; omit `--json` for a copy-friendly human handoff with Promotion Tasks. The candidate human handoff also renders `preflight_required`, `preflight_blocker`, and `runbook_first`, so contributors see the live LLM gate before starting a real `explore`. Add `--issue-template` to print a GitHub issue body for a candidate promotion task, including Acceptance Criteria, `expected_adapter_package`, a `Primary Runbook`, LLM preflight `Command SHA-256`, `Promotion Command Plan Summary`, `Promotion Command Plan` `command_sha256` sub-lines plus `source` / `missing` metadata, standard LLM/doctor blocker comments, `Doctor Preflight Evidence Fields`, and a `Doctor Preflight Evidence Template` with paste-ready placeholders for `cliany-site doctor --llm-live --json` output; combine it with `--json` to also read `issue_template_primary_task`, `issue_template_promotion_command_plan_summary`, the same acceptance, runbook, preflight fields, structured `doctor_preflight_evidence_template`, plus `doctor_preflight_evidence_template_field_count` / `doctor_preflight_evidence_template_sha256` without parsing Markdown. Add `--evidence-bundle` to print a structured local evidence checklist; combine it with `--json` for a machine-readable evidence bundle, including `promotion_command_plan_summary` and a `promotion_command_plan` that starts with `llm_live_preflight` before adapter package, metadata validation, and online smoke commands, per-step `promotion_command_plan[*].command_sha256` drift checks, `primary_next_task_runbook` and `primary_next_task_runbook_first_command` for the current ordered checklist, `llm_live_preflight_required`, `llm_live_preflight_command_sha256`, `doctor_preflight_evidence_fields`, `doctor_preflight_evidence_template`, `doctor_preflight_state_fields`, `doctor_preflight_state_statuses`, and the template/state count/hash aliases on the adapter package task, `expected_adapter_package` for the package artifact, plus `acceptance_criteria` for the proof each evidence task must attach. Use `python scripts/plan_next_iteration.py --issues-dir /tmp/cliany-candidate-issues` to generate reviewable candidate issue artifacts; planner JSON exposes `candidate_promotions[*].issue_template_command`, `candidate_promotions[*].issue_template_json_command`, `candidate_promotions[*].promotion_command_plan_summary`, `candidate_promotions[*].doctor_preflight_evidence_template`, `candidate_promotions[*].doctor_preflight_state_statuses`, and template/state hash aliases, while `issue-metadata.json` and the artifacts README show the same Issue Template / Issue Template JSON handoff and `promotion_command_plan_summary` alongside `Primary Evidence Status`, `Primary Acceptance Criteria`, `primary_next_task_acceptance_criteria`, compact `case_promotion_evidence_primary_runbook_steps` / hash fields, `case_promotion_evidence_primary_runbook_first_command`, `case_promotion_evidence_primary_llm_live_preflight_required`, `case_promotion_evidence_primary_llm_live_preflight_command_sha256`, `case_promotion_evidence_primary_llm_live_preflight_blocker_comment`, `case_promotion_evidence_primary_doctor_preflight_blocker_comment`, `case_promotion_evidence_primary_doctor_preflight_evidence_template_sha256`, `case_promotion_doctor_preflight_evidence_template_sha256`, `doctor_preflight_evidence_fields`, `doctor_preflight_state_fields`, `doctor_preflight_state_statuses`, `required_labels`, `required_label_count`, `required_labels_sha256`, and `case_promotion_llm_live_preflight_evidence_fields` count/hash aliases before maintainers create issues or compare artifact drift.
`--promotion-plan --json` also mirrors doctor template drift metadata onto `promotion_plan.primary_doctor_preflight_evidence_template_field_count`, `promotion_plan.primary_doctor_preflight_evidence_template_sha256`, `promotion_plan.primary_llm_live_preflight_command_sha256`, each candidate's `primary_doctor_preflight_evidence_template_sha256`, and each incomplete `task_queue[*].doctor_preflight_evidence_template_sha256` / `task_queue[*].llm_live_preflight_command_sha256`, so queue-only bots can compare the current doctor evidence contract without opening a full evidence bundle.
`scripts/validate_cases.py --json` now carries the same drift signal on `promotion_evidence_summary.primary_next_task.doctor_preflight_evidence_template_sha256` plus the `doctor_preflight_state_fields` / `doctor_preflight_state_statuses` contract; `scripts/validate_cases.py --report` renders `primary_doctor_preflight_evidence_template_field_count` and `primary_doctor_preflight_evidence_template_sha256` in the Candidate Promotion Evidence Summary table; plain `scripts/validate_cases.py --strict` also prints `promotion_evidence_primary_doctor_preflight_evidence_template_field_count`, `promotion_evidence_primary_doctor_preflight_evidence_template_sha256`, and `promotion_evidence_primary_llm_live_preflight_command_sha256` for stdout-only validation logs. Evidence bundles also expose `doctor_preflight_evidence_selectors`, mapping semantic fields such as `checks[llm_live].details.error_code` to actual doctor JSON selectors such as `data.checks[name="llm_live"].details.error_code`; `doctor_preflight_state_statuses` mirrors the extractor states `ready`, `blocked`, and `missing_fields`.
The `doctor_preflight_state_fields` contract lists `preflight_state.status`, `preflight_state.ready_for_adapter_package`, `preflight_state.primary_reason`, `preflight_state.reason_codes`, and `preflight_state.next_action`; `doctor_preflight_state_statuses` is limited to `ready`, `blocked`, and `missing_fields`, so README-only maintainers can tell whether to continue to `explore` or attach blocker evidence first.
Candidate promotion treats `summary.capabilities.run_browser_workflows.ready=false`, `summary.llm_live_preflight.ready=false`, `generate_adapters.ready=false`, or any `llm_live` warning/error such as `E_LLM_UNAVAILABLE` provider connection failures as blocker evidence; keep `adapter_package` pending or blocked instead of fabricating adapter package proof.
When the live gate blocks promotion, save the doctor result with `cliany-site doctor --llm-live --json > /tmp/cliany-doctor-preflight.json`, then run `cliany-site cases --case-id pypi-project-search --evidence-bundle --doctor-json /tmp/cliany-doctor-preflight.json --json` or `cliany-site cases --case-id pypi-project-search --issue-template --doctor-json /tmp/cliany-doctor-preflight.json`; the output includes `doctor_preflight_evidence_values`, `doctor_preflight_evidence_ok`, `doctor_preflight_evidence_missing_count`, `doctor_preflight_evidence_null_count`, `doctor_preflight_evidence_null_fields`, and `doctor_preflight_state` on the bundle and primary `adapter_package` task. A nullable field is present in doctor JSON with value `null`; a missing field has no matching selector, so automation can handle connection-level failures without conflating them with schema drift.

### SuiteCRM Demo (Enterprise CRM)
```bash
# 1. Install adapter
cliany-site market install https://github.com/pearjelly/cliany.site/releases/download/v0.14.1/demo.suiteondemand.com-0.14.1.cliany-adapter.tar.gz --sha256 1671dd92d3828cecb1f04f41eefceb7bdc727d0dee1f35d4f14ca360432ced31

# 2. Login (opens browser — use demo account from https://demo.suiteondemand.com/)
cliany-site login https://demo.suiteondemand.com/

# 3. Query accounts (no browser needed after login)
cliany-site demo.suiteondemand.com list-accounts --limit 5 --json
```

### ASF Jira (Issue Tracker)
```bash
cliany-site market install https://github.com/pearjelly/cliany.site/releases/download/v0.14.1/issues.apache.org-0.14.1.cliany-adapter.tar.gz --sha256 ad5867d361f372914c536fb59c8f26837af96ed407859cf69dc8464922f05319
cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json
```

### ASF Confluence (Wiki)
```bash
cliany-site market install https://github.com/pearjelly/cliany.site/releases/download/v0.14.1/cwiki.apache.org-0.14.1.cliany-adapter.tar.gz --sha256 effaa19d1604a833aa474733ba05e216cfc1dbb4d9340e4a775ec6b0e8f313fa
cliany-site cwiki.apache.org search-pages --space SPARK --query "release" --json
```

### ASF Jenkins (Build Status)
```bash
cliany-site market install https://github.com/pearjelly/cliany.site/releases/download/v0.14.1/builds.apache.org-0.14.1.cliany-adapter.tar.gz --sha256 b09710acbabfb5465a6e04b5b140a4ffa4aa24795a2b4ada60eeabbddddea0c2
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
cliany-site market publish github.com --version 1.0.0 --json

# Preflight the local adapter package (no runtime writes)
cliany-site market install ~/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz --dry-run --json

# Preflight or install a publisher-provided remote package with a pinned digest
cliany-site market install https://publisher.example/releases/github.com-1.0.0.cliany-adapter.tar.gz --sha256 <64-hex-sha256> --dry-run --json

# Install adapter after reviewing dry_run, package_sha256, files, would_replace, and would_create_backup
cliany-site market install ~/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz

# Rollback
cliany-site market rollback github.com
```

The successful publish JSON returns `data.package_sha256`, a lowercase 64-character hexadecimal SHA-256 of the completed archive. Hand that value to the installer and use it in the remote package's `--sha256 <64-hex-sha256>` argument.

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
| `market install <source>` | `[--sha256] [--force] [--dry-run] [--json]` | Install a local package or an HTTPS package with a pinned SHA-256. |
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

The current iteration plan is tracked in [docs/roadmap-2026-q3.md](docs/roadmap-2026-q3.md). Release and commit cadence is defined in [docs/release-cadence.md](docs/release-cadence.md): one to three verified versions per day, with commits on at least three days each week. Maintainers can use the [weekly maintainer loop](docs/weekly-maintainer-loop.md), plus `next_actions`, `primary_next_action`, `weekly_commit_cadence_ok`, `release_count_today`, `max_daily_releases`, `daily_release_limit_ok`, `daily_release_cap_blocked`, and `daily_release_resume_date` from `scripts/release_readiness.py --json`, `scripts/check_release_cadence.py --json`, or `scripts/check_release_publication.py --json`, to choose the next small verified release slice and confirm whether the latest local tag is publicly visible. Weekly commit-day shortfalls stay visible as cadence next actions, while the daily release gate is driven by the release count cap and other tag/version/changelog/worktree checks; when `daily_release_cap_blocked=true`, `scripts/release_readiness.py --json` also exposes `daily_release_resume_command` and `daily_release_resume_command_sha256` beside the next eligible tag date. After the tag workflow completes, `scripts/check_release_publication.py --remote --distribution --json` also verifies that GitHub Release and PyPI expose the target version; when PyPI project latest cache lags, `distribution.pypi_latest_version`, `distribution.pypi_release_version`, and backward-compatible `distribution.pypi_version` show whether the version-specific PyPI release is already public. Automation can compare `next_actions_sha256`, `publication_blockers_sha256`, `publication_next_actions_sha256`, `publication_publish_commands_sha256`, `target_tag_commands_sha256`, `daily_release_resume_command_sha256`, and `distribution.next_actions_sha256` to detect release-action drift without parsing Markdown reports.

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

For v0.14.4 quality-gate details, see the [release draft](docs/releases/v0.14.4-draft.md).
