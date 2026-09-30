# Confluence keyword-search probe (2026-09-28)

The published v0.14.1 `cwiki.apache.org` adapter maps `--query` to an exact `title` filter and returns zero rows for `release` in the `SPARK` space. To check whether a real keyword path is available, a separate read-only request used Atlassian's documented [CQL search endpoint](https://developer.atlassian.com/server/confluence/rest/v931/api-group-search/):

```text
GET https://cwiki.apache.org/confluence/rest/api/search
cql=space=SPARK AND siteSearch~"release"
limit=5
```

The response returned `size=5`, `totalSize=6`, and five result objects. One result had `content.id=38572314` and `content.title="Preparing Spark Releases"`; other returned titles included `Wiki Homepage`, `Spark SQL Internals`, `PySpark Internals`, and `Java API Internals`. Search-result display titles may contain highlighting markers, so a future adapter should use the content title for clean output and preserve the result URL.

This proves that a read-only keyword endpoint returned nonempty data from this network at this time. It does not validate an adapter, prove every row's relevance, or restore the degraded case. The next work is to generate a replacement without editing the historical generated file, package and strictly verify it, run the declared `--space SPARK --query release` command, and require nonempty relevant rows before changing the case status.
