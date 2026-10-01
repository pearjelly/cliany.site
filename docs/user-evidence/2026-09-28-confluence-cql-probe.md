# Confluence keyword-search probe (2026-09-28)

The published v0.14.1 `cwiki.apache.org` adapter maps `--query` to an exact `title` filter and returns zero rows for `release` in the `SPARK` space. To check whether a real keyword path is available, a separate read-only request used Atlassian's documented [CQL search endpoint](https://developer.atlassian.com/server/confluence/rest/v931/api-group-search/):

```text
GET https://cwiki.apache.org/confluence/rest/api/search
cql=space=SPARK AND siteSearch~"release"
limit=5
```

The response returned `size=5`, `totalSize=6`, and five result objects. One result had `content.id=38572314` and `content.title="Preparing Spark Releases"`; other returned titles included `Wiki Homepage`, `Spark SQL Internals`, `PySpark Internals`, and `Java API Internals`. Search-result display titles may contain highlighting markers, so a future adapter should use the content title for clean output and preserve the result URL.

This proves that a read-only keyword endpoint returned nonempty data from this network at this time. It does not validate an adapter, prove every row's relevance, or restore the degraded case. A replacement must be built without editing the historical generated file, packaged and strictly verified, then run with `--space SPARK --query release` before changing the case status.

## Maintained replacement candidate

An isolated candidate now lives under `curated_adapters/cwiki.apache.org/`. The historical generated file remains unchanged. Eight offline tests cover CQL mapping, scope escaping, result parsing, failure envelopes, isolated archive creation, installation, and strict verification. A direct read-only command invocation on September 28 returned five rows for `--space SPARK --query release --limit 5`; the first was `Preparing Spark Releases` and its returned URL responded HTTP 200. The archive has not been publicly released or installed over the user's adapter. The active case therefore remains degraded pending a published, digest-pinned archive and post-install command audit.

On September 30, after incorporating published v0.16.364 into the candidate branch, the same read-only command again returned five rows. The first result was `Preparing Spark Releases` (`content.id=38572314`); the remaining titles were `Wiki Homepage`, `Spark SQL Internals`, `PySpark Internals`, and `Java API Internals`. This was a direct invocation of the maintained source, not a public archive install or case promotion.

On October 1, the maintained source again returned five rows. A frozen v0.16.365 archive (`sha256:85ab3e918f32070fd69ae2947e69530b936a9d6655588d5153612d2686cac84f`) was dry-run, installed, and strictly verified in a temporary HOME; the installed CLI also returned five rows for the same read-only command. This is local package evidence, not proof that the future GitHub Release asset is reachable or that an existing user's adapter was safely replaced. The case stays degraded until that exact public asset passes an independent install and replay audit.
