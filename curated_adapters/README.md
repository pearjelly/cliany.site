# Maintained adapters

These source files are reviewed project assets, not generated user adapters. Do not copy them into an existing `~/.cliany-site/adapters/` directory by hand.

## ASF Confluence keyword search

`cwiki.apache.org` searches public Confluence pages with the documented read-only CQL endpoint. It keeps `--space` as a scope and uses `--query` as a keyword/phrase search, unlike the historical v0.14.1 adapter's exact-title filter.

Build an installable archive from an isolated temporary home:

```bash
uv run python scripts/build_curated_adapter.py --domain cwiki.apache.org --version VERSION --output-dir dist
```

The builder refuses to replace an existing archive and never reads or writes installed adapters. Run `cliany-site market install ARCHIVE --dry-run --json` and verify the SHA-256 before distributing it. Users with an existing adapter should follow the marketplace's explicit replacement flow only after the new archive is published and independently verified.

## ASF Jenkins job listing

`builds.apache.org` reads the public controller's top-level jobs and folders through the Jenkins JSON API, now served from `ci-builds.apache.org`. The new adapter reports the full top-level total separately from the limited returned count. Its source is maintained here because the historical v0.14.1 archive does not pass schema v3 validation; the historical generated file remains untouched.

```bash
uv run python scripts/build_curated_adapter.py --domain builds.apache.org --version VERSION --output-dir dist
```
