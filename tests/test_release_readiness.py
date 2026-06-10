import hashlib
import importlib.util
import json
import subprocess
import sys
import tarfile
from datetime import date
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SCRIPT = SCRIPTS / "release_readiness.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("release_readiness", SCRIPT)
assert SPEC is not None
release_readiness = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = release_readiness
SPEC.loader.exec_module(release_readiness)

RELEASE_PREFLIGHT_COMMAND = (
    "python scripts/release_readiness.py --strict "
    '--release-tag "${{ github.ref_name }}" '
    "--report release-readiness-report.md"
)


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.check_call(["git", *args], cwd=repo, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _commit(repo: Path, filename: str, content: str, day: str) -> None:
    path = repo / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(repo, "add", filename)
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": f"{day}T12:00:00+00:00",
        "GIT_COMMITTER_DATE": f"{day}T12:00:00+00:00",
    }
    _git(repo, "commit", "-m", f"test {day}", env=env)


def _release_draft(target_version: str, current_version: str) -> str:
    return f"""# v{target_version} 发布草案

**状态：** draft
**目标版本：** `{target_version}`
**提交范围：** `v{current_version}..HEAD`

## 用户价值

- Demo release value.

## 案例库映射

- cases/README.md
- cases/manifest.json
- search-extraction-gap

## 风险与兼容性

- No compatibility risk.

## 发版前验证

```bash
python scripts/release_readiness.py --strict
```

## 发版步骤

1. Run release readiness.
"""


def _ci_workflow() -> str:
    return """name: CI

jobs:
  case-catalog:
    name: Case Catalog Validation
    steps:
      - run: |
          python scripts/validate_cases.py --strict --report case-catalog-report.md
          pytest tests/test_validate_cases.py tests/test_cases_manifest.py -q --no-cov
        env:
          CLIANY_QA_OFFLINE: "1"
      - uses: actions/upload-artifact@v4
        with:
          name: case-catalog-report
          path: case-catalog-report.md

  release-readiness:
    name: Release Readiness Report
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - run: |
          python scripts/release_readiness.py --json --report release-readiness-report.md
        env:
          CLIANY_QA_OFFLINE: "1"
      - uses: actions/upload-artifact@v4
        with:
          name: release-readiness-report
          path: release-readiness-report.md

  extract-quality:
    name: Extract Quality Regression
    steps:
      - run: |
          pytest \
            tests/test_extract_quality.py \
            tests/test_extract_writer_quality.py \
            tests/test_runtime_helpers_extract_quality.py \
            tests/test_browser_part_c.py \
            tests/test_generated_orchestration.py \
            tests/test_search_extraction_gap_fixture.py \
            -q --no-cov
        env:
          CLIANY_QA_OFFLINE: "1"
"""


def _release_workflow() -> str:
    return """name: Release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write
  id-token: write

jobs:
  ci:
    uses: ./.github/workflows/ci.yml

  release-preflight:
    name: Release Preflight
    needs: ci
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - run: |
          __RELEASE_PREFLIGHT_COMMAND__
        env:
          CLIANY_QA_OFFLINE: "1"
      - uses: actions/upload-artifact@v4
        with:
          name: release-readiness-report
          path: release-readiness-report.md

  build:
    name: Build Distribution
    needs: [ci, release-preflight]
    steps:
      - run: rm -rf dist
      - run: uv build
      - run: uvx twine check dist/*
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  github-release:
    name: GitHub Release
    needs: build
    steps:
      - run: gh release create "${{ github.ref_name }}" dist/* --generate-notes

  pypi-publish:
    name: Publish to PyPI
    needs: build
    environment:
      name: pypi
      url: https://pypi.org/p/cliany-site
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
""".replace("__RELEASE_PREFLIGHT_COMMAND__", RELEASE_PREFLIGHT_COMMAND)


def _cases_manifest() -> str:
    return json.dumps(
        [
            {
                "id": "demo-case",
                "title": "Demo case",
                "category": "demo",
                "status": "active",
                "target_url": "https://demo.example.com/",
                "adapter_domain": "demo.example.com",
                "source_release": "v0.1.0",
                "docs": "README.md#demo",
                "example_output": "cases/examples/demo-case.json",
                "commands": [
                    "cliany-site market install ./demo.example.com.cliany-adapter-v0.1.0.tar.gz",
                    "cliany-site demo.example.com list-items --json",
                ],
                "validation": {
                    "offline": "metadata validates",
                    "online": "read-only command returns rows",
                },
            }
        ],
        ensure_ascii=False,
    )


