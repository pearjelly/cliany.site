# Controlled explore-to-replay benchmark (2026-10-02)

## Scope

Opt-in live LLM test on commit `aa227fb1a643c766fa1a0289fed13b8d8d19ae84` (`git_dirty=false`), using the local v0.16.369 candidate and configured `deepseek-v4.1-flash` provider. These are controlled local pages, not public-site workflows or a published PyPI v0.16.369 build. Each trial used a fresh runtime home and headless Chromium instance for exploration; each replay used another fresh browser. Playwright read the page DOM independently of the generated command result.

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
