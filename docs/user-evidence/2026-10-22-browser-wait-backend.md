# Actor Browser Wait Compatibility

Date: 2026-10-22. Scope: Issue113; maintainer controls, not independent first use or candidate promotion.

## Captured Failure

Official PyPI0.16.392 (non-editable, direct_url absent) reached the crates.io search shell, but the separate predeclared access-only wait returned `E_UNKNOWN`: the pinned browser-use actor Page has no `wait_for_load_state`. The selector path similarly calls an absent `wait_for_selector`. Six controlled native CLI cases on that actual public package failed in13.47seconds: idle, DOM, explicit selector, both explicit navigation waits and missing-selector timeout classification. Existing mocks had supplied methods the real Page does not expose.

The npm CLI access check reached a challenge and stopped. Crates access plansv1/v2 stopped before strictdoctor or any model generation; each three planned replays remained unrun. Normal search results in a separately observed interactive browser do not prove the CLI browser can reach them. The shell's missing-result cause remains unknown. No challenge bypass, model-discovery success or case promotion is claimed.

## Bounded Correction And Controls

Use the pinned native CDP client's separate owned connection to monitor the exact focused target, main frame and current loader. Do not overwrite the backend's single registered lifecycle handler or rely on its cached events. Preserve native state strength; networkidle requires Chrome's networkIdle, not just load. The existing user-specified selector is passed as data to a read-only visibility check, never used as an action fallback. No new dependency, action, navigation, model call, retry or larger budget is added.

One monotonic positive wait budget includes observation; late completions cannot become success. External cancellation propagates; success/failure/cancel close only the monitor, not the user's browser/page. Backend error text is omitted. Default navigation and generated semantic replay stay unchanged.

Initial cache-based controls passed6/6, but an expanded run passed7/9: explicit idle navigation timed out, and a separate test fixture could not restore an element after hiding it. Preserve both raw failures; the fixture correction uses an explicit hidden semantic locator. A diagnostic native pending-fetch probe showed a second Playwright CDP observer returning idle in0.733seconds while the request was still pending. Do not substitute that approach or attribute the old cache timeout's precise subcause without evidence.

The owned-monitor correction passed9 native tests in28.33seconds and39 focused checks in6.05seconds. The nine include the six original CLI conditions, pending-request/selector refusal followed by readiness without renavigation, and focused-target identity with identical URLs. Unit controls cover stale/child/weaker events, cancellation/cleanup, late or hanging probes, invalid pre-browser arguments and opaque backend failures. These pre-version controls are not complete versioned-source, final-master, fresh real-provider or official393 acceptance.

## Preservation And Publication Boundaries

Private165-file whitelist archive: `2026-10-22-browser-wait-backend` under the maintainer evidence directory. Archive SHA256: `4b7cbb02a97c306e1acf63c8bb3bf4bd9daa4b20d94be87091794c6eb9f03c36`. Manifest SHA256: `a2e442aef03339d2526c73d4e44be8973b6017b61fd929d9dc577aebdce20d74`. Every archived member's bytes were rehashed; directory700, files/members600. It includes the original public-package red, expanded failed attempt, later green and access-only failures, not browser profiles/sessions. Raw evidence may be sensitive: no public raw upload or secret-free content claim. Earlier391/392 archives and scores are not rewritten.

Require all fresh versioned/final-master, real workflow, local and actual public package, ordinary/native CI, tagged readiness, actual online Shanghai release cap, exact GitHub/PyPI, correct Vercel production pages/aliases and final distribution audit. Candidate manual preview remains unperformed after denial; retain residual visual risk and actual production checks. Independent first use remains0/2 on fixed387; human A/B, assistance, first failure and retry are separate. Invite two non-builders; no maintainer check fills a participant slot.
