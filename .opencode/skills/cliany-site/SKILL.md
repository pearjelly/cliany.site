---
name: cliany-site
description: Use when the user wants to automate web workflows into CLI commands via Chrome CDP and LLM. Supports exploring pages, generating adapters, and replaying actions through the cliany-site tool.
metadata:
  homepage: "https://github.com/pearjelly/cliany.site"
  version: "0.1.1"
  category: "tools"
---

# cliany-site Skill

Use this skill when the user wants to automate web workflows into callable CLI commands using cliany-site.

cliany-site converts any web workflow into an executable CLI command. It connects to Chrome via CDP, captures page accessibility trees (AXTree), uses an LLM to plan actions, and generates Python/Click command-line adapters.

## When to Use

- User wants to automate a web workflow (form submission, search, navigation, etc.)
- User wants to turn a web operation into a repeatable CLI command
- User wants to check if cliany-site environment is ready
- User wants to manage web sessions or login states
- User wants to list or run previously generated adapters
- User mentions "cliany-site", "web automation", "CDP", "browser CLI", or "web CLI"

## Prerequisites

Before using cliany-site, verify the environment:

1. **Python 3.11+** with `cliany-site` installed
2. **Chrome** with CDP enabled (auto-managed or manual `--remote-debugging-port=9222`)
3. **LLM API Key** — at least one of:
   - `CLIANY_ANTHROPIC_API_KEY` (recommended)
   - `CLIANY_OPENAI_API_KEY`
   - Legacy `ANTHROPIC_API_KEY` (still supported)

Run the doctor command to verify all prerequisites:

```bash
cliany-site doctor --json
```

Expected output on success:
```json
{
  "success": true,
  "data": {"cdp": true, "llm": true, "adapters_dir": "/Users/you/.cliany-site/adapters"},
  "error": null
}
```

## Installation

```bash
# Clone and install
git clone https://github.com/pearjelly/cliany.site.git
cd cliany.site
pip install -e .

# Verify
cliany-site --version
cliany-site doctor --json
```

### LLM Configuration

Set up via environment variables or `.env` file:

```bash
# Anthropic (recommended)
export CLIANY_LLM_PROVIDER=anthropic
export CLIANY_ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI alternative
export CLIANY_LLM_PROVIDER=openai
export CLIANY_OPENAI_API_KEY="sk-..."
```

Configuration file locations (priority low to high):
1. `~/.config/cliany-site/.env`
2. `~/.cliany-site/.env`
3. Project `.env`
4. System environment variables

## Commands Reference

### doctor — Environment Check

```bash
cliany-site doctor [--json]
```

Checks all prerequisites: CDP connection, LLM key, adapter directory structure.

**Output fields:**
- `cdp` (bool): Chrome CDP available
- `llm` (bool): LLM API key configured
- `adapters_dir` (str): adapter storage path

**Always run doctor first** before any other operation to ensure the environment is ready.

### login — Website Login

```bash
cliany-site login <url> [--json]
```

Opens the specified URL, waits for the user to complete manual login, then saves the session to `~/.cliany-site/sessions/`.

**When to use:** Before exploring workflows that require authentication.

### explore — Explore and Generate Workflow

```bash
cliany-site explore <url> <workflow_description> [--json]
```

This is the core command. It:
1. Connects to Chrome via CDP
2. Captures the page AXTree
3. Sends the tree to the LLM with the workflow description
4. LLM plans and executes actions step by step
5. Generates a Click CLI adapter at `~/.cliany-site/adapters/<domain>/`

**Parameters:**
- `url`: Target web page URL
- `workflow_description`: Natural language description of the workflow

**Example:**
```bash
cliany-site explore "https://github.com" "Search for cliany.site repository and view README" --json
```

After success, a `github.com` adapter is auto-registered as a subcommand.

### list — List Adapters

```bash
cliany-site list [--json]
```

Lists all generated adapters by domain name.

### Execute Adapter Commands

```bash
cliany-site <domain> <command> [args...] [--json]
```

