# Semantic extract layout replay review

**Date:** 2026-10-09. **Scope:** source candidate for v0.16.380, controlled maintainer evidence for [Issue 37](https://github.com/pearjelly/cliany.site/issues/37). Three fresh live explorations produced commands whose six changed-layout positive and zero-match replays returned the expected counts and package names. This is not published-package acceptance, a general success rate, or independent first-user evidence.

## Reproduced wrong success

A deterministic generated adapter on clean baseline `0b2e6aec68d7abcbdabfc9c3db2de15b0db7a914` used the observed `#results` list and explicitly allowed zero matches. After the page renamed that result region, `gamma` returned `ok=true`, exit 0 and `[]`, while a separately operated browser displayed `Gamma toolkit`. The baseline recorded AX information during exploration but did not retain a semantic extract target for replay. This failure does not mean legitimate zero matches should become errors.

The candidate records targets from the actual pre-extract snapshot, replacing model-provided target claims. Replay resolves their role, stable name and observed attributes against the current AX/DOM mapping. It then verifies a unique live root before reading. Missing targets, unresolved equal-score matches, duplicate roots and unsupported native collection shapes fail closed; an existing intended container can still return zero matches when the command permits them. No guessed CSS fallback or historical generated-module rewrite was added.

## Retained first study

The first three-trial study ran on clean `6991c8bd91b00ac2c5f45148d050af5e5a0f01be`, with the candidate source installed as development version `0.16.379`, not the public v0.16.379 runtime. The provider preflight passed in 3.81 seconds. All three commands retained observed status/list targets, and all six returned-value and independent-browser checks passed. The overall score remained **0/3** because none of the six replays established a changed button reference.

| Trial | Explore seconds | Positive replay seconds | Zero-match replay seconds | Failure |
| --- | ---: | ---: | ---: | --- |
| 1 | 80.56 | 4.17 | 8.17 | `REF_DID_NOT_CHANGE` on both replays |
| 2 | 106.17 | 4.20 | 8.17 | `REF_DID_NOT_CHANGE` on both replays |
| 3 | 26.61 | 4.19 | 8.11 | `REF_DID_NOT_CHANGE` on both replays |

A deterministic browser probe found that separate fresh browsers assigned the same backend node ID, `3`, to Search despite the injected control. The harness now observes the original DOM in each fresh replay browser before navigating to the changed page. Its fixture responses use `Cache-Control: no-store` so the second navigation cannot silently retain the old variant. A Chromium regression verifies both the changed reference and changed result root. This changes test preparation, not the product resolver or output oracle; the failed study is not rescored.

## Fixed study

The complete repeat used clean `5e121a69ce2a9f37ccc39e4b588eec87e6f4871a`, unchanged product code, three new explorations and six new replay browsers. The normal OS home was preserved while each exploration used an isolated runtime directory. Real model calls used the OpenAI-compatible custom provider with `deepseek-v4.1-flash`; the live preflight passed in 3.67 seconds. Exploration/replay limits stayed 300/120 seconds. No fake responses or command-partition repair were used.

```bash
env -u CLIANY_QA_OFFLINE -u CLIANY_QA_FAKE_LLM_RESPONSES \
  .venv/bin/python tests/embodied/run_live_benchmark.py \
  --allow-live-llm --case filter-catalog --shift-filter-layout \
  --trials 3 --report /tmp/semantic-extract-source-review.json
```

Each generated command recorded the `status` target at observed `summary` and the `list` target named `Package results` at observed `results`, with a recorded `li` suffix. Replay renamed both IDs, added another control and reused the old list ID for unrelated Favorites. The intended list's stable name prevented that old ID from selecting Favorites. Dynamic result text was not frozen as the target identity.

| Trial | Explore seconds | Positive replay seconds | Zero-match replay seconds | Returned values and independent browser | Recorded to replay Search ref |
| --- | ---: | ---: | ---: | --- | --- |
| 1 | 22.16 | 4.19 | 7.90 | Both passed | `3` to `34`, both |
| 2 | 121.23 | 4.15 | 10.97 | Both passed | `3` to `34`, both |
| 3 | 130.42 | 7.13 | 11.02 | Both passed | `3` to `34`, both |

The result is **3/3**, with **6/6** strict `per-row-v2` output checks and independent-browser checks. `gamma` returned `1 matches` plus `Gamma toolkit`; `no-such-package` returned `0 matches` plus an empty collection under the recorded `expects_nonempty=false` contract. The oracle compares exact cardinality, order and every returned collection, not merely the presence of one expected value. A separate browser performs the ordinary search and verifies count, names and package codes. No wrong success was observed in this bounded repeat.

Trial 2 retained one visible retry: attempt durations were 5.84, 98.92 and 10.10 seconds, with outcomes success, retry and success and a scheduled two-second backoff. Trial 3 retained a 116.98-second successful attempt. The sample does not establish improved latency or provider availability. It is one task, not the three-task reliability matrix; the report's general `eligible_for_issue_acceptance` remains false while its scoped `eligible_for_grounding_review` is true.

## Regression and compatibility gates

The fixed source passed 3,332 offline tests, source type checking, scoped lint and both ordinary and Chromium CI on the exact study commit. Deterministic tests cover grounding, renamed IDs, dynamic count text, ambiguous and missing mappings, root uniqueness, loading-phase re-resolution, malformed targets, native-mode mismatch, generated metadata, merging and atom capability imports. Chromium tests exercise generated CLI count/name replay, valid zero matches, delayed root replacement and nonzero failure for removed or ambiguous result regions. PR checks use offline mode without real model keys.

A separate compatibility fixture generated by the candidate was checked with the public Python 3.11 v0.16.379 package from `site-packages`. That package lacks the semantic execution capability import. Both strict verification and direct dispatch exited 1 with `E_VERIFY_STATIC` / `commands_unloadable` / `ImportError`, before browser or model work. A newer supporting runtime is required for these new adapters; old generated adapters retain their existing behavior and are not automatically migrated.

## Limits and next gate

Native list mode supports observed `ul`/`ol` regions and native table mode supports `table`; arbitrary ARIA collections, inaccessible frames and custom DOM readers are not established here. Unnamed regions depend on unique roles or observed attributes; arbitrary identity changes and duplicate names need not be resolvable. Existing field-quality checks and the 100-row cap remain. These controlled results do not promote any case, prove complete collection, close provider-tail work, or satisfy independent first-user acceptance.

Issue 37 stays open until final-master CI, standard three-end publication and a separate fresh installed-package repeat pass. Issues 33, 38, 53 and 55 remain separate open acceptance work.
