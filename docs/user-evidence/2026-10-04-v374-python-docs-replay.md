# Published v0.16.374 Python Docs Adapter Replay

**Date:** 2026-10-04 (Asia/Shanghai). **Scope:** maintainer-only, read-only replay of a public browser-generated candidate. This is not an independent first-user trial or a new live-LLM exploration.

## Setup

- Installed `cliany-site==0.16.374` from PyPI into a fresh Python 3.11.14 virtual environment outside the repository; `cliany-site --version` reported `0.16.374`.
- Downloaded the unchanged [public adapter archive](https://github.com/pearjelly/cliany.site/releases/download/v0.16.373/docs.python.org-0.1.0.cliany-adapter.tar.gz). Its SHA-256 was `29f1ece48fd6749e53cf7384f5be0878c1617d1d8344641e284b6c37150f6592`, matching the pinned quickstart.
- Launched Chrome 154 headless with the normal macOS OS `HOME`, a temporary browser profile, and a dedicated CDP port. The published CLI used a separate temporary OS `HOME` and connected to that Chrome through `--cdp-url`. This split avoids touching the user's adapter directory and avoids the known synthetic-`HOME` Chrome launch problem tracked in [Issue #53](https://github.com/pearjelly/cliany.site/issues/53). It is a maintainer test arrangement, not the ordinary auto-launch path.
- Local archive installation succeeded, then `cliany-site verify docs.python.org --strict --json` returned `verdict=ok` with no issues. Browser replay started only after that gate.

## Read-only outcomes

| Query | CLI exit / quality | Returned rows | First title / relative URL | Independent browser check |
| --- | --- | ---: | --- | --- |
| `pathlib` | 0 / `ok` | 100, `limit_reached=true` | `pathlib` / `library/pathlib.html#module-pathlib` | Previously checked against the site search in the [candidate evidence](2026-10-03-python-docs-browser-candidate.md). |
| `asyncio` | 0 / `ok` | 100, `limit_reached=true` | `asyncio` / `library/asyncio.html#module-asyncio` | A separate browser submitted `asyncio` through Quick search on Python 3.14.8 docs: the first list item had the same title and URL; the page displayed 399 result items. |
| `cliany_no_such_topic_20261004_qq` | 1 / `E_EMPTY_RESULT` | 0, `limit_reached=false` | none | A separate browser search showed zero `#search-results li` items. |

The adapter reports at most 100 rows. Reaching that limit does not prove completeness; for `asyncio`, the independent page showed 399 matching items. Both successful replays reported `data.quality.ok=true`, and the zero-result replay reported `data.quality.ok=false` rather than a successful empty result.

## Boundary

These observations verify the unchanged public archive under one maintainer-controlled split environment at one point in time. They do not test a new user's setup, Chrome auto-launch under a synthetic OS `HOME`, live model generation, or future third-party availability. Keep the adapter candidate and collect independent, sanitized first-use feedback in [Issue #55](https://github.com/pearjelly/cliany.site/issues/55).
