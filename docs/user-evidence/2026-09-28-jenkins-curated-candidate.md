# ASF Jenkins read-only replacement candidate (2026-09-28)

The [September 22 audit](2026-09-22-active-demo-audit.md) found that the published v0.14.1 `builds.apache.org` archive claims metadata schema v3 but lacks `generated_at` and `generator_version`. Its generated code and the user's installed adapter were not edited.

The public `https://builds.apache.org/api/json?tree=jobs[name,url,color]` request redirected to `https://ci-builds.apache.org/` and returned HTTP 200 with 106 top-level entries. Running the historical command directly (without installation or modification) returned five rows for `--limit 5` but mislabeled `total` as 5.

The maintained replacement source under `curated_adapters/builds.apache.org/` uses the same read-only Jenkins JSON API. Jenkins [documents its top-level API as a listing of configured jobs](https://www.jenkins.io/doc/book/using/remote-access-api/). The new command reports `count=5`, `total=106`, and only same-site HTTPS result URLs. In a fresh temporary HOME, the candidate archive installed with a SHA-256 pin, passed `verify builds.apache.org --strict --json`, and returned five rows through the top-level `cliany-site builds.apache.org list-jobs --limit 5 --json` command. Its first returned URL, `https://ci-builds.apache.org/job/2.1/`, responded HTTP 200.

This is local candidate evidence, not a published package or proof that every Jenkins entry is a runnable build. The catalog remains degraded until a release asset, pinned public install command, and post-publication smoke pass.