def _write_package(packages_dir: Path, filename: str, *, domain: str) -> None:
    packages_dir.mkdir(parents=True, exist_ok=True)
    commands_content = b"import click\n\n@click.group()\ndef cli():\n    pass\n"
    metadata_content = json.dumps(
        {
            "schema_version": 3,
            "domain": domain,
            "generated_at": "2026-06-10T00:00:00Z",
            "generator_version": "test",
            "commands": [{"name": "list-items"}],
        }
    ).encode("utf-8")
    manifest = {
        "manifest_version": "1",
        "domain": domain,
        "files": ["commands.py", "metadata.json"],
        "file_hashes": {
            "commands.py": hashlib.sha256(commands_content).hexdigest(),
            "metadata.json": hashlib.sha256(metadata_content).hexdigest(),
        },
    }

    with tarfile.open(packages_dir / filename, "w:gz") as tar:
        manifest_content = json.dumps(manifest).encode("utf-8")
        manifest_info = tarfile.TarInfo(name="manifest.json")
        manifest_info.size = len(manifest_content)
        tar.addfile(manifest_info, BytesIO(manifest_content))

        commands_info = tarfile.TarInfo(name="commands.py")
        commands_info.size = len(commands_content)
        tar.addfile(commands_info, BytesIO(commands_content))

        metadata_info = tarfile.TarInfo(name="metadata.json")
        metadata_info.size = len(metadata_content)
        tar.addfile(metadata_info, BytesIO(metadata_content))


def _template_content(filename: str) -> str:
    return {
        ".github/PULL_REQUEST_TEMPLATE.md": (
            "python scripts/validate_cases.py --strict\n"
            "python scripts/release_readiness.py --json\n"
            "CLIANY_QA_OFFLINE=1\n"
            "~/.cliany-site/\n"
        ),
        ".github/ISSUE_TEMPLATE/bug_report.yml": (
            "id: target_url\n"
            "id: error_code\n"
            "id: axtree_snapshot\n"
            "id: doctor_output\n"
        ),
        ".github/ISSUE_TEMPLATE/feature_request.yml": (
            "id: problem\n"
            "id: solution\n"
            "id: checklist\n"
        ),
        ".github/ISSUE_TEMPLATE/case_proposal.yml": (
            'labels: ["case-proposal"]\n'
            "id: target_url\n"
            "id: expected_command\n"
            "id: example_output\n"
            "python scripts/validate_cases.py --strict\n"
            "degraded\n"
        ),
    }[filename]


def _init_repo(tmp_path: Path, *, with_draft: bool) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / "cases").mkdir()
    (repo / "docs" / "releases").mkdir(parents=True)
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    for filename in ("LICENSE", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "SUPPORT.md"):
        (repo / filename).write_text(f"# {filename}\n", encoding="utf-8")
    for filename in (
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/case_proposal.yml",
    ):
        (repo / filename).write_text(_template_content(filename), encoding="utf-8")
    (repo / "pyproject.toml").write_text(
        '[project]\n'
        'name = "demo"\n'
        'version = "0.1.0"\n'
        'description = "Demo package."\n'
        'readme = "README.md"\n\n'
        '[project.urls]\n'
        'Homepage = "https://demo.example.com"\n'
        'Repository = "https://github.com/example/demo"\n'
        'Changelog = "https://github.com/example/demo/blob/main/CHANGELOG.md"\n',
        encoding="utf-8",
    )
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Added\n"
        "- Pending release note.\n\n"
        "## [0.1.0] - 2026-06-08\n\n"
        "[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.1.0...HEAD\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# Demo\n\n## demo\n", encoding="utf-8")
    (repo / "cases" / "manifest.json").write_text(_cases_manifest(), encoding="utf-8")
    (repo / "cases" / "examples").mkdir()
    (repo / "cases" / "examples" / "demo-case.json").write_text(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "command": "list-items",
                    "results": [{"ok": True, "data": {"items": [{"name": "Example"}]}}],
                },
                "error": None,
                "meta": {
                    "source": "case-example",
                    "case_id": "demo-case",
                    "sample": True,
                },
            }
        ),
        encoding="utf-8",
    )
    (repo / ".github" / "workflows" / "ci.yml").write_text(_ci_workflow(), encoding="utf-8")
    (repo / ".github" / "workflows" / "release.yml").write_text(_release_workflow(), encoding="utf-8")
    if with_draft:
        (repo / "docs" / "releases" / "v0.1.1-draft.md").write_text(
            _release_draft("0.1.1", "0.1.0"),
            encoding="utf-8",
        )
    _git(
        repo,
        "add",
        "pyproject.toml",
        "CHANGELOG.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "SUPPORT.md",
        "README.md",
        "cases/manifest.json",
        "cases/examples/demo-case.json",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/case_proposal.yml",
    )
    if with_draft:
        _git(repo, "add", "docs/releases/v0.1.1-draft.md")
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": "2026-06-08T12:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-06-08T12:00:00+00:00",
    }
    _git(repo, "commit", "-m", "initial", env=env)
    _git(repo, "tag", "v0.1.0")
    return repo


