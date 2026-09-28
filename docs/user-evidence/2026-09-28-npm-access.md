# npm search access check (2026-09-28)

The candidate target was `https://www.npmjs.com/search?q=playwright`. From the maintainer network, a read-only HTTP request returned 403. An isolated, auto-launched headless Chrome on CDP port 19333 reported navigation success, but its page-readiness check timed out after about eight seconds. The captured AXTree had eight nodes, including Cloudflare links and image, and no package-result content. The browser process was closed after capture.

Navigation success here only means that the browser accepted the URL; it is not evidence that npm search is usable. No model exploration, adapter package, or online search result was produced. Keep `npm-package-search` as `candidate`. Recheck normal page access from an independent network before running the real live-model gate and read-only exploration; do not bypass the challenge page.
