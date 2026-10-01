# October 2026 Value Plan

**Decision date:** 2026-10-02. **Published baseline:** v0.16.368. The v0.16.369 release candidate is open in [PR #29](https://github.com/pearjelly/cliany.site/pull/29), not published. The controlled explore/replay study is in draft [PR #31](https://github.com/pearjelly/cliany.site/pull/31) and [Issue #30](https://github.com/pearjelly/cliany.site/issues/30), not part of the published package.

## Product outcome

A new user should be able to install the public package, obtain one useful read-only result, and trust a command generated from a browser workflow enough to reuse it with a changed input. Count success only when a fresh environment and an independent business-result check agree; passing tests, a generated adapter file, or a successful JSON envelope alone are insufficient.

## Evidence at the decision point

- Four maintained active cases exist. Published-package, fresh-HOME demos have returned nonempty Jira and Confluence results; the Jenkins first-result path also passed a published-package check. These are maintained read-only integrations, not proof that a live model discovered a public browser workflow.
- A real model completed 8 of 9 fresh explore-to-replay trials across three controlled local tasks on the clean v0.16.369 candidate. The failed trial supplied an invalid command action partition. A later semantic-only 3/3 sample did not trigger the new correction path, so it cannot establish that the correction improved the live success rate. These are small, single-provider samples, not a general accuracy estimate.
- PyPI search reached `Client Challenge`; npm reached a Cloudflare challenge; crates.io timed out or returned HTTP 403 from the maintainer network. Their cases remain candidates. Do not bypass site restrictions or promote them on package verification alone.
- No independent first-time user's end-to-end quickstart result has been recorded. The historical Q3 plan's 1.0-alpha checkpoint is therefore not evidence of alpha readiness.

## Ordered work

| Priority | Deliverable | Acceptance evidence | Stop or downgrade when |
| --- | --- | --- | --- |
| 0. Close the release loop | Merge #27, #28, then #29 in the next open publication window; release v0.16.369 from final master. | Exact master SHA passes ordinary and embodied CI; strict target and tagged gates pass; GitHub Release notes/assets, PyPI exact-version install, and `www.cliany.site` production alias all show v0.16.369; fresh-clone remote distribution audit passes. | GitHub's Shanghai publication-day cap is reached, a check fails, or any public surface lags. Do not tag or describe the version as published. |
| 1. Prove first use | Ask at least two people who did not build the case adapters to run the public quickstart in clean runtime homes, using a published package. | Record OS, package version, elapsed time, commands, the first failure, strict adapter verification, and an independent nonempty result. At least one person must complete the install-to-result path without maintainer intervention; fix the most common blocker before calling the path self-service. | A maintainer-only run or an existing adapter directory is the sole evidence; report the task as unverified instead of expanding marketing claims. |
| 2. Measure generated-command reliability | After v0.16.369, finish review of #31 and repeat controlled fresh explore/replay runs with changed replay inputs. | Predeclare the same three task oracles; run at least 10 fresh trials per task on a fixed commit/provider, recording phase, latency, correction count, and wrong-success count. Target at least 27/30 correct independent replays and zero silent wrong successes before using reliability language beyond "controlled sample." | Provider availability, harness defects, or missing oracle data make a trial uninterpretable; exclude it explicitly and rerun, never count it as success. |
| 3. Prove one real browser use case | Select a third-party read-only page that serves normal content without a challenge from a fresh browser, then generate, package, and replay one useful command. | Public package URL and SHA-256, fresh-HOME install, strict verify, three fresh normal-site explore/replay trials with changed inputs, and an independent nonempty result. Keep API-backed demos and browser-generated evidence separate. | Normal page access fails or requires bypassing an access challenge. Keep the case candidate and select another legitimate target. |
| 4. Audit alpha contract | Reconcile the CLI/JSON, adapter schema, Python SDK, and HTTP surfaces against the successful user paths above. | Publish an alpha-readiness report listing stable surfaces, migration and security limits, unsupported concurrency/localStorage behavior, and open blockers. | Any core first-use or real browser task remains unverified; do not declare 1.0 alpha ready. |

## Release discipline

Keep the user-requested daily verified release cadence, with at most three public releases on a Shanghai calendar day. A release is complete only after GitHub Release, PyPI, and the production website agree on the exact version and a fresh remote audit succeeds. Work waiting behind the daily cap stays in reviewed PRs, not as an unverified tag. Default PR CI remains offline with no real LLM key; live-provider and third-party runs are explicit, bounded evidence tasks.

## Next review

Review this plan after the first independent quickstart attempt and the 30-trial controlled study, or by 2026-10-16, whichever comes first. Re-rank work based on observed user failures, not on the number of releases or tests alone.
