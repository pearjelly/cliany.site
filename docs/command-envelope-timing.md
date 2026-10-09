# Command Envelope Timing

**Status: unreleased.** The proposed timing fields below are not available in the published v0.16.377 package. That package's `meta.duration_ms` values must not be treated as measured command latency. This change addresses [Issue #69](https://github.com/pearjelly/cliany.site/issues/69), not workflow performance or alpha readiness.

## Reading Metadata

The CLI envelope remains version `1` and `duration_ms` remains a nonnegative integer. The optional `duration_measured` boolean makes its provenance explicit:

| Metadata | Meaning |
| --- | --- |
| `duration_measured=true` | A sample from an active invocation timer. Zero is valid for less than one millisecond. |
| `duration_measured=false` | No active invocation timer; `duration_ms=0` is a compatibility sentinel, not a speed measurement. |
| Field absent | Historical or other-producer metadata with unspecified measurement provenance. Treat its duration as unavailable for automation. |

Illustrative measured metadata:

```json
{"duration_ms":32,"duration_measured":true,"source":"builtin"}
```

Illustrative unavailable metadata:

```json
{"duration_ms":0,"duration_measured":false,"source":"builtin"}
```

Existing version-1 envelopes without the flag remain schema-valid. Consumers should require the flag to be explicitly `true` before using `duration_ms` in latency statistics, timeout decisions or comparisons; do not infer measurement from a nonzero legacy value alone.

## Measurement Boundary

The root `SafeGroup.main` activates a monotonic nanosecond clock before Click parses and dispatches the invocation. Each envelope samples elapsed time when its metadata is constructed, rounding down to integer milliseconds. It is not whole-process elapsed time: imports before CLI entry, subsequent serialization/output, final cleanup after a snapshot and work after the invocation are outside that sample. It is not CPU time, an LLM-only metric or a network timeout.

Each nested root CLI call gets a separate timer. The parent's timer resumes after the child returns and includes child execution plus other work before its own snapshot. Timers are invocation-local, not keyed by command names, so overlapping same-name calls cannot overwrite one another. Multiple envelopes can sample an active timer without consuming it. On exit, the timer is invalidated and the enclosing context restored, including success, errors and explicit exits; copied contexts cannot keep measuring an ended invocation.

## Adapter SDK and HTTP Boundaries

New adapter templates sample parent metadata through the existing envelope helper, while nested atom invocations report their own times. Existing generated adapter files are not edited. Their behavior depends on which shared helper the saved code uses: helper-produced envelopes get the new flag when run with the new runtime; manually assembled historical metadata may omit it. Regeneration is required to obtain the new parent snapshot from such a template. Running an ordinary generated Click group directly, outside the root timing boundary, does not establish a measured CLI duration.

The SDK and HTTP `success/data/error` envelopes keep their existing shape and gain no top-level timing promise. An internal CLI-shaped envelope constructed outside the active timer reports unavailable metadata; an SDK/HTTP wrapper may discard that metadata as before. Doctor's per-check timing fields are separate and unchanged. CLI duration correctness does not establish browser concurrency support or cross-entrypoint envelope identity.

## Verification

Deterministic tests cover success and rendered errors, parse errors and explicit exits, submillisecond zero, multiple snapshots, overlapping same-command threads and async contexts, expired copied contexts, generated parent/child success and failure, schema compatibility and unchanged SDK/HTTP doctor responses. Existing browser, LLM and data-quality gates remain independent. Publication and a fresh installed-package repeat are still required before presenting this behavior as shipped.
