# Maintained adapters

These source files are reviewed project assets, not generated user adapters. Do not copy them into an existing `~/.cliany-site/adapters/` directory by hand.

## ASF Confluence keyword search

`cwiki.apache.org` searches public Confluence pages with the documented read-only CQL endpoint. It keeps `--space` as a scope and uses `--query` as a keyword/phrase search, unlike the historical v0.14.1 adapter's exact-title filter.

Build an installable archive from an isolated temporary home:

```bash
uv run python scripts/build_curated_confluence_adapter.py --version VERSION --output-dir dist
```

The builder refuses to replace an existing archive and never reads or writes installed adapters. Run `cliany-site market install ARCHIVE --dry-run --json` and verify the SHA-256 before distributing it. Users with an existing adapter should follow the marketplace's explicit replacement flow only after the new archive is published and independently verified.