Runs a specific command from a generated adapter.

**Example:**
```bash
cliany-site github.com search --query "browser-use" --json
```

### tui — Terminal UI Manager

```bash
cliany-site tui
```

Visual terminal interface for managing adapters, viewing logs, and configuration.

## Output Format

All commands output a standard JSON envelope when `--json` is passed:

```json
{
  "success": true,
  "data": { "..." },
  "error": null
}
```

On failure:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

**Error codes:**

| Code | Meaning |
|------|---------|
| `CDP_UNAVAILABLE` | Chrome not running or port 9222 not open |
| `LLM_KEY_MISSING` | No LLM API key configured |
| `COMMAND_NOT_FOUND` | Unknown command or adapter not found |
| `EXPLORE_FAILED` | Workflow exploration failed |

**Exit codes:**
- `0`: success
- `1`: failure (details in JSON `error` field)

## Typical Workflow

Follow this sequence when automating a new website:

### Step 1: Verify Environment
```bash
cliany-site doctor --json
```
If `cdp` is false, Chrome will be auto-started. If `llm` is false, configure API keys first.

### Step 2: Login (if needed)
```bash
cliany-site login "https://target-site.com" --json
```
Wait for the user to complete manual login in the browser.

### Step 3: Explore Workflow
```bash
cliany-site explore "https://target-site.com" "describe the workflow here" --json
```
The LLM analyzes the page and generates adapter commands.

### Step 4: Use Generated Commands
```bash
cliany-site list --json
cliany-site target-site.com <generated-command> [args] --json
```

### Step 5: Re-explore if Needed
Run explore again on the same domain to add more commands. Existing adapters are merged incrementally — existing commands are preserved.

## Automation Script Example

```bash
#!/bin/bash
set -e

# Check environment
result=$(cliany-site doctor --json)
if ! echo "$result" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); exit(0 if d['success'] else 1)"; then
  echo "Environment not ready"
  exit 1
fi

# Explore workflow
cliany-site explore "https://example.com" "submit the contact form" --json

# Execute generated command
cliany-site example.com submit --name "Test" --email "test@test.com" --json
```

## Architecture Notes

- **Adapter storage**: `~/.cliany-site/adapters/<domain>/` (commands.py + metadata.json)
- **Session storage**: `~/.cliany-site/sessions/`
- **AXTree-based selectors**: Fuzzy element matching survives minor UI changes
- **Incremental merging**: Re-exploring the same domain adds new commands without breaking existing ones
- **Atomic commands**: Reusable operations (login, search) extracted and shared across adapters

## Security & Privacy

- cliany-site connects to a local Chrome instance via CDP on `localhost:9222`
- LLM API calls send page AXTree (accessibility structure, no visual content) to the configured provider
- Session cookies are stored locally under `~/.cliany-site/sessions/`
- Generated adapters contain only Click CLI code and metadata — no credentials are embedded
- No data is sent to external endpoints other than the configured LLM API

## External Endpoints

| Endpoint | Purpose | Data Sent |
|----------|---------|-----------|
| Configured LLM API (Anthropic/OpenAI) | Workflow analysis and action planning | Page AXTree structure, workflow description |
| `localhost:9222` | Chrome CDP connection | CDP protocol commands |

## Trust Statement

By using this skill, page accessibility tree data is sent to your configured LLM provider (Anthropic or OpenAI) for workflow analysis. Only install and use if you trust your LLM provider with the structural content of pages you browse.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `CDP_UNAVAILABLE` | Run `cliany-site doctor` to auto-start Chrome, or manually start with `--remote-debugging-port=9222` |
| `LLM_KEY_MISSING` | Set `CLIANY_ANTHROPIC_API_KEY` or `CLIANY_OPENAI_API_KEY` |
| Explore produces no commands | Provide more specific workflow description; ensure the page has loaded fully |
| Adapter command fails | Page structure may have changed; re-run explore to regenerate |
| Login session expired | Re-run `cliany-site login <url>` |
