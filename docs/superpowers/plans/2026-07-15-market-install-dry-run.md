# Market Install Dry Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a zero-side-effect `cliany-site market install <package> --dry-run` preflight that validates a local adapter package and reports its real installation plan.

**Architecture:** Extract one context-managed package-validation reader in `marketplace.py`; both the existing installer and a new read-only inspector use that reader, so tar safety, manifest parsing and payload hashes cannot drift. The Click command chooses the inspector only when `--dry-run` is passed and keeps the existing success/error envelopes for normal installation.

**Tech Stack:** Python 3.11, Click, pytest, `tarfile`, existing `AdapterManifest`, existing JSON response helpers, static Vercel site.

## Global Constraints

- Preserve the existing `market install` behavior and response data when `--dry-run` is absent.
- Preflight must never write `~/.cliany-site/adapters/`, `~/.cliany-site/backups/`, sessions, snapshots or repository runtime state; tests must use the existing temporary configuration fixture.
- Continue to reject tar path traversal and validate every declared payload hash through `_validate_extracted_adapter_package`.
- Return package failures through the existing `INSTALL_FAILED` code and `_install_fix_hint`; do not introduce an error code or migrate the market response envelope.
- Keep user-facing help and documentation in the repository's Chinese/English conventions; generated adapter code and AXTree selector behavior are out of scope.
- Release `0.16.263` on 2026-07-15 through the existing tag workflow, GitHub Release, PyPI publish, and `site/` Vercel production deploy.

---

## File Structure

- Modify `src/cliany_site/marketplace.py`: centralize read-only package validation, calculate an installation plan, and expose `inspect_adapter_package`.
- Modify `src/cliany_site/commands/market.py`: add the `--dry-run` Click flag and route preflight through the existing response/error boundary.
- Modify `tests/test_marketplace.py`: cover inspector validation, intent fields, strict zero side effects and CLI JSON behavior.
- Modify `docs/adapter-lifecycle.md`, `README.md`, and `README.zh.md`: document preflight before an actual installation and update the command tables.
- Modify `site/index.html` and `site/script.js`: expose the preflight command in the current release baseline, including both translations.
- Modify `tests/test_readme_current_features.py` and `tests/test_site_content.py`: lock the documentation and website wording.
- Create `docs/releases/v0.16.263-draft.md`: describe release value, case status, verification, and publication steps.
- Modify `tests/test_release_draft_docs.py`: require the v0.16.263 release-draft contract.
- Modify `CHANGELOG.md`, `pyproject.toml`, and `uv.lock`: publish the `0.16.263` version and changelog entry.

### Task 1: Share Package Validation and Produce a Read-only Installation Plan

**Files:**
- Modify: `tests/test_marketplace.py`
- Modify: `src/cliany_site/marketplace.py`

**Interfaces:**
- Consumes: `AdapterManifest`, `_sha256_file(path: Path) -> str`, `_validate_extracted_adapter_package(manifest, tmp_path) -> None`, `get_config()`.
- Produces: `inspect_adapter_package(pack_path: str | Path, *, force: bool = False) -> dict[str, Any]`.
- Produces: `_validated_adapter_package(pack_path: str | Path) -> Iterator[tuple[AdapterManifest, Path, str]]`, whose yielded values are manifest, temporary extraction directory, and package SHA-256.

- [ ] **Step 1: Write the failing inspector tests**

Extend the marketplace import list and add these tests below `TestInstallAdapter`:

