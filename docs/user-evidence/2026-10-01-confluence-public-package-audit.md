# Confluence public package audit (2026-10-01)

The maintained v0.16.365 asset was independently fetched from the public GitHub Release into an isolated HOME using its pinned SHA-256:

```text
https://github.com/pearjelly/cliany.site/releases/download/v0.16.365/cwiki.apache.org-0.16.365.cliany-adapter.tar.gz
sha256:85ab3e918f32070fd69ae2947e69530b936a9d6655588d5153612d2686cac84f
```

The published PyPI CLI v0.16.365 completed a dry-run, real install and `verify cwiki.apache.org --strict --json` with verdict `ok`. A read-only `search-pages --space SPARK --query release --limit 5 --json` returned five page rows, including `Preparing Spark Releases` (`content.id=38572314`). No existing user adapter was replaced.

The source CLI's `demo --case-id apache-confluence-search --json` then ran the same pinned public install, strict verification and read-only query in a new isolated HOME. The first invocation returned `ok=true`, `installed_now=true`, `row_count=6`; a second invocation returned `ok=true`, `installed_now=false`, `row_count=6`. Both started with `Preparing Spark Releases`. The difference between five and six rows reflects the direct command's `--limit 5` versus the demo command's default limit of 10.

This supports promoting the maintained case to `active`. It does not rehabilitate the historical v0.14.1 exact-title adapter, guarantee future third-party availability, or prove every returned page is relevant to the search term. Existing installations must still be strictly verified; the demo never overwrites them.
