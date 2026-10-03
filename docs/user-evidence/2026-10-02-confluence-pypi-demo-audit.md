# Confluence PyPI demo audit (2026-10-02)

## Scope

Installed public `cliany-site==0.16.368` from PyPI in an isolated Python 3.11 environment and used a fresh temporary HOME. The case was `apache-confluence-search`; no LLM key, Chrome/CDP session, or login was used. Only public read-only Confluence search was run.

## Public package

The maintained v0.16.365 [GitHub Release asset](https://github.com/pearjelly/cliany.site/releases/tag/v0.16.365), `cwiki.apache.org-0.16.365.cliany-adapter.tar.gz`, was independently downloaded. Its SHA-256 was `85ab3e918f32070fd69ae2947e69530b936a9d6655588d5153612d2686cac84f`, matching `cases/manifest.json`.

## First result and reuse

In the empty HOME:

```bash
cliany-site demo --case-id apache-confluence-search --json
```

The command exited 0 with `ok=true`, `installed_now=true`, `adapter_domain=cwiki.apache.org`, and `row_count=6`. The nested result reported `space=SPARK`, `query=release`, `count=6`, and page URLs under `https://cwiki.apache.org/confluence/spaces/SPARK/`, including `Preparing Spark Releases`. A second run in the same HOME exited 0 with `installed_now=false` and `row_count=6`. Separate `verify cwiki.apache.org --strict --json` returned `verdict=ok`, `manifest.status=ok`, and `issues=[]`.

As a read-only negative control, `search-pages --space SPARK --query cliany-nonexistent-928473 --json` returned `count=0` and `results=[]`. This shows the query affects the public API result, but does not independently verify the relevance of every full-text hit. The nonempty demo result is not evidence of live LLM exploration, browser-generated commands, or future third-party availability.
