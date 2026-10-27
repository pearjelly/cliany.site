# Local CDP Discovery: Occupied Port

## Observed Failure

On the source tree corresponding to published v0.16.393, an isolated local
HTTP service responded to `/json/version` with status 200 and JSON `[]`. Local
discovery raised `AttributeError` when accessing the response as an object.
`doctor --json` returned the generic `E_UNKNOWN` rather than a CDP diagnostic.
The service, browser state and runtime directory were owned test fixtures; no
existing session, profile or generated adapter was modified.

## Bounded Correction

Validate the local discovery object's `Browser` and WebSocket URL fields using
the same shape expectations as remote discovery. Invalid or non-JSON responses
are not evidence of an available browser. When discovery fails and the local
port already accepts TCP connections, stop rather than launching a second
browser. Existing valid discovery is still reused and an unoccupied port still
uses the normal launcher. The check does not eliminate concurrent port races or
authenticate an otherwise valid-looking CDP endpoint.
The CDP failure guidance also asks users to check whether another service holds
the port; the diagnostic does not claim to identify every connection failure.

New local fixture tests recorded eight failures and two passes before the
correction. After the correction, the focused discovery, launcher and remote
endpoint groups passed 74 tests, and a separate real Chromium test exercised
automatic browser launch and two generated-command replays. The offline
non-embodied suite passed 3,947 tests; 100 browser tests were excluded from that
run. A separate local browser suite passed 100 tests, but the doctor guidance
text changed while it was running; it is not an exact-final-commit suite.
These are source-level controls, not a tagged release, independent-user
acceptance or proof of a fix for the separately tracked intermittent Chrome
startup timeout.

On the fixed published 0.16.387 first-use path, a separate maintainer attempt
failed to download the Jira adapter. A subsequent network control initially
failed TLS after the GitHub redirect, then later returned HTTP 200. A demo retry
returned five rows, strict verification passed and reuse returned five rows;
an independent HTTP request to the normal public issue page matched its first
key and summary. This was not a normal-browser comparison or independent
first use, and it does not erase the first failure. Raw observations remain in
a private maintainer evidence directory.

Independent first use remains pending: two non-builders must report their
first attempts, with first failure, help and retries kept distinct. The
published trial stays fixed at 0.16.387; this correction neither promotes a
candidate nor modifies previously generated adapters.
