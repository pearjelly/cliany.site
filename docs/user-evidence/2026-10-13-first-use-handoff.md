# Independent first-use handoff

**Date:** 2026-10-13 (Asia/Shanghai). **Scope:** trial preparation and one maintainer's repeat of the already published PyPI `cliany-site==0.16.385`. **Independent participant reports:** 0/2. No new package version, model discovery, candidate promotion or user acceptance is claimed.

## Current public baseline

Fresh online checks found GitHub latest `v0.16.385`, published at `2026-10-12T09:10:30Z`, and PyPI latest/exact `0.16.385`. Remote master remains `c97f1462ea0c9d70ecffef916792c7d390b7ff71`. The production documentation page shows `v0.16.385`; the homepage loads `script.js?v=20261012b`. The strict online Shanghai release-cap check returned 0/3 releases for October 13, not evidence that another release is warranted. The [completed PR #92 receipt](https://github.com/pearjelly/cliany.site/pull/92#issuecomment-6121504202) remains the published release evidence, not this documentation branch's acceptance.

Fresh reads of [Issue #33](https://github.com/pearjelly/cliany.site/issues/33) and [Issue #55](https://github.com/pearjelly/cliany.site/issues/55) found no independent user report. Their historical trial bodies still pin v0.16.378. Do not overwrite earlier evidence to make it look current; attach a dated handoff to the already published baseline instead.

## Trial preparation

The [trial guide](../first-use-trial.md) separates a no-browser Jira API first result from the existing Python docs browser candidate. It pins the published package, supplies empty runtime and virtual-environment setup, keeps normal OS HOME/USERPROFILE, and uses the unchanged public browser archive URL/SHA-256. The browser path uses a checked dedicated loopback port and an explicit root CDP URL rather than a potentially private configured endpoint. A port check is not a concurrency guarantee.

The new `First Use Trial` issue form records environment, path, whether the participant developed the project/adapter, maintainer help and first-attempt evidence. Success and retry fields are optional so installation failures and unmeasured time can be reported. It requests no raw logs, credentials, cookies, personal paths or browser state, and does not apply the automated reproduction label. The form is not available on GitHub until merged to the default branch; existing #33/#55 comments remain the immediately usable feedback route.

At least two people who did not build the adapters must try the published-package path; at least one must obtain and independently check a nonempty result without maintainer intervention. Prefer one participant also attempting the browser case. Keep the API/browser scores and original failed first attempts distinct. A maintainer repeat below does not fill either participant slot.

## Maintainer repeat

A new Python 3.11 virtual environment installed the exact official PyPI package with no cache or editable/source import. Package metadata, actual site-packages import and `pip check` passed. A new `CLIANY_RUNTIME_HOME` isolated adapters and all runtime files outside the repository; normal OS HOME was unchanged. Offline model mode prevented discovery while real public network requests remained enabled. No existing adapter was overwritten and no generated file was edited.

| Check | Observed result | External command wall time |
| --- | --- | --- |
| Fresh environment creation | Passed | 2.18 s |
| Official package installation | Passed, 0.16.385 | 171.01 s |
| Jira first demo | Passed, `installed_now=true`, five rows | 6.51 s |
| Jira strict verification | Passed | 0.60 s |
| Jira second demo | Passed, `installed_now=false`, five rows | 3.32 s |
| Pinned Python docs archive installation | Passed | 3.18 s |
| Browser archive strict verification | Passed before replay | 0.62 s |
| `pathlib` browser replay | Passed, 100 rows, `limit_reached=true` | 15.80 s |
| `asyncio` changed-input browser replay | Passed, 100 rows, `limit_reached=true` | 12.89 s |
| Browser archive verification after replay | Passed; owned CDP port closed afterward | 0.68 s |

The installation wait is retained, not omitted from first-use effort or presented as a speed improvement. These individual command times exclude independent browser observation and are not a full install-to-independently-checked-result duration. No such combined time was measured.

A separately opened normal [SPARK-60211 issue page](https://issues.apache.org/jira/browse/SPARK-60211) matched the returned key and summary, `Fix applyInPandasWithState failure with PyArrow 26 due to float slice offsets`. Separate normal Python docs search pages reached the completed `Search Results` heading: pathlib had 134 rows, asyncio 403. Each returned list matched that page's entire ordered 100-row prefix, including first title/link. These are capped results, not complete collection. The independent browser oracle is still run by a maintainer, not an independent person.

The first Jira oracle attempt used an unsupported heading-level filter in the browser-control interface, resulting in an ambiguous observer locator. Retargeting the exact observed heading completed the check. This observer failure is retained separately and is not a cliany CLI failure or an independent-user failure. The CLI command sequence encountered no failure; there is no observed first-user runtime defect to claim fixed.

Private attempt records and the separate oracle remain outside the repository. Only this sanitized summary is public. No raw terminal output, local profile, user runtime data, model configuration or credentials are committed.

## Handoff checks

Four new documentation/form checks failed before the guide/form/entry existed and pass afterward. The selected first-use, template, quickstart, demo and runtime-isolation checks passed 29 tests. The full offline suite passed **3,514 tests in 324.92 seconds**. Ruff passed source plus the new test module; Mypy passed all 125 source files. Case catalog and the four active distribution-package checks passed with statuses unchanged. These are preparation checks, not a new version's release gates or independent participant results. Exact-commit GitHub CI is recorded separately in the handoff PR; no tag or merge is authorized by this note alone.

## Next decision

Invite real participants now and collect their unassisted first attempts through #33/#55. Preserve original report links, package versions and first failure phases. Add reproduction, fix and retry evidence as new entries; do not rescore an earlier failure as a first-pass success. Classify third-party outages separately and say when a report could not be reproduced. The browser case remains candidate and the product's independent first-use acceptance remains open.

Keep this handoff reviewed without releasing a package solely for the calendar. A runtime or materially necessary onboarding fix from real evidence must complete all existing release gates before merge/tag/publication. The current package and production site remain 0.16.385.
