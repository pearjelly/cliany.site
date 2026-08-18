# cliany-site Public Roadmap

- **Updated:** 2026-08-18
- **Current baseline:** v0.16.327
- **Maintainer roadmap:** [roadmap-2026-q3.md](roadmap-2026-q3.md)

cliany-site turns real browser workflows into reusable CLI commands. The Q3 roadmap focuses on making that path more reliable, easier to try, and easier to share.

## What Is Already In Place

- A 10-minute first-run path that starts with `doctor`, real demo cases, and replay before requiring users to configure an LLM.
- A real case catalog with CRM, DevOps, knowledge-base, and package-search workflows.
- Structured JSON envelopes for success and failure, including retryable LLM outage reporting through `E_LLM_UNAVAILABLE`.
- Adapter verification, marketplace packaging, metadata validation, and generated-code security checks.
- Four maintained historical demos with copyable GitHub Release asset URLs and pinned SHA-256 installation checks.
- Release readiness and publication checks that keep GitHub Release, PyPI, CI, changelog, website publication, and case catalog validation tied together.

## Near Term: 2026-07-29 to 2026-08-05

The next focus is turning candidate real-world cases into verified active demos.

As of v0.16.300, the cadence report exposes `daily_release_capacity_remaining` separately from `daily_release_limit_ok`: an exactly full `3/3` day still has a valid current count but zero capacity for a new tag, and its next action says to wait until tomorrow. This makes the daily cap decision explicit for maintainers and release automation.

As of v0.16.301, invoking a discovered current-schema adapter that cannot register no longer looks like an unknown command. The root CLI returns structured `E_VERIFY_STATIC` details and points to `cliany-site verify <domain> --strict --json`; this is a local static diagnosis, not proof that a browser, site workflow, or LLM provider is ready.

As of v0.16.302, `cliany-site cases --status active` gives each maintained active case a human-readable first-run order: fixed-SHA HTTPS installation, strict verification, only the login declared by that case, and then its declared read-only command. It is guidance only: it does not install, log in, execute, overwrite, or turn an occupied directory into health evidence.

As of v0.16.303, SDK and HTTP callers get the same local adapter preflight before browser startup: invalid adapter directory names return a request error, while unsafe, missing, unreadable, or unloadable installed adapter files return a structured static verification error. This separates a repairable local adapter problem from Chrome, LLM, or third-party workflow readiness.

As of v0.16.304, integrations can perform that same bounded check directly through asynchronous `ClanySite.verify(domain)`, synchronous `verify(domain)`, or `GET /verify?domain=<domain>`. These endpoints provide the CLI's static diagnostics before browser work, preserving `400` for invalid input, `404` for an absent adapter, and `422` for a failed local adapter verification; they do not establish workflow, LLM, or third-party availability.

As of v0.16.305, the installed adapter is also a bounded local trust surface: root CLI registration, strict verification, SDK verification/execution, and HTTP verification/execution reject symbolic-link adapter directories and core files before reading or importing them. The same `security_issue` / `E_VERIFY_STATIC` repair signal remains local-only and does not claim browser, workflow, or provider readiness.

As of v0.16.306, root CLI registration also rejects a symbolic-link manifest before importing commands. SDK `execute` and `POST /execute` check a present manifest and its declared file hashes before browser startup, so a local manifest failure remains a static `E_VERIFY_STATIC` / HTTP `422` repair path rather than a browser, workflow, or provider result.

As of v0.16.307, direct root CLI adapter dispatch also checks a present manifest's declared file hashes before importing `commands.py`. A mismatch is a local `manifest_error` / `E_VERIFY_STATIC` repair path, so all adapter execution surfaces use the same installed-file boundary without claiming browser, workflow, or provider readiness.

As of v0.16.308, direct root CLI adapter dispatch also runs the generated-module source scan before importing `commands.py`. Banned patterns and non-UTF-8 modules now return the same local `security_issue` / `E_VERIFY_STATIC` repair path used by strict verification and SDK/API execution; this remains local-only evidence.

As of v0.16.309, `doctor --json` separates local configuration from a real provider result: `ready_for_explore` remains the compatibility signal for local prerequisites, while `ready_for_live_explore` becomes true only after `doctor --llm-live --require-capability generate_adapters --json` succeeds. Automation can therefore stop before a real `explore` when the provider has not been tested or is unavailable.

As of v0.16.310, the nested `generate_adapters` capability makes that distinction actionable without changing its established local `ready` field: `local_ready` names the local result, while `live_blockers` identifies an omitted or failed live preflight and `next_step` gives the strict preflight command. This prevents a locally configured machine from presenting an untested provider as the next runnable `explore` step.

