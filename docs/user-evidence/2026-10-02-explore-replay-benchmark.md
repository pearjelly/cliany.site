# Controlled explore-to-replay benchmark (2026-10-02)

## Scope

Opt-in live LLM test on commit `aa227fb1a643c766fa1a0289fed13b8d8d19ae84` (`git_dirty=false`), using the local v0.16.369 candidate and configured `deepseek-v4.1-flash` provider. These are controlled local pages, not public-site workflows or a published PyPI v0.16.369 build. Each trial used a fresh runtime home and headless Chromium instance for exploration; each replay used another fresh browser. Playwright read the page DOM independently of the generated command result.

The semantic-target fixture inserts a different number of preceding buttons on each load. An embodied test captures the project's actual AXTree `selector_map` over CDP on two loads and verifies that `Inspect Beta` retains its button role/name while its `@ref` changes. This checks the claimed reference drift directly, beyond DOM row order.

Run: `uv run python tests/embodied/run_live_benchmark.py --allow-live-llm --trials 3 --report /tmp/cliany-live-benchmark-2026-10-02-aa227fb.json`. The JSON report is outside the repository; it contains per-trial phase, latency, generated command, declared empty-result expectation, replay outcome, and error code. No token or cost metric was available from this invocation.

| Task | Fresh explorations with correct independent replay | Replay oracle |
| --- | ---: | --- |
| Form action | 3/3 | Changed parameters produce `Grace:Red` |
| Filter/search | 3/3 | `gamma` yields one coded row; `no-such-package` yields zero rows |
| Semantic target after layout changes | 2/3 | Exactly one `Inspect Beta` hit and `Beta` result |
| **Total** | **8/9** | All successful trials passed their DOM oracle |

| Task | Trial | Explore (s) | Replay (s) | First failing phase / result |
| --- | ---: | ---: | --- | --- |
| Form | 1 | 44.28 | 2.21 | Pass |
| Form | 2 | 15.71 | 2.22 | Pass |
| Form | 3 | 16.31 | 2.21 | Pass |
| Filter | 1 | 26.47 | 2.12, 4.05 | Pass, including zero match |
| Filter | 2 | 19.91 | 2.14, 4.04 | Pass, including zero match |
| Filter | 3 | 15.58 | 3.92, 4.06 | Pass, including zero match |
| Semantic | 1 | 17.91 | Not run | Exploration: invalid action partition |
| Semantic | 2 | 23.03 | 1.88 | Pass |
| Semantic | 3 | 54.35 | 1.90 | Pass |

The failed semantic-target trial stopped during exploration: the model declared an invalid command action partition. The CLI rejected it with `E_UNKNOWN` before adapter generation. The successful explorations took 15.58-54.35 seconds; successful replays took 1.88-4.06 seconds. This small, single-provider sample is not a general success-rate estimate.

## Observed defect and change

On the earlier clean baseline (`08be170`, 8/9 overall), the filter task passed 2/3. A filter-only diagnostic rerun passed 1/3: one exploration failed its extraction quality gate (`E_EMPTY_RESULT`, 209.02 seconds), and another generated command rejected a legitimate zero-match replay with `E_EMPTY_RESULT`. The system prompt had limited `expects_nonempty=false` to absence-confirmation workflows despite the benchmark's explicit zero-match requirement.

The prompt now tells the model to set `expects_nonempty=false` for search/filter workflows that explicitly allow zero matches, while preserving rejection of missing fields and incomplete extraction. Focused deterministic prompt/runtime regressions passed (60 tests); the full offline suite passed (3,152 tests). A filter-only live rerun after this change passed 3/3, and the clean-commit matrix above also passed filter 3/3. This is evidence of improvement on this task, not proof that the model always honors the instruction or that the remaining action-partition failure is fixed.

Three preliminary form smokes were excluded from the nine-trial matrix: the first two exposed a harness bug that read `type` instead of `action_type` in generated metadata, and the third was a one-trial harness check before the committed baseline. The diagnostic filter reruns were also excluded from the final nine-trial denominator because they ran on changing, uncommitted harness/prompt states. Their outcomes are described above rather than silently pooled.

## Partition-repair follow-up

Commit `7b4c215e5d7b38070a749bf7fe7d2f5d42e22994` adds one strictly validated LLM correction request after an invalid final command partition. The correction cannot execute new page actions; a second invalid partition still fails. Deterministic tests cover successful correction, rejection of newly proposed actions, and exhaustion without guessing indices. The full offline suite passed 3,154 tests, with Ruff and mypy passing.

