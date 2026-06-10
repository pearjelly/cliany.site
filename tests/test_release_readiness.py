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
          python scripts/validate_cases.py --strict
          pytest tests/test_validate_cases.py tests/test_cases_manifest.py -q --no-cov
        env:
          CLIANY_QA_OFFLINE: "1"

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


def _init_repo(tmp_path: Path, *, with_draft: bool) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / "cases").mkdir()
    (repo / "docs" / "releases").mkdir(parents=True)
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8")
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n### Added\n- Pending release note.\n\n## [0.1.0] - 2026-06-08\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# Demo\n\n## demo\n", encoding="utf-8")
    (repo / "cases" / "manifest.json").write_text(_cases_manifest(), encoding="utf-8")
    (repo / ".github" / "workflows" / "ci.yml").write_text(_ci_workflow(), encoding="utf-8")
    if with_draft:
        (repo / "docs" / "releases" / "v0.1.1-draft.md").write_text(
            _release_draft("0.1.1", "0.1.0"),
            encoding="utf-8",
        )
    _git(repo, "add", "pyproject.toml", "CHANGELOG.md", "README.md", "cases/manifest.json", ".github/workflows/ci.yml")
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
    assert report.package_gate.ok is True
    assert report.package_gate.required is False
    assert report.package_gate.checked is False


def test_release_readiness_blocks_missing_release_draft(tmp_path):
    repo = _init_repo(tmp_path, with_draft=False)

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release draft validation failed" in report.blockers
    assert report.draft.ok is False
    assert report.draft.issues == ["release draft is missing"]


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
