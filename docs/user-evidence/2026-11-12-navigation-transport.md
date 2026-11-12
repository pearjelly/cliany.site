# Page Transport Failure With A Reachable Browser

## Preserved Public Workflow Failure

On October 28, final master `e44b75f7` completed three live generations but
only 1/3 complete workflows and 6/9 planned replays. One replay stopped with
`document_not_ready` before input. Two others stopped on
`net::ERR_CONNECTION_CLOSED`, labeled `E_CDP_UNAVAILABLE`, without an
observed collection. Neither failure is a valid zero-result query.
[Issue124](https://github.com/pearjelly/cliany.site/issues/124) links the
original stop receipt. Separate same-version replays observed connection
closure with healthy CDP discovery; later normal browser visits succeeded.
The [November 12 official-package pass](https://github.com/pearjelly/cliany.site/pull/121#issuecomment-6811949279)
is a new cohort, not a correction to the October results.

## Controlled Chromium Reproduction

One isolated local HTTP fixture accepts a request and closes before sending
a response. Native Chromium reports `ERR_EMPTY_RESPONSE`. On unchanged
396 source, the real CLI exited nonzero with `E_CDP_UNAVAILABLE`, although
the CDP browser ID was unchanged and the same tab subsequently loaded a
healthy local page. The focused regression failed at that classification
assertion, not at setup or recovery. The original failure envelope SHA-256
is `d3220a6a4fa325c461589765c9090730353bb30d393a1e3e532bbc7e049b0d8e`.

With the correction, the same control exits nonzero with
`E_PAGE_NOT_READY` and the details `phase=navigation`,
`reason=navigation_transport_failed` and `browser_error=ERR_EMPTY_RESPONSE`.
The external browser ID stays unchanged and the separate recovery navigation
still succeeds. The post-fix failure envelope SHA-256 is
`73d6acd5d6964ed7c5d0b417968d0d2ce646730f984447882b9e8830c7c9e499`.
The two raw controls are retained privately, without overwriting either.

## Contract And Limits

Only recognized Chromium network error tokens raised at the navigation call
are classified this way. Connection setup, unrelated browser errors, existing
timeout handling and challenge checks are unchanged. The new error details
do not include the URL, query or exception body. SDK replay and its HTTP
endpoint stop before subsequent input; HTTP returns 503. The shared executor
also stops on this failure for legacy callers that allow other step errors.
There is no automatic retry, timeout increase or generated file edit.

The local fixture proves diagnostic separation, not the cause of the
intermittent public-page failure or any improvement to network availability.
Document readiness remains a separate failure. Exact-source, final-master,
real-workflow and distribution gates are still required for any new release.
No case was promoted; the independent trial stays fixed at 0.16.387.