An opt-in clean-commit rerun of only the semantic-target task used the same provider and fresh runtime/browser isolation: 3/3 trials passed the independent DOM oracle. Explore times were 15.28, 13.54, and 20.28 seconds; replay times were 1.96, 1.87, and 1.88 seconds. Run: `uv run python tests/embodied/run_live_benchmark.py --allow-live-llm --case semantic-reorder --trials 3 --report /tmp/cliany-live-benchmark-semantic-repair-2026-10-02.json`. The runner does not count partition-correction calls, so this 3/3 does **not** prove that the correction path was exercised by the live model. It is not pooled with the original nine-trial matrix.

Commit `04f037c8ef420a084dcbc9b2ef5162b44ca069a1` adds `partition_repair_attempts` to the exploration response and benchmark report. A further clean-commit semantic-only rerun passed 3/3 with independent replay, but the count was **0 in all three trials**. Explore times were 18.52, 9.70, and 16.63 seconds. Run: `uv run python tests/embodied/run_live_benchmark.py --allow-live-llm --case semantic-reorder --trials 3 --report /tmp/cliany-live-benchmark-semantic-observed-2026-10-02.json`. Thus this sample explicitly did not exercise the repair path; the repair behavior is demonstrated by deterministic tests, not live attribution.

## Public-site search smoke

