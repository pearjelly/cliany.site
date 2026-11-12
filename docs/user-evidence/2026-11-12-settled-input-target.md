# Named Input After Document Initialization

## Separate Public Observation

[Issue124](https://github.com/pearjelly/cliany.site/issues/124) retains the
October failed replay with `E_PAGE_NOT_READY / document_not_ready`. The
original envelope SHA-256 is
`17aaa0ef2736880551cbdcaeb82388123bdeb83d45706f394f7e27a37bc729ff`.
The cause was not recorded at the failure boundary.

Four predeclared no-model observations used the actual PyPI 0.16.397 package
and byte-identical copies of the archived read-only Python docs adapter,
each with a fresh isolated Chromium profile. All 4/4 replays matched every
returned ordered title and URL against a separate completed public page.
The three positive observations returned 100-row prefixes of 135 or 404
results; the explicit zero returned an observed empty collection.
The first sampled input match in each trial had positive DOMContentLoaded
end timing, followed by a submitted URL containing the same query.
The observer missed five transient samples across the cohort, and the
historical failure did not recur. The original adapter was not changed.
Private observation report SHA-256:
`c911c989bcf69479a7af26c25b95099ec2f49aa81207313875dbc799b4689600`.

## Controlled Chromium Regression

A local read-only fixture initially exposes two textboxes with the same
accessible name. A deferred initializer removes the temporary textbox only
after the first real AX snapshot. Unchanged 397 source rejected that
snapshot with `E_SELECTOR_NOT_FOUND / target_ambiguous`. The ready page
had one textbox, unchanged, with no submission. The separate persistent
pair control remained a correct refusal. The red run retained one failure
and one pass. Temporary-pair red receipt:
`710ce0d81e250d654a375b36135ce1dce7ae963474d2d32466bcfc30d68aa9f4`.

The correction waits for the existing document initialization check before
judging a named-input tie. It then resolves against the fresh AX snapshot.
The temporary pair becomes one target and the actual browser submits the
intended value exactly once. A persistent pair still returns
`target_ambiguous` with both values unchanged and no submission. Both
initialization regressions, including the earlier slow-image and delayed
script workflows, also passed. Temporary and persistent green receipts:
`4f9b2170dce355bbfdb12b710400311957234dd986dba167aad6faffba7dae0d` and
`97f77c26fc6471a45afc61785ab3f935026a9a902a27f05e8ce5c901759e50b9`.

## Limits

The existing ten-second read-only observation budget, challenge checks
and explicit-ref behavior are unchanged. A persistent tie is not resolved
by choosing the first match. There is no input or submission retry, CSS
fallback or generated-file rewrite. This fixture proves a separate
failure mode, not the cause of Issue124 or readiness for arbitrary
post-DOMContentLoaded page changes. Independent acceptance is still
pending on fixed 0.16.387, and no case is promoted.
