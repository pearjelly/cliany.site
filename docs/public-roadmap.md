# cliany-site Public Roadmap

- **Updated:** 2026-08-07
- **Current baseline:** v0.16.305
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
