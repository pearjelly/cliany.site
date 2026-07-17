# v0.16.265 PyPI Case Promotion Design

**Date:** 2026-07-17
**Target version:** v0.16.265
**Status:** Approved under the standing autonomous release mandate.

## Problem

`pypi-project-search` is the highest-priority candidate in the case catalog,
but it has no generated adapter package, package-validation evidence, online
read-only smoke result, or published release asset. The public catalog must not
claim it is active until all three promotion evidence tasks are complete.

The previous release added verified HTTPS adapter installation, but the release
workflow publishes only the Python wheel and source distribution. A real demo
adapter must therefore be created from the live browser workflow, verified
locally, and attached explicitly to the GitHub Release that was created by the
tag workflow.

## Decision

Promote only `pypi-project-search` in v0.16.265. The promotion is gated by a
live LLM/CDP preflight, generated adapter package validation, a public
read-only PyPI search smoke, and a GitHub Release asset whose SHA-256 is pinned
in the documented installation command.

The release workflow remains responsible for the GitHub Release and PyPI
package publication. After it succeeds, the maintainer uploads the verified
adapter package to that same GitHub Release. This keeps the runtime-generated
asset out of the repository while making the published demo reproducible.

## Promotion Flow

1. Run `cliany-site doctor --llm-live --json` and capture its JSON under
   `/tmp`. Continue only when its preflight state is `ready` and adapter
   generation is ready.
2. Run the declared PyPI exploration workflow against `https://pypi.org`.
   The generated adapter remains in `~/.cliany-site/`; no runtime state is
   written to the repository.
3. Run `market publish pypi.org --version 0.16.265 --json`, calculate the
   archive SHA-256, and validate it with
   `validate_cases.py --include-candidate-packages --strict`.
4. Run the generated `pypi.org search-projects` command against PyPI and
   accept only a success envelope with `data.quality.ok=true` and a positive
   row count. Store a sanitized, representative response in the existing
   `cases/examples/` fixture; do not store cookies, tokens, local paths, or
   unrelated search results.
5. Update `cases/manifest.json` only after all three evidence tasks are
   complete: set status to `active`, set `source_release` to `v0.16.265`, and
   record the GitHub Release asset name, immutable download URL, SHA-256, and
   concise smoke summary as evidence. Update the cases README, both READMEs,
   public roadmap, and website to show the verified remote installation path.
6. Complete the normal v0.16.265 release workflow. Once its GitHub Release is
   published, upload the exact verified adapter archive to that release. Then
   run `market install <release-asset-url> --sha256 <digest> --dry-run --json`
   in an isolated runtime home to confirm that the public asset is installable
   without writing adapters or backups.

## Failure Behavior

If the LLM/CDP preflight is not ready, exploration, package creation, metadata
validation, or online smoke fails, do not create an adapter asset and do not
mark the case active. Capture the structured preflight or command evidence in
the case handoff output, keep the relevant evidence task `pending` or
`blocked`, and select a separate verified release slice instead of treating a
failed upstream call as proof of promotion.

No brittle CSS selector fallback, provider change, automatic package discovery,
or repository-local runtime artifact is in scope.

## Public Contract

The active-case installation command will use this shape:

```bash
cliany-site market install \
  https://github.com/pearjelly/cliany.site/releases/download/v0.16.265/pypi.org-0.16.265.cliany-adapter.tar.gz \
  --sha256 <64-hex-sha256> --dry-run --json
```

The case remains read-only: it searches public PyPI project cards and emits the
normal JSON envelope. The release asset URL is public, immutable for the tag,
and paired with an explicit digest; users are not asked to trust a `latest`
resolver or a local path from maintainer documentation.

## Tests And Release Gates

Focused tests cover the changed case manifest, candidate-to-active rules,
example response shape, documentation links, and release asset installation
contract. The full release must also pass:

```bash
python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --include-candidate-packages --strict
CLIANY_QA_OFFLINE=1 pytest tests/ -q
uv build --out-dir /tmp/cliany-site-v0.16.265-dist
uvx twine check /tmp/cliany-site-v0.16.265-dist/*
python scripts/release_readiness.py --strict --target-version 0.16.265 --remote
```

After the tag workflow and asset upload, the final audit verifies the GitHub
Release, PyPI `cliany-site==0.16.265`, the remote tag, the adapter asset's
digest-backed dry-run install, and the production website deployment.
