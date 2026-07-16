# v0.16.264 Remote Adapter Package Install Design

**Date:** 2026-07-16
**Target version:** v0.16.264
**Status:** Approved under the standing autonomous release mandate.

## Problem

`cliany-site market install` accepts only a local package path. Existing tar safety, manifest, and payload-hash checks make a downloaded adapter package safe to validate, but a user cannot install a published release asset without manually downloading it first. Candidate promotion remains blocked by the live LLM preflight, so this release must improve an already usable lifecycle rather than fabricate candidate evidence.

## Decision

Extend `market install` to accept either a local path or one direct HTTPS adapter-package URL. A remote URL requires an explicit `--sha256` digest. The implementation downloads the archive to a system temporary file, verifies the complete archive SHA-256, then uses the existing inspection or installation path unchanged.

This release does not add release discovery, `latest` resolution, unsigned URL installation, GitHub API integration, adapter asset upload, candidate promotion, or changes to the existing install/rollback transaction behavior.

## CLI Contract

```text
cliany-site market install <source> [--sha256 <64-hex>] [--force] [--dry-run] [--json]
```

- `<source>` remains compatible with all current local package paths.
- A source with an `https` scheme is remote. It requires `--sha256`; a local path does not.
- HTTP, file, data, and other schemes are rejected before a request starts.
- `--sha256` accepts exactly 64 hexadecimal characters and is compared case-insensitively to the streamed archive digest.
- HTTPS redirects are permitted only when every redirect target is HTTPS. A redirect to any other scheme fails before the body is read.
- Remote responses are limited to 64 MiB. Both `Content-Length` and streamed bytes enforce the limit; a missing or misleading header cannot bypass it.
- `--dry-run` may perform the remote fetch because it must validate the exact bytes that a normal install would consume. It does not create the configured runtime home, adapters, sessions, backups, snapshots, or persistent download cache.
- The existing dry-run payload remains authoritative. `package_sha256` is the verified remote digest. The command does not expose a temporary filename or URL query/fragment values.
- A normal remote install downloads once, validates the digest, then delegates to the same existing local install path. Temporary data is removed on success and every failure path.

## Error Contract

All source validation, network, redirect, size, digest, archive, manifest, and install failures surface through the existing `INSTALL_FAILED` envelope.

- Invalid source scheme, missing remote digest, malformed digest, downgrade redirect, network error, and size limit failures use a focused user-facing message and existing install remediation.
- Digest mismatch reports expected versus actual SHA-256, but never includes a temporary path.
- Source URLs in messages redact query strings and fragments so signed asset links do not leak credentials.
- Existing local package errors, including corrupt tar/gzip normalization and post-validation install failures, retain their current messages and semantics.

## Architecture

`marketplace.py` owns a small source-resolution context manager. It returns a local archive path that is either the caller's original local path or a temporary verified remote download. The context manager owns only source acquisition and cleanup; it does not duplicate tar, manifest, payload, install, backup, or rollback logic.

`commands/market.py` keeps a single public `install` command. It parses `source`, validates the option shape through the marketplace boundary, invokes the resolver around `inspect_adapter_package` or `install_adapter`, and preserves root `--json` behavior and the established `INSTALL_FAILED` response handling.

The downloader uses Python's standard-library urllib facilities already used elsewhere in the repository. It streams in bounded chunks to a system temporary file while updating SHA-256. A dedicated HTTPS-only redirect handler and a small source-display helper prevent downgrade redirects and URL-secret leakage.

## Tests

Focused tests must cover:

1. Local paths remain backward compatible without `--sha256`.
2. Remote source rejects non-HTTPS, missing digest, malformed digest, and a downgrade redirect before installation.
3. A mocked HTTPS response with the correct digest reaches the same dry-run plan as a local package, uses `package_sha256`, and leaves no runtime-home or temporary file behind.
4. A digest mismatch, network failure, declared oversize response, streamed oversize response, corrupt archive, and malformed manifest return `INSTALL_FAILED` without adapter/backup writes.
5. A root CLI dry-run uses the actual root command and verifies no configured runtime directory is created.
6. Existing local archive integrity, post-yield installation errors, force/backup semantics, and rollback tests remain green.

## Documentation And Release

Update the adapter lifecycle guide and English/Chinese README marketplace examples with a generic publisher-provided HTTPS URL and pinned digest. Do not advertise an unavailable adapter asset or promote any candidate case. Add the v0.16.264 release draft, version bump, changelog entry, and website copy consistent with the public contract.

The standard release sequence remains: target readiness before changelog finalization, commit and push `master`, wait for CI, create and strict-check the local tag, push the tag, verify GitHub Release/PyPI, deploy `site/` to the `cliany.site` Vercel project, inspect `www.cliany.site`, and run the final publication audit.