```python
from cliany_site.marketplace import inspect_adapter_package


class TestInspectAdapterPackage:
    def test_inspect_valid_new_package_has_no_runtime_side_effects(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "inspect-new.com", version="2.0.0")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            report = inspect_adapter_package(pack_path)

        assert report == {
            "dry_run": True,
            "package_sha256": _sha256_file(pack_path),
            "domain": "inspect-new.com",
            "version": "2.0.0",
            "files": ["commands.py", "metadata.json"],
            "would_replace": False,
            "would_create_backup": False,
        }
        assert not (cfg.adapters_dir / "inspect-new.com").exists()
        assert not (cfg.home_dir / "backups").exists()

    def test_inspect_force_reports_replace_without_writing_backup(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter(cfg.adapters_dir, "inspect-force.com", version="1.0.0")
        commands_before = (adapter_dir / "commands.py").read_bytes()
        pack_path = _make_tarball(tmp_path / "packs", "inspect-force.com", version="2.0.0")

        with patch("cliany_site.marketplace.get_config", return_value=cfg):
            report = inspect_adapter_package(pack_path, force=True)
            backups_after = list_backups("inspect-force.com")

        assert report["would_replace"] is True
        assert report["would_create_backup"] is True
        assert (adapter_dir / "commands.py").read_bytes() == commands_before
        assert backups_after == []

    def test_inspect_duplicate_without_force_raises_without_writing(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter(cfg.adapters_dir, "inspect-duplicate.com")
        commands_before = (adapter_dir / "commands.py").read_bytes()
        pack_path = _make_tarball(tmp_path / "packs", "inspect-duplicate.com")

        with patch("cliany_site.marketplace.get_config", return_value=cfg), pytest.raises(
            FileExistsError, match="已安装"
        ):
            inspect_adapter_package(pack_path)

        assert (adapter_dir / "commands.py").read_bytes() == commands_before
        assert not (cfg.home_dir / "backups").exists()

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"bad_hash": True}, "文件校验失败"),
            ({"path_traversal": True}, "不安全路径"),
        ],
    )
    def test_inspect_rejects_invalid_package_without_writing(
        self,
        tmp_path: Path,
        kwargs: dict[str, bool],
        message: str,
    ) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "inspect-invalid.com", **kwargs)

        with patch("cliany_site.marketplace.get_config", return_value=cfg), pytest.raises(
            ValueError, match=message
        ):
            inspect_adapter_package(pack_path)

        assert not (cfg.adapters_dir / "inspect-invalid.com").exists()
        assert not (cfg.home_dir / "backups").exists()
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_marketplace.py::TestInspectAdapterPackage -q --no-cov --tb=short
```

Expected: collection fails because `inspect_adapter_package` is not exported by `cliany_site.marketplace`.

- [ ] **Step 3: Implement the shared validated-package boundary and inspector**

In `src/cliany_site/marketplace.py`, import `Iterator` and add the following helpers before `install_adapter`:

```python
from collections.abc import Iterator


@contextlib.contextmanager
def _validated_adapter_package(
    pack_path: str | Path,
) -> Iterator[tuple[AdapterManifest, Path, str]]:
    archive_path = Path(pack_path)
    if not archive_path.exists():
        msg = f"安装包不存在: {archive_path}"
        raise FileNotFoundError(msg)

    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    msg = f"安装包包含不安全路径: {member.name}"
                    raise ValueError(msg)

            try:
                manifest_file = tar.extractfile("manifest.json")
                if manifest_file is None:
                    msg = "安装包缺少 manifest.json"
                    raise ValueError(msg)
                with manifest_file:
                    manifest_data = json.loads(manifest_file.read().decode("utf-8"))
            except KeyError:
                msg = "安装包缺少 manifest.json"
                raise ValueError(msg) from None

            manifest = AdapterManifest.from_dict(manifest_data)
            if not manifest.domain:
                msg = "manifest.json 缺少 domain 字段"
                raise ValueError(msg)

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                tar.extractall(tmp_path, filter="data")  # noqa: S202
                _validate_extracted_adapter_package(manifest, tmp_path)
                yield manifest, tmp_path, _sha256_file(archive_path)
    except tarfile.TarError as exc:
        msg = f"安装包无法读取: {archive_path}"
        raise ValueError(msg) from exc


def _adapter_install_target(
    manifest: AdapterManifest,
    *,
    force: bool,
) -> tuple[Path, bool]:
    cfg = get_config()
    adapter_dir = cfg.adapters_dir / manifest.domain
    would_replace = adapter_dir.exists()
    if would_replace and not force:
        existing_version = _get_installed_version(manifest.domain)
        version_detail = f" (版本 {existing_version})" if existing_version else ""
        msg = (
            f"adapter '{manifest.domain}' 已安装{version_detail}。"
            "使用 --force 覆盖安装，或先卸载。"
        )
        raise FileExistsError(msg)
    return adapter_dir, would_replace


def inspect_adapter_package(
    pack_path: str | Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """校验 adapter 分发包并报告安装计划，不写入运行时状态。"""
    with _validated_adapter_package(pack_path) as (manifest, _tmp_path, package_sha256):
        _adapter_dir, would_replace = _adapter_install_target(manifest, force=force)
        return {
            "dry_run": True,
            "package_sha256": package_sha256,
            "domain": manifest.domain,
            "version": manifest.version,
            "files": sorted(manifest.files),
            "would_replace": would_replace,
            "would_create_backup": would_replace and force,
        }
```

