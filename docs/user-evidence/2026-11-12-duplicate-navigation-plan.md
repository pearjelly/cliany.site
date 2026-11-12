# Consecutive Navigation Clicks From One Observation

## Preserved Real Candidate Failure

The first non-editable 0.16.398 local wheel at
`36f6bd29c0bb4cedbf3526d3dc691f154769150a` passed strict live
`doctor --llm-live --require-capability generate_adapters --json`.
Its predeclared public Python docs study failed overall: 2/3 complete
workflows and 6/9 planned replays passed; three replays were not run.
The first generation returned `E_UNKNOWN` with phase `execution`
and reason `action_execution_failed`. The recorded plan contained
two consecutive clicks on the same observed Search page link, with
relative href `search.html`. Execution failed at the second click;
no completed execution receipt or generated workflow was recorded.
Do not reconstruct an unrecorded page state from that receipt.

The private failure-journal SHA-256 is
`edb5a13444fe6392d03e298d2a387ebb150efe3b9922dc3db63fe112ae72fd8e`.
The original failed assessment SHA-256 is
`f19aed96d1d54d3bdde809513ddaa3c7fed1af8bc82a16e6e30dbc52da10c41b`.
Passing later trials do not change that result.

## Chromium Reproduction And Repair

A deterministic offline plan on the real local Chromium fixture
reproduced the two-click failure. The first action reached the form
(HTTP 200); the second could not find the previous link. The original
native failure log SHA-256 is
`88ed0db6041149cf68d651f50dc31b005cea8efb078f23831820e3bc57623c3f`.

Preflight now detects an adjacent pair of clicks referring to the same
observed anchor with a different HTTP(S) origin or path. Neither click
in that plan is recorded or dispatched. The existing one semantic-plan
repair requests one click and a fresh observation. After repair,
Chromium reached the form, generated a strict-verifiable command and
replayed a changed query successfully with an unchanged adapter core.
The green receipt SHA-256 is
`b11edf63b0cf7d06cc4c292a46e2778f3d5ac73bc3359bd5616d9ef80defc5e8`.
The existing noneditable-link control also passed.

## Limits

This is a planning check, not a browser retry or replay deduplication.
It does not invent a destination or alter existing generated files.
Buttons, same-path anchors, observed custom handlers, downloads,
explicit new targets and non-adjacent clicks are not folded together.
There is no new LLM budget, action timeout or change to case status.
This is separate from the historical readiness failure in #124 and
does not establish independent first use. The revised source needs its
own full and real-workflow acceptance before publication.
