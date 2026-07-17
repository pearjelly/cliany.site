# Market Publish Package Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release v0.16.265 so `cliany-site market publish --json` returns the SHA-256 needed to publish and install the exact generated adapter archive.

**Architecture:** Keep `pack_adapter`'s `Path` return contract unchanged. Add a tiny marketplace-owned digest helper that hashes a completed archive, then have the Click publish command add its result as `package_sha256` in the existing success envelope. Documentation treats that field as the handoff value for a verified GitHub Release asset and direct HTTPS installation.

**Tech Stack:** Python 3.11, Click, pytest, hashlib, existing JSON response helpers, static Vercel site.

## Global Constraints

- `package_sha256` is lowercase 64-character SHA-256 for the completed `.cliany-adapter.tar.gz` file, not `manifest.checksum` or a payload-file hash aggregate.
- Preserve `pack_adapter(domain, version, author) -> Path`, all existing response envelopes, root `--json`, and publish error codes.
- Do not change local/remote install, `--sha256` validation, dry-run, manifest validation, backup, rollback, generated adapters, or AXTree selector behavior.
- Runtime packages remain under `~/.cliany-site/`; all tests use temporary configuration or temporary HOME.
- Keep `pypi-project-search` as a blocked candidate while the live LLM preflight returns `E_LLM_UNAVAILABLE`; do not create case evidence or a release asset for it.
- Release `0.16.265` through the standard GitHub tag workflow, PyPI publication, Vercel `cliany.site` deployment, and remote publication audit.

---

## File Structure

- Modify `src/cliany_site/marketplace.py`: expose one package-file SHA-256 helper without altering `pack_adapter`'s return type.
- Modify `src/cliany_site/commands/market.py`: add `package_sha256` to successful publish response data.
- Modify `tests/test_marketplace.py`: cover direct and root JSON publish output plus unchanged missing-adapter error behavior.
- Modify `docs/adapter-lifecycle.md`, `README.md`, and `README.zh.md`: document the publish-to-remote-install digest handoff.
- Modify `site/index.html`, `site/script.js`, and `site/docs/index.html`: update the public maintainer baseline and digest handoff copy.
- Modify `tests/test_adapter_lifecycle_docs.py`, `tests/test_readme_current_features.py`, and `tests/test_site_content.py`: lock public wording and preserve the candidate boundary.
- Create `docs/releases/v0.16.265-draft.md`: record release value, scope, risk, validation, and release order.
- Modify `tests/test_release_draft_docs.py`, `CHANGELOG.md`, `pyproject.toml`, and `uv.lock`: prepare target-version metadata and its validated draft.

### Task 1: Return the Completed Package Digest From Market Publish

**Files:**
- Modify: `tests/test_marketplace.py:18-34,1163-1200`
- Modify: `src/cliany_site/marketplace.py:245-310`
- Modify: `src/cliany_site/commands/market.py:5-60`

**Interfaces:**
- Consumes: `_sha256_file(path: Path) -> str`, `pack_adapter(domain: str, version: str, author: str) -> Path`, and the existing `success_response` envelope.
- Produces: `package_sha256(pack_path: str | Path) -> str` and successful publish `data` with `domain`, `version`, `pack_path`, and `package_sha256`.

- [ ] **Step 1: Write failing CLI response tests**

Add the following tests to `TestMarketCLI` in `tests/test_marketplace.py` and import `ADAPTER_NOT_FOUND` from `cliany_site.errors`:

```python
    def test_publish_success_returns_exact_package_sha256(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        _create_adapter(cfg.adapters_dir, "cli-pub.com")

        result = self._invoke(["publish", "cli-pub.com", "--json"], cfg)

        assert result.exit_code == 0
        data = json.loads(result.output)["data"]
        pack_path = Path(data["pack_path"])
        expected = hashlib.sha256(pack_path.read_bytes()).hexdigest()
        assert data["package_sha256"] == expected
        assert len(data["package_sha256"]) == 64
        assert data["package_sha256"] == data["package_sha256"].lower()
        assert set(data["package_sha256"]) <= set("0123456789abcdef")

    def test_root_json_publish_returns_package_sha256(self, tmp_path: Path, tmp_home: Path) -> None:
        from cliany_site.cli import cli

        pack_path = tmp_path / "root-publish.cliany-adapter.tar.gz"
        pack_path.write_bytes(b"completed adapter archive")

        with patch("cliany_site.commands.market.pack_adapter", return_value=pack_path):
            result = CliRunner().invoke(cli, ["--json", "market", "publish", "root-publish.com"])

        assert result.exit_code == 0
        data = json.loads(result.output)["data"]
        assert data["package_sha256"] == hashlib.sha256(pack_path.read_bytes()).hexdigest()
        assert (tmp_home / ".cliany-site").exists()

    def test_publish_missing_adapter_keeps_adapter_not_found_envelope(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)

        result = self._invoke(["publish", "nope.com", "--json"], cfg)

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == ADAPTER_NOT_FOUND
```

