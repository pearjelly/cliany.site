# Jira PyPI demo audit (2026-10-02)

## Scope

Installed public `cliany-site==0.16.368` from PyPI in an isolated Python 3.11 environment and used a fresh temporary HOME. The case was `apache-jira-issues`; no LLM key, Chrome/CDP session, or login was used. This is a read-only query of ASF's public Jira data at the time of the run.

## Public package

The case's v0.14.1 [GitHub Release asset](https://github.com/pearjelly/cliany.site/releases/tag/v0.14.1), `issues.apache.org-0.14.1.cliany-adapter.tar.gz`, was independently downloaded. Its SHA-256 was `ad5867d361f372914c536fb59c8f26837af96ed407859cf69dc8464922f05319`, matching `cases/manifest.json`.

## First result and reuse

In the empty HOME:

```bash
cliany-site demo --case-id apache-jira-issues --json
```

The command exited 0 with `ok=true`, `installed_now=true`, `adapter_domain=issues.apache.org`, and `row_count=5`. The nested read-only result reported `project=SPARK`, `count=5`, and `total=59502`; its issue rows had keys such as `SPARK-59927` and nonblank summaries. A second run in the same HOME exited 0 with `installed_now=false` and `row_count=5`, reusing the installation. A separate `cliany-site verify issues.apache.org --strict --json` returned `verdict=ok`, `manifest.status=ok`, `issues=[]`, and `smoke=null`.

This proves the current published CLI's fixed-hash install, static gate, and declared read-only Jira result worked together at this moment. Jira's issue IDs, totals, and availability can change; this does not prove live LLM exploration or a browser-generated workflow.

## Fresh Python 3.11 first-use check

A separate run installed the same pinned PyPI version into a new Python 3.11.14 virtual environment with a fresh temporary HOME and no LLM key. From outside the repository, `cliany-site doctor --json` exited 0 with `ok=true`; it warned about the missing LLM key and `AGENT.md`. `cliany-site demo --case-id apache-jira-issues --json` exited 0 with `ok=true`, `installed_now=true`, and `row_count=5`. `cliany-site verify issues.apache.org --strict --json` then returned `verdict=ok`.

The demo returned `SPARK-59935` with a summary and `Open` status. A separate direct request to Jira's public REST issue endpoint returned the same summary and status. This is a maintainer-operated fresh-install check of the published v0.16.368 path, not independent-user evidence or a v0.16.370 acceptance test. The observed `doctor` warning motivated clearer guidance in the v0.16.370 candidate: existing adapters do not require `AGENT.md` or an LLM key.
