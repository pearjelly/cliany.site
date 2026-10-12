# SDK Browser Acquisition Errors

**Observed:** 2026-10-12. **Published baseline:** PyPI v0.16.383, non-editable Python 3.11 installation. **Candidate:** v0.16.384. [Issue 89](https://github.com/pearjelly/cliany.site/issues/89).

## Reproduction

A reserved but non-listening owned loopback port supplied an explicitly non-root CDP endpoint, preventing local Chrome auto-launch. No private provider, credentials, user adapter or third-party write was involved. The unchanged public Python documentation adapter was reused only from a maintainer-owned isolated runtime directory.

All five SDK methods (`execute`, `login`, `save_session`, `navigate`, `get_page_info`) raised an uncaught `CdpError`. Actual aiohttp execute/login handlers returned HTTP 500 with `text/plain`, so clients could not consume the advertised SDK JSON error envelope. The corresponding source follow-up returned five `CDP_UNAVAILABLE` envelopes and two HTTP JSON 503 responses against the same unavailable endpoint. These were real endpoint failures, not a mocked provider or live exploration.

## Correction And Controls

Only the browser-acquisition boundary catches `CdpError`, `ConnectionError` and `TimeoutError`. It uses fixed repair text and `phase=browser_connect`, without reflecting configured URLs or raw exceptions. The existing HTTP status mapping handles 503; no server routes or generated files change. The private browser acquisition method still raises, while public callers return an error envelope. Unknown exceptions and cancellation are not mislabeled.

- Baseline source `0169912b`: the new deterministic tests recorded 26 failures and 10 passing controls. Expected failures cover five methods and existing HTTP handlers; controls preserve cancellation and unexpected exceptions.
- Corrected focused SDK/generated/parameter regressions: 297 passed. Ruff and Mypy source checks passed before release preparation.
- Two headless Chromium checks passed through SDK and actual HTTP handlers. An explicitly scripted probe transition reports unavailable first, then allows a real CDP connection on the same SDK instance. Changed-input semantic replay writes Grace to the independently read Name field; navigation and page observation succeed. Login and save-session persist one fixture cookie under `tmp_home`, with actual encryption/decryption and no plaintext cookie in the file. Only the key supplier is replaced with a fixture key; the OS credential store is not changed.

## Limits And Publication

The Chromium probe transition is scripted, not an unmocked network-reconnection experiment. The separate unavailable-endpoint checks are real but do not prove provider availability, third-party workflow success, localStorage support or concurrent browser use. No live model is invoked and no candidate is promoted. No retries, cleanup policy, browser infrastructure or action-phase exception behavior are changed.

These are maintainer source checks. Full versioned regression, builds, case packages, final-master ordinary/Chromium CI, target/tagged readiness and fresh online Shanghai capacity must pass before tag publication. GitHub/PyPI exact-version checks, named-project Vercel production inspection, fresh official-package failure and success acceptance, and the final remote distribution audit remain required. Issue 89 stays pending until those publication and installed-package gates pass.
