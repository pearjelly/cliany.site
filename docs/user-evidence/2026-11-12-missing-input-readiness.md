# Distinguish an unfinished page from a missing named input

## Original failure and separate diagnostics

[The v0.16.400 candidate receipt](https://github.com/pearjelly/cliany.site/pull/136#issuecomment-6818181084)
retains the original Python Docs cohort: **2/3 complete workflows and 8/9
replays**. The third adapter reported a successful click on the search-page
link, then its `browser type` step failed to find `Search`; there was no
extracted collection. The original receipt did not establish the state of
the destination document at failure.

The same unchanged local adapter passed one instrumented zero-match replay,
then six separately declared diagnostic replays in fresh Chromium contexts:
three explicit zero queries returned one empty list and three `pathlib`
queries matched the first 100 ordered title/link rows on a normally opened
public page. All three document navigations returned HTTP 200 in those six
replays. These are separate maintainer diagnostics, not rescored first-run
results. The intermittent original failure did not reproduce, and its cause
is still unknown.

## Controlled Chromium reproduction

On a local read-only page, a deferred script builds the named input.
While the script is held, Chromium reports `interactive` and
`domContentLoadedEventEnd == 0`; there is no input in the page. The old
candidate wheel returned `E_SELECTOR_NOT_FOUND` with no reason after the
existing wait, even though initialization had not finished.

| Native browser control | Patched source result |
| --- | --- |
| Initialization held past the budget, no input | `E_PAGE_NOT_READY`, `reason=document_not_ready`; no input or submit |
| Initialized document never exposes the input | `E_SELECTOR_NOT_FOUND`; no input or submit |
| Initialization creates the input within the budget | Named input succeeds and the fixture sees the requested value |

Named input checks document readiness during the existing observation budget
even when there is no match yet. It still refreshes the semantic observation
before dispatch. No timeout extension, input retry, guessed selector, or
change to explicit-ref handling is included. This change does not prove the
cause of the original Python Docs failure, modify any generated adapter, or
promote a case. The independent human trial remains pinned to 0.16.387.
