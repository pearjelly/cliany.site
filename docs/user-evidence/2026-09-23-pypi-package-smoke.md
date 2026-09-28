# PyPI adapter package smoke (2026-09-23)

## Scope

Read-only local package acceptance for the generated PyPI adapter, followed by public asset verification on 2026-09-24.

Package: `pypi.org-0.16.360.cliany-adapter.tar.gz`

SHA-256: `37efcddbf52606c3249155b41c015d0dab22765b6d813dd0ed575b739170ad23`

The package and all installed runtime state remained under `~/.cliany-site/` or a fresh `/tmp` HOME; no generated adapter was committed to the repository.

## Acceptance

With a fresh temporary HOME and matching XDG config directory:

1. `market install <local-package> --sha256 <digest> --dry-run --json` returned `success=true`, `would_replace=false`, and listed `commands.py` and `metadata.json`.
2. The same install without `--dry-run` returned `success=true`.
3. `verify pypi.org --strict --json` returned `ok=true`, `verdict=ok`, and no issues.
4. `pypi.org search-packages --query cliany-site --json` returned `ok=true`, `quality.status=ok`, 20 rows, and a `cliany-site` project row.

The first `--query pytest` run returned `E_EMPTY_RESULT` immediately after the search click, despite the typed value being `pytest`. A direct browser state check of `https://pypi.org/search/?q=pytest` showed package links, and a subsequent adapter run returned 20 rows. The exact upstream/browser timing cause is not proven. The generated-adapter runtime now retries an otherwise successful empty list/table extraction after 0.5 and 1.0 seconds; persistent empty and partial-quality results still fail. After this change, three consecutive `pytest` adapter runs in the same isolated HOME returned `quality.status=ok`, 20 rows, with `pytest` as the first title.

A later `cliany-site` query on the shared Chrome returned `E_CDP_UNAVAILABLE` after a browser-use click event timed out. The same query in a fresh, isolated headless Chrome returned `E_EMPTY_RESULT`; CDP's tab list identified the resulting PyPI search page as `Client Challenge`. This establishes that the later empty extraction was not a legitimate zero-match result. It does not prove that every click timeout has the same cause. PyPI online reliability remains unverified; do not bypass its challenge or promote the case on the earlier passes alone.

With the v0.16.360 candidate's page-title diagnostic, another fresh isolated Chrome replay returned top-level `E_PAGE_NOT_READY` with `reason=site_challenge` and `title=Client Challenge`. The browser was closed after the check. This improves the failure explanation; it does not make the PyPI workflow pass or establish site availability.

## Public Asset (2026-09-24)

GitHub Release `v0.16.360` publishes the archive with the same SHA-256. Using the published `cliany-site==0.16.360` in a fresh HOME, installation from the public HTTPS release URL with `--sha256` succeeded, and `verify pypi.org --strict --json` returned `verdict=ok` with no issues. This was repeated in a second fresh HOME. The package asset and metadata gates are complete.

## Remaining Gate

Keep `pypi-project-search` as `candidate` until an independent HOME can repeat a successful read-only smoke against normal PyPI search results. The isolated Chrome check on 2026-09-24 still reached PyPI's `Client Challenge` and returned `E_PAGE_NOT_READY` with `reason=site_challenge`; do not bypass the challenge or treat package verification as online workflow success.

On 2026-09-28, a fresh `/tmp` HOME installed `cliany-site==0.16.363` from the official PyPI index, installed the public v0.16.360 adapter asset by its recorded SHA-256, and passed `verify pypi.org --strict`. Its isolated headless read-only `search-packages --query cliany-site` run exited nonzero with `E_PAGE_NOT_READY` after `on_NavigateToUrlEvent` timed out at 30 seconds. An independent HTTP request to the same search URL returned a `Client Challenge` title. The browser stopped and its isolated CDP port was no longer listening. This confirms the published timeout classification, but does not establish a successful online smoke or prove the challenge caused that specific timeout.

A controlled follow-up kept the normal system HOME while directing cliany-site runtime data to the isolated temporary directory. Auto-launched headless Chrome reached a local page twice; a fresh PyPI navigation showed `Client Challenge` in the browser. With the published v0.16.363 package and public adapter in this arrangement, the read-only search returned `E_SELECTOR_NOT_FOUND`, not project rows. Replacing system HOME with `/tmp` is therefore a confound in the earlier navigation-timeout runs; the exact Chrome mechanism is unproven. The site challenge independently prevents promotion.

The next-version candidate identified a separate generated-command defect behind that `E_SELECTOR_NOT_FOUND`: each nested browser step closed its auto-launched Chrome. Holding the browser for the full command let the unchanged public adapter navigate, type `cliany-site`, and click Search. Extraction then observed `Client Challenge` and returned `E_PAGE_NOT_READY` with `reason=site_challenge`. The search still did not return project rows, so online smoke remains pending.