One opt-in live exploration started from the [Python documentation homepage](https://docs.python.org/3/) in fresh headless Chromium and generated `docs.python.org search-python-docs --query ...` in an isolated temporary runtime home. The model used the page's `Quick search` field and `Go` button and recorded a parameterized list extraction from the resulting search page. This is a real public-site workflow, but only one exploration, not an independent-user test.

Before the replay fix, fresh-browser runs returned success with 21 `pathlib` rows and 2 `asyncio` rows. The browser DOM already had 41 and 21 matching rows, respectively, immediately after those CLI calls, and the page was still rendering. This is a silent partial-result defect: nonempty quality alone did not mean the list had settled.

Generated list/table replay now resamples every 0.5 seconds until four consecutive contents agree, with a six-second bound and `E_PAGE_NOT_READY` if results keep changing. Errors from a later sample pass through. On fresh-browser reruns of the same generated command, `pathlib` and `asyncio` each returned 100 rows; the page showed `Search finished` and contained 131 and 399 rows. All 100 returned titles and links matched the browser DOM for both queries. The extractor intentionally caps list output at 100 items, so these results demonstrate the first 100 only, **not** complete retrieval or a universal guarantee that a short quiet period means a page is done. The rule adds about 1.5 seconds for stable lists and up to six seconds for changing ones. No public-site claim is included in the controlled 8/9 score above.

### Fresh public-page trials and package candidate

On commit `47c64dec15dea04f6cf968b597d6a1e71065524c`, three more opt-in `deepseek-v4.1-flash` explorations independently started from the Python documentation homepage with fresh runtime homes and Chromium processes. The workflow explicitly requested the first 100 search titles and links. Each generated one `search-python-docs` command with a required `query` argument. Each command was replayed in a separate fresh browser for `pathlib` and `asyncio`. The independent oracle required the query in the resulting page URL, visible `Search finished` status, a nonempty result, and exact title/link agreement with the first 100 browser DOM rows. All six replays passed; this is 3/3 explorations, not a population-level reliability estimate.

| Trial | Explore (s) | `pathlib` replay (s) | `asyncio` replay (s) | Oracle |
| --- | ---: | ---: | ---: | --- |
| 1 | 49.75 | 7.42 | 6.36 | Both 100/100 match |
| 2 | 20.87 | 5.96 | 6.48 | Both 100/100 match |
| 3 | 43.28 | 7.36 | 5.81 | Both 100/100 match |

Trial 1's unedited generated adapter was locally packaged as `docs.python.org-0.16.370.cliany-adapter.tar.gz` (SHA-256 `bb56d401923b7aa5b632657843a56d938778d8ed39465aed05b94980e132c0b7`). A separate clean runtime home installed that archive, passed `verify docs.python.org --strict`, and replayed a changed `dataclasses` query in a fresh browser: 44 returned rows exactly matched the page's 44 title/link rows after `Search finished`. The package is **local and unpublished**; no public package URL, published-version install, or fixed-SHA remote download has yet passed. This case remains a candidate until those release-time checks do.

The catalog tracks this as `python-docs-search` with the local package metadata gate complete and the public-package and published-install smoke gates pending. Focused `validate_cases.py --case-id python-docs-search --packages-dir ~/.cliany-site/packages --include-candidate-packages --strict` passed for the local SHA-256 archive; it does not replace validation of the future Release download.

## Thirty-trial fixed-baseline follow-up

An opt-in run on clean commit `8c240719f80fc09bddd19204e2a8ce251362be7b` (`git_dirty=false`, local package version `0.16.370`, configured `deepseek-v4.1-flash`) used the same three predeclared controlled tasks and fresh runtime/browser isolation. Command: `uv run python tests/embodied/run_live_benchmark.py --allow-live-llm --trials 10 --report /tmp/cliany-live-benchmark-2026-10-02-8c24071-30.json`. Live LLM preflight passed. The local JSON report is outside the repository; no token or cost metric was captured.

| Task | Correct independent replays | First failing phase |
| --- | ---: | --- |
| Form action | 10/10 | None |
| Filter/search, including zero-match replay | 7/10 | Trial 5: explore quality gate `E_EMPTY_RESULT` after 237.66 s; trial 8: benchmark explore timeout at 300.03 s; trial 10: positive `gamma` replay returned `E_EMPTY_RESULT` |
| Semantic target after layout changes | 10/10 | None |
| **Total** | **27/30** | Three filter failures, retained in the denominator |

All 35 replays that returned success passed their independent page-DOM oracle; one additional `gamma` replay failed explicitly, while its zero-match companion passed. No silent wrong success was observed in this sample. The explore-time median was 33.28 seconds, with a 237.66-second near-tail failure and a 300.03-second timeout. All recorded `partition_repair_attempts` were zero, so the live sample still does not exercise that correction path. The harness records only the failed replay's error code, not the generated extraction metadata or quality details; the cause of trial 10's `E_EMPTY_RESULT` is unresolved and tracked in [Issue #35](https://github.com/pearjelly/cliany.site/issues/35). This controlled single-provider result meets the plan's 27/30 numerical threshold, but does not establish public-site or population-level reliability. In particular, the 7/10 filter result and latency outliers remain product work.

### Filter diagnosis

The original filter trial 5 quality details show a 20-action command with extra `url` fields that were blank in every row, plus a later extraction execution error. A separate filter-only 10-trial run on clean commit `f9c35d4c131249db1c5068081fc5c0cc4b6f03e0` scored 9/10. Its trial 8 failed exploration after 88.64 seconds: the generated command again required a `url` field absent from the result, despite the workflow requesting only count and package names. The existing one-time completion feedback gave the model `extract_quality_failed` but omitted the blank field name; the repeated correction still failed. The median exploration time in this second filter-only sample was 68.13 seconds and the maximum was 155.42 seconds. It does not erase the earlier 7/10 result or identify the separate positive `gamma` replay failure.

The candidate completion feedback now includes up to five field names blank in all rows and tells the model to drop a field only when the task does not require it and the page lacks it, or to locate a real value before re-extracting when it is required. It never invents values or relaxes the extraction quality gate. Focused tests and the full 3,160-test offline suite pass. Two attempted clean-commit live runs on `b4e05b20c40437478abede3b07d16a38f2b263ba` stopped at the 120-second LLM preflight timeout before any trials, despite local `doctor` recognizing the configured key. They contribute **zero** post-change trials; live impact remains unverified.

Further deterministic investigation found that the original command-partition rule required every recorded action to be emitted, while completion quality checked every owned extract. A failed extract therefore kept failing even after a new valid extract was recorded. The candidate now permits omission only of extract indices already proven failed by completion evidence; all other actions remain mandatory, and a new successful extract is required. Tests cover successful replacement, continued rejection of a partial replacement, non-executing partition correction, and rejection of omitted required actions. The full offline suite passed 3,163 tests. This demonstrates that the repair path is reachable under controlled responses, not that the live model will choose the right correction.

### Post-repair live filter sample

The provider preflight later recovered. A clean-commit filter-only run on `89645327b19b4f0982abc4ab16891c19d6dbd591` used `--case filter-catalog --trials 10` and wrote `/tmp/cliany-live-benchmark-filter-recovery-2026-10-02-8964532.json`. It passed **6/10**, not an improvement over the earlier 7/10 and 9/10 samples. Trial 2 finished exploration without declaring a reusable command; trial 7 reached the 300-second exploration timeout. Trials 3 and 8 generated commands whose positive `gamma` replay passed, but whose zero-match replay returned `E_EMPTY_RESULT`. The captured quality details showed an empty count-text extraction and a one-row list with every field blank, aggregated as `partial`. Treating that malformed row as a valid zero-row result would weaken the quality gate, so the explicit error is preferable to a silent wrong success. All 14 replays that returned success passed their independent DOM oracles; two failed explicitly. Trial 5 recorded one partition-correction attempt and passed both replays, but the report does not establish whether it used the failed-extract recovery path. These results leave live benefit unproven and show the filter workflow still needs work.
