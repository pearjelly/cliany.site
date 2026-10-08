# Synthetic HOME Chrome CDP controls (2026-10-04)

Issue [#53](https://github.com/pearjelly/cliany.site/issues/53) tracks first-navigation timeouts when a maintainer launches macOS Chrome with an empty temporary OS `HOME`. This diagnostic ran outside the repository, without an adapter, model, or cliany browser session. It does not identify the exact macOS or Chrome cause.

## Setup

- macOS host, Chrome 154, fresh temporary `--user-data-dir` for each run, `--headless=new`, and a dedicated loopback CDP port. All Chrome processes were stopped and temporary profiles removed afterward.
- An `aiohttp` client created `about:blank` targets through CDP and sent `Page.navigate`, then `Runtime.evaluate`. The target was either a `data:` page, a local `127.0.0.1` HTTP page served by the same test process, or `https://docs.python.org/3/library/pathlib.html`.
- The only intended launch-environment difference was `HOME`: the ordinary macOS user home versus a newly created empty temporary directory. The Chrome binary, flags, test host, and profile isolation were otherwise the same. Each CDP request had a bounded timeout.

## Observations

| Chrome launch HOME | Target | CDP result |
| --- | --- | --- |
| Ordinary user home | Python documentation HTTPS page | Navigation returned; title and complete document were readable. |
| Empty temporary home | Python documentation HTTPS page | CDP discovery and target creation worked; navigation and page evaluation timed out. |
| Empty temporary home | `data:` page | Navigation returned; title and complete document were readable. |
| Ordinary user home | Local HTTP page on `127.0.0.1` | Navigation returned; `Local Control` title was readable. |
| Empty temporary home | The same local HTTP page | CDP discovery worked; navigation and page evaluation timed out. |
| Empty temporary home, diagnostic `--no-sandbox` | The same local HTTP page | Navigation and page evaluation still timed out. |

The local HTTP control rules out a docs.python.org-only failure, DNS-only failure, and a public-site challenge as sufficient explanations. The `data:` control shows that Chrome and basic CDP page commands can run under the synthetic home. This points to Chrome's network-navigation environment on this host, not generated adapter extraction or cliany action replay. The `--no-sandbox` control was diagnostic only; it is not a recommended product flag or a security fix. The precise cause remains open.

The historical [v0.16.374 published-package replay](2026-10-04-v374-python-docs-replay.md) launched Chrome with ordinary OS `HOME` and a temporary profile, then connected a CLI with a separate temporary `HOME` through loopback CDP. That split kept adapter state out of the user's default directory; it did not identify the Chrome cause.

## Current isolation path (2026-10-08)

From published v0.16.376 onward, keep both processes' normal OS `HOME` and set `CLIANY_RUNTIME_HOME` before starting the CLI to select an empty runtime directory. A manually managed browser still needs its own disposable profile and dedicated loopback CDP port; this setting does not isolate an existing browser, XDG model configuration or system credentials. Do not attach a browser carrying private account state.

The [v0.16.377 public-archive replay](2026-10-08-public-python-docs-archive-replay.md) verified the unchanged pinned Python docs adapter with explicit fresh CDP and with automatic headless Chrome on an unused port. All 100 returned rows matched the independent normal site's 100-row prefix, while 131 rows were available. This remains one-host maintainer evidence, not proof of complete collection or automatic startup under arbitrary new accounts. Independent first-user acceptance remains open in [#33](https://github.com/pearjelly/cliany.site/issues/33) and [#55](https://github.com/pearjelly/cliany.site/issues/55).
