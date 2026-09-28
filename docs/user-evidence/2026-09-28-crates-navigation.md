# crates.io candidate navigation (2026-09-28)

The read-only `crates-io-crate-search` candidate was tested in an isolated temporary HOME with headless Chrome. Real `doctor --llm-live --require-capability generate_adapters --json` reported both CDP and model preflight ready.

`https://crates.io/search?q=serde` returned HTTP 403 to a direct request from this network. Two browser exploration attempts timed out during initial `Page.navigate()` after 20 seconds. The first, on v0.16.361, reported generic `E_UNKNOWN`; the local diagnostic fix returned `E_PAGE_NOT_READY` with `reason=navigation_timeout` and `phase=navigation` on the same path.

No adapter was generated, no case was promoted, and this does not prove crates.io is unavailable from other networks. Before retrying model exploration, check that the normal search page is reachable from the intended browser environment. Do not bypass site access controls.
