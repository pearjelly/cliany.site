# SDK and HTTP Provider Error Review

**Date:** 2026-10-10, Asia/Shanghai. **Baseline:** `f78f1aaf0bdaee545d113898ef3fc565ab745336`, after first-generation PR 85. **Release target:** v0.16.382. Issue 84 remains open until final-source and installed-public-package acceptance.

## Reproduction

The SDK caught `OSError`, `RuntimeError` and `ValueError`, but the explorer's typed `LlmUnavailableError` inherits none of them. A failed configured upstream request therefore escaped the SDK's documented result boundary. Actual HTTP `POST /explore` with a real SDK returned plain-text 500, not JSON. Its exception traceback could include synthetic private response or endpoint markers. A previously mocked SDK error result did not cover this failure.

The predeclared regressions retained **26 failures and two passing retry-recovery controls** on the baseline in 1.93 seconds. They exercise both SDK and actual HTTP handlers, typed authentication/request rejection, rate-limit/gateway exhaustion and timeout. No browser, live provider or invalid real credential is used. Actual OpenAI-compatible SDK clients operate over HTTPX mock transport with a dummy key and zero internal retries; requests never reach the network. The production retry helper supplies outer attempts, while successful controls use a declared fixture result rather than pretending to discover a real page.

## Correction and Contract

The SDK now catches the typed provider failure before adapter generation and returns its existing `success/data/error` shape. Upstream HTTP 401/403 preserves `E_LLM_AUTH_FAILED`; other typed failures return `E_LLM_UNAVAILABLE`. `error.details` contains retryability, observed status (or null) and fixed `llm_invoke` phase. Messages and repair hints are fixed; upstream exception text is not copied into the response or an uncaught server traceback.

HTTP uses JSON with 503 for unavailable upstream dependencies, including upstream credentials. This is not 401 authentication of the local caller; no new auth layer or permission is introduced. Clients must inspect `retryable=false` and repair configuration rather than repeatedly retrying every 503. A transient error can remain retryable at exhaustion. Existing budgets, SDK-internal retry settings, browser semantics and data-quality gates remain unchanged.

The new checks assert one actual request for 400/401/403, three for 429/502 or typed timeout exhaustion, and two for successful retry recovery. Synthetic private markers must be absent from responses and captured logs. Failed generation emits no core files; two additional guards preserve existing core contents even with explicit `force=True`. Unknown/non-provider exceptions and legacy OSError codes retain their earlier contracts, so this is not a whole-SDK privacy guarantee or identical CLI/SDK/HTTP envelopes.

## Related Success Evidence and Remaining Gates

Release preparation passed **3,413 offline tests with no skips** in 290.38 seconds on Python 3.11.14; the focused release/SDK/site run passed 687. Source/scoped-test Ruff, Mypy (125 files), eight-case/four-active-package checks and website JavaScript syntax passed. Preparation wheel/sdist and Twine validation passed; they are not final-SHA or public-index artifacts. Initial readiness correctly failed on the uncommitted worktree; no tag was pushed. The final clean source must rerun that gate.

Local Chinese/English homepage copy and Chinese SDK docs fit 390-pixel mobile and 1440-pixel desktop checks without page-wide overflow or observed console warnings/errors. The new English paragraph and Chinese SDK paragraph were visually inspected. A mobile language lookup initially failed because navigation was collapsed; opening the actual navigation exposed the control and language switching passed. No hidden control was forced or unrelated interface behavior changed. The owned QA server and tabs were closed and viewport override reset. These are local preparation checks, not production deployment acceptance.

PR 85's clean `5cab9625d4dd29776fb924e3102cc333268f7447` passed strict real capability preflight in 3.73 seconds and one new read-only source SDK Python docs generation in 48.46 seconds. Six SDK/HTTP replays matched all 100 returned titles/links against independent 134/403-result normal pages and an empty page. The [receipt](https://github.com/pearjelly/cliany.site/pull/85#issuecomment-6094943992) retains the exact scope, earlier helper failures and page-readiness warnings. This is a source generation and capped-prefix result, not a real HTTP-generation study, complete collection or published v0.16.382 acceptance.

The earlier real capability failure on 52ad115 remains 6.44 seconds, `E_LLM_UNAVAILABLE`, zero matrix trials. A later passing source preflight does not erase it or establish general availability/latency. Issues 33/55 still need independent people; Issue 38 remains the provider/public-site timing study.

Full offline regression, static checks, unchanged case/package gates, exact final-master ordinary/Chromium CI, online Shanghai publication cap and tagged readiness are required before a tag. GitHub/PyPI hashes, production alias/browser checks and fresh official-index SDK/HTTP failure and first-generation acceptance follow publication, ending with the strict remote distribution audit. Source fixtures or the already published v0.16.381 receipt do not replace those gates.