def test_release_readiness_passes_for_minimal_ready_repo(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    _commit(repo, "notes/tuesday.md", "tuesday", "2026-06-09")
    _commit(repo, "notes/wednesday.md", "wednesday", "2026-06-10")

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

    assert report.ok is True
    assert report.current_version == "0.1.0"
    assert report.target_version == "0.1.1"
    assert report.blockers == []
    assert report.cadence.ok is True
    assert report.cases.ok is True
    assert report.draft.ok is True
    assert report.ci.ok is True
    assert report.release_workflow.ok is True
    assert report.project_metadata.ok is True
    assert report.package_gate.ok is True
    assert report.package_gate.required is False
    assert report.package_gate.checked is False


def test_release_readiness_writes_markdown_report(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    _commit(repo, "notes/tuesday.md", "tuesday", "2026-06-09")
    _commit(repo, "notes/wednesday.md", "wednesday", "2026-06-10")
    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=3)
    report_path = tmp_path / "reports" / "release-readiness.md"

    release_readiness._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "# cliany-site Release Readiness" in text
    assert "| ok | `true` |" in text
    assert "| target_version | `0.1.1` |" in text
    assert "| cadence | `true` | commit days `3/3`: 2026-06-08, 2026-06-09, 2026-06-10 |" in text
    assert "| release_workflow | `true` |" in text
    assert "| project_metadata | `true` |" in text
    assert "https://github.com/pearjelly/cliany.site/compare/v0.1.0...HEAD" in text


def test_release_readiness_markdown_report_includes_gate_issues(tmp_path):
    repo = _init_repo(tmp_path, with_draft=False)
    (repo / "LICENSE").unlink()
    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=3)
    report_path = tmp_path / "reports" / "release-readiness.md"

    release_readiness._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "## Gate Issues" in text
    assert "- `cadence`: commit days 1/3" in text
    assert "- `draft`: release draft is missing" in text
    assert "- `project_metadata`: open source metadata file is missing: LICENSE" in text


def test_release_readiness_blocks_missing_release_draft(tmp_path):
    repo = _init_repo(tmp_path, with_draft=False)

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release draft validation failed" in report.blockers
    assert report.draft.ok is False
    assert report.draft.issues == ["release draft is missing"]


def test_release_readiness_blocks_stale_changelog_compare_link(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Added\n"
        "- Pending release note.\n\n"
        "## [0.1.0] - 2026-06-08\n\n"
        "[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.0.9...HEAD\n",
        encoding="utf-8",
    )

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert any("CHANGELOG Unreleased compare link is stale" in blocker for blocker in report.blockers)
    assert report.cadence.changelog_unreleased_compare_ok is False


def test_release_readiness_blocks_missing_ci_extract_gate(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        "name: CI\njobs:\n  case-catalog:\n    name: Case Catalog Validation\n",
        encoding="utf-8",
    )

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "CI release gates validation failed" in report.blockers
    assert report.ci.ok is False
    assert any("extract-quality:" in issue for issue in report.ci.issues)


def test_release_readiness_blocks_missing_release_workflow_pypi_publish(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / ".github" / "workflows" / "release.yml").write_text(
        "name: Release\non:\n  push:\n    tags: [\"v*\"]\n",
        encoding="utf-8",
    )

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release workflow validation failed" in report.blockers
    assert report.release_workflow.ok is False
    assert any("pypa/gh-action-pypi-publish@release/v1" in issue for issue in report.release_workflow.issues)


