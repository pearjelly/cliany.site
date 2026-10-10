# SDK Parameter Integrity Review

**Date:** 2026-10-10, Asia/Shanghai. **Published baseline:** v0.16.382, final master `9f6226a5036c9d9fb8e6d0a76ea2bdb20a9efdf3`. **Issue:** [87](https://github.com/pearjelly/cliany.site/issues/87). This is an unreleased source correction, not installed-public-package acceptance.

## Observed User Failure

The fresh official-index, non-editable v0.16.382 installation used the unchanged adapter from its earlier real SDK Python docs generation, with isolated cliany runtime data and the normal OS HOME for owned browsers. The command declares `query`, including recorded default `typing`. Actual SDK execution with `params={"qurey": "asyncio"}` returned success and 100 titles/links for **typing**. Actual HTTP `POST /execute` returned the same data and HTTP 200. Browser logs visibly typed `typing`, and the returned first rows were Glossary/duck-typing and the typing module, not the requested asyncio module. Both entrypoints closed their owned browser/server resources; no model call or third-party write was made.

This is a wrong-input success: extraction quality can pass even when a misspelled parameter is ignored and a recorded default drives the workflow. The CLI already rejects unknown options, but SDK dictionary merging did not reject unused keys. A successful JSON envelope and nonempty rows alone did not prove the requested task.

## Correction and Compatibility

For generated commands carrying recorded `commands[].actions`, the SDK derives accepted raw parameter names from the command's declared arguments, or the existing auto-detection of value placeholders when no arguments are declared. Unknown keys return `E_INVALID_PARAM` before CDP/session/replay work, even with valid keys alongside them or with `dry_run=True`. Details contain only sorted `unknown_params` and `allowed_params` names; values are neither reflected nor used to run a different input. HTTP uses its existing mapping to return JSON 400. No fuzzy typo correction occurs.

Declared defaults, correctly spelled changed inputs, auto-detected placeholders and parameter-free commands remain valid. Required-argument checks, substitution/value conversion, sandbox rules and output-quality checks are unchanged. Existing generated modules and manifest hashes are not rewritten. Legacy `command_defs` without this generated-command argument contract keep their existing behavior; this is not a promise that all legacy adapters reject unused keys or that arbitrary parameter value types are validated.

## Verification and Remaining Gates

The predeclared tests retained **36 failures and 12 passing controls** on the exact published source baseline, in 2.68 seconds. They cover SDK/actual HTTP, defaults/auto-detection/no arguments, typo-only/extra/non-string keys, normal/dry-run, names-only errors, no browser/session/replay calls and unchanged core files. The correction passes those tests and existing SDK suites: **309 passed** in 2.72 seconds. Source/scoped-test Ruff and Mypy (125 source files) passed on Python 3.11.14.

Both real Chromium first-generation tests passed in 27.15 seconds using the existing deterministic offline model, then strict verification and a correctly spelled changed-input replay with returned data plus independent DOM checks. Eight typo-only and mixed-valid/unknown calls returned names-only errors and left the page inputs/result and adapter bytes unchanged, including dry-run. This fixture work is not a live-provider exploration, candidate promotion or an independent person's first use.

A separate actual source SDK/HTTP check used the unchanged newly generated public Python docs adapter and the unchanged v0.16.373 archive. All 16 invalid-input calls returned names-only `E_INVALID_PARAM` (HTTP 400) with no SDK CDP/session created. Four correctly spelled `asyncio` replays passed strict verify and output-quality checks and each returned 100 rows. An independently operated normal page completed with 403 matches; every returned title/link row matched its 100-row prefix SHA-256 `3af330f44b2b9c50d1f463bfb382556f2352b54ff6b5f8a1beab08afcbfc81e4`. Core files and the historical manifest remained byte-identical. All owned browsers and HTTP servers were closed. This is source replay against existing adapters, not a new live-model generation or public installation of the correction.

The full non-embodied offline run passed **3,405 tests**, with 56 embodied cases deliberately deselected rather than counted as passed, in 62.29 seconds. Eight-case/four-active-package validation passed without promoting any candidate. The combined full suite and exact-head remote checks remain separate gates below.

Full offline regression and exact-head ordinary/Chromium CI are still required. Publication requires a versioned reviewed release, fresh online Shanghai publication-time cap, final-master/tagged readiness and package checks, GitHub/PyPI/production agreement, fresh installed-package input-integrity acceptance and final remote distribution audit. Issue 87 remains open until those gates pass. Prior v0.16.382 acceptance does not cover this correction.

## Versioned Release Preparation

The [source candidate receipt](https://github.com/pearjelly/cliany.site/pull/88#issuecomment-6095820688) records 3,461 combined tests with no skips in 273.64 seconds and exact `6cd2d761` ordinary/Chromium CI. The later versioned preparation changes package/lock versions only, release metadata and bilingual site copy; it does not change the runtime correction. Preparation wheel/sdist and Twine checks passed, as did unchanged eight-case/four-active-package validation, source Ruff and Mypy125. The site test file retains two pre-existing E501 long lines; its other scoped lint checks passed without altering those unrelated lines.

Local Chinese/English homepage and Chinese SDK docs passed 390-pixel mobile and 1440-pixel desktop layout checks without page-wide overflow or observed console warnings/errors. The mobile SDK paragraph was visually inspected. A read-only browser helper used an unsupported `checkVisibility` method, then used supported state/layout inspection; another helper retained the English menu label after switching to Chinese and was corrected from a fresh snapshot. Neither is a site failure, and no hidden control was forced. Owned QA page/server resources were closed and viewport reset.

The first strict online release-cap read failed, so no release was authorized. A later fresh strict online read recovered actual Shanghai publication timestamps and reported 2/3. Initial preparation readiness stopped on the uncommitted tree and a stale local v0.16.381 tag context; the actual remote v0.16.382 tag was fetched without modifying any tag. Final clean readiness and a new immediately-before-push online cap remain mandatory. These preparation checks do not prove a published v0.16.383 package or production deployment.
