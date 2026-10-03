# SuiteCRM public package audit (2026-10-02)

## Scope

The published `cliany-site==0.16.368` CLI was installed from PyPI into an isolated Python 3.11 virtual environment. Runtime data used fresh temporary HOME directories, not the maintainer's `~/.cliany-site/` or the repository. This audit checks distribution and static loading only. The SuiteCRM demo requires login; no credentials were supplied and no account query was run.

## Public asset and checks

The asset was downloaded from [GitHub Release v0.14.1](https://github.com/pearjelly/cliany.site/releases/tag/v0.14.1):

`demo.suiteondemand.com-0.14.1.cliany-adapter.tar.gz`

Its observed SHA-256 was `1671dd92d3828cecb1f04f41eefceb7bdc727d0dee1f35d4f14ca360432ced31`, matching `cases/manifest.json`.

With the published CLI and one empty HOME, local-archive `market install --dry-run --json` reported `dry_run=true`, `would_replace=false`, and the same digest. Installation succeeded, `verify demo.suiteondemand.com --strict --json` returned `verdict=ok` with no issues, and the installed CLI exposed the read-only `list-accounts` command.

A second empty HOME repeated the user-facing HTTPS path:

```bash
cliany-site market install https://github.com/pearjelly/cliany.site/releases/download/v0.14.1/demo.suiteondemand.com-0.14.1.cliany-adapter.tar.gz --sha256 1671dd92d3828cecb1f04f41eefceb7bdc727d0dee1f35d4f14ca360432ced31 --json
cliany-site verify demo.suiteondemand.com --strict --json
```

The remote install succeeded. Strict verification again returned `verdict=ok`, `manifest.status=ok`, `issues=[]`, and `smoke=null`.

## Evidence boundary

This proves that the exact public archive is downloadable, matches the pinned digest, installs without replacing an existing adapter in a fresh HOME, passes static verification, and registers its command with PyPI cliany-site 0.16.368. It does **not** prove the third-party demo is currently reachable, that login works, or that `list-accounts` returns live rows. Those require an authorized, separate online smoke check; static `verify` must not be presented as that result.