- [ ] **Step 2: Run the new tests to confirm the missing field fails**

Run:

```bash
uv run --extra dev --frozen pytest \
  tests/test_marketplace.py::TestMarketCLI::test_publish_success_returns_exact_package_sha256 \
  tests/test_marketplace.py::TestMarketCLI::test_root_json_publish_returns_package_sha256 \
  tests/test_marketplace.py::TestMarketCLI::test_publish_missing_adapter_keeps_adapter_not_found_envelope \
  -q --no-cov --tb=short
```

Expected: the two success tests fail with `KeyError: 'package_sha256'`; the error-envelope regression already passes.

- [ ] **Step 3: Add the minimal shared helper and response field**

In `src/cliany_site/marketplace.py`, immediately after `_sha256_file`, add:

```python
def package_sha256(pack_path: str | Path) -> str:
    """Return the SHA-256 digest of one completed adapter package archive."""
    return _sha256_file(Path(pack_path))
```

In `src/cliany_site/commands/market.py`, import `package_sha256` with the other marketplace functions and replace the publish success response with:

```python
        pack_path = pack_adapter(domain, version=version, author=author)
        resp = success_response(
            {
                "domain": domain,
                "version": version,
                "pack_path": str(pack_path),
                "package_sha256": package_sha256(pack_path),
            }
        )
```

- [ ] **Step 4: Run targeted regressions and static checks**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_marketplace.py -q --no-cov --tb=short
uv run --extra dev --frozen ruff check src/cliany_site/marketplace.py src/cliany_site/commands/market.py tests/test_marketplace.py
uv run --extra dev --frozen mypy src/cliany_site/marketplace.py src/cliany_site/commands/market.py
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit the implementation**

```bash
git add src/cliany_site/marketplace.py src/cliany_site/commands/market.py tests/test_marketplace.py
git commit -m "feat(market): report package digest on publish"
```

### Task 2: Publish the Digest Handoff Contract in Docs and Website

**Files:**
- Modify: `docs/adapter-lifecycle.md:18-54`
- Modify: `README.md:353-387`
- Modify: `README.zh.md:358-391`
- Modify: `site/index.html:487-490`
- Modify: `site/script.js:172-176`
- Modify: `site/docs/index.html:108-150`
- Modify: `tests/test_adapter_lifecycle_docs.py`
- Modify: `tests/test_readme_current_features.py`
- Modify: `tests/test_site_content.py`

**Interfaces:**
- Consumes: publish success `data.package_sha256` from Task 1 and existing direct HTTPS `market install --sha256` safety contract.
- Produces: bilingual, asset-agnostic instructions that carry the exact published archive digest from source packaging into installation.

- [ ] **Step 1: Write failing content assertions**

Add a lifecycle assertion that requires `market publish github.com --version 1.0.0 --author "team" --json`, `package_sha256`, and the statement that it is the completed archive digest. Add a README assertion for both languages requiring `market publish github.com --version 1.0.0 --json`, `package_sha256`, and `--sha256 <64-hex-sha256>`. Extend the site test to require all of the following in the appropriate static files:

```python
assert "Current baseline: v0.16.265" in index
assert "当前基线：v0.16.265" in script
assert "market publish" in index
assert "package_sha256" in index
assert "v0.16.265 · Python" in docs
assert "package_sha256" in docs
assert "pypi-project-search" in index
assert "E_LLM_UNAVAILABLE" in index
```

- [ ] **Step 2: Run the documentation tests and confirm they fail**

Run:

```bash
uv run --extra dev --frozen pytest \
  tests/test_adapter_lifecycle_docs.py \
  tests/test_readme_current_features.py \
  tests/test_site_content.py \
  -q --no-cov --tb=short
```

Expected: new assertions fail because v0.16.265 and the publish digest handoff are not yet documented.

- [ ] **Step 3: Document the exact handoff without advertising an asset**

Update the lifecycle guide's packaging step to use `--json`, explain that `data.package_sha256` hashes the completed tarball, and use that output in the generic HTTPS installation example. Update both READMEs' marketplace examples with the same statement in their respective languages. Update the website maintainer copy and docs page from v0.16.264 to v0.16.265, include `market publish --json` and `package_sha256`, and retain the generic publisher URL and `<64-hex-sha256>` placeholder. Do not add a download link or change the PyPI candidate status.

