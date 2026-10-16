# Remote-install diagnostics and retained failure evidence

## Actual published baseline

At the start of this iteration, remote master/tag is `a65ff7131beab3ecbf581bb2e3b928ed0779110c`, with GitHub/PyPI and actual production home/docs at v0.16.388. The [full receipt](https://github.com/pearjelly/cliany.site/pull/98#issuecomment-6220439464) records 3,650 full final-master tests, exact-SHA ordinary/native CI, matching actual artifacts, correct production and strict remote distribution audit. Fresh online GitHub actual-publication-time capacity reports one formal release on October 17 Shanghai, v0.16.388. There is no quota reason to rush another release.

Issues 33/55 remain open, unchanged, with no independent participant report. The human trial stays pinned to 0.16.387, 0/2; this work does not change invitations or count maintainers as participants. Four active API-backed cases and the existing candidate/known-gap boundaries remain unchanged. No new live LLM generation or case promotion is attempted.

## Real download failures are not archive-format evidence

The v388 final-master combined harness first stopped at Jira archive installation with `E_DOWNLOAD_FAILED`. Both initial official-PyPI Docs and Jira attempts also stopped at installation, before browser/query steps. Their nested `INSTALL_FAILED` messages did not retain a precise underlying exception and advised checking package format. Separate resolver diagnostics and subsequent complete workflow rechecks passed, without relaxing hashes/TLS or adding retries. The original failed reports remain failed; their exact transport causes are not recoverable from those envelopes.

A predeclared four-download refresh used the unchanged official installed v388 resolver, alternating the pinned Jira/Python Docs public assets twice. All four downloads matched their expected SHA-256. This is a small maintainer availability observation, not a reproduction of the old transport cause, a workflow completion score or a continuing-availability promise.

## Confirmed diagnostic and privacy defects

The resolver collapsed non-ValueError transport exceptions into a ValueError string; `market install` then emitted only archive-format advice. Its URL display stripped query/fragment but retained URL login credentials. Certificate verification exceptions also inherit ValueError, so direct certificate errors bypassed the transport wrapper and could expose their raw text. These are source/fault-control findings, not invented causes for earlier public failures.

Thirty-four new baseline regressions failed. The first implementation retained 153 passes and two direct-certificate failures because that inheritance boundary was still wrong. Catch partitioning was corrected without changing ordinary package-validation failures. A scoped run then passed 235 checks; expanded read-cleanup and real-HTTPS coverage passed 239. A scoped Ruff check initially found one import-order warning, subsequently fixed; Mypy passed all 126 source files. These working-source results are not frozen release gates.

Three real local HTTPS child-process checks failed against the actual non-editable official v388 package for missing diagnostics: trusted-CA HTTP 404, trusted-CA HTTP 503 and an untrusted certificate. The corrected source passed all three. HTTP failures made one request each with no retry; untrusted TLS made no HTTP request. The test CA/key exist only in the temporary test home, and CA trust is selected in each test child, not installed globally. Raw response bodies/query sentinels stay out of CLI JSON. Additional privacy-only controls and final gates need their own receipts.

Two privacy-only controls then also failed against the actual official v388 package: URL login credentials appeared in a download failure, and a direct certificate exception exposed its sentinel body. The later candidate's first versioned check retained 810 passes and two metadata failures (a stale no-JavaScript baseline and a split-string Unreleased compare assertion); those current-version pointers were corrected without altering historical release ranges. A new test-line width warning was corrected separately. These failures are retained rather than overwritten or counted green.

The next versioned check retained 811 passes and one further stale documentation-intro version assertion. That current-version assertion was updated without changing historical version-specific expectations; final frozen gates remain separate.

The corrected versioned related suite passed 812 checks, including the controlled HTTPS and privacy regressions. Source/new-code Ruff, Mypy (126 files), node syntax and the unchanged dependency lock passed. Five immutable public adapter archives were freshly downloaded and matched the current manifest/pinned hashes, including the offline-only CRM package (no private CRM query). The source environment metadata is 0.16.389 and retains Playwright 1.64.0/installed Chromium. These preparation checks do not replace the full frozen source/master, exact-SHA CI or official publication gates.

## Scoped correction and limits

`AdapterDownloadError` remains a ValueError subclass. It provides only fixed stage/reason fields and a valid integer HTTP status, never raw exception/response/header content or incomplete bytes. Unknown I/O failures retain an unknown download category, not an invented connection cause. CLI repair hints distinguish asset absence, access, certificate trust and connection/read problems. `demo` already forwards the typed upstream error and still stops before verify/query. URL rendering omits login credentials/query/fragment; unparseable redirect URLs receive a fixed placeholder.

Hash, TLS, redirect, size, path, metadata and no-overwrite checks remain in place. Successful payloads and actual requested source URLs are unchanged. Existing timeout/retry policies remain unchanged; there is no added automatic retry or overall command deadline. Partial download files are removed before exit, even with --force, without replacing existing adapter data. This improves diagnosis and safe next steps, not upstream network reliability or independent-user completion.

Before publication, require full final-source/master tests, static/case/public-package/build gates, exact-SHA ordinary/native CI, fresh online Shanghai publication capacity before tag creation and push, strict target/tagged readiness, exact GitHub/PyPI bytes, correct production/aliases, official installed-package controlled/public workflows and a final strict remote distribution audit. All initial failures and later rechecks stay separate.
