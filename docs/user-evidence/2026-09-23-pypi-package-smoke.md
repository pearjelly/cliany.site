# PyPI adapter package smoke (2026-09-23)

## Scope

Read-only local package acceptance for the generated PyPI adapter. This is not evidence that a GitHub Release asset is publicly installable.

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

## Release Gate

Keep `pypi-project-search` as `candidate` until the exact archive is attached to GitHub Release `v0.16.360`, its public SHA-256 is verified, and an independent HOME can install the asset by HTTPS URL and repeat strict verification plus a successful read-only smoke against normal PyPI search results.
