# First-result row integrity review

**Date:** 2026-10-14 (Asia/Shanghai). **Public baseline:** official PyPI 0.16.386, release/tag master `07f206b8e99e7cb6774b2d6ca187bd856f83c5cd`. **Status:** unreleased source correction, not a new public package. **Independent participants:** 0/2. The preceding release and [first-use invitation](../first-use-trial.md) remain the current published trial; this source work does not rescore earlier reports or change that invitation's pinned version.

## Observed failure

The actual installed public package's `demo` accepted each of these six **controlled** child results as `ok=true`, exit 0: missing Jira key, blank summary, a valid first row followed by a row missing summary, unrelated fields instead of an issue, blank Confluence title and whitespace-only Jenkins name. Three valid controls also succeeded. Each query ran an actual Python child returning the selected JSON; installation and strict verification were represented by controlled successful child envelopes. This proves the first-result oracle boundary, not that a third-party service returned those failures, that a real participant encountered them or that the public installation/verification pipeline was exercised in the fault study.

The cause was a row-count-only check: any nonempty object counted as an issue, page or job. The trial requires nonblank business identifiers and titles and a separate normal-page comparison; an object is insufficient evidence of a useful result. The original six wrong successes are retained, not converted into successes by the corrected code.

The first 54 deterministic checks retained **51 failures and 3 passing controls** before correction. A separate evidence-recorder regression retained six failures. Six catalog-example regressions retained the failure to respect declared row paths/fields. A further first focused run exposed that the hand-authored Jira/Jenkins examples still had historical nested extraction shapes, unlike the maintained public packages. Those examples are corrected and remain explicitly synthetic (`sample=true`); they are not newly observed business data or edited generated adapters.

## Correction and scope

- The three runnable no-login cases declare `expected_rows.required_fields`: Jira `key`/`summary`, Confluence `id`/`title`, Jenkins `name`/`url`. All declared values must be strings with non-whitespace content in every row. Optional assignee, color or other fields do not become mandatory.
- Shared `check_case_rows` evaluates the declared row path, minimum count, object shape and text fields for the CLI and evidence recorder. The catalog/example validator remains standard-library-only, checks the same contract and has parity regressions against the runtime oracle. Historical recorder/example cases without text-field declarations keep their previous shape checks; they do not inherit an unsupported first-result claim. The CLI requires an explicit valid field contract before installation.
- A bad business row returns existing `E_EMPTY_RESULT`, `error.details.stage=oracle`, actual row count/minimum and `field_invalid_rows` with 1-based offending row numbers. The new diagnostic contains field names and positions, not copied values or raw query output. Existing upstream errors retain their prior behavior; this is not a blanket privacy guarantee.
- Valid upstream result payloads and successful outer envelopes are unchanged. Invalid row shapes, empty results, candidate/login rejection, fixed package hashes, strict verification, no overwrite, stopped later steps and the existing 90-second child budget remain intact. No retry or generated-file migration is introduced.

Nonblank text does not prove factual correctness, URL safety, complete results, schema parity across entrypoints or continuing third-party availability. The separately opened normal-page check is still required; this does not replace semantic browser quality gates or validate every directly invoked old adapter.

## Retained first candidate gate failures

Frozen commit `83e33c6f1ba9902c79f7ff7cc6537c5aedf98ea1` passed 167 focused checks, lint/type/case/build checks, a repeated real workflow study and local built-wheel controlled probes, but the full local run was **1 failed / 3,608 passed**. An old runtime-home fixture lacked an explicit field declaration; its custom case now declares its existing key field without changing generated fixture code, payloads or isolation assertions. Windows/ordinary CI exposed the same fixture problem.

Ordinary CI also failed the release-readiness job because importing the application oracle into `validate_cases.py` broke the required uninstalled, standard-library-only bootstrap. That first abstraction was rejected; the catalog now remains standalone, with two no-site-packages bootstrap regressions and explicit oracle parity checks. No workflow, conftest, snapshot, global import path or package alias workaround was added. The first failed run and cancelled matrix siblings remain historical gates; they are not green CI or a failure of the published package. Later snapshots require new full and exact-head receipts.

## Preliminary real workflow checks

A fresh source environment with normal OS HOME and isolated cliany runtime files installed the three **unchanged public archives**, passed strict verification, then repeated each demo without replacement. Jira returned **5/5 rows**, Confluence **6/6**, Jenkins **5/5** on first/reuse. Required fields were nonblank in every row; generated core hashes stayed unchanged. A separate normal browser matched Jira **SPARK-60230** and its complete summary, Confluence **38572314 / Preparing Spark Releases**, and Jenkins **2.1** at the returned public job URL.

These are maintainer source checks preceding the final frozen snapshot, not independent users, live model discovery, browser-generated search acceptance, a new release or a general availability claim. The final source snapshot, full offline/static/case/build checks and exact-head ordinary/native Chromium CI require their own receipt. Version, release metadata, final-master gates, online Shanghai capacity, tagged readiness, exact GitHub/PyPI, production aliases, public installed acceptance and the final distribution audit are required before publishing a future version.

## Human acceptance remains open

The actual current #33/#55 reports still contain no independent participant. The user has been asked to invite two people who did not develop/build the adapters, with at least one unaided install-to-result success and independent business-result comparison. Original first failures, help and later retries stay separate. Keep the published trial fixed while this correction is reviewed; no calendar-only version or case promotion is justified by this controlled work.

## October 15 release preparation

The resumed task first re-read the actual PR head and completed runs. Corrected source `aa606a3f5a504c014769c32a081b5a10d804a671` passed **3,621 tests in 338.61 seconds**, all 14 jobs in [ordinary CI](https://github.com/pearjelly/cliany.site/actions/runs/38504477589) and [real Chromium CI](https://github.com/pearjelly/cliany.site/actions/runs/38504477566), completed at 2026-10-14T03:11:30Z. The prior pause stopped only a local observer, not the remote job; its final success is now verified, not assumed or obtained by rerunning it. The earlier candidate failures remain above.

Remote master/tag and exact/latest PyPI still resolve to published v0.16.386. Production home/docs show that baseline. The fresh online Shanghai actual-publication check on October 15 initially reports 0/3 releases; that is not the final pre-tag gate. The versioned correction targets v0.16.387 and must repeat final-snapshot checks, exact-head CI and all publication gates. The updated trial requires confirmed PyPI publication first and links to the immutable v0.16.386 guide for people already using it; their first attempts are never rescored. Current independent reports remain 0/2. Final-master and new public-package acceptance require a separate dated receipt.
