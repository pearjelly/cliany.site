# First-success conversion design

**Date:** 2026-07-17

**Status:** Approved direction — ready for review
**Decision:** Prioritize a visitor's first verified success, then make product feedback and workflow proposals the natural next action.

## Context

`cliany-site` turns a browser workflow into a reusable CLI command. Its current README and site describe substantial capability, but a new visitor has to navigate historical release announcements, large feature inventories, and maintainer-oriented instructions before seeing a short, reliable first-run path.

The project needs two outcomes:

1. More visitors install the package and reach a meaningful, verifiable first result.
2. More users report friction and propose the workflows they want automated.

## Goals

- State the user benefit before implementation detail: turn a repeated browser task into a reusable command.
- Put a low-risk, copyable first-run path above long reference material.
- Offer a distinct next step for users who want to automate their own workflow.
- Make bug reports, feature requests, and read-only workflow proposals visible from both the README and the website.
- Keep English and Simplified Chinese content equivalent.
- Avoid claims tied to stale versions or release asset filenames.

## Non-goals

- Change CLI behavior, package release automation, or the case catalogue.
- Add telemetry, forms, authentication, or a new backend.
- Replace the current visual language or rewrite technical reference content that does not affect first-run conversion.

## Audience and conversion path

The primary audience is a technical user who repeatedly performs browser work and can run Python commands. The conversion path is deliberately small:

```text
Value proposition → install → doctor summary → choose a maintained demo or own workflow → report outcome
```

The first route has no requirement to configure an LLM before the visitor can inspect readiness and discover maintained examples. The second route is clearly labelled as requiring Chrome/CDP and an LLM provider. This prevents a missing key or browser configuration from looking like an installation failure.

## README changes

### Above the fold

1. Retain badges and language links.
2. Replace the historical release-announcement block with one short positioning statement, a one-sentence explanation, and two links: the first-success path and the release history.
3. Add a `Start here` section before `Features` with three commands:

   ```bash
   pip install cliany-site
   cliany-site doctor
   cliany-site cases
   ```

   The surrounding copy explains what each command confirms and links to the full 10-minute guide for a maintained demo or an own-workflow path.
4. Add a small `Tell us what happened` callout after the start section with separate links for a bug, a feature/requested automation, and a public read-only workflow proposal.

### Reference material

- Keep the existing detailed feature, API, marketplace, and maintainer material below the conversion content.
- Move version-specific material into the changelog/release links instead of repeating old release bullets at the top.
- Apply the same information architecture and feedback callout to `README.zh.md`, using natural Chinese rather than literal translation.

## Website changes

### Hero and navigation

- Refresh the title, description, and primary hero copy around a concrete outcome: make a repeated browser task reusable from the terminal.
- Make the primary CTA scroll to a new `Try it in minutes` section. The secondary CTA remains a repository link for users who want to inspect the project first.
- Add a `Feedback` navigation link that scrolls to the feedback section.
- Update document and social metadata to match the first-success message.

### First-success section

Insert a concise three-step section before the existing detailed quickstart:

1. Install from PyPI.
2. Run `cliany-site doctor` for a human-readable readiness summary.
3. Run `cliany-site cases` to discover maintained demos, then follow the linked 10-minute guide for the selected path.

Each command has a copy action. The copy explicitly distinguishes the demo route from generating a command for a visitor's own site, so prerequisites are not hidden.

### Feedback section

Add a closing section with three equal, plain-language actions:

- **Something broke** → GitHub bug-report form.
- **Want a capability or automation** → GitHub feature-request form.
- **Have a safe public workflow to share** → GitHub case-proposal form.

Every link opens in a new tab with safe `rel` attributes. The section includes a short expectation: reproducible steps or a target URL and expected result are the most helpful input. It does not create a separate submission system.

### Existing content

- Preserve the feature, use-case, and detailed technical sections, but keep them below the first-success route.
- Replace stale hard-coded adapter version text and filenames in the fast path with release-agnostic wording plus the maintained guide.
- Add all visible new copy, aria labels, and button states to the existing bilingual translation map.

## Data flow and failure handling

The page remains static. CTA interactions are anchors, copy buttons, and external GitHub links; no user data is collected.

- A user without an LLM key can still install, run `doctor`, and inspect `cases`.
- A user who cannot proceed finds a bug or feature route without needing to decode maintainer documentation.
- External links use durable GitHub issue-template URLs whose target filenames are stored in the repository.

## Acceptance criteria

1. Both README files lead with the current value proposition and a three-command first-success route; no historical v0.14 announcement block remains above it.
2. Both README files expose links to bug, feature, and case-proposal feedback forms.
3. The site hero's primary CTA points to the first-success section, and the navigation includes feedback.
4. The site contains a bilingual three-step first-success section and a bilingual three-option feedback section.
5. New site content has matching English and Chinese translation keys, accessible labels, and responsive styling.
6. All internal anchors, feedback links, README links, and command-copy values are checked after implementation.
7. The static site build/deployment validation succeeds before publication.

## Validation plan

- Inspect the rendered HTML for the expected first-success and feedback anchors in both languages.
- Check that every `data-i18n` key introduced in HTML exists in `site/script.js` for both locales.
- Check that each GitHub form URL maps to a tracked file under `.github/ISSUE_TEMPLATE/`.
- Verify README links and command blocks with a small non-mutating script or existing project validation tooling.
- Run the site's configured production validation before deployment, then publish only after it succeeds.

## Scope review

This design confines changes to user-facing copy, anchors, styles, translation keys, metadata, and documentation. It deliberately avoids product-runtime changes, telemetry, new dependencies, or changes to release infrastructure.
