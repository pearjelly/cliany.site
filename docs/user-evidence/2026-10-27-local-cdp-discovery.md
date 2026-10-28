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

## Cancellation Evidence

A separate signal control reproduced an empty `E_UNKNOWN` inside the same
generated browser workflow, without the original page-readiness warning. During
Click command execution, a local correction returns `E_CANCELLED` and a safe reason; direct keyboard
interruption exits 130. Existing generated wrappers preserve the failure and
stop later actions but retain outer exit 1. A first post-change browser control
timed out after 120 seconds without a signal-delivery receipt; a subsequent
instrumented control recorded delivery and returned `E_CANCELLED` promptly.
Both controls and the original failure remain separate in Issue116. Their
results do not establish the cause of either timeout or prove broad browser
reliability; all revised-source and publication gates must be repeated.
An explicit cancellation also suppresses optional healing; other errors retain
the existing healing behavior. The regression first exposed a local import
shadowing error in the correction, which was fixed and rerun separately.

## October 28 Recheck

The revised source passed 59 focused cancellation, generated-orchestration,
runtime and healer tests. Its first fresh type check failed on the new union
error-field access; narrowing the optional error value separately corrected it,
and the subsequent type check passed all 128 source files. A new isolated real
browser signal control recorded delivery and returned nonzero `E_CANCELLED`
in 5.02 seconds without an observer timeout or empty `E_UNKNOWN`. Its injected
interruption intentionally fails the test's normal-success assertion; it is a
cancellation control, not a passing ordinary workflow. The private log SHA256
is `bd72ab7f47bf29e3ae9d202c403831271c953b165902f411b01de24d7cbfe51b`.

The October27 uninterrupted 100-test browser run and local-wheel3/3 generation,
9/9 returned-prefix comparison belong to the previous04cba7b5 commit, not this
revision. They preserve rather than resolve the earlier 99/1 failure and the
120-second observer timeout with no delivery receipt. Repeat the ordinary
full-suite, exact-head CI and installed-wheel/live gates on the new commit;
keep Issue116 open because the historical timeout cause is unproven.

The exact27c58ebc ordinary CI run40624086760 failed: Python3.12 reported
3,947 passes,19 skips and nine benchmark-fixture errors with pytest9.2.0 and
pytest-benchmark5.3.0. The sibling matrix jobs were cancelled by fail-fast;
they are not passing evidence. A separate isolated environment reproduced
all nine `_nodeid` errors. Changing only pytest to9.1.1 passed all nine in
5.32 seconds. Bound both test-extra and development pytest requirements below
9.2 until that incompatible pair is repaired upstream. Preserve all tests,
workflow jobs and runtime dependencies; repeat final-source gates rather than
relabeling the earlier3,956 local passes as final revised-commit acceptance.

The actual non-editable27c58ebc local wheel passed a fresh strict live doctor
in6.73 seconds, three default-recording real-model generations and all nine
changed-query returned-value checks. A separately launched normal browser
confirmed completed Python Docs searches with135 pathlib and403 asyncio rows,
and explicit completed zero matches. Every returned row matched the ordered
100-row prefix (or empty list); no completeness claim, candidate promotion or
independent-user credit follows. The source report SHA256 is
`79474b9c66ff5cc1c08c04b4fb8393aec0242cf34f6bd44817a1e1369c6bab32`.
The first package/readiness checks used a stale local archive directory and
failed on two missing assets. A separate isolated download of all four active
public archives matched pinned hashes and passed strict package/readiness
checks; no user package directory was modified. Neither this recheck nor the
model study replaces the failed ordinary CI or waives revised-source gates.
