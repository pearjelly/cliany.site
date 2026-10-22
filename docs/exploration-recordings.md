# Failed Exploration Recordings

**Source baseline:0.16.392.** Published0.16.391 has the [captured missing-failure-evidence gap](user-evidence/2026-10-22-rejected-plan-recordings.md). Official392 availability requires its complete publication receipt; a source checkout or controlled check is not a release or independent-user acceptance.

Exploration normally records locally. To opt out, use `explore ... --no-record`; the correction adds no failure-journal writes in that mode. Recording does not establish that the workflow succeeded.

For a recorded exploration that fails after a turn begins, look under the selected runtime directory:

```text
recordings/<domain>/<session>/manifest.json
recordings/<domain>/<session>/failure.json
```

The runtime defaults to `~/.cliany-site`; an explicit `CLIANY_RUNTIME_HOME` selects another directory without changing the browser's OS home.

The manifest stays incomplete. The separate `failure.json` retains the existing planning-time AX observation, raw model response when available, fixed reason, phase and dispatch status. `preceding_turns` preserves earlier turns, including proposals rejected before the shared repair was consumed. No additional browser observation or model call is made to reconstruct the failure. A response unavailable because the model failed or was cancelled stays null; it is not invented.

`execution_receipt=false` means this journal is not proof that the model's proposed actions ran. `dispatch_status` describes whether the validated batch was not started, started or completed; a started batch may have stopped partway. Raw responses can contain unexecuted or deferred proposals. Do not put them into adapters, relabel them as successful steps or change original action indices.

New recording session directories use mode700 and journal files use mode600. An existing journal is not overwritten. I/O failure may leave an incomplete new journal; it must not replace the original exploration error. Cancellation remains cancellation. Successful recordings keep their existing manifest/step format, without a failure sidecar.

These files can contain sensitive page content, URLs and model text. Keep them private and review locally; never upload the full recording, profile, cookies or raw journal to a public issue. Public JSON errors do not embed this journal. Share only a sanitized phase/reason and relevant public result. There is no automatic upload or automatic retry, and this does not repair an old missing recording.
