# Controlled Explore-to-Replay Benchmark

The opt-in runner uses three local browser tasks: a parameterized form, a filter with positive and zero-match results, and a button whose AXTree ref changes between loads while its role and name stay stable. Each trial explores with a fresh cliany-site runtime directory and a fresh headless Chromium CDP browser. Each generated command is then replayed with changed inputs in another browser. A trial passes only when the returned extract values and an independent page-state oracle both match.

Run from a clean checkout with a configured live provider and Playwright Chromium:

```bash
env -u CLIANY_QA_OFFLINE uv run python tests/embodied/run_live_benchmark.py --allow-live-llm --trials 3 --report /tmp/cliany-explore-benchmark.json
```

For the acceptance sample, use `--trials 10` on a fixed commit and provider. Record all failures and the first failing phase; do not remove timeout trials from the denominator. The runner rejects offline/fake-LLM mode and report paths inside the repository. Default PR CI remains offline and runs only fixture and runner tests. A passing local benchmark is not evidence that a third-party site or a published adapter works.
