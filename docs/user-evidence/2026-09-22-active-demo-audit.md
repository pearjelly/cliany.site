# 2026-09-22 Demo Audit

Baseline: cliany-site v0.16.354, followed by the v0.16.355 package validation fix.

## Jira

`cliany-site verify issues.apache.org --strict --json` passed for the installed adapter (manifest missing). `cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json` returned `success=true`, `count=5`, `total=59283`, with keys SPARK-59708 through SPARK-59704. This adapter calls Jira's REST API; the result is not evidence of browser replay or LLM exploration.

## Confluence

The installed adapter passed strict verification (manifest missing). `cliany-site cwiki.apache.org search-pages --space SPARK --query "release" --json` returned `success=true`, `count=0`, `results=[]`. The capture script currently checks the envelope only and reported success. This does not prove useful search results; a follow-up should verify the query and extraction behavior before claiming a successful demo.

## Jenkins: Degraded

`cliany-site verify builds.apache.org --strict --json` failed with `E_VERIFY_STATIC` and `'generated_at' is a required property`. The read-only command was not run.

The published [v0.14.1 archive](https://github.com/pearjelly/cliany.site/releases/download/v0.14.1/builds.apache.org-0.14.1.cliany-adapter.tar.gz) was downloaded separately without replacing the installation. Its SHA-256 is `b09710acbabfb5465a6e04b5b140a4ffa4aa24795a2b4ada60eeabbddddea0c2`, matching the catalog. Its metadata declares schema version 3 but lacks both `generated_at` and `generator_version`.

Before the fix, `market install <archive> --dry-run --json` reported success because only archive structure and hashes were checked. After the fix it returns `INSTALL_FAILED` with the missing-field diagnosis. Regression tests also prove forced installation leaves the existing adapter and backups unchanged on invalid metadata.

The catalog now marks Jenkins `degraded`. Restoring `active` requires a new valid package, a fixed SHA-256 download command, strict metadata validation, and a real successful read-only smoke. The historical generated adapter has not been edited or republished.

## Follow-Up

The three remaining active v0.14.1 archives (Jira, Confluence, SuiteCRM) were each downloaded through their catalog HTTPS URL and fixed SHA-256, then passed `market install --dry-run --json` with the new validator. These checks did not overwrite any installed adapter and do not prove all three online workflows succeed.

- Check Confluence's empty result before advertising useful search output.
- Add row-aware validation to the evidence capture script so envelope success alone cannot pass a nonempty demo requirement.
- Rebuild Jenkins through the supported generation path after live provider preflight succeeds, then verify the complete new-user installation flow.
- Runtime archives remain under `~/.cliany-site/`; no sessions, snapshots, or adapter code are committed here.
