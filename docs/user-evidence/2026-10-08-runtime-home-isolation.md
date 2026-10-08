# Runtime Home Isolation Across Demo Subprocesses

**Date:** 2026-10-08 (Asia/Shanghai). **Scope:** maintainer-only, read-only public Jira demo on clean implementation commit `3c0d1ea89f35c71241809abd059a155c57c87787`, based on published v0.16.375. This is unreleased implementation evidence, not an independent user's trial.

## Reproduction and offline boundary

The earlier published-package attempt in [Issue #70](https://github.com/pearjelly/cliany.site/issues/70) selected an empty runtime directory through the benchmark runner. The parent changed its in-process config, but the demo's install subprocess loaded the default directory and stopped with an already-installed adapter error. It did not overwrite or query.

The new `CLIANY_RUNTIME_HOME` setting is inherited by new processes; demo also exports its current configured home to each child. The runner sets this environment setting before CLI initialization. Remaining hard-coded runtime paths now use the shared config. Chrome's normal OS HOME is preserved.

The real subprocess regression places a same-domain adapter and sentinel Session/index in a temporary default home, then installs a fixed-hash local package into an empty selected home, verifies strictly and reads the selected adapter's `ISOLATED-1` result. The default files remain byte-identical. Separate persistence checks exercise index rebuild, existing-adapter context, repair/heal cache writes, recording images/AXTree, screenshot output and PID writes; Obscura's default cache location also follows the setting. All tests use `tmp_home`; no protected infrastructure or generated adapter is edited.

## Public read-only check

With the normal macOS OS HOME and a new cliany-site runtime directory:

```bash
env -u CLIANY_QA_OFFLINE \
  CLIANY_RUNTIME_HOME=/tmp/cliany-issue70-3c0d1ea8-20261008 \
  uv run --frozen cliany-site demo --case-id apache-jira-issues --json
```

The active case supplies its existing public archive URL and SHA-256 `ad5867d361f372914c536fb59c8f26837af96ed407859cf69dc8464922f05319`. The adapter code and metadata are unchanged. No `--force`, LLM call or browser-generation claim is involved.

| Run | Exit / envelope | Installation | Business result |
| --- | --- | --- | --- |
| First | 0 / `ok=true` | `installed_now=true`, strict verify passed before query | 5 nonblank SPARK issue records; total 59,649; first `SPARK-60074`. |
| Repeat | 0 / `ok=true` | `installed_now=false` | 5 nonblank SPARK issue records; total 59,650; first `SPARK-60075`. |

The live project changed between calls, so matching full result sets is not asserted. A separate request to [SPARK-60074's public issue API](https://issues.apache.org/jira/rest/api/2/issue/SPARK-60074?fields=summary,status) confirmed the returned summary, "Avoid parsing the requested schema twice per split in the vectorized Parquet reader", and status `Open`.

## Limits and release gate

This validates one maintainer's isolated API-backed path at one point in time. It does not establish independent first-user success, browser startup under every account, LLM generation quality or continuing third-party availability. Issues #33 and #55 remain open. Final-master offline/static/browser checks, tagged readiness, GitHub/PyPI publication, production website verification and a repeat from the published package are still required for v0.16.376.
