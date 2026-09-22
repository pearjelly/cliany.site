# Active Demo Evidence: cwiki.apache.org

## Follow-Up Diagnosis

Captured while the case was active; it is now degraded. Reading the installed,
unchanged v0.14.1 adapter shows that `--query` becomes the REST `/content`
parameter `title`, not a full-text query. A read-only listing without `--query`
returned three pages. The observed title `Wiki Homepage` returned one page with
id `33293106` when supplied as the query. The original `release` query below
still returned zero. This distinguishes the advertised search mismatch from
an inability to read public pages; it does not prove all authentication paths.

The [official REST examples](https://developer.atlassian.com/server/confluence/confluence-rest-api-examples/)
document the content API. Restore active status only after regenerating a
keyword-search adapter through a supported path, packaging it, and checking
the original query's nonempty relevant results. Do not substitute the easier
exact-title lookup as proof of keyword search. The historical generated file
and published archive have not been changed.

The new evidence gate checks configured row location, minimum count, and row
object shape. It does not establish relevance or correctness of every field.

**Captured:** 2026-09-22
**Package baseline:** `cliany-site` 0.16.356
**Case:** `apache-confluence-search` (ASF Confluence page search)
**Target:** https://cwiki.apache.org/
**Overall:** `false`
**Row check:** `{"ok": false, "status": "too_few_rows", "row_count": 0, "min_count": 1}`

This is a dated maintainer evidence snapshot, not a service-availability guarantee. It records only the commands declared by the active case. The read-only command is run only after strict static verification returns a successful JSON envelope. It does not prove that the adapter is a downloadable release asset, candidate package promotion, live LLM availability, or continuing third-party workflow availability.

## Results

### Strict Static Verification
- Command: `cliany-site verify cwiki.apache.org --strict --json`
- Exit status: `0`
- JSON envelope success (`ok` or `success`): `true`

#### stdout

```json
{
  "ok": true,
  "version": "1",
  "command": "verify",
  "data": {
    "domain": "cwiki.apache.org",
    "results": [
      {
        "domain": "cwiki.apache.org",
        "verdict": "ok",
        "issues": [],
        "smoke": null,
        "manifest": {
          "status": "missing",
          "issues": [],
          "action": "未检测到 market manifest；若需要分发，请运行 cliany-site market publish <domain>。"
        }
      }
    ]
  },
  "error": null,
  "meta": {
    "duration_ms": 0,
    "source": "builtin"
  }
}
```

### Declared Read-Only Command
- Command: `cliany-site cwiki.apache.org search-pages --space SPARK --query "release" --json`
- Exit status: `0`
- JSON envelope success (`ok` or `success`): `true`

#### stdout

```json
{
  "success": true,
  "data": {
    "space": "SPARK",
    "query": "release",
    "count": 0,
    "results": []
  },
  "error": null
}
```
