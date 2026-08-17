# Active Demo Evidence: issues.apache.org

**Captured:** 2026-08-17
**Package baseline:** `cliany-site` 0.16.325
**Case:** `apache-jira-issues` (ASF Jira issue list)
**Target:** https://issues.apache.org/jira/
**Overall:** `true`

This is a dated maintainer evidence snapshot, not a service-availability guarantee. It records only the commands declared by the active case. The read-only command is run only after strict static verification returns a successful JSON envelope. It does not prove that the adapter is a downloadable release asset, candidate package promotion, live LLM availability, or continuing third-party workflow availability.

## Results

### Strict Static Verification
- Command: `cliany-site verify issues.apache.org --strict --json`
- Exit status: `0`
- JSON envelope success (`ok` or `success`): `true`

#### stdout

```json
{
  "ok": true,
  "version": "1",
  "command": "verify",
  "data": {
    "domain": "issues.apache.org",
    "results": [
      {
        "domain": "issues.apache.org",
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
- Command: `cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json`
- Exit status: `0`
- JSON envelope success (`ok` or `success`): `true`

#### stdout

```json
{
  "success": true,
  "data": {
    "project": "SPARK",
    "total": 58392,
    "count": 5,
    "issues": [
      {
        "key": "SPARK-58816",
        "summary": "INSERT with a column list resolves structs inside arrays and maps by name instead of position",
        "status": "Open",
        "assignee": "",
        "priority": "Major"
      },
      {
        "key": "SPARK-58815",
        "summary": "Make attribute binding collision-safe in DSv2 row-level operations",
        "status": "Open",
        "assignee": "",
        "priority": "Major"
      },
      {
        "key": "SPARK-58814",
        "summary": "Format round-trips Parquet/ORC/Avro/CSV",
        "status": "Open",
        "assignee": "",
        "priority": "Major"
      },
      {
        "key": "SPARK-58813",
        "summary": "SQL goldens charvarchar-* under standardSemantics",
        "status": "Open",
        "assignee": "",
        "priority": "Major"
      },
      {
        "key": "SPARK-58812",
        "summary": "Collation RTRIM trailing-blank compare tests",
        "status": "Open",
        "assignee": "",
        "priority": "Major"
      }
    ]
  },
  "error": null
}
```
