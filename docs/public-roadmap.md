# cliany-site Public Roadmap

- **Updated:** 2026-07-02
- **Current baseline:** v0.16.252
- **Maintainer roadmap:** [roadmap-2026-q3.md](roadmap-2026-q3.md)

cliany-site turns real browser workflows into reusable CLI commands. The Q3 roadmap focuses on making that path more reliable, easier to try, and easier to share.

## What Is Already In Place

- A 10-minute first-run path that starts with `doctor`, real demo cases, and replay before requiring users to configure an LLM.
- A real case catalog with CRM, DevOps, knowledge-base, and package-search workflows.
- Structured JSON envelopes for success and failure, including retryable LLM outage reporting through `E_LLM_UNAVAILABLE`.
- Adapter verification, marketplace packaging, metadata validation, and generated-code security checks.
- Release readiness and publication checks that keep GitHub Release, PyPI, CI, changelog, website publication, and case catalog validation tied together.

## Near Term: 2026-07-01 to 2026-07-07

The next focus is turning candidate real-world cases into verified active demos.

Planned outcomes:

- Promote package-search cases for PyPI, npm, and crates.io after adapter packages and read-only smoke checks are ready.
- Publish downloadable adapter assets that users can install and verify locally.
- Keep candidate cases clearly labeled until release assets and online smoke evidence exist.
- Improve the public quickstart and website so users can pick a real demo without reading internal maintainer docs.
- Keep live LLM preflight failures visible as blockers instead of treating them as adapter evidence.

## Mid Term: 2026-07-08 to 2026-07-28

The next layer is adapter lifecycle and extraction reliability.

Planned outcomes:

- Make adapter packaging, installation, verification, rollback, and failure hints a documented loop.
- Expand structured extraction quality checks for search and list pages.
- Make common failures easier to understand: LLM provider outage, Chrome/CDP connection, page readiness, selector mismatch, empty result, and partial data quality.
- Keep generated adapters safe by auditing code before it is written.

## Late Q3: 2026-07-29 to 2026-08-05

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
- Use `cliany-site doctor --json` before local runs, and `cliany-site doctor --llm-live --json` before LLM-backed exploration.
- Follow GitHub Releases and PyPI for published versions.
