# cliany-site

[![PyPI version](https://img.shields.io/pypi/v/cliany-site)](https://pypi.org/project/cliany-site/)
[![Python](https://img.shields.io/pypi/pyversions/cliany-site)](https://pypi.org/project/cliany-site/)
[![CI](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml/badge.svg)](https://github.com/pearjelly/cliany.site/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/pearjelly/cliany.site)](LICENSE)

> 🌐 Languages: [English](README.md) | [简体中文](README.zh.md)

> **⚠️ v0.9.0 BREAKING**: metadata schema v2 hardcut. Legacy adapters (no schema_version) are auto-rejected.  
> Regenerate: `cliany-site explore <url> "<workflow>"`

> Automate any web workflow into callable CLI commands

cliany-site is built on browser-use and Large Language Models (LLMs), enabling full-process automation from web exploration to code generation and replay via the Chrome CDP protocol. Explore with one command, execute with another—turning complex web workflows into repeatable CLI tools.

## Features

### Core Capabilities

- **Zero-Intrusion Exploration** — Chrome CDP captures page AXTree without script injection.
- **LLM-Driven Code Generation** — Claude / GPT-4o understands page semantics and generates Python CLI commands automatically.
- **LLM Call Retry Mechanism** — Automatic retries during network fluctuations to improve exploration success rates.
- **Standard JSON Output** — All commands support `--json`, outputting a unified `{success, data, error}` envelope.
- **Persistent Sessions** — Maintains Cookie / LocalStorage login states across commands.
- **Dynamic Adapter Loading** — Automatically registers CLI subcommands by domain, allowing for easy expansion.
- **Automatic Chrome Management** — Detects and starts Chrome debugging instances automatically.
- **Data Extraction** — Supports extracting structured data from pages and saving it as Markdown.

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

### New in v0.9.x

- **Metadata Schema v2 Hardcut** — Mandatory schema_version=2; legacy adapters are rejected with a prompt to regenerate via `cliany-site explore <url> "<workflow>"`.
- **Smart Healing (`--heal`)** — AXTree snapshot diff + selector hot-fixes without re-exploring; supports healing caps and sidecar recording.
- **Static Verification (`verify`)** — Checks adapter schema, signatures, and dependency integrity without opening a browser; `cliany-site verify <domain> --json`.
- **Self-Describing Endpoints (`--explain`)** — `cliany-site --json --explain` outputs a machine-readable Agent contract for easier automation integration.
- **AGENT.md Auto-Rewrite** — AGENT.md includes sentinels and hashes; automatically updates with new features to keep the agent contract current.
- **Atomic Command System** — Generated commands call reusable atom commands instead of inlining CDP operations, shared across adapters.
- **Unified Envelope (`ok()`)** — All built-in commands use the unified `{success, data, error}` output format.
- **Extended Doctor Health Check** — Covers registry / legacy adapter detection / agent-md consistency validation.
- **Breakpoint Resumption (`--resume`)** — Records breakpoints after adapter command failures, supporting recovery from the point of failure.

## Quick Start (v0.9.0+)

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

# Explore web workflow (requires LLM)
cliany-site explore "https://github.com" "搜索后查看结果" --json

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
```

Also supports `.env` file configuration. Search order: `~/.config/cliany-site/.env` → `~/.cliany-site/.env` → project directory `.env` → environment variables.

### Verify Environment

```bash
cliany-site doctor --json
```

## Usage Examples

### Basic Flow

```bash
# 1. Explore workflow
cliany-site explore "https://github.com" "搜索仓库并查看 README" --json

# 2. List generated commands
cliany-site list --json

# 3. Execute generated command
cliany-site github.com search --query "browser-use" --json
```

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

```bash
# Pack adapter
cliany-site market publish github.com --version 1.0.0

# Install adapter
cliany-site market install ./github.com.cliany-adapter.tar.gz

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
| `verify <domain>` | `[--json]` | Statically verify adapter schema, signatures, and dependency integrity. |
| `replay <domain>` | `[--session <id>] [--step]` | Replay exploration recording with screenshots and actions. |
| `check <domain>` | `[--json] [--fix]` | Check adapter health status. |
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

**Global Options:** `--json` `--verbose` `--debug` `--cdp-url <ws://host:port>` `--headless` `--sandbox` `--explain`

## Architecture Overview

```
cliany-site/src/cliany_site/
├── cli.py              # Main entry point, SafeGroup global exception capture
├── config.py           # Unified configuration center (env + .env)
├── errors.py           # Exception hierarchy + error codes
├── response.py         # JSON envelope {success, data, error}
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

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR workflow.

## Limitations

- Requires Chrome/Chromium (auto-start or manual `--remote-debugging-port=9222`).
- Requires a valid LLM API Key (Anthropic or OpenAI).
- Generated commands depend on page DOM structure; major redesigns may require re-exploration (minor changes handled by fuzzy matching and self-healing).
- Sessions are not shared across browser profiles.
- Recursive collection for cross-origin iframes is enabled by default (configurable via `CLIANY_CROSS_ORIGIN_IFRAMES`).

## Changelog

See full changelog: [CHANGELOG.md](CHANGELOG.md)
