# v0.16.371 Controlled Explore Baseline

On 2026-10-03, the clean published-version master commit `779e592d520a00558e73645726510fd3f5acf855` ran the opt-in three-task benchmark:

```bash
env -u CLIANY_QA_OFFLINE uv run python tests/embodied/run_live_benchmark.py --allow-live-llm --trials 3 --report /tmp/cliany-v371-master-strict-3x3-20261003-779e592.json
```

The runner reported `git_dirty=false`, package `0.16.371`, and live preflight success in 3.25 seconds. It used a new cliany-site runtime directory and headless Chromium CDP browser for every explore, then another browser and changed inputs for each replay. Generated metadata on completed trials identified `deepseek-v4.1-flash`; the report did not independently record a model name for the timed-out trial. No real LLM secret or generated adapter is stored in this repository.

| Task | Strict trials | Failures |
| --- | ---: | --- |
| Form result | 2/3 | Trial 2 reached the 300.02-second explore cap. Successful explores took 162.63 and 139.98 seconds. |
| Filter catalog | 0/3 | All three commands generated and replayed positive and zero-match inputs. All six DOM oracles passed, but all six returned-value checks failed with `EXTRACT_MISMATCH`. Explore times: 33.48, 196.01, 23.62 seconds. |
| Semantic reorder | 2/3 | Trial 3 passed its DOM oracle but returned the wrong extract value (`EXTRACT_MISMATCH`). Explore times: 137.45, 98.45, 16.10 seconds. |
| **Total** | **4/9** | One explore timeout and four trials with incorrect returned data. |

All 11 replay page-state oracles passed, while only four returned-value checks passed. This is a small same-provider controlled sample, not a public-site success estimate. The report does not retain extracted values or generated selectors for successful command generation, so it does not prove the exact cause of each mismatch. It does prove that page-state-only success would materially overstate utility on the published v0.16.371 baseline. The previous 25/30 result came from a different, unmerged draft runtime and is not comparable as a version-to-version improvement claim.

The follow-up candidate addresses the observed filter failure class without inventing CSS fallback selectors: visible read-only AX nodes expose only stable selectors derived from observed DOM attributes; single semantic list containers extract their `<li>` items; and an empty scalar cannot be masked by an allowed empty list. Unit and Chromium regressions cover these contracts.

On clean candidate `7b918c554842efd471e374ff7c9b1a8ecda7fd59`, a focused `--case filter-catalog --trials 3` run wrote `/tmp/cliany-filter-grounded-20261003-7b918c5.json`. Live preflight passed in 3.78 seconds. The task scored **2/3**: trials 2 and 3 generated reusable commands whose positive and zero-match replays all passed both returned-value and DOM checks (four replays, 2.13-6.06 seconds). Trial 1 failed closed with `E_EMPTY_RESULT` during exploration after 243.75 seconds and generated no command. Explore times for the two successes were 110.86 and 154.19 seconds. This is a small focused sample on a different commit, not a causal estimate against the 0/3 baseline. The remaining extraction failure and model-wait tail are open; full cross-task and 10-trial-per-task acceptance have not passed.