As of v0.16.311, `local_ready` and `local_blockers` exclude the `llm_live` result. A retryable provider outage can now truthfully report that local prerequisites remain ready while overall generation is blocked by `live_blockers=["llm_live"]`; the strict retry command remains the next step.

As of v0.16.312, candidate doctor evidence bundles, issue templates, the standalone extractor, case validation, and next-iteration artifacts also retain `generate_adapters.local_ready` and `local_blockers`. A blocker handoff can now show healthy local prerequisites beside a failed live provider without weakening the live preflight gate.

As of v0.16.313, the production website's English maintainer translation uses a quote-safe JavaScript delimiter. Apostrophes no longer stop `site/script.js` from parsing and leave the homepage body blank; site regression, `node --check`, and production browser inspection guard the recovery.

As of v0.16.315, that incident check is part of the release system: master CI has a dedicated website JavaScript syntax job, tag preflight repeats it, and strict readiness verifies both commands remain present. This moves a production white-screen failure from post-deploy discovery to pre-publication blocking.

As of v0.16.316, the tag workflow creates each GitHub Release from its reviewed versioned notes file. Strict readiness checks that file's version heading and user-facing content before a tag is pushed, and rejects a workflow that falls back to generated compare-only notes. This keeps GitHub Release and PyPI publication aligned without a post-publication note repair.

As of v0.16.318, public candidate issue bodies retain the doctor evidence values hash and gate state without exposing a maintainer's local source path. When a saved preflight is attached, the handoff separates unfinished package evidence from the provider gate and tells contributors to rerun the strict preflight after provider recovery; it never treats blocked evidence as permission to explore.

As of v0.16.319, candidate issue handoffs make that evidence boundary explicit in both human Markdown and machine-readable primary-task fields, so a public blocker issue no longer says that all evidence is absent when the doctor preflight has already been attached.

As of v0.16.320, planner-generated candidate issue artifacts distinguish attached doctor preflight evidence from still-pending adapter package evidence, including a recovery-and-rerun handoff when the provider is unavailable. This keeps a saved blocker report useful without making candidate exploration runnable.

As of v0.16.321, the repository's CI, release, and dependency-verification workflows use the reviewed checkout, Node, Python, uv, and artifact action updates. The maintenance change is validated by fresh repository CI and release preflight evidence; it does not establish browser, LLM, adapter-package, or third-party workflow readiness.

As of v0.16.322, Dependabot groups GitHub Actions upgrades into one reviewable proposal and no longer carries a stale action-version inventory in its configuration comment. This reduces duplicate dependency branches while preserving the existing CI, release, and live-LLM evidence gates; it does not establish browser, adapter-package, or third-party workflow readiness.

As of v0.16.323, strict release readiness requires the reviewed `actions/setup-python@v7` major in both master CI and tag Release Preflight. This keeps the merged Dependabot action update enforced before publication without changing runtime behavior or establishing browser, adapter-package, live-LLM, or third-party workflow readiness.

As of v0.16.324, the public quickstart links a dated maintainer evidence snapshot for the installed `issues.apache.org` active demo: strict static verification passed, and the declared read-only Apache Spark query returned five results. The snapshot preserves the commands, observed output, and evidence boundary; it is not candidate package, live LLM, online smoke, or current third-party availability evidence.

As of v0.16.325, maintainers can run `scripts/capture_active_demo_evidence.py` for a named active case to produce the same dated snapshot format. It derives the strict verify command and declared read-only JSON command from `cases/manifest.json`, runs the latter only after a successful static envelope, and records a failed or skipped path as nonzero evidence rather than silently publishing a success claim. The helper is a capture workflow, not a claim that the third-party service or candidate promotion gate is continuously available.

As of v0.16.326, `doctor --llm-live --require-capability <capability> --json` preserves the full failed check summary in `error.details` and returns a stable error code for the first hard blocker, such as `E_CDP_UNAVAILABLE`. Automation can now distinguish a missing browser from a provider outage and retry the correct repair path instead of interpreting a generic `E_UNKNOWN` as an actionable capability result.

As of v0.16.327, the same capability gate reports `E_LLM_DISABLED` when the local machine has no LLM key, while retaining `E_LLM_UNAVAILABLE` for a failed provider preflight. Both paths preserve the full checks and summary in `error.details`, so automation can distinguish configuration repair from an upstream retry without weakening the live-LLM gate.

As of 2026-07-29, the PyPI, npm, and crates.io package-search cases remain candidates. A live LLM preflight is still required before adapter packaging and online smoke work can count as promotion evidence.

