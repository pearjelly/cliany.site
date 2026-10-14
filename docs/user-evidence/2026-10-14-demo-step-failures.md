# First-result child failure evidence

**Date:** 2026-10-14 (Asia/Shanghai). **Scope:** maintainer-controlled subprocess fault injection on official PyPI 0.16.385 and a v0.16.386 source candidate. **Independent people:** 0/2, based on fresh reads of #33/#55. This is not an independent user's failed trial, live model exploration or a third-party availability failure.

## Reproduction

The first-result `demo` delegates fixed-hash install, strict verification and read-only query to Python child commands. On the actual installed 0.16.385 package, a real child printing non-JSON text returned `(False, None)`, dropping the reason. A real child writing invalid UTF-8 raised `UnicodeDecodeError` rather than returning through the stage-specific path. The outer CLI could therefore lose whether install, verify or query failed. No public adapter or generated file was modified to reproduce this boundary.

Ten added deterministic regressions failed before correction. They cover actual child malformed output, startup/timeout exceptions with private sentinels, available exit codes, explicit stream encoding and each CLI phase's stopped execution. Additional controls retain valid upstream errors and run real Unicode JSON with inherited ASCII stream settings. Exception/timeout tests are labelled simulated where applicable; the separate real-child probe records an actual unchanged 90-second timeout independently of those unit tests.

The separate six-case actual-child probe compared the installed public baseline with the source candidate, using normal OS HOME and fresh runtime directories outside the repository:

| Controlled child | Published 0.16.385 | Candidate source |
| --- | --- | --- |
| Non-JSON text | Failure without reason | `invalid_json`, exit 0 retained |
| JSON array instead of object | Failure without reason | `invalid_envelope`, exit 0 retained |
| Invalid UTF-8 byte | Uncaught decoding exception | `invalid_utf8`, no raw stream |
| Missing child executable | Failure without reason | `start_failed`, no private path |
| Unicode JSON under inherited ASCII stdio | Child failed, no reason | Succeeded with exact Unicode value |
| Child sleeping 95 seconds | Failure without reason after 90.00 s | `timeout`, `timeout_seconds=90`, after 90.01 s |

These controlled local failures do not establish how often a public first-time user encounters them. No measured end-to-end speed improvement or automatic recovery is inferred.

## Correction

- Keep the original install/verify/query error code and `error.details.stage`.
- For newly diagnosed local child failures, add `error.details.upstream_error.details.reason`: `timeout`, `start_failed`, `invalid_utf8`, `invalid_json` or `invalid_envelope`.
- Include `timeout_seconds=90` only for timeout and `returncode` when a completed malformed-JSON/non-object child provided one. Do not infer an exit status when unavailable.
- Use fixed Chinese messages; omit raw output, child arguments, exception text and private paths from the new diagnostic payload.
- Set UTF-8 only for the Python child and parent reader, including child `PYTHONIOENCODING` so an inherited non-UTF-8 pipe encoding does not override the JSON contract. Do not modify the user's terminal or global environment.
- Preserve the existing 90-second per-step timeout, no retries, strict verification, no-overwrite and stop-before-later-steps behavior. A reason is diagnostic evidence, not proof that retry will succeed.

Valid upstream JSON errors retain their prior forwarding behavior; this is not a new privacy guarantee for all adapter messages, progress events or historical errors. No browser resolution, generator, session or provider code changes.

## First-use acceptance

The [fixed-version guide](../first-use-trial.md) and new feedback form are brought forward from PR #94 so people can report an original first failure without raw logs. The earlier [October 13 handoff](2026-10-13-first-use-handoff.md), its public package version and maintainer observations remain historical evidence. Do not count them as participants or rescore their results.

Invite two people who did not develop/build the adapters; preferably one also tries the existing browser candidate. API-backed Jira and browser results remain separate. Case status, the 100-row browser cap, missing independent feedback and alpha acceptance remain unchanged. Candidate validation, final-master CI, exact GitHub/PyPI, production aliases, fresh installed-package checks and final remote audit must complete before this source candidate is considered a release.
