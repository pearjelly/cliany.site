# Active Demo Evidence: issues.apache.org

**Captured:** 2026-08-16
**Package baseline:** `cliany-site` v0.16.324 candidate on the maintainer worktree
**Purpose:** Reproduce the maintained active demo's static verification and one read-only command.

This is a dated maintainer evidence snapshot, not a service-availability guarantee. It records one real run from the release worktree. The candidate package-promotion gate was still blocked by the separate live LLM preflight (`E_LLM_UNAVAILABLE`), so this snapshot does not promote any candidate case or claim adapter generation, metadata validation, online smoke, live LLM, or third-party workflow readiness.

## Commands

```bash
cliany-site verify issues.apache.org --strict --json
cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json
```

Both commands exited with status `0`.

## Static Verification Result

The installed active adapter returned `ok=true`, domain `issues.apache.org`, and verdict `ok`. Its market manifest status was `missing` with no manifest issues. The output explicitly says that a manifest is optional unless distribution is needed; this is a local adapter verification result, not a package-publication result.

```json
{
  "ok": true,
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
          "issues": []
        }
      }
    ]
  },
  "error": null
}
```

## Read-Only Result

The Apache Spark project query returned `success=true`, `count=5`, and a reported `total=58368` at capture time. The five returned issue keys were `SPARK-58792`, `SPARK-58791`, `SPARK-58790`, `SPARK-58789`, and `SPARK-58788`. Their summaries, status, assignee, and priority are preserved in the captured command output below so a maintainer can compare a future run without treating this snapshot as current data.

```json
{
  "success": true,
  "data": {
    "project": "SPARK",
    "total": 58368,
    "count": 5,
    "issues": [
      {
        "key": "SPARK-58792",
        "summary": "[SQL] Isolate Hive GenericUDF instances per expression copy to fix wrong results and ClassCastException from optimizer-duplicated UDF expressions",
        "status": "Open",
        "assignee": "",
        "priority": "Major"
      },
      {
        "key": "SPARK-58791",
        "summary": "Upgrade Parquet to 1.17.1",
        "status": "Open",
        "assignee": "Dongjoon Hyun",
        "priority": "Major"
      },
      {
        "key": "SPARK-58790",
        "summary": "Use native Spark function for NumPy modf",
        "status": "Open",
        "assignee": "",
        "priority": "Major"
      },
      {
        "key": "SPARK-58789",
        "summary": "Add CredentialProvider.additionalSparkProperties() SPI for executor-side auto-configuration",
        "status": "Open",
        "assignee": "",
        "priority": "Major"
      },
      {
        "key": "SPARK-58788",
        "summary": "Add the TRIM_ARRAY array function",
        "status": "Open",
        "assignee": "",
        "priority": "Minor"
      }
    ]
  },
  "error": null
}
```

## Boundary

- The snapshot proves one installed active adapter passed strict static verification and one declared read-only command returned a successful JSON envelope from this environment.
- It does not prove that the adapter is a downloadable release asset, that a candidate package is ready, or that a live LLM provider is available.
- Re-run both commands when fresh third-party data matters; do not copy this dated result as current issue state.
