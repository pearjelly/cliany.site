# crates.io candidate navigation (2026-09-28)

The read-only `crates-io-crate-search` candidate was tested in an isolated temporary HOME with headless Chrome. Real `doctor --llm-live --require-capability generate_adapters --json` reported both CDP and model preflight ready.

`https://crates.io/search?q=serde` returned HTTP 403 to a direct request from this network. Two browser exploration attempts timed out during initial `Page.navigate()` after 20 seconds. The first, on v0.16.361, reported generic `E_UNKNOWN`; the local diagnostic fix returned `E_PAGE_NOT_READY` with `reason=navigation_timeout` and `phase=navigation` on the same path.

No adapter was generated, no case was promoted, and this does not prove crates.io is unavailable from other networks. Before retrying model exploration, check that the normal search page is reachable from the intended browser environment. Do not bypass site access controls.

A fresh installation of published v0.16.362 from the official PyPI simple index reached a second failure form: the browser event bus interrupted `on_NavigateToUrlEvent` after 30 seconds and `explore` still returned `E_UNKNOWN`. The v0.16.363 candidate recognizes that navigation-handler `TimeoutError` as `E_PAGE_NOT_READY` while leaving unrelated timeouts unchanged. The default installer index initially lagged the version-specific PyPI endpoint; an uncached install from `https://pypi.org/simple` succeeded. Neither installation result establishes a working crates.io page.

Later local controls found that replacing the system HOME with `/tmp` can confound Chrome navigation: two auto-launched sessions with normal system HOME and isolated cliany-site runtime data reached a local page. The earlier browser timeouts therefore cannot be attributed to crates.io alone. The independent HTTP 403 remains observed; no normal crates.io browser result or adapter was obtained.
