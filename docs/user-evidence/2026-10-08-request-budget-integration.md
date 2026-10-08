# Request Budget Integration Review

**Date:** 2026-10-08 (Asia/Shanghai). **Fixed implementation:** `6a3540d290f5dbea18f5a5796d341e9bf4f3dfa4`, clean worktree, based on v0.16.376 plus the privacy-safe provider report in PR #66. The model was `deepseek-v4.1-flash`, provider class `openai`, endpoint type `custom`. Runtime directories and reports were outside the repository; Chrome retained the normal OS HOME. These are maintainer-only trials, not independent-user acceptance.

## Deterministic and Client Boundary Checks

The complete offline suite passed 3,231 tests with six existing warnings in 192.05 seconds. Focused tests, Ruff and Mypy passed. The real synchronous and asynchronous SDK clients both have a 120-second network timeout and zero internal retries. Mock HTTPX transport tests convert `ReadTimeout` into the actual SDK `APITimeoutError`, then exercise recovery and exhaustion through the existing outer loop: two visible attempts produce exactly two HTTP requests, with no private text in progress events. JSON mode remains enabled. PR CI and Embodied CI passed on this implementation.

This is a network-operation timeout, not a hard end-to-end deadline. The [HTTPX contract](https://www.python-httpx.org/advanced/timeouts/) separates connect/read/write/pool waits; response chunks and multiple workflow stages can extend elapsed time. Exploration retains its existing outer attempts and backoff; doctor retains one explicit preflight attempt. Retries may incur model cost, which these reports do not expose.

## Availability and Controlled Integration

Three benchmark starts were retained. The first strict preflight failed in 6.17 seconds with `E_LLM_UNAVAILABLE`; the second reached the existing 120.01-second benchmark preflight limit. Neither started a trial. A separate strict doctor probe passed between those starts, so one successful probe did not establish sustained availability. The third start passed preflight in 4.86 seconds and ran the full predeclared three-task, three-trial integration sample. No trial was excluded and the 300-second exploration limit was unchanged.

| Task | Explore acceptance | Changed-input output + independent DOM | Explore seconds |
| --- | ---: | ---: | --- |
| Form result | 3/3 | 3/3 | 11.22, 15.55, 10.68 |
| Positive/zero-match filter | 3/3 | 6/6 | 23.20, 17.43, 42.98 |
| Changed AXTree reference | 3/3 | 3/3 | 141.20, 12.58, 13.33 |

All 12 replays passed both returned-value and independent DOM checks; no silent wrong success was observed in this sample. Median exploration was 15.55 seconds; nearest-rank p95 was 141.20 seconds. Semantic trial 1 recorded a retry outcome after 121.35 seconds, a scheduled two-second backoff, and a successful next attempt in 6.55 seconds; a subsequent model call took 7.62 seconds. This directly verifies recovery through the current outer retry path, not a causal or population latency improvement.

Reports: `/tmp/cliany-pr67-rebased-matrix9-6a3540d2-20261008.json`, `/tmp/cliany-pr67-rebased-matrix9-retry-6a3540d2-20261008.json`, and `/tmp/cliany-pr67-rebased-matrix9-attempt3-6a3540d2-20261008.json`. Each used:

```bash
env -u CLIANY_QA_OFFLINE uv run --frozen python tests/embodied/run_live_benchmark.py \
  --allow-live-llm --trials 3 --report <report-path-outside-repository>
```

This is a fresh integration smoke, not a replacement for the earlier [fixed-commit 29/30 full controlled study](2026-10-04-openai-request-budget.md), which retained its one timeout and all 38 correct replays. The timeout-policy runtime code is unchanged from that study. No general reliability or tail-latency claim follows from either sample.

## Public Browser Workflow

A fresh headless Chromium over an explicit CDP port and an initially absent selected runtime directory ran the actual CLI, not the benchmark CLI wrapper. A read-only exploration of `https://docs.python.org/3/` searched for `asyncio` through Quick search and generated `search-python-docs --query` in 30.29 seconds. Its two model attempts succeeded in 6.21 and 13.89 seconds without retry. `verify docs.python.org --strict --json` returned `verdict=ok`; the newly generated adapter has no market manifest yet and was not published.

Each replay used another fresh browser and the same selected runtime directory. Changed input `pathlib` completed in 7.77 seconds with extract quality `ok`, 100 rows, and `limit_reached=true`. The first title was `pathlib`, with relative link `library/pathlib.html#module-pathlib`. An independent Playwright browser submitted the site's own search form and showed completed `Search Results`, 131 rows and that same first title/link. Thus this checks a capped nonempty result and its first item, not every returned row or all matching pages. A changed query `cliany-no-match-20261008-67401123` exited nonzero with `E_EMPTY_RESULT` in 9.63 seconds; the independent completed page had zero list rows and its no-match message. No generated code was edited or access challenge bypassed.

The source trial, positive replay and safe negative summary are at `/tmp/cliany-pr67-public-explore-6a3540d2-20261008.json`, `/tmp/cliany-pr67-public-pathlib-6a3540d2-20261008.json` and `/tmp/cliany-pr67-public-empty-6a3540d2-20261008.json`. The adapter is under `/tmp/cliany-pr67-public-runtime-6a3540d2-20261008`. Independent browser artifacts are under `/tmp/cliany-pr67-public-oracle-20261008`; its browser was closed.

## Release Decision and Limits

Include PR #66 and #67 in the next release, subject to final-master and three-channel publication gates. The client timeout and explicit retry path are verified, while transient preflight failures, long waits, historical successful requests exceeding 120 seconds, and the 100-row cap remain relevant limits. Keep Issues #38, #33 and #55 open. Case statuses remain unchanged; this one-site maintainer trial neither promotes the Python docs candidate nor establishes independent first use. Repeat appropriate checks from the published package before completing the release.
