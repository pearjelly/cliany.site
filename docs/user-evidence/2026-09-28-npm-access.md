# npm search access check (2026-09-28)

The candidate target was `https://www.npmjs.com/search?q=playwright`. From the maintainer network, a read-only HTTP request returned 403. An isolated, auto-launched headless Chrome on CDP port 19333 reported navigation success, but its page-readiness check timed out after about eight seconds. The captured AXTree had eight nodes, including Cloudflare links and image, and no package-result content. The browser process was closed after capture.

Navigation success here only means that the browser accepted the URL; it is not evidence that npm search is usable. No model exploration, adapter package, or online search result was produced. Keep `npm-package-search` as `candidate`. Recheck normal page access from an independent network before running the real live-model gate and read-only exploration; do not bypass the challenge page.

The v0.16.364 candidate added a read-only AXTree check to Chrome `browser navigate`. During development, four of five independent npm attempts returned `E_PAGE_NOT_READY`; one saw a partial three-node challenge tree without the usual challenge-platform link and falsely returned success. After recognizing the waiting title together with a Cloudflare marker, five further isolated headless attempts all returned `E_PAGE_NOT_READY`. A separate `https://example.com` navigation still returned success. These are observations on this network, not a guarantee for every challenge variant or future site state.

A local Chromium regression serves a deterministic challenge-page fixture and an ordinary form page. The navigation command rejects the former and accepts the latter. The full embodied suite passed locally (23 passed, 1 non-embodied test deselected); remote CI still needs to pass on the final candidate SHA.
