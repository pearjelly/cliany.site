# SDK and HTTP First Generation Review

**Date:** 2026-10-10, Asia/Shanghai. **Published baseline:** v0.16.381, final master `bc0260d8524a3ff3b9ca4010d4ba50d39c53e18f`. **Status:** unreleased candidate. This extends the CLI first-generation correction to the Python SDK and the local HTTP exploration path; it is not a cross-entrypoint response-format migration.

## Reproduced First-Use Failure

The explorer saves extraction Markdown before returning. A successful first SDK exploration therefore already has an auxiliary adapter directory, but not `commands.py` or `metadata.json`. The SDK still used directory existence to choose merge handling, unlike the corrected CLI path. HTTP `POST /explore` delegates to that SDK method and inherits the same defect. The merger's auxiliary-only reconstruction drops the recorded starting path and model provenance.

On the published source, all six declared first-generation regressions failed: empty, real extraction-Markdown and snapshot directories, each through the SDK and HTTP. They incorrectly returned `adapter_mode=merged`. Twelve existing-core, partial-file/symlink and explicit-force protection checks passed. No actual provider was called to reproduce this local persistence failure.

The candidate checks for either core artifact using the same existence/symlink boundary as the CLI. An auxiliary-only directory takes normal generation with the complete `ExploreResult`; existing core artifacts retain merge handling. The change does not rewrite generated adapters, alter the merger or add a new public option.

## Controlled Browser Acceptance

Two actual Chromium/CDP flows exercise SDK and HTTP separately. A deterministic model uses semantic control references captured from the real form. The disposable browser serves the existing local fixture at a reserved test-domain URL with a path and no port. This is deliberate: extract Markdown uses the raw domain, while generated directory names normalize ports; a loopback URL containing a port can miss the original directory collision. No third-party page or real model is involved.

Both flows run the real explorer and generator, preserve extraction Markdown, retain the exact starting URL in metadata and generated `SOURCE_URL`, and persist `offline-sdk-first-generation` as the fixture model. Each then performs strict verification and replays changed values (`Grace`, `Red`), requiring both returned text `Grace:Red` and the browser DOM to agree. The HTTP flow uses `/explore`, `/verify` and `/execute`, not a mocked SDK success response.

The first browser-test draft produced two failures because its assertion expected the CLI extraction shape `data.content`; the SDK's existing shape is `data` directly. Those are retained test-helper failures, not a runtime format defect. After correcting that assertion and exercising the HTTP replay endpoint, both flows passed in 31.50 seconds. The focused SDK/HTTP/CLI compatibility run passed 239 checks; Ruff and Mypy passed. Full offline regression and exact-head CI are required before release, followed by final-master and fresh installed-package acceptance.

The full offline run then passed **3,383 tests with no skips** in 281.51 seconds on Python 3.11.14. Source/scoped-test Ruff, Mypy (125 source files), eight-case/four-active-package validation and website JavaScript syntax passed. Runtime state remained under `tmp_home` or explicitly isolated directories; the per-process null keyring backend was not a system setting. Exact candidate CI, final-master and public-package checks are still separate gates.

## Real Source Follow-Up

Clean `5cab9625d4dd29776fb924e3102cc333268f7447` then passed strict real capability preflight in 3.73 seconds and one new source SDK Python docs generation in 48.46 seconds. Original starting path, actual model and extract Markdown were preserved, and strict verification passed. Six actual SDK/HTTP changed-query checks matched all returned titles/links against independent 100-row prefixes of 134/403 normal-page results and an empty normal page. Both negatives returned the declared `E_EMPTY_RESULT`; HTTP used 422. Some page-readiness warnings and an initially mislocated after-replay verification command are retained in the [receipt](https://github.com/pearjelly/cliany.site/pull/85#issuecomment-6094943992). All owned browsers and loopback servers were closed.

Exact-head ordinary CI and Chromium CI passed; the latter executed both new tests and passed 56 marked checks. This is one real source SDK generation, not a real HTTP-generation study, complete collection or v0.16.382 public installation. Version 382 must repeat its own final-master and installed-package gates.

## Boundaries and Next Evidence

Keep CLI `ok` and SDK/HTTP `success` envelopes distinct. This candidate does not resolve every SDK exploration error mapping, promise browser concurrency or improve provider latency. A separate deterministic probe reproduced uncaught `LlmUnavailableError` in SDK and HTTP 500 `text/plain` rather than JSON; [Issue 84](https://github.com/pearjelly/cliany.site/issues/84) tracks that concrete gap without sending invalid real credentials. The first-generation change preserves the existing partial-core merge policy rather than claiming arbitrary symlink artifacts are safe. Existing generated files are not silently migrated; users with already incorrect provenance need a deliberate regeneration decision.

The previous real capability preflight on clean 52ad115 failed `E_LLM_UNAVAILABLE` in 6.44 seconds and started no trials; it cannot validate this SDK candidate. A fresh real `doctor --llm-live --require-capability generate_adapters --json` must pass before any new live generation is counted. Offline Chromium acceptance remains useful when the upstream provider is unavailable, but cannot promote a public case. Independent-user Issues 33/55 and provider-tail Issue 38 remain open.

Today's v0.16.381 GitHub/PyPI/production publication is verified separately in the [public receipt](https://github.com/pearjelly/cliany.site/pull/82#issuecomment-6094736906); it does not contain this source correction. Do not advertise this candidate as installed public behavior until a later version completes its own publication and public-install gates.
