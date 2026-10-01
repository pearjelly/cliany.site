# Jenkins public package audit (2026-10-02)

The maintained read-only Jenkins package was published as a separate asset of [v0.16.367](https://github.com/pearjelly/cliany.site/releases/tag/v0.16.367). A fresh download of the public archive matched the frozen release input and the hash pinned in the case catalog:

```text
https://github.com/pearjelly/cliany.site/releases/download/v0.16.367/builds.apache.org-0.16.367.cliany-adapter.tar.gz
sha256:10ac9f4dc1ce2b4cc364d9fe9517e1ecabd50743885f404040abf8fc248ef18b
```

In a new temporary HOME, the public archive passed `market install --dry-run --json`, actual installation, and `verify builds.apache.org --strict --json` with verdict `ok`. The read-only `list-jobs --limit 5 --json` command returned `count=5` and `total=106`; the first row was `2.1` at `https://ci-builds.apache.org/job/2.1/`.

A separate Python 3.11 environment installed `cliany-site==0.16.367` from PyPI, then repeated the pinned public install, strict verification, and online query in another empty HOME with the same result. No existing user adapter was replaced. Master CI and Embodied CI passed at release commit `4f11f47cbb4fa5399e6bed65b6289ae25de16196`; the tag Release workflow also passed. A fresh clone of remote master passed `check_release_publication.py --remote --distribution --strict` with the same tag at HEAD and GitHub Release/PyPI version `0.16.367` publicly visible.

With the candidate marked active in the source catalog, `demo --case-id apache-jenkins-jobs --json` used the same public package in a fresh HOME and returned `ok=true`, `installed_now=true`, and `row_count=5`. A second invocation reused the verified installation (`installed_now=false`) and again returned five rows.

This supports promoting the maintained job-list case to `active`. It does not rehabilitate the historical v0.14.1 archive, prove that every entry is a runnable build, or guarantee future ASF availability. Existing installations must still be strictly verified; replacing one requires an explicit reviewed `--force`.
