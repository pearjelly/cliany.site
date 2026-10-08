# Published Python docs archive replay

**Date:** 2026-10-08 (Asia/Shanghai). **Scope:** one macOS maintainer host, public PyPI `cliany-site==0.16.377`, and the unchanged v0.16.373 browser-generated adapter archive. This checks an old distributed command against the current published runtime, not a newly generated command or independent first use.

## Package and isolation

The actual CLI was `/tmp/cliany-v377-pypi-20261008/bin/cliany-site`, in the clean Python 3.11 environment used for the [v0.16.377 publication checks](https://github.com/pearjelly/cliany.site/pull/67#issuecomment-6051817216). An import-path assertion confirmed the installed package, not the source checkout. A new selected runtime directory `/tmp/cliany-v377-public-archive-trial-20261008` kept the adapter, sessions and logs outside the repository and default runtime. Normal OS `HOME` was unchanged. No generated code was edited or existing adapter force-overwritten.

Installation used the exact public archive and SHA-256:

```bash
cliany-site market install https://github.com/pearjelly/cliany.site/releases/download/v0.16.373/docs.python.org-0.1.0.cliany-adapter.tar.gz --sha256 29f1ece48fd6749e53cf7384f5be0878c1617d1d8344641e284b6c37150f6592 --json
cliany-site verify docs.python.org --strict --json
```

Both succeeded. Strict verification reported `verdict=ok`, no issues and a matching manifest. The installed `commands.py` SHA-256 was `ee6de206856fc850f540940e669598eb8bbbf7f25666252f4c713bf2e7e63d58`; `metadata.json` was `376535d70d80ed539db1988dce9dfffd3aeb6c6aa60cfe21a261f0e37f748d0e`.

## Replay and independent result

An external harness opened a fresh headless Chromium profile on a dynamically selected unused loopback CDP port, ran the published CLI and closed the browser. The positive command used `--cdp-url ws://127.0.0.1:<fresh-port> docs.python.org search-python-docs --query pathlib --json`; the negative command changed only the query to `cliany-no-match-20261008-67401123`. The same selected runtime directory was inherited by both calls. `CLIANY_QA_OFFLINE=1` guarded against live model use while real public website requests remained enabled; an existing adapter needs no model discovery.

| Path | Observed result |
| --- | --- |
| Fresh explicit CDP, `pathlib` | Exit 0, `ok=true`, quality `ok`, 100 rows and `limit_reached=true`, 8.03 seconds external wall time. |
| Fresh explicit CDP, no-match query | Exit 1, `E_EMPTY_RESULT`, 9.69 seconds; no false successful empty result. |
| Automatic `--headless`, `pathlib` | Exit 0, `ok=true`, 100 rows and `limit_reached=true`, 17.02 seconds; the dedicated browser port was closed after completion. |

The automatic run set `CLIANY_CDP_PORT` to an unused local port, left `CLIANY_CDP_URL` empty and selected Chrome. It did not attach a pre-existing debugging browser. These are individual observations, not a latency comparison or arbitrary-account startup guarantee. The published envelope's zero duration metadata is not used as a timing measurement.

A separate new Playwright browser submitted `pathlib` through the normal Python 3.14.8 documentation search form and waited for completed `Search Results`. It had 131 list entries. Every returned title and relative link, in order, matched the first 100 entries, including `pathlib` / `library/pathlib.html#module-pathlib`. The same independent browser submitted the no-match query and confirmed a completed no-match page with zero rows. Screenshots were inspected and the browser was closed. This verifies the capped prefix for this query, not the remaining 31 entries or every possible query.

Reports are `/tmp/cliany-v377-public-archive-pathlib-20261008.json`, `/tmp/cliany-v377-public-archive-empty-20261008.json`, `/tmp/cliany-v377-public-archive-auto-20261008.json` and `/tmp/cliany-v377-public-archive-oracle-20261008/pathlib-comparison.json`. Browser artifacts are under that oracle directory; no runtime artifact is committed.

## Acceptance status

The archive remains a candidate. Issues [#33](https://github.com/pearjelly/cliany.site/issues/33) and [#55](https://github.com/pearjelly/cliany.site/issues/55) still require people who did not build the adapters. The synthetic-home Chrome cause in [#53](https://github.com/pearjelly/cliany.site/issues/53) remains unresolved. Prefer `CLIANY_RUNTIME_HOME` for product-state isolation, keep normal OS `HOME`, and isolate browser profiles separately. This evidence neither promotes the case nor establishes full collection, continuing service availability or alpha readiness.