def test_release_readiness_blocks_missing_project_description(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8")

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert report.project_metadata.ok is False
    assert "project.description is required for PyPI" in report.project_metadata.issues


def test_release_readiness_blocks_missing_open_source_metadata_file(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "LICENSE").unlink()

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert "open source metadata file is missing: LICENSE" in report.project_metadata.issues


def test_release_readiness_blocks_missing_open_source_template(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / ".github" / "ISSUE_TEMPLATE" / "case_proposal.yml").unlink()

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert (
        "open source metadata file is missing: .github/ISSUE_TEMPLATE/case_proposal.yml"
        in report.project_metadata.issues
    )


def test_release_readiness_blocks_incomplete_open_source_template(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / ".github" / "PULL_REQUEST_TEMPLATE.md").write_text(
        "python scripts/validate_cases.py --strict\n",
        encoding="utf-8",
    )

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert (
        "open source metadata file missing snippet: .github/PULL_REQUEST_TEMPLATE.md: "
        "python scripts/release_readiness.py --json"
    ) in report.project_metadata.issues


def test_release_readiness_blocks_release_workflow_without_strict_preflight(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    release_workflow = _release_workflow().replace(
        RELEASE_PREFLIGHT_COMMAND,
        "python scripts/release_readiness.py --json --report release-readiness-report.md",
    )
    (repo / ".github" / "workflows" / "release.yml").write_text(release_workflow, encoding="utf-8")

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release workflow validation failed" in report.blockers
    assert any("--strict --release-tag" in issue for issue in report.release_workflow.issues)


def test_release_readiness_blocks_release_workflow_without_distribution_check(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    release_workflow = _release_workflow().replace("      - run: uvx twine check dist/*\n", "")
    (repo / ".github" / "workflows" / "release.yml").write_text(release_workflow, encoding="utf-8")

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release workflow validation failed" in report.blockers
    assert any("uvx twine check dist/*" in issue for issue in report.release_workflow.issues)


def test_release_readiness_blocks_release_workflow_without_clean_dist(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    release_workflow = _release_workflow().replace("      - run: rm -rf dist\n", "")
    (repo / ".github" / "workflows" / "release.yml").write_text(release_workflow, encoding="utf-8")

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release workflow validation failed" in report.blockers
    assert any("rm -rf dist" in issue for issue in report.release_workflow.issues)


def test_release_readiness_accepts_tagged_release_mode(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    _commit(repo, "notes/tuesday.md", "tuesday", "2026-06-09")
    (repo / "pyproject.toml").write_text(
        '[project]\n'
        'name = "demo"\n'
        'version = "0.1.1"\n'
        'description = "Demo package."\n'
        'readme = "README.md"\n\n'
        '[project.urls]\n'
        'Homepage = "https://demo.example.com"\n'
        'Repository = "https://github.com/example/demo"\n'
        'Changelog = "https://github.com/example/demo/blob/main/CHANGELOG.md"\n',
        encoding="utf-8",
    )
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [0.1.1] - 2026-06-10\n\n"
        "### Added\n"
        "- Pending release note.\n\n"
        "## [0.1.0] - 2026-06-08\n\n"
        "[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.1.1...HEAD\n",
        encoding="utf-8",
    )
    _git(repo, "add", "pyproject.toml", "CHANGELOG.md")
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": "2026-06-10T12:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-06-10T12:00:00+00:00",
    }
    _git(repo, "commit", "-m", "release 0.1.1", env=env)
    _git(repo, "tag", "v0.1.1")

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=3, release_tag="v0.1.1")

    assert report.ok is True
    assert report.current_version == "0.1.1"
    assert report.target_version == "0.1.1"
    assert report.blockers == []
    assert report.cadence.latest_tag == "v0.1.1"
    assert report.cadence.commits_since_latest_tag == 0
    assert report.draft.ok is True


def test_release_readiness_blocks_when_required_package_check_not_run(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)

    report = release_readiness.build_report(
        repo,
        today=date(2026, 6, 10),
        min_commit_days=1,
        require_packages=True,
    )

    assert report.ok is False
    assert "case package validation not run" in report.blockers
    assert report.package_gate.ok is False
    assert report.package_gate.required is True
    assert report.package_gate.checked is False
    assert report.package_gate.issues == ["case package validation is required; pass --packages-dir"]


def test_release_readiness_accepts_required_valid_packages(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    _commit(repo, "notes/tuesday.md", "tuesday", "2026-06-09")
    _commit(repo, "notes/wednesday.md", "wednesday", "2026-06-10")
    packages_dir = tmp_path / "packages"
    _write_package(
        packages_dir,
        "demo.example.com.cliany-adapter-v0.1.0.tar.gz",
        domain="demo.example.com",
    )

    report = release_readiness.build_report(
        repo,
        today=date(2026, 6, 10),
        min_commit_days=3,
        packages_dir=packages_dir,
        require_packages=True,
    )

    assert report.ok is True
    assert report.blockers == []
    assert report.cases.checked_packages is True
    assert report.cases.cases[0].package["status"] == "ok"
    assert report.package_gate.ok is True
    assert report.package_gate.required is True
    assert report.package_gate.checked is True
    assert report.package_gate.packages_dir == str(packages_dir)
