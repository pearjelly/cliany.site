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
