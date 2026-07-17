# Market Publish Package Digest Design

**Status:** Approved on 2026-07-17 under the standing autonomous release mandate.

## Context

`v0.16.264` requires a fixed SHA-256 when installing an adapter package from a direct HTTPS URL. `cliany-site market publish` already computes the completed archive digest for its log line, but its JSON success envelope returns only the package path. A publisher or release automation therefore has to recalculate a value that the command already knows before it can publish a trustworthy `market install --sha256` instruction.

The scheduled PyPI case promotion remains blocked by the live LLM preflight (`E_LLM_UNAVAILABLE`). This release must improve the generic distribution path without changing that candidate's status or fabricating package evidence.

## Decision

Release `0.16.265` adds `package_sha256` to the successful JSON payload of `cliany-site market publish`.

The value is the lowercase, 64-character SHA-256 of the exact completed `.cliany-adapter.tar.gz` file at `pack_path`. It is not the manifest's `checksum` field and not an aggregate of the payload file hashes. The command computes it through a small marketplace-owned helper so command code does not reimplement byte hashing.

Example successful JSON data:

```json
{
  "domain": "github.com",
  "version": "1.0.0",
  "pack_path": "/home/user/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz",
  "package_sha256": "<64-lowercase-hex-digest>"
}
```

Publishers can attach that exact file to a GitHub Release and copy the digest into the public direct-HTTPS installation instruction. The release does not implement asset discovery, signing, registry lookup, automatic upload, or a new package format.

## Compatibility And Error Contract

- `pack_adapter(domain, version, author)` continues to return `Path`; external and internal callers keep their existing API.
- The non-JSON and root `--json` response conventions remain intact. Root JSON mode must expose the same added field.
- Missing adapters and operating-system failures retain their current `ADAPTER_NOT_FOUND` and `EXECUTION_FAILED` envelopes.
- Local installation, remote HTTPS restrictions, explicit `--sha256` validation, dry-run inspection, manifest validation, backup, and rollback behavior are out of scope.
- The `pypi-project-search` case remains `candidate`; no adapter archive, GitHub Release asset, online smoke result, or promotion evidence is added for it in this release.

## Documentation And Website

The lifecycle guide and both READMEs will show that `market publish --json` returns the archive digest and that this exact value is the one to publish with a remote install command. The website maintainer baseline will mention `v0.16.265` and the command-to-release-asset handoff without advertising an unavailable asset.

The release draft, changelog, package version, and lockfile will describe the field as a machine-readable handoff for verified package distribution. The normal GitHub Release, PyPI, Vercel production deployment, and publication audit remain required before claiming the version is published.

## Verification

Focused tests must prove:

1. A successful `market publish --json` payload contains `package_sha256` equal to an independently computed SHA-256 of the returned archive.
2. The digest is lowercase hexadecimal and exactly 64 characters.
3. Root `--json` produces the same field and the existing missing-adapter error envelope is unchanged.
4. Documentation and website tests lock the public wording without claiming a concrete candidate asset.

The release gate includes focused tests, the full offline suite, static checks, strict case validation, wheel/sdist validation, target/tag readiness, GitHub Release and PyPI audit, and Vercel inspection of `www.cliany.site`.