As of v0.16.299, ordinary human `doctor` first asks for a live provider preflight before it presents `explore`; an explicit failed live preflight now prints the exact strict retry command, so users can repair the provider and pass the same gate before `explore`. Default doctor does not call a provider, so local configuration is not mistaken for live availability. Candidate promotion has a strict capability gate alongside semantic action replay and data-command evidence checks. Candidate evidence, promotion-plan JSON, and generated public issue templates remain executable-first: `primary_command`, the queue command, and the issue's Primary Evidence Task point to `cliany-site doctor --llm-live --require-capability generate_adapters --json` for `adapter_package`; an unavailable live provider exits nonzero while preserving the diagnostic payload for blocker evidence. `scripts/audit_candidate_issues.py` keeps already-open public candidate issues aligned with that current template through a read-only audit and an explicit reviewed rewrite; an unknown labeled issue is now an `unexpected` blocker rather than silently outside the report. The later explore command remains `task_command`. Explicit `cliany-site verify <domain> --json` now returns `ADAPTER_NOT_FOUND` rather than a successful empty result when that adapter is absent; a marketplace dry run remains only a package preflight, and a duplicate dry-run now returns its incoming `version`, `installed_version`, and `requires_force=true` as a read-only replacement plan rather than installation permission. `installed_version=null` is not an absence claim; `would_replace` remains the presence signal. Doctor now exposes `recommended_commands` for its active demo path and prints the same three copyable commands in its human output when the active demo is absent: fixed-SHA installation, `verify --strict`, then the read-only command. It never runs that path automatically; an occupied target still begins at strict verification and is not represented as healthy. Candidate handoffs now label a future adapter command as not runnable until the package is published, installed, and strictly verified, while the quickstart separates ordinary `doctor` output from JSON-only automation fields. Generated adapters now reject a missing or blank extract selector with `E_PARSE_FAILED`; when their JSON envelope has `ok=false`, they preserve that payload and exit nonzero, while an explicitly declared `expects_nonempty=false` empty result remains successful. Failed structured object-row extraction now adds optional `data.quality.field_blank_rows`, mapping each blank field to 1-based result row numbers so users can locate a field mapping or page-content problem without treating partial data as usable. Server and Docker docs now put the root `--headless` or `--cdp-url` option before both `explore` and `serve`, distinguish launching Chrome for an API service from connecting to an existing remote browser, and list `GET /health` as the service-reachability probe. The probe now also returns the installed service version, while `/doctor` remains the browser and provider readiness check. This is a reliability and handoff improvement, not evidence that any candidate has passed live LLM, packaging, or online smoke validation.

Planned outcomes:

- Promote package-search cases for PyPI, npm, and crates.io after adapter packages and read-only smoke checks are ready.
- Publish downloadable adapter assets that users can install and verify locally, including a pinned HTTPS install path when an asset is available.
- Keep candidate cases clearly labeled until release assets and online smoke evidence exist.
- Improve the public quickstart and website so users can pick a real demo without reading internal maintainer docs.
- Keep live LLM preflight failures visible as blockers instead of treating them as adapter evidence.

## Mid Term: 2026-08-06 to 2026-08-19

The next layer is adapter lifecycle and extraction reliability.

Planned outcomes:

- Make adapter packaging, installation, verification, rollback, and failure hints a documented loop.
- Expand structured extraction quality checks for search and list pages.
- Let generated list/search commands explicitly declare when zero matches are valid: `expects_nonempty=false` returns `ok=true` for that outcome while retaining `data.quality`; the default remains `true`, and the declaration survives later explore merges plus package installation.
- Make common failures easier to understand: LLM provider outage, Chrome/CDP connection, page readiness, selector mismatch, unexpected empty result, and partial data quality.
- Keep generated adapters safe by auditing code before it is written.

## Late Q3: 2026-08-20 to 2026-09-30

The final Q3 checkpoint is 1.0 alpha readiness.

Planned outcomes:

- Document which CLI, JSON envelope, adapter metadata, SDK, and HTTP API surfaces are stable enough to build on.
- Provide copy-paste SDK, HTTP API, headless, and remote CDP examples.
- Mark experimental areas clearly, including Obscura provider support and any remaining schema migration risks.
- Publish an alpha readiness report that lists remaining 1.0 blockers.

## What We Are Not Optimizing For

- Adding more browser or LLM providers before the current real workflows are more reliable.
- Hiding candidate or experimental features as if they were stable.
- Depending on real LLM keys in default PR checks.
- Falling back to brittle CSS selectors when AXTree semantics should drive replay.

## How To Track Progress

- Read [CHANGELOG.md](../CHANGELOG.md) for version-by-version changes.
- Run `cliany-site cases --json` to inspect maintained real-world cases.
- Use `cliany-site doctor --json` before local runs, and `cliany-site doctor --llm-live --require-capability generate_adapters --json` before LLM-backed exploration.
- Follow GitHub Releases and PyPI for published versions.