- [ ] **Step 4: Run documentation regressions**

Run:

```bash
uv run --extra dev --frozen pytest \
  tests/test_adapter_lifecycle_docs.py \
  tests/test_readme_current_features.py \
  tests/test_site_content.py \
  -q --no-cov --tb=short
```

Expected: all documentation checks exit 0.

- [ ] **Step 5: Commit the public-contract update**

```bash
git add docs/adapter-lifecycle.md README.md README.zh.md site/index.html site/script.js site/docs/index.html \
  tests/test_adapter_lifecycle_docs.py tests/test_readme_current_features.py tests/test_site_content.py
git commit -m "docs: explain published adapter digests"
```

### Task 3: Prepare v0.16.265 Metadata and Release Draft

**Files:**
- Create: `docs/releases/v0.16.265-draft.md`
- Modify: `tests/test_release_draft_docs.py:11316-11380`
- Modify: `CHANGELOG.md:1-16,2520-2522`
- Modify: `pyproject.toml:7`
- Modify: `uv.lock`

**Interfaces:**
- Consumes: v0.16.265 feature/digest contract from Tasks 1-2 and the release sequence used by `v0.16.264-draft.md`.
- Produces: target-version package metadata, unreleased changelog entry, a readiness-valid release draft, and a synchronized lockfile.

- [ ] **Step 1: Write the failing release-draft contract test**

Add this test after the v0.16.264 draft tests:

```python
def test_v016265_release_draft_tracks_package_digest_handoff() -> None:
    text = (ROOT / "docs" / "releases" / "v0.16.265-draft.md").read_text(encoding="utf-8")

    required = [
        "# v0.16.265 发布草案",
        "**目标版本：** `0.16.265`",
        "**提交范围：** `v0.16.264..HEAD`",
        "package_sha256",
        "completed archive",
        "market publish",
        "--sha256",
        "pypi-project-search",
        "E_LLM_UNAVAILABLE",
        "git tag v0.16.265",
        "release_readiness.py --strict --target-version 0.16.265 --remote",
        "release_readiness.py --strict --release-tag v0.16.265 --remote --remote-name origin",
        "vercel inspect www.cliany.site --wait --timeout 90s",
        "check_release_publication.py --strict --remote --distribution --json",
    ]
    for snippet in required:
        assert snippet in text
```

- [ ] **Step 2: Run the draft test to confirm it fails**

Run:

```bash
uv run --extra dev --frozen pytest \
  tests/test_release_draft_docs.py::test_v016265_release_draft_tracks_package_digest_handoff \
  -q --no-cov --tb=short
```

Expected: failure because `docs/releases/v0.16.265-draft.md` does not exist.

- [ ] **Step 3: Add target metadata, draft, and unreleased changelog entry**

Set `project.version` to `0.16.265`, then run `uv lock` so `uv.lock` carries the same package version. Add an `[Unreleased]` `### Added` bullet stating that `market publish --json` emits `package_sha256` for the exact completed adapter archive, which publishers can carry to release-asset `market install --sha256` instructions.

Create a release draft modeled on `v0.16.264-draft.md` with the same sections and ordering. Its case section must state that the PyPI candidate remains blocked by `E_LLM_UNAVAILABLE`, and its release section must require target readiness before changelog finalization, then commit/push, tag readiness, tag push, GitHub Release/PyPI audit, Vercel deploy, and production alias inspect.

- [ ] **Step 4: Run metadata and release-draft checks**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_release_draft_docs.py -q --no-cov --tb=short
uv run --extra dev --frozen python scripts/release_readiness.py --strict --target-version 0.16.265
```

Expected: release-draft tests pass. The local target readiness command exits 0 once the source/version/changelog/draft are synchronized; remote availability is verified by the parent release gate.

- [ ] **Step 5: Commit release preparation**

```bash
git add CHANGELOG.md pyproject.toml uv.lock docs/releases/v0.16.265-draft.md tests/test_release_draft_docs.py
git commit -m "chore(release): prepare v0.16.265"
```

## Parent Release Gate

After all three tasks pass task-level review, the parent performs the integrated checks, finalizes `[Unreleased]` into `0.16.265`, pushes `master`, creates and validates tag `v0.16.265`, verifies GitHub Release and PyPI publication, deploys `site/` with `vercel link --yes --project cliany.site` and `vercel --prod --yes`, confirms `www.cliany.site`, and runs the strict remote publication audit. No external publication occurs on a failed or stale gate.
