# Returned Value and First Generation Review

**Date:** 2026-10-09. **Published baseline:** PyPI v0.16.378, installed into a fresh Python 3.11 environment, not an editable checkout. **Fix target:** v0.16.379; published acceptance is separate from source evidence below. All browser/model trials are maintainer checks, not independent first-user reports. Runtime data and browser profiles were isolated outside the repository with normal OS HOME.

## Stronger Controlled Oracle

[PR #76](https://github.com/pearjelly/cliany.site/pull/76) fixes false acceptance when an expected name appeared alongside extra, duplicate or contradictory rows. The runner requires exact row cardinality, order and expected values across returned collections; requested values can coexist with unrequested object fields. Count strings and single-value text cannot contradict the expected result. Reports identify `per-row-v2`.

The fresh fixed-harness matrix against the public baseline passed **9/9 explorations and 12/12 changed-input returned-value plus independent DOM checks**. All trials used the same configured OpenAI-compatible custom endpoint category and `deepseek-v4.1-flash`, with a declared 300-second explore limit. No command-partition repair occurred. Zero wrong successes were observed within this bounded oracle, not across arbitrary sites.

| Task | Three generation times, seconds |
| --- | --- |
| Form | 14.00, 19.81, 264.62 |
| Filter | 27.95, 25.47, 17.30 |
| Semantic | 20.79, 15.72, 10.02 |

Median was 19.81 seconds; nearest-rank p95 was 264.62. The long form trial retained two roughly 120-second failed provider attempts, six seconds of backoff and eventual success. Failures were not removed or restarted to shorten the sample. #38 remains open. Earlier summaries, including the historical 29/30 study, did not retain raw result payloads and **cannot be rescored under this oracle**; no causal or general latency comparison is supported.

## Three Fresh Public Website Generations

After separate strict live capability preflights, three new public-baseline workflows used the real Python documentation Quick search. Generation took 27.80, 27.21 and 41.22 seconds; all generated a reusable query command without manually editing generated code.

Each command replayed `pathlib` and `asyncio`. All **six positive results, 600 title/link rows**, matched the independently observed ordered 100-row prefix. The normal pages held 131 and 399 rows respectively; `limit_reached=true` correctly prevented a complete-collection claim.

The negative query had an independently empty page. Trials 1/2 declared `expects_nonempty=true` and exited nonzero with `E_EMPTY_RESULT`. Trial 3 had already declared `expects_nonempty=false` and correctly returned a successful empty result with EMPTY quality status. The original probe incorrectly hardcoded the first contract for all trials: its third negative `accepted=false` record is retained. Original probe acceptance was therefore 8/9, while the separate metadata-aware business check agrees with all three declared contracts. This is not a new runtime empty-result defect or a silently rewritten historical score.

## First Generation Bug and Fix

All three public-baseline generations lost the persisted model and changed the recorded starting URL from `https://docs.python.org/3/` to the host root. The configured model was separately observed, but must not be stamped into the missing metadata as historical evidence.

[Issue #77](https://github.com/pearjelly/cliany.site/issues/77) records the cause: exploration saves auxiliary extract Markdown before the CLI decides whether an adapter exists. A directory-existence check sent a new domain into the merger, which rebuilt the result without the original URL path or model. Controlled fixtures with a host port did not expose that same directory collision.

[PR #78](https://github.com/pearjelly/cliany.site/pull/78) checks for `commands.py` or `metadata.json`, including symbolic-link artifacts, before using the existing merge path. Auxiliary-only directories use normal generation with the original rich result. Existing full/partial core handling and historical generated modules are unchanged. Eight isolated regressions cover empty, real extract Markdown and snapshot directories, full adapters, partial files and dangling links. Full source validation passed 3,291 offline tests plus Ruff, Mypy and exact-head ordinary/Chromium CI.

At source commit `1c0563107686162d75bb8bed0b80e9b86584dc3b`, a new real-model generation passed preflight (3.98s), generation (32.64s, `adapter_mode=created`) and strict verification (0.69s). Both metadata and generated `SOURCE_URL` retained `/3/`; the actual model was persisted and the extract Markdown remained present. A changed `pathlib` query matched all 100 rows of the independent 131-row prefix. Its predeclared nonempty negative query failed closed with zero rows. This is source evidence, not published-v0.16.379 acceptance.

## Evidence Retention and Remaining Gates

Sanitized local reports are retained outside the repository: `cliany-v378-per-row-v2-matrix9-20261009.json`, three `cliany-v378-public-live-trialN-20261009.json` reports and their query replays, both `cliany-v379-baseline-{pathlib,asyncio}-comparison-20261009.json` records, and `cliany-v379-source-first-generation-1c056310-20261009.json`. No provider URLs, credentials, model response logs or private page content are published here.

Published-v0.16.379 must repeat first generation and strict verification from a new public installation, then check a changed-query prefix and the actual declared empty contract. #77 stays open until that passes. #37's precise changed-layout/ref acceptance, #38's long tail, #53's synthetic-HOME problem, #33/#55 independent-user acceptance and alpha contract decisions are not closed by these results. Case catalog status remains unchanged.