Replace the body of `install_adapter` with the shared validation and conflict plan, retaining its return type and copy logic:

```python
    with _validated_adapter_package(pack_path) as (manifest, tmp_path, _package_sha256):
        adapter_dir, would_replace = _adapter_install_target(manifest, force=force)

        if would_replace:
            _create_backup(manifest.domain)
            shutil.rmtree(adapter_dir)
        adapter_dir.mkdir(parents=True, exist_ok=True)

        for filename in manifest.files:
            shutil.copy2(str(tmp_path / filename), str(adapter_dir / filename))

        manifest_dest = adapter_dir / "manifest.json"
        manifest_dest.write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    logger.info(
        "adapter 已安装: domain=%s version=%s",
        manifest.domain,
        manifest.version,
    )
    return manifest
```

- [ ] **Step 4: Run inspector and existing install regression tests**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_marketplace.py::TestInspectAdapterPackage tests/test_marketplace.py::TestInstallAdapter -q --no-cov --tb=short
```

Expected: all selected tests pass; the force-install backup test still observes one backup while all inspector tests observe no adapter mutation or backup.

- [ ] **Step 5: Commit the runtime behavior and direct tests**

```bash
git add src/cliany_site/marketplace.py tests/test_marketplace.py
git commit -m "feat(market): add package install dry run"
```

### Task 2: Expose `--dry-run` Through the Market CLI

**Files:**
- Modify: `tests/test_marketplace.py`
- Modify: `src/cliany_site/commands/market.py`

**Interfaces:**
- Consumes: `inspect_adapter_package(pack_path, force=force) -> dict[str, Any]` from Task 1.
- Produces: `cliany-site market install <pack_path> --dry-run [--force] [--json]` using the existing `success_response` and `INSTALL_FAILED` boundary.

- [ ] **Step 1: Write the failing CLI tests**

Add these methods to `TestMarketCLI`:

```python
    def test_install_dry_run_returns_package_plan(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        pack_path = _make_tarball(tmp_path / "packs", "cli-dry-run.com", version="2.0.0")

        result = self._invoke(["install", str(pack_path), "--dry-run", "--json"], cfg)

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["dry_run"] is True
        assert data["data"]["domain"] == "cli-dry-run.com"
        assert data["data"]["version"] == "2.0.0"
        assert data["data"]["would_replace"] is False
        assert data["data"]["would_create_backup"] is False
        assert not (cfg.adapters_dir / "cli-dry-run.com").exists()

    def test_install_dry_run_duplicate_uses_install_failed_envelope(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter(cfg.adapters_dir, "cli-dry-duplicate.com")
        commands_before = (adapter_dir / "commands.py").read_bytes()
        pack_path = _make_tarball(tmp_path / "packs", "cli-dry-duplicate.com")

        result = self._invoke(["install", str(pack_path), "--dry-run", "--json"], cfg)

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INSTALL_FAILED"
        assert "--force" in data["error"]["fix"]
        assert (adapter_dir / "commands.py").read_bytes() == commands_before
        assert not (cfg.home_dir / "backups").exists()
```

- [ ] **Step 2: Run the new CLI tests to verify they fail**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_marketplace.py::TestMarketCLI::test_install_dry_run_returns_package_plan tests/test_marketplace.py::TestMarketCLI::test_install_dry_run_duplicate_uses_install_failed_envelope -q --no-cov --tb=short
```

Expected: both tests fail because Click reports `No such option: --dry-run`.

- [ ] **Step 3: Add the Click option and response branch**

Update the marketplace import and `install_cmd` in `src/cliany_site/commands/market.py`:

```python
from cliany_site.marketplace import (
    get_adapter_info,
    inspect_adapter_package,
    install_adapter,
    list_backups,
    pack_adapter,
    rollback_adapter,
    uninstall_adapter,
)


@market_group.command("install")
@click.argument("pack_path", type=click.Path(exists=True))
@click.option("--force", is_flag=True, default=False, help="强制覆盖已安装版本")
@click.option("--dry-run", is_flag=True, default=False, help="仅校验包与安装计划，不写入运行时状态")
@click.option("--json", "json_mode", is_flag=True, default=False, help="JSON 输出")
@click.pass_context
def install_cmd(
    ctx: click.Context,
    pack_path: str,
    force: bool,
    dry_run: bool,
    json_mode: bool,
) -> None:
    """从分发包安装适配器，或预检安装计划。"""
    root = ctx.find_root()
    jm = json_mode or (isinstance(root.obj, dict) and root.obj.get("json_mode", False))

    try:
        if dry_run:
            resp = success_response(inspect_adapter_package(pack_path, force=force))
        else:
            manifest = install_adapter(pack_path, force=force)
            resp = success_response(manifest.to_dict())
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        resp = error_response(INSTALL_FAILED, str(exc), _install_fix_hint(str(exc)))
    except OSError as exc:
        resp = error_response(INSTALL_FAILED, str(exc), ERROR_FIX_HINTS[INSTALL_FAILED])

    print_response(resp, json_mode=jm)
```

- [ ] **Step 4: Run all marketplace tests**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_marketplace.py -q --no-cov --tb=short
```

Expected: all marketplace unit and CLI integration tests pass, including non-dry-run behavior.

- [ ] **Step 5: Commit the CLI contract**

```bash
git add src/cliany_site/commands/market.py tests/test_marketplace.py
git commit -m "feat(cli): expose market install dry run"
```

### Task 3: Document the Preflight in Lifecycle Guides and the Official Website

**Files:**
- Modify: `tests/test_readme_current_features.py`
- Modify: `tests/test_site_content.py`
- Modify: `docs/adapter-lifecycle.md`
- Modify: `README.md`
- Modify: `README.zh.md`
- Modify: `site/index.html`
- Modify: `site/script.js`

**Interfaces:**
- Consumes: the stable CLI contract from Task 2 and its `dry_run`, `package_sha256`, `would_replace`, and `would_create_backup` fields.
- Produces: user-facing instructions that prescribe preflight before a real installation and state that preflight does not mutate adapters or backups.

- [ ] **Step 1: Write the failing documentation and website assertions**

Add this focused README test to `tests/test_readme_current_features.py`:

```python
def test_readmes_document_adapter_package_preflight() -> None:
    expected = {
        "README.md": "cliany-site market install ~/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz --dry-run --json",
        "README.zh.md": "cliany-site market install ~/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz --dry-run --json",
    }
    for filename, command in expected.items():
        text = (ROOT / filename).read_text(encoding="utf-8")
        assert command in text
        assert "[--force] [--dry-run] [--json]" in text
```

In `tests/test_site_content.py`, replace both baseline assertions and add the command assertions:

```python
    assert "Current baseline: v0.16.263" in index
    assert "cliany-site market install &lt;package&gt; --dry-run --json" in index
    assert "Current baseline: v0.16.263" in script
    assert "cliany-site market install &lt;package&gt; --dry-run --json" in script
```

- [ ] **Step 2: Run the documentation tests to verify they fail**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_readme_current_features.py tests/test_site_content.py -q --no-cov --tb=short
```

Expected: failures identify the absent dry-run command and the outdated `v0.16.262` website baseline.

- [ ] **Step 3: Update lifecycle documentation, both READMEs, and site translations**

Make these concrete content changes:

```markdown
# docs/adapter-lifecycle.md, before the real install command
cliany-site market install ~/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz --dry-run --json
# Review dry_run, package_sha256, files, would_replace and would_create_backup.
# This preflight only uses a temporary extraction directory and does not write adapters or backups.
cliany-site market install ~/.cliany-site/packages/github.com-1.0.0.cliany-adapter.tar.gz --json
```

Add the same preflight command before the real install example in the adapter-market sections of `README.md` and `README.zh.md`; change both command-table entries to `market install <path> | [--force] [--dry-run] [--json]`.

In `site/index.html`, change the maintainer baseline text to `Current baseline: v0.16.263.` and append this HTML-safe command sentence:

```html
Use <code>cliany-site market install &lt;package&gt; --dry-run --json</code> to validate a local adapter package and inspect replacement or backup intent before installation.
```

In `site/script.js`, set the matching `qs.maintainer.desc` translation values to `v0.16.263` and include the exact same HTML command. The Chinese text must state that the command validates a local package and only checks whether replacement or backup would occur; it must not claim that preflight downloads, installs, or creates a backup.

- [ ] **Step 4: Run documentation, website, and marketplace regression tests**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_marketplace.py tests/test_readme_current_features.py tests/test_site_content.py -q --no-cov --tb=short
```

Expected: all selected tests pass and both website translation sources contain the same dry-run command.

- [ ] **Step 5: Commit the user-facing documentation**

```bash
git add docs/adapter-lifecycle.md README.md README.zh.md site/index.html site/script.js tests/test_readme_current_features.py tests/test_site_content.py
git commit -m "docs: document adapter install preflight"
```

### Task 4: Prepare, Verify, and Publish v0.16.263

**Files:**
- Create: `docs/releases/v0.16.263-draft.md`
- Modify: `tests/test_release_draft_docs.py`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

**Interfaces:**
- Consumes: completed runtime, CLI, documentation, and website behavior from Tasks 1-3.
- Produces: package metadata version `0.16.263`, tag `v0.16.263`, GitHub Release assets, PyPI `cliany-site==0.16.263`, and an inspected Vercel production deployment for `www.cliany.site`.

- [ ] **Step 1: Write the failing release-draft test**

Add this test at the end of `tests/test_release_draft_docs.py`:

```python
def test_v016263_release_draft_tracks_market_install_dry_run() -> None:
    text = (ROOT / "docs" / "releases" / "v0.16.263-draft.md").read_text(
        encoding="utf-8"
    )

    required = [
        "market install <package> --dry-run",
        "package_sha256",
        "would_replace",
        "would_create_backup",
        "INSTALL_FAILED",
        "~/.cliany-site/backups/",
        "cases/README.md",
        "cases/manifest.json",
        "search-extraction-gap",
        "llm_live_preflight_not_ready",
        "git tag v0.16.263",
        "vercel inspect www.cliany.site --wait --timeout 90s",
        "check_release_publication.py --remote --distribution --json",
    ]
    for snippet in required:
        assert snippet in text
```

- [ ] **Step 2: Run the release-draft test to verify it fails**

Run:

```bash
uv run --extra dev --frozen pytest tests/test_release_draft_docs.py::test_v016263_release_draft_tracks_market_install_dry_run -q --no-cov --tb=short
```

Expected: FAIL with `FileNotFoundError` for `docs/releases/v0.16.263-draft.md`.

- [ ] **Step 3: Add release materials and update package version**

Create `docs/releases/v0.16.263-draft.md` with the required release-readiness sections and these factual release constraints:

```markdown
# v0.16.263 发布草案

**目标版本：** `0.16.263`
**提交范围：** `v0.16.262..HEAD`
**当前状态：** 2026-07-15 release execution；本版在安装前提供本地 adapter 包的只读校验与覆盖计划。

## 用户价值

`cliany-site market install <package> --dry-run --json` 复用真实安装的 tar 安全、manifest 与文件哈希校验，并返回 `package_sha256`、`would_replace` 与 `would_create_backup`。预检仅在临时目录解压，不会写入 `~/.cliany-site/adapters/` 或 `~/.cliany-site/backups/`。
```

The draft must also include `## 案例库映射`, `## 风险与兼容性`, `## 发版前验证`, and `## 发版步骤`; it must state that `pypi-project-search` remains a candidate because `llm_live_preflight_not_ready` still blocks real exploration, and it must name `cases/README.md`, `cases/manifest.json`, and `search-extraction-gap`.

Under `[Unreleased]` in `CHANGELOG.md`, add an `Added` entry for dry-run package validation and zero-side-effect replacement/backup intent. Update the project version to `0.16.263` in `pyproject.toml`, then run the lock command below so its editable-package version in `uv.lock` stays synchronized:

```bash
uv lock --offline
```

- [ ] **Step 4: Run release-focused validation and build the distribution**

Run:

```bash
git diff --check
uv run --extra dev --frozen ruff check src/cliany_site/marketplace.py src/cliany_site/commands/market.py tests/test_marketplace.py tests/test_readme_current_features.py tests/test_site_content.py tests/test_release_draft_docs.py
uv run --extra dev --frozen pytest tests/test_marketplace.py tests/test_readme_current_features.py tests/test_site_content.py tests/test_release_draft_docs.py -q --no-cov
uv run --extra dev --frozen python scripts/validate_cases.py --strict
CLIANY_QA_OFFLINE=1 uv run --extra dev --frozen pytest tests/ -q
uv build --out-dir /tmp/cliany-site-v0.16.263-dist
uvx twine check /tmp/cliany-site-v0.16.263-dist/*
uv run --extra dev --frozen python scripts/release_readiness.py --strict --target-version 0.16.263 --remote
```

Expected: formatting, focused tests, full offline suite, case validation, wheel/sdist metadata and target-version readiness all pass. Do not proceed to a tag if any command fails.

- [ ] **Step 5: Commit the release preparation and publish branch and tag**

```bash
git add CHANGELOG.md pyproject.toml uv.lock docs/releases/v0.16.263-draft.md tests/test_release_draft_docs.py docs/superpowers/plans/2026-07-15-market-install-dry-run.md
git commit -m "chore(release): prepare v0.16.263"
git push origin master
CI_RUN_ID="$(gh run list --workflow ci.yml --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId')"
gh run watch "$CI_RUN_ID" --exit-status
git tag v0.16.263
uv run --extra dev --frozen python scripts/release_readiness.py --strict --release-tag v0.16.263 --remote --remote-name origin
git push origin v0.16.263
RELEASE_RUN_ID="$(gh run list --workflow release.yml --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId')"
gh run watch "$RELEASE_RUN_ID" --exit-status
```

Expected: branch CI succeeds before the tag, the release workflow creates the GitHub Release and publishes `cliany-site==0.16.263` to PyPI, and the release-tag readiness gate remains green.

- [ ] **Step 6: Deploy and verify the official website and public release**

Run:

```bash
cd site
vercel link --yes --project cliany.site
vercel --prod --yes
vercel inspect www.cliany.site --wait --timeout 90s
cd ..
uv run --extra dev --frozen python scripts/check_release_publication.py --strict --remote --distribution --json
git status --short --branch
```

Expected: `www.cliany.site` points at the inspected production deployment; the final audit reports the matching GitHub Release, PyPI version `0.16.263`, published branch/tag and a clean worktree.
