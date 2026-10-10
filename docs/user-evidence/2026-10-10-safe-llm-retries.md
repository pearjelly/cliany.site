# Safe LLM retry review

**Date:** 2026-10-10 (Asia/Shanghai). **Scope:** request failure handling and diagnostics for the v0.16.381 candidate, not a general browser success-rate or latency study.

## Reproduced defects

On published-baseline source `c0af3eaa7f54fd3f336e525071930f6a9baa196c`, deterministic failures with HTTP 400/401/403/404/422 and a gateway keyword in their bodies were each invoked three times. Retry warnings retained a synthetic private marker from the HTML title. An unstructured gateway error also copied a private URL into its summary. A typed timeout whose message did not say "timed out" was not recognized as retryable. Ten of eleven newly declared checks failed on the old code; the legacy reporter compatibility check passed.

The candidate prioritizes valid observed HTTP statuses, keeps the existing transient status set and uses typed timeout/network exceptions before legacy text heuristics. Rejections stop rather than retry. CLI and live doctor preserve the existing authentication code for 401/403. Fixed summaries and whitelisted error events replace raw upstream titles or exception text in retry diagnostics. A new optional callback does not change existing reporter signatures.

## Deterministic evidence

The first focused run passed 110 checks, including actual OpenAI SDK clients over mock HTTPX transport. HTTP 400/401/403 emitted exactly one request despite gateway words in the upstream body. Existing timeout tests still used two visible attempts and exactly two requests for recovery or exhaustion. Privacy tests inspect both emitted events and captured warnings; invalid status types, unknown categories and cyclic exception chains are covered. These are deterministic transport checks, not real provider requests.

The first complete offline run retained one failure and 3,358 passes in 291.65 seconds with six existing warnings. The failure was an old doctor assertion requiring the raw `Connection error.` suffix. Follow-ups `ab51d33f` and `f53a7a34` preserve connection-repair guidance with a fixed summary and update both unsafe-message assertions. Their focused rerun passed 129 checks. Final full regression, static checks and exact release-master CI remain required; a focused rerun alone is not the final release gate.

The Python 3.11 release-preparation run was explicitly stopped after a version-document assertion needed synchronization, then a second run stopped at an existing cross-module encryption test waiting on the OS keychain. Neither interrupted run is counted as a complete pass. The two encryption tests now use the existing `tmp_home` fixture and replace only keychain I/O, exercising the same real encryption/decryption against isolated temporary files. Runtime encryption and `tests/conftest.py` are unchanged; no system credential authorization is requested for QA.

The next preparation run passed 3,306 checks but skipped five browser modules because the auxiliary Playwright package was missing; it was not accepted as complete browser validation. After installing Playwright 1.63.0, the full Python 3.11.14 offline run passed **3,360 checks with no skips** in 256.77 seconds. That local QA process used `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring`, not a persistent system setting. Focused release/diagnostic checks passed 633, source Ruff and Mypy passed (125 source files), website JavaScript syntax and the eight-case/four-active-package gate passed. Preparation build and Twine passed; the final release SHA still needs its own gates.

The localhost homepage and docs showed v0.16.381. Chinese and English failure notes fit a 390-pixel viewport with no horizontal overflow; the expanded English paragraph was visually inspected. Production publication and alias checks are separate later gates.

Before any tag, review reproduced three additional failures with real SDK `APIStatusError` objects whose HTTPX response carried standard `HTTPStatus` enums. HTTP 400/401 repeated and HTTP 429 lost its status because the first guard accepted only exact `int`. The correction preserves integer subclasses, rejects booleans and normalizes accepted statuses to plain integers. The new regressions verify rejection attempt counts and error-event status retention; the earlier 3,360-pass run and PR 82 CI are not substituted for the corrected final commit's gates.

## Retained live preflight failure

The predeclared three-task, three-trial matrix started on clean `52ad115906fe721f754b7c387eb2a7ccae7572af`, development package version 0.16.380, with `per-row-v2` and normal OS HOME. Each runtime directory and browser profile was isolated outside the repository. Its real `doctor --llm-live --require-capability generate_adapters --json` returned `E_LLM_UNAVAILABLE` in 6.44 seconds. No exploration or replay trial started. The sanitized report does not retain the provider or transport cause, so neither is inferred.

Report: `/tmp/cliany-v381-safe-retries-matrix9-20261010.json`. Invocation:

```bash
env -u CLIANY_QA_OFFLINE -u CLIANY_QA_FAKE_LLM_RESPONSES \
  .venv/bin/python tests/embodied/run_live_benchmark.py \
  --allow-live-llm --trials 3 --report /tmp/cliany-v381-safe-retries-matrix9-20261010.json
```

The blocked start remains evidence and is not counted as a nine-trial success or excluded timeout. Deterministic SDK failure tests and offline Chromium checks remain valid work when the real provider is unavailable. No generated archive, case status, prompt, timeout budget or returned-value oracle was changed. No upstream key was deliberately sent with invalid credentials to reproduce authentication rejection.

## Release and remaining acceptance

Publish only after current version/changelog/roadmap/site/notes, complete offline regression, static and package checks, final-master ordinary and Chromium CI, online Shanghai daily cap and tagged readiness pass. GitHub Release, exact PyPI version, correct Vercel production alias and fresh installed-package checks require their own receipts before claiming publication.

Keep Issue 38 open: this fixes unnecessary rejected-request retries and adds usable failure evidence, but does not prove faster successful requests or stable provider availability. Issues 33/55 still require independent people; Issue 53 remains a separate Chrome environment investigation. The unchanged historical Python docs archive and active API-backed demos do not establish new model discovery or complete collection.
