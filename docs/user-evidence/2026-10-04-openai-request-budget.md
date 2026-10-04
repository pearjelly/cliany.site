# OpenAI request budget experiment (2026-10-04)

PR #67 tested a 120-second OpenAI-compatible SDK request timeout with SDK-internal retries disabled. The existing cliany-site outer retry loop remains responsible for attempt progress and backoff. The first three controlled runs used clean code commit `f37115c92a6152da6ee2d8b7a61ae73441050609`; all runs used the configured `deepseek-v4.1-flash` model through an OpenAI-compatible endpoint and isolated cliany runtime data outside the repository. PR-triggered CI used offline QA, not a real LLM key.

| Predeclared run | Explore acceptance | Changed-input replay acceptance | Explore timing and retries |
| --- | ---: | ---: | --- |
| `filter-catalog`, 3 trials | 3/3 | 6/6 returned-value plus independent DOM | 14.32-75.76s; no retries |
| `filter-catalog`, 10 trials | 10/10 | 20/20 returned-value plus independent DOM | Median 29.05s; nearest-rank p95 139.54s; one visible retry |
| Three-task controlled matrix, 3 trials per task | 9/9 | 12/12 returned-value plus independent DOM | 9.52-90.01s; no retries |
| Three-task controlled matrix, 10 trials per task | 29/30 | 38/38 returned-value plus independent DOM | Median 27.39s; nearest-rank p95 222.85s; seven trials with retries |

The tenth trial of the 10-filter run is direct evidence of the new boundary: its first model call succeeded in 5.69s, its next attempt ended in a retry outcome at 120.01s, then the retry succeeded in 6.98s after a scheduled 2s backoff. The exploration finished in 139.54s; both changed positive and zero-match replays matched returned values and the independent DOM oracle. The other nine filter trials also passed. Reports remain local at `/tmp/cliany-openai-budget-filter3-f37115c9-20261004.json`, `/tmp/cliany-openai-budget-filter10-f37115c9-20261004.json`, and `/tmp/cliany-openai-budget-matrix3-f37115c9-20261004.json`; the benchmark reports contain numeric timing and result classifications, not prompt or response text.

The predeclared full matrix used the clean evidence-only follow-up commit `33933e283428e85368ef5c38772ce1623ce05a7f` with identical runtime code. Form and semantic tasks scored 10/10 each; filter scored 9/10. Its only failure was filter trial 8, which reached the 300.03s exploration limit after a 5.50s successful model call, two requests ending in visible retry outcomes at 120.01s and 120.56s, and a third attempt still in flight. It produced no command or replay. Six other trials recovered after at least one retry. Of all 30 explorations, 14 exceeded 60s; p50 was 27.39s, nearest-rank p95 was 222.85s, and the maximum was 300.03s. All 38 replays from successful explorations passed returned-value and independent DOM checks, with no silent wrong success or command-partition repair observed. Local report: `/tmp/cliany-openai-budget-strict30-33933e28-20261004.json`. This clears the controlled 27/30 numeric target on one fixed commit, not a general reliability claim or proof of a causal improvement.

The full matrix ran with fresh headless Chromium over CDP for each exploration and independent replay, fresh runtime and adapter directories, and the [predeclared task oracles](../controlled-explore-benchmark.md). Live preflight succeeded in 3.83s; no runs were excluded. The provider did not expose token or cost data in this report. Exact invocation:

```bash
env -u CLIANY_QA_OFFLINE uv run python tests/embodied/run_live_benchmark.py --allow-live-llm --trials 10 --report /tmp/cliany-openai-budget-strict30-33933e28-20261004.json
```

Each `pass` row below passed every changed-input returned-value and independent DOM oracle. Replay counts are one for form and semantic tasks, two for filter (positive and zero-match); the sole failure has no replay. Times are exploration seconds, not replay time.

| Task | Trial | Explore s | Retries | Result / first failing phase |
| --- | ---: | ---: | ---: | --- |
| Form | 1 | 222.85 | 1 | pass |
| Form | 2 | 10.95 | 0 | pass |
| Form | 3 | 131.07 | 1 | pass |
| Form | 4 | 90.58 | 0 | pass |
| Form | 5 | 11.36 | 0 | pass |
| Form | 6 | 9.98 | 0 | pass |
| Form | 7 | 12.03 | 0 | pass |
| Form | 8 | 133.49 | 1 | pass |
| Form | 9 | 31.06 | 0 | pass |
| Form | 10 | 11.62 | 0 | pass |
| Filter | 1 | 187.29 | 0 | pass |
| Filter | 2 | 76.53 | 0 | pass |
| Filter | 3 | 14.86 | 0 | pass |
| Filter | 4 | 142.11 | 1 | pass |
| Filter | 5 | 23.71 | 0 | pass |
| Filter | 6 | 18.23 | 0 | pass |
| Filter | 7 | 135.66 | 1 | pass |
| Filter | 8 | 300.03 | 2 | fail: explore timeout |
| Filter | 9 | 12.44 | 0 | pass |
| Filter | 10 | 19.03 | 0 | pass |
| Semantic reorder | 1 | 14.95 | 0 | pass |
| Semantic reorder | 2 | 9.83 | 0 | pass |
| Semantic reorder | 3 | 12.06 | 0 | pass |
| Semantic reorder | 4 | 18.73 | 0 | pass |
| Semantic reorder | 5 | 75.36 | 0 | pass |
| Semantic reorder | 6 | 88.63 | 0 | pass |
| Semantic reorder | 7 | 15.56 | 0 | pass |
| Semantic reorder | 8 | 111.00 | 0 | pass |
| Semantic reorder | 9 | 201.73 | 0 | pass |
| Semantic reorder | 10 | 139.02 | 2 | pass |

A separate fresh read-only browser exploration of `https://docs.python.org/3/` searched for `asyncio` and generated `search-python-docs --query` in 193.24s. Its three model requests succeeded in 42.60s, 69.69s, and 68.08s without retries. Strict adapter verification passed. A changed `pathlib` command replay returned extract quality `ok`, 100 rows, `limit_reached=true`, and first row `pathlib` / `library/pathlib.html#module-pathlib`. A separate Playwright browser showed the completed search page reporting 131 matches and the same first title and relative link. Thus the command returned a correct capped prefix in this maintainer trial, not all matches. The generated adapter and replay result are local under `/tmp/cliany-pr67-python-public-20261004` and `/tmp/cliany-pr67-python-public-replay-pathlib.json`; the independent browser snapshot is outside the checkout at `/tmp/cliany-pr67-playwright-oracle-20261004`.

For context, an earlier clean 10-filter run on `dbb9d930` without this request budget scored 9/10, with one 300.03s timeout and nearest-rank p95 300.03s. The runs are different samples, so their scores and latencies do not establish a causal reliability or population-latency improvement. Historical samples also include successful individual model requests longer than 120s; this experiment does not prove that every such request is safely replaceable by a retry. No independent first-time user was involved, and the public-site trial is one site and one changed query. Keep the returned-value, DOM, and fail-closed gates for further evaluation.
