# Owned Chrome Cleanup After Disconnect Failure

## Official395 Controlled Failure

An actual non-editable official PyPI0.16.395 control started an isolated
headless Chrome and confirmed its CDP endpoint. While disconnect awaited a
controlled waiting session.stop, a real asyncio task cancellation propagated,
but the owned Chrome and port remained alive. The session/process references
also remained set. A bounded observer then stopped only that test-owned
process. This is fault injection at a teardown boundary, not a spontaneously
observed browser-use stop error or a cause claim for historical Issue116.

## Retained Test Failures And Correction

The first nine-test run failed. Two assertions incorrectly required
TimeoutError propagation; it is an OSError subclass already handled here.
The first native timeout harness failed that erroneous exception assertion,
so it is not evidence of a native timeout leak. Preserve both failed artifacts.
Nine corrected regressions then failed on old source, covering unhandled stop
errors, cancellation, state clearing and missing kill/reap escalation.
A subsequent focused command named a nonexistent test file and ran no tests;
only the corrected invocation counts as verification.

The first complete offline run then retained3978 passes and one documentation
failure: the docs version badge had not been updated to396. Correct that badge
and repeat the complete run; no tests or version gate are weakened.

An additional unchanged shell QA run failed8/1: its direct doctor helper saw
an uninitialized isolated runtime. A separately initialized run still failed
8/1 because it required obsolete top-level chrome_binary_path/auto-launch
fields; neither the unchanged doctor source nor the published395 helper has
those fields. Update only that diagnostic contract: inspect the single CDP
check and summary in success data or failure details, validate the actual
connection's boolean ownership flag, and always disconnect its owned process.
Do not turn a failed diagnostic envelope into browser-availability success.
Repeat all frozen-source/final-master gates after this QA-only correction;
earlier396 passes remain separate, with no tag pushed.

Source396 moves owned-process cleanup into disconnect's finally block and
clears session/ownership state. Reuse the bounded cleanup from failed startup:
terminate/wait5 seconds, kill/wait5 seconds on timeout. Preserve existing
OSError/RuntimeError handling and propagate all other original errors or
cancellation even if ordinary OS cleanup fails. No process search by port,
external browser termination, model-budget change or timeout extension.

The initial local correction passed29 focused tests and3 native browser
controls: startup SIGINT, disconnect cancellation with owned Chrome/same-port
retry, and cancellation while reusing an external browser that stays alive.
A separate native source control returned cancellation with process and port
gone and no observer cleanup. Its editable metadata still read395; it is
uncommitted396 source evidence, not an actual released396 result.

## Acceptance Boundary

Require fresh full exact-source and final-master validation, both CI classes,
strict live doctor before real model work, actual-package controls, tagged
readiness, certain online Shanghai release capacity and complete three-end
publication/audit. Local passes do not waive these gates. OS cleanup can still
fail, and no end-to-end cancellation deadline is added. Issue119 tracks this
distinct failure. Historical timeouts in116 remain open. Independent first
use stays0/2 on fixed387, with A/B, first failures, help and retries separate;
maintainer and automated controls never fill participant slots.
