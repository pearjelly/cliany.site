import hashlib
import importlib.util
import json
import subprocess
import sys
import tarfile
from dataclasses import replace
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


def _build_report(repo: Path, **kwargs):
    return release_readiness.build_report(repo, min_case_assets=1, **kwargs)


def test_markdown_cell_preserves_zero_and_false():
    assert release_readiness._markdown_cell(0) == "0"
    assert release_readiness._markdown_cell(False) == "False"
    assert release_readiness._markdown_cell(None) == "-"
    assert release_readiness._markdown_cell("") == "-"


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

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"

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

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"

jobs:
  release-preflight:
    name: Release Preflight
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
    needs: release-preflight
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
                    "offline_commands": ["python scripts/validate_cases.py --strict"],
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


def _append_active_case(repo: Path, *, case_id: str, domain: str) -> None:
    manifest_path = repo / "cases" / "manifest.json"
    cases = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases.append(
        {
            "id": case_id,
            "title": "Second demo case",
            "category": "demo",
            "status": "active",
            "target_url": f"https://{domain}/",
            "adapter_domain": domain,
            "source_release": "v0.1.0",
            "docs": "README.md#demo",
            "example_output": f"cases/examples/{case_id}.json",
            "commands": [
                f"cliany-site market install ./{domain}.cliany-adapter-v0.1.0.tar.gz",
                f"cliany-site {domain} list-items --json",
            ],
            "validation": {
                "offline": "metadata validates",
                "offline_commands": ["python scripts/validate_cases.py --strict"],
                "online": "read-only command returns rows",
            },
        }
    )
    manifest_path.write_text(json.dumps(cases), encoding="utf-8")
    (repo / "cases" / "examples" / f"{case_id}.json").write_text(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "command": "list-items",
                    "results": [{"ok": True, "data": {"items": [{"name": "Second"}]}}],
                    "quality": {"ok": True, "status": "ok", "row_count": 1},
                },
                "error": None,
                "meta": {
                    "source": "case-example",
                    "case_id": case_id,
                    "sample": True,
                },
            }
        ),
        encoding="utf-8",
    )


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
            "id: promotion\n"
            "Candidate Promotion Tasks\n"
            "Issue Body Template\n"
            "adapter_package\n"
            "metadata_validation\n"
            "online_smoke\n"
            "python scripts/validate_cases.py --strict\n"
            "degraded\n"
        ),
        ".github/ISSUE_TEMPLATE/config.yml": (
            "blank_issues_enabled: false\n"
            "url: https://github.com/pearjelly/cliany.site/security/advisories/new\n"
            "name: Documentation\n"
        ),
    }[filename]


def _readme_content() -> str:
    return (
        "# Demo\n\n"
        "10-minute success path\n"
        "10 分钟成功路径\n"
        "data.quality\n"
        "--strict-quality\n"
        "E_EMPTY_RESULT\n"
        "scripts/release_readiness.py\n"
        "scripts/check_release_publication.py\n"
        "Real Demo Case Proposal\n"
        "docs/good-first-issues.md\n"
        "docs/module-ownership.md\n"
        "weekly-maintainer-loop.md\n"
        "next_actions\n"
        "github.com-1.0.0.cliany-adapter.tar.gz\n"
        "## demo\n"
    )


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
        ".github/ISSUE_TEMPLATE/config.yml",
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
    (repo / "README.md").write_text(_readme_content(), encoding="utf-8")
    (repo / "README.zh.md").write_text(_readme_content(), encoding="utf-8")
    (repo / "docs" / "roadmap-2026-q3.md").write_text(
        "# Roadmap\n\n[每周维护者循环](weekly-maintainer-loop.md)\n",
        encoding="utf-8",
    )
    (repo / "docs" / "release-cadence.md").write_text(
        "# Release Cadence\n\n"
        "[每周维护者循环](weekly-maintainer-loop.md)\n"
        "scripts/check_release_publication.py\n"
        "python scripts/check_release_publication.py --remote --json\n"
        "python scripts/check_release_publication.py --remote --report\n",
        encoding="utf-8",
    )
    (repo / "docs" / "good-first-issues.md").write_text(
        "# Good First Issues\n\n"
        "CLIANY_QA_OFFLINE=1\n"
        "python scripts/validate_cases.py --strict\n"
        "python scripts/release_readiness.py --json\n"
        "promotion\n"
        "Candidate Promotion Tasks\n"
        "Issue Body Template\n"
        "Issue 拆分清单\n"
        "推荐验证命令\n"
        "~/.cliany-site/\n",
        encoding="utf-8",
    )
    (repo / "docs" / "contributor-starter.md").write_text(
        "# 贡献者上手地图\n\n"
        "good-first-issues.md\n"
        "module-ownership.md\n"
        "CLIANY_QA_OFFLINE=1\n"
        "Real Demo Case Proposal\n"
        "Candidate Promotion Tasks\n"
        "Issue Body Template\n"
        "AXTree snapshot\n",
        encoding="utf-8",
    )
    (repo / "docs" / "module-ownership.md").write_text(
        "# 模块 Ownership 与验证地图\n\n"
        "Owner area\n"
        "Adapter lifecycle\n"
        "Case catalog\n"
        "Release operations\n"
        "scripts/check_release_publication.py\n"
        "Contributor experience\n"
        "CLIANY_QA_OFFLINE=1\n"
        "python scripts/validate_cases.py --strict\n"
        "tests/test_release_publication.py\n"
        "~/.cliany-site/\n",
        encoding="utf-8",
    )
    (repo / "docs" / "weekly-maintainer-loop.md").write_text(
        "# 每周维护者循环\n\n"
        "python scripts/release_readiness.py --json\n"
        "python scripts/validate_cases.py --strict\n"
        "CLIANY_QA_OFFLINE=1\n"
        "commit days N/3\n",
        encoding="utf-8",
    )
    (repo / "cases" / "manifest.json").write_text(_cases_manifest(), encoding="utf-8")
    (repo / "cases" / "examples").mkdir()
    (repo / "cases" / "examples" / "demo-case.json").write_text(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "command": "list-items",
                    "results": [{"ok": True, "data": {"items": [{"name": "Example"}]}}],
                    "quality": {"ok": True, "status": "ok", "row_count": 1},
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
        "README.zh.md",
        "docs/roadmap-2026-q3.md",
        "docs/release-cadence.md",
        "docs/contributor-starter.md",
        "docs/good-first-issues.md",
        "docs/module-ownership.md",
        "docs/weekly-maintainer-loop.md",
        "cases/manifest.json",
        "cases/examples/demo-case.json",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/case_proposal.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
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

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

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
    assert report.to_dict()["cases"]["promotion_command_plan_summary"] == {
        "candidate_count": 0,
        "command_count": 0,
        "expected_command_count": 0,
        "missing_command_count": 0,
        "ready_candidate_count": 0,
        "all_declared": True,
        "task_missing_counts": {
            "llm_live_preflight": 0,
            "adapter_package": 0,
            "metadata_validation": 0,
            "online_smoke": 0,
        },
        "missing_tasks": [],
        "missing_cases": [],
        "primary_missing_task": None,
    }
    assert report.to_dict()["next_actions"] == [
        "Set an upstream branch for `master` before checking publication status.",
        (
            "After final release readiness is clean, create target tag `v0.1.1` at HEAD and push it "
            "after the branch is published. Commands: `git tag v0.1.1` then "
            "`git push origin v0.1.1`."
        ),
    ]
    assert report.to_dict()["next_action_count"] == 2
    assert report.to_dict()["primary_next_action"] == report.to_dict()["next_actions"][0]
    assert report.to_dict()["next_actions_sha256"] == release_readiness._stable_json_sha256(
        report.to_dict()["next_actions"]
    )


def test_release_readiness_json_includes_next_actions_when_blocked(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

    payload = report.to_dict()
    publish_commands = payload["publication_publish_commands"]
    publication_next_actions = payload["publication_next_actions"]
    publication_ref_context = payload["publication_ref_context"]
    publication_summary = payload["publication_summary"]
    standard_release_flow = payload["standard_release_flow"]
    assert payload["blockers"] == ["commit days 1/3"]
    assert payload["publication_ok"] is False
    assert publication_summary["status"] == "blocked"
    assert publication_summary["branch"] == payload["publication"]["branch"]
    assert publication_summary["latest_tag"] == payload["publication"]["latest_tag"]
    assert publication_summary["next_action_count"] == len(publication_next_actions)
    assert publication_summary["primary_next_action"] == publication_next_actions[0]
    assert publication_summary["publish_command_count"] == len(publish_commands)
    assert publication_summary["primary_publish_command"] == publish_commands[0]
    assert payload["publication_summary_sha256"] == release_readiness._stable_json_sha256(publication_summary)
    assert payload["publication_summary_primary_next_action"] == publication_summary["primary_next_action"]
    assert (
        payload["publication_summary_primary_publish_command"]
        == publication_summary["primary_publish_command"]
    )
    assert publication_ref_context["branch"] == payload["publication"]["branch"]
    assert publication_ref_context["latest_tag"] == payload["publication"]["latest_tag"]
    assert publication_ref_context["remote_checked"] == payload["publication"]["remote_checked"]
    assert payload["publication_worktree_clean"] is True
    assert payload["publication_worktree_status_count"] == 0
    assert payload["publication_worktree_status"] == []
    assert payload["publication_blockers"] == [
        "latest local release is not published",
        "latest local release tag is not published",
    ]
    assert payload["publication_blocker_count"] == len(payload["publication_blockers"])
    assert payload["publication_primary_blocker"] == "latest local release is not published"
    assert payload["publication_blockers_sha256"] == release_readiness._stable_json_sha256(
        payload["publication_blockers"]
    )
    assert payload["publication"]["publish_commands"] == publish_commands
    assert payload["publication_tag_publish_decision"] == payload["publication"]["tag_publish_decision"]
    assert payload["publication_tag_publish_decision"]["status"] == "needs_remote_check"
    assert payload["publication_tag_publish_decision"]["can_push_tag"] is False
    assert payload["publication_tag_publish_decision"]["target_tag"] == "v0.1.1"
    assert (
        payload["publication_tag_publish_decision"]["target_tag_status"]
        == "create_target_tag_at_head"
    )
    assert (
        payload["publication_tag_publish_decision"]["target_tag_release_gate_status"]
        == "blocked_by_readiness"
    )
    assert (
        payload["publication_tag_publish_decision"]["target_tag_release_gate_blocker_count"]
        == len(payload["blockers"])
    )
    assert (
        payload["publication_tag_publish_decision"]["target_tag_release_gate_blockers"]
        == payload["blockers"]
    )
    assert (
        payload["publication_tag_publish_decision"]["target_tag_release_gate_primary_blocker"]
        == "commit days 1/3"
    )
    assert (
        payload["publication_tag_publish_decision"]["target_tag_release_gate_blockers_sha256"]
        == release_readiness._stable_json_sha256(payload["blockers"])
    )
    assert (
        payload["publication_tag_publish_decision"]["target_tag_release_gate_required_action"]
        == "Clear release readiness blockers before creating target tag `v0.1.1`."
    )
    assert payload["publication_tag_publish_decision"]["target_tag_commands"] == [
        "git tag v0.1.1",
        "git push origin v0.1.1",
    ]
    assert payload["publication_tag_publish_decision"]["target_tag_commands_sha256"] == (
        release_readiness._stable_json_sha256(
            payload["publication_tag_publish_decision"]["target_tag_commands"]
        )
    )
    assert publication_summary["target_tag"] == "v0.1.1"
    assert publication_summary["target_tag_primary_command"] == "git tag v0.1.1"
    assert publication_summary["target_tag_release_gate_status"] == "blocked_by_readiness"
    assert publication_summary["target_tag_release_gate_blocker_count"] == len(payload["blockers"])
    assert publication_summary["target_tag_release_gate_primary_blocker"] == "commit days 1/3"
    assert payload["publication"]["next_actions"] == publication_next_actions
    assert payload["publication_next_action_count"] == len(publication_next_actions)
    assert payload["publication_next_actions_sha256"] == release_readiness._stable_json_sha256(
        publication_next_actions
    )
    assert payload["publication_primary_next_action"] == publication_next_actions[0]
    assert (
        "Rerun with `--remote` when network access is available to verify live remote refs."
        in publication_next_actions
    )
    assert payload["publication_publish_command_count"] == len(publish_commands)
    assert payload["publication_publish_commands_sha256"] == release_readiness._stable_json_sha256(
        publish_commands
    )
    assert payload["publication_primary_publish_command"] == publish_commands[0]
    assert "python scripts/check_release_publication.py --remote --json" in publish_commands
    assert standard_release_flow["status"] == "blocked"
    assert standard_release_flow["target_version"] == "0.1.1"
    assert standard_release_flow["target_tag"] == "v0.1.1"
    assert standard_release_flow["blockers"] == [
        "commit days 1/3",
        "latest local release is not published",
        "latest local release tag is not published",
    ]
    assert standard_release_flow["primary_next_action"] == payload["next_actions"][0]
    assert "python scripts/release_readiness.py --strict --target-version 0.1.1" in (
        standard_release_flow["commands"]
    )
    assert "CLIANY_QA_OFFLINE=1 pytest tests/ -q" in standard_release_flow["commands"]
    assert "python scripts/validate_cases.py --strict" in standard_release_flow["commands"]
    assert "git tag v0.1.1" in standard_release_flow["commands"]
    assert "git push origin v0.1.1" in standard_release_flow["commands"]
    assert "python scripts/check_release_publication.py --remote --json" in (
        standard_release_flow["commands"]
    )
    assert payload["standard_release_flow_status"] == standard_release_flow["status"]
    assert (
        payload["standard_release_flow_primary_next_action"]
        == standard_release_flow["primary_next_action"]
    )
    assert payload["standard_release_flow_command_count"] == len(
        standard_release_flow["commands"]
    )
    assert payload["standard_release_flow_commands_sha256"] == (
        release_readiness._stable_json_sha256(standard_release_flow["commands"])
    )
    assert payload["standard_release_flow_sha256"] == release_readiness._stable_json_sha256(
        standard_release_flow
    )
    assert payload["next_actions"] == [
        "Set an upstream branch for `master` before checking publication status.",
        (
            "After final release readiness is clean, create target tag `v0.1.1` at HEAD and push it "
            "after the branch is published. Commands: `git tag v0.1.1` then "
            "`git push origin v0.1.1`."
        ),
        (
            "Ship verified slices on `2` more unique commit days this week; "
            "current commit days are `1/3`. Use `docs/weekly-maintainer-loop.md` to pick the next slice."
        ),
    ]
    assert payload["next_action_count"] == len(payload["next_actions"])
    assert payload["primary_next_action"] == payload["next_actions"][0]
    assert payload["next_actions_sha256"] == release_readiness._stable_json_sha256(
        payload["next_actions"]
    )
    assert not any(action.startswith("- ") for action in payload["next_actions"])


def test_release_readiness_default_requires_eight_case_assets(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    _commit(repo, "notes/tuesday.md", "tuesday", "2026-06-09")
    _commit(repo, "notes/wednesday.md", "wednesday", "2026-06-10")

    report = release_readiness.build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

    assert report.ok is False
    assert report.min_case_assets == 8
    assert "case assets 1/8" in report.blockers
    assert report.to_dict()["min_case_assets"] == 8
    assert (
        "Add verified active or candidate case assets until the catalog reaches `8` tracked cases."
        in report.to_dict()["next_actions"]
    )


def test_release_readiness_writes_markdown_report(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    _commit(repo, "notes/tuesday.md", "tuesday", "2026-06-09")
    _commit(repo, "notes/wednesday.md", "wednesday", "2026-06-10")
    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=3)
    report_path = tmp_path / "reports" / "release-readiness.md"

    release_readiness._write_markdown_report(report, report_path)

    publication_summary = report.to_dict()["publication_summary"]
    text = report_path.read_text(encoding="utf-8")
    assert "# cliany-site Release Readiness" in text
    assert "| ok | `true` |" in text
    assert "| target_version | `0.1.1` |" in text
    assert (
        "| cadence | `true` | commit days `3/3`: 2026-06-08, 2026-06-09, 2026-06-10; "
        "daily releases `0/3` |"
    ) in text
    assert "| cases | `true` | active `1`, candidate `0`, known_gap `0`, total `1`, min_assets `1` |" in text
    assert "| release_workflow | `true` |" in text
    assert "| project_metadata | `true` |" in text
    assert "https://github.com/pearjelly/cliany.site/compare/v0.1.0...HEAD" in text
    assert "## Weekly Review" in text
    assert "## Publication Publish Commands" in text
    assert "- publication_ok: `false`" in text
    assert "- publication_summary_status: `blocked`" in text
    assert "- publication_summary_branch: `master`" in text
    assert "- publication_summary_latest_tag: `v0.1.0`" in text
    assert "- publication_summary_target_tag: `v0.1.1`" in text
    assert "- publication_summary_target_tag_status: `create_target_tag_at_head`" in text
    assert (
        "- publication_summary_target_tag_release_gate_status: "
        "`ready_for_publication_review`"
    ) in text
    assert "- publication_summary_target_tag_release_gate_blocker_count: `0`" in text
    assert "- publication_summary_target_tag_release_gate_primary_blocker: `-`" in text
    assert "- publication_summary_sha256: `" in text
    assert "- publication_summary_primary_next_action: `" in text
    assert (
        "- publication_summary_primary_publish_command: "
        f"`{publication_summary['primary_publish_command']}`"
    ) in text
    assert "- publication_blocker_count: `3`" in text
    assert "- publication_blockers_sha256: `" in text
    assert "- publication_primary_blocker: `latest local release is not published`" in text
    assert "### Publication Blockers" in text
    assert "- latest local release is not published" in text
    assert "- tag_publish_decision: `manual_decision_required`" in text
    assert "- tag_can_push: `false`" in text
    assert "- tag_required_action: `Move to the latest tag commit or create a new release tag at HEAD " in text
    assert "- target_tag: `v0.1.1`" in text
    assert "- target_tag_status: `create_target_tag_at_head`" in text
    assert "- target_tag_release_gate_status: `ready_for_publication_review`" in text
    assert "- target_tag_release_gate_blocker_count: `0`" in text
    assert "- target_tag_release_gate_primary_blocker: `-`" in text
    assert (
        "- target_tag_release_gate_required_action: "
        "`After final release readiness is clean, create target tag `v0.1.1` at HEAD "
    ) in text
    assert "- target_tag_release_gate_blockers_sha256: `" in text
    assert "- target_tag_commands_sha256: `" in text
    assert "- target_tag_primary_command: `git tag v0.1.1`" in text
    assert "- publication_next_action_count: `" in text
    assert "- publication_next_actions_sha256: `" in text
    assert "- publication_primary_next_action: `" in text
    assert "### Publication Next Actions" in text
    assert "- Move to the `v0.1.0` commit or create a new release tag at HEAD before publishing." in text
    assert "### Publication Ref Context" in text
    assert "| branch | `master` |" in text
    assert "| latest_tag | `v0.1.0` |" in text
    assert "| tag_points_at_head | `false` |" in text
    assert "### Publication Worktree Status" in text
    assert "- clean: `true`" in text
    assert "- status_count: `0`" in text
    assert "- Worktree is clean." in text
    assert "- publish_command_count: `" in text
    assert "- publication_publish_commands_sha256: `" in text
    assert "- primary_publish_command: `git push -u origin master`" in text
    assert "python scripts/check_release_publication.py --remote --json" in text
    assert "## Standard Release Flow" in text
    assert "- standard_release_flow_status: `blocked`" in text
    assert "- standard_release_flow_target_version: `0.1.1`" in text
    assert "- standard_release_flow_target_tag: `v0.1.1`" in text
    assert "- standard_release_flow_blocker_count: `3`" in text
    assert "- standard_release_flow_primary_next_action: `" in text
    assert "- standard_release_flow_command_count: `" in text
    assert "- standard_release_flow_commands_sha256: `" in text
    assert "- standard_release_flow_sha256: `" in text
    assert "### Standard Release Commands" in text
    assert "`python scripts/release_readiness.py --strict --target-version 0.1.1`" in text
    assert "`git tag v0.1.1`" in text
    assert "`git push origin v0.1.1`" in text
    assert "### Standard Release Steps" in text
    assert "| `strict_release_readiness` | `ready` |" in text
    assert "| `target_tag` | `create_target_tag_at_head` |" in text
    assert "| Does the week have enough commit days? | `3/3`: 2026-06-08, 2026-06-09, 2026-06-10 |" in text
    assert (
        "| What is the next smallest release slice? | Set an upstream branch for `master` "
        "before checking publication status. |"
    ) in text
    assert "## Next Actions" in text
    assert "- Set an upstream branch for `master` before checking publication status." in text


def test_release_readiness_markdown_report_includes_candidate_promotions(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    metadata_validation = "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict"
    cases = json.loads((repo / "cases" / "manifest.json").read_text(encoding="utf-8"))
    cases.append(
        {
            "id": "candidate-case",
            "title": "Candidate case",
            "category": "demo",
            "status": "candidate",
            "target_url": "https://demo.example.com/search",
            "adapter_domain": "demo.example.com",
            "source_release": None,
            "docs": "README.md#demo",
            "example_output": "cases/examples/candidate-case.json",
            "commands": ["cliany-site demo.example.com search-items --query demo --json"],
            "validation": {
                "offline": "candidate metadata validates",
                "offline_commands": ["python scripts/validate_cases.py --strict"],
                "online": "read-only search returns rows",
            },
            "promotion": {
                "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
                "metadata_validation": metadata_validation,
                "online_smoke": "cliany-site demo.example.com search-items --query demo --json",
            },
            "promotion_evidence": {
                "adapter_package": {
                    "status": "pending",
                    "evidence": None,
                    "next_action": "Generate demo.example.com-<version>.cliany-adapter.tar.gz.",
                },
                "metadata_validation": {
                    "status": "pending",
                    "evidence": None,
                    "next_action": "Run metadata validation.",
                },
                "online_smoke": {
                    "status": "pending",
                    "evidence": None,
                    "next_action": "Run online smoke.",
                },
            },
        }
    )
    (repo / "cases" / "manifest.json").write_text(json.dumps(cases), encoding="utf-8")
    (repo / "cases" / "examples" / "candidate-case.json").write_text(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "command": "search-items",
                    "results": [{"ok": True, "data": {"items": [{"name": "Candidate"}]}}],
                },
                "error": None,
                "meta": {
                    "source": "case-example",
                    "case_id": "candidate-case",
                    "sample": True,
                },
            }
        ),
        encoding="utf-8",
    )
    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)
    report_path = tmp_path / "reports" / "release-readiness.md"

    release_readiness._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "## Candidate Primary Next Task" in text
    assert (
        "| `candidate-case` | `adapter_package` | `pending` | Not attached yet. | "
        "Generate demo.example.com-<version>.cliany-adapter.tar.gz. |"
    ) in text
    assert "## Candidate Promotion Command Plan Summary" in text
    assert "| candidate_count | `1` |" in text
    assert "| command_count | `4` |" in text
    assert "| expected_command_count | `4` |" in text
    assert "| missing_command_count | `1` |" in text
    assert "| all_declared | `false` |" in text
    assert "| `candidate-case` | `adapter_package` |" in text
    assert "## Candidate Promotions" in text
    assert "| `candidate-case` |" in text
    assert "publish demo.example.com-<version>.cliany-adapter.tar.gz" in text
    assert metadata_validation in text
    assert "cliany-site demo.example.com search-items --query demo --json" in text


def test_release_readiness_text_output_omits_next_actions_when_ready(tmp_path, capsys):
    repo = _init_repo(tmp_path, with_draft=True)
    _commit(repo, "notes/tuesday.md", "tuesday", "2026-06-09")
    _commit(repo, "notes/wednesday.md", "wednesday", "2026-06-10")
    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

    release_readiness._print_text(report)

    publication_summary = report.to_dict()["publication_summary"]
    output = capsys.readouterr().out
    assert "ok: True" in output
    assert "cases: True (active 1, candidate 0, known_gap 0, total 1, min_assets 1)" in output
    assert "candidate_command_plan_summary: all_declared=true, commands=0/0, missing=0" in output
    assert "publication: False" in output
    assert "publication_summary: status=blocked, worktree_clean=true, ahead=None" in output
    assert "target_tag=v0.1.1" in output
    assert "publication_summary_sha256:" in output
    assert "publication_summary_primary_next_action:" in output
    assert (
        "publication_summary_primary_publish_command: "
        f"{publication_summary['primary_publish_command']}"
    ) in output
    assert "publication_blocker_count: 3" in output
    assert "publication_blockers_sha256:" in output
    assert "publication_primary_blocker: latest local release is not published" in output
    assert "publication_blockers:" in output
    assert "publication_worktree: clean=true, status_count=0" in output
    assert "publication_worktree_status:" not in output
    assert "publication_ref_context: branch=master, upstream=(none), ahead=None, latest_tag=v0.1.0" in output
    assert "publication_tag_publish_decision: status=manual_decision_required, can_push_tag=false" in output
    assert (
        "publication_tag_required_action: Move to the latest tag commit or create a new release tag at HEAD"
        in output
    )
    assert "publication_target_tag: v0.1.1" in output
    assert "publication_target_tag_status: create_target_tag_at_head" in output
    assert "publication_target_tag_release_gate_status: ready_for_publication_review" in output
    assert "publication_target_tag_release_gate_blocker_count: 0" in output
    assert "publication_target_tag_release_gate_primary_blocker:" not in output
    assert "publication_target_tag_commands_sha256:" in output
    assert "publication_target_tag_primary_command: git tag v0.1.1" in output
    assert "publication_next_action_count:" in output
    assert "publication_next_actions_sha256:" in output
    assert "publication_primary_next_action: Set an upstream branch for `master`" in output
    assert "publication_next_actions:" in output
    assert "- Move to the `v0.1.0` commit or create a new release tag at HEAD before publishing." in output
    assert "publication_publish_command_count:" in output
    assert "publication_publish_commands_sha256:" in output
    assert "publication_primary_publish_command: git push -u origin master" in output
    assert "publication_publish_commands:" in output
    assert "- python scripts/check_release_publication.py --remote --json" in output
    assert "standard_release_flow: status=blocked, target_tag=v0.1.1" in output
    assert "standard_release_flow_sha256:" in output
    assert "standard_release_flow_primary_next_action:" in output
    assert "standard_release_flow_commands_sha256:" in output
    assert "package_gate_summary: checked=false, failed=0, missing=0, invalid=0, repair_actions=0" in output
    assert "package_gate_primary_repair_action:" not in output
    assert "next_actions:" in output.splitlines()
    assert "- Set an upstream branch for `master` before checking publication status." in output


def test_release_readiness_text_output_includes_next_actions_when_blocked(tmp_path, capsys):
    repo = _init_repo(tmp_path, with_draft=True)
    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

    release_readiness._print_text(report)

    output = capsys.readouterr().out
    assert "blockers:" in output
    assert "- commit days 1/3" in output
    assert "publication_target_tag_release_gate_status: blocked_by_readiness" in output
    assert "publication_target_tag_release_gate_blocker_count: 1" in output
    assert "publication_target_tag_release_gate_primary_blocker: commit days 1/3" in output
    assert "next_actions:" in output
    assert (
        "- Ship verified slices on `2` more unique commit days this week; "
        "current commit days are `1/3`. Use `docs/weekly-maintainer-loop.md` to pick the next slice."
    ) in output


def test_release_readiness_markdown_report_includes_gate_issues_and_next_actions(tmp_path):
    repo = _init_repo(tmp_path, with_draft=False)
    (repo / "LICENSE").unlink()
    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=3)
    report_path = tmp_path / "reports" / "release-readiness.md"

    release_readiness._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "## Gate Issues" in text
    assert "- `cadence`: commit days 1/3" in text
    assert "- `draft`: release draft is missing" in text
    assert "- `project_metadata`: open source metadata file is missing: LICENSE" in text
    assert "## Next Actions" in text
    assert "## Weekly Review" in text
    assert (
        "- Ship verified slices on `2` more unique commit days this week; "
        "current commit days are `1/3`. Use `docs/weekly-maintainer-loop.md` to pick the next slice."
    ) in text
    assert (
        "| What is the next smallest release slice? | Commit, stash, or discard local worktree changes "
        "before publishing release refs. |"
    ) in text
    assert "- Update the target release draft under `docs/releases/`" in text
    assert "- Restore PyPI metadata and open-source community entrypoints required by project metadata gate." in text


def test_release_readiness_blocks_missing_release_draft(tmp_path):
    repo = _init_repo(tmp_path, with_draft=False)

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

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

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert any("CHANGELOG Unreleased compare link is stale" in blocker for blocker in report.blockers)
    assert report.cadence.changelog_unreleased_compare_ok is False


def test_release_readiness_blocks_missing_ci_extract_gate(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        "name: CI\njobs:\n  case-catalog:\n    name: Case Catalog Validation\n",
        encoding="utf-8",
    )

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "CI release gates validation failed" in report.blockers
    assert report.ci.ok is False
    assert any("extract-quality:" in issue for issue in report.ci.issues)


def test_release_readiness_blocks_ci_workflow_without_node24_actions_opt_in(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    ci_workflow = _ci_workflow().replace(
        'env:\n  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"\n\n',
        "",
    )
    (repo / ".github" / "workflows" / "ci.yml").write_text(ci_workflow, encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "CI release gates validation failed" in report.blockers
    assert report.ci.ok is False
    assert any("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24" in issue for issue in report.ci.issues)


def test_release_readiness_blocks_missing_release_workflow_pypi_publish(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / ".github" / "workflows" / "release.yml").write_text(
        "name: Release\non:\n  push:\n    tags: [\"v*\"]\n",
        encoding="utf-8",
    )

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release workflow validation failed" in report.blockers
    assert report.release_workflow.ok is False
    assert any("pypa/gh-action-pypi-publish@release/v1" in issue for issue in report.release_workflow.issues)


def test_release_readiness_blocks_release_workflow_without_node24_actions_opt_in(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    release_workflow = _release_workflow().replace(
        'env:\n  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"\n\n',
        "",
    )
    (repo / ".github" / "workflows" / "release.yml").write_text(release_workflow, encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release workflow validation failed" in report.blockers
    assert report.release_workflow.ok is False
    assert any("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24" in issue for issue in report.release_workflow.issues)


def test_release_readiness_blocks_missing_project_description(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert report.project_metadata.ok is False
    assert "project.description is required for PyPI" in report.project_metadata.issues


def test_release_readiness_blocks_missing_open_source_metadata_file(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "LICENSE").unlink()

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert "open source metadata file is missing: LICENSE" in report.project_metadata.issues


def test_release_readiness_blocks_missing_open_source_template(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / ".github" / "ISSUE_TEMPLATE" / "case_proposal.yml").unlink()

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

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

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert (
        "open source metadata file missing snippet: .github/PULL_REQUEST_TEMPLATE.md: "
        "python scripts/release_readiness.py --json"
    ) in report.project_metadata.issues


def test_release_readiness_blocks_incomplete_readme_entrypoint(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert "open source metadata file missing snippet: README.md: Real Demo Case Proposal" in (
        report.project_metadata.issues
    )


def test_release_readiness_blocks_stale_website_quickstart(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "site" / "docs").mkdir(parents=True)
    (repo / "site" / "index.html").write_text("<h2>Quick Start</h2>\n", encoding="utf-8")
    (repo / "site" / "docs" / "index.html").write_text("<h2>5 分钟快速开始</h2>\n", encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert "open source metadata file missing snippet: site/index.html: 10-Minute Success Path" in (
        report.project_metadata.issues
    )
    assert "open source metadata file missing snippet: site/docs/index.html: 10 分钟成功路径" in (
        report.project_metadata.issues
    )


def test_release_readiness_blocks_stale_readme_marketplace_package_name(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    text = (repo / "README.md").read_text(encoding="utf-8")
    (repo / "README.md").write_text(
        text.replace("github.com-1.0.0.cliany-adapter.tar.gz", "./github.com.cliany-adapter.tar.gz"),
        encoding="utf-8",
    )

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert (
        "open source metadata file missing snippet: README.md: "
        "github.com-1.0.0.cliany-adapter.tar.gz"
    ) in report.project_metadata.issues


def test_release_readiness_blocks_missing_weekly_maintainer_loop_doc(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "docs" / "weekly-maintainer-loop.md").unlink()

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert "open source metadata file is missing: docs/weekly-maintainer-loop.md" in (
        report.project_metadata.issues
    )


def test_release_readiness_blocks_missing_weekly_loop_link(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "docs" / "roadmap-2026-q3.md").write_text("# Roadmap\n", encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert "open source metadata file missing snippet: docs/roadmap-2026-q3.md: weekly-maintainer-loop.md" in (
        report.project_metadata.issues
    )


def test_release_readiness_blocks_stale_quickstart_path(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    (repo / "docs" / "quickstart-10min.md").write_text(
        "# 快速开始\n\ncliany-site explore \"https://github.com\" \"search repos\" --json\n",
        encoding="utf-8",
    )

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "project metadata validation failed" in report.blockers
    assert "open source metadata file missing snippet: docs/quickstart-10min.md: 10 分钟成功路径" in (
        report.project_metadata.issues
    )
    assert (
        "open source metadata file missing snippet: docs/quickstart-10min.md: "
        "cliany-site verify issues.apache.org --json"
    ) in report.project_metadata.issues


def test_release_readiness_blocks_release_workflow_without_strict_preflight(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    release_workflow = _release_workflow().replace(
        RELEASE_PREFLIGHT_COMMAND,
        "python scripts/release_readiness.py --json --report release-readiness-report.md",
    )
    (repo / ".github" / "workflows" / "release.yml").write_text(release_workflow, encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release workflow validation failed" in report.blockers
    assert any("--strict --release-tag" in issue for issue in report.release_workflow.issues)


def test_release_readiness_blocks_release_workflow_without_distribution_check(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    release_workflow = _release_workflow().replace("      - run: uvx twine check dist/*\n", "")
    (repo / ".github" / "workflows" / "release.yml").write_text(release_workflow, encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert "release workflow validation failed" in report.blockers
    assert any("uvx twine check dist/*" in issue for issue in report.release_workflow.issues)


def test_release_readiness_blocks_release_workflow_without_clean_dist(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    release_workflow = _release_workflow().replace("      - run: rm -rf dist\n", "")
    (repo / ".github" / "workflows" / "release.yml").write_text(release_workflow, encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

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

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=3, release_tag="v0.1.1")

    assert report.ok is True
    assert report.current_version == "0.1.1"
    assert report.target_version == "0.1.1"
    assert report.release_mode == "tagged"
    assert report.release_tag == "v0.1.1"
    assert report.blockers == []
    assert report.cadence.latest_tag == "v0.1.1"
    assert report.cadence.commits_since_latest_tag == 0
    assert report.draft.ok is True
    assert report.to_dict()["release_mode"] == "tagged"
    assert report.to_dict()["release_tag"] == "v0.1.1"


def test_release_readiness_markdown_tagged_mode_points_to_publish_step(tmp_path):
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
    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=3, release_tag="v0.1.1")
    report_path = tmp_path / "reports" / "release-readiness.md"

    release_readiness._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "| release_mode | `tagged` |" in text
    assert "| release_tag | `v0.1.1` |" in text
    assert (
        "| What is the next smallest release slice? | Set an upstream branch for `master` "
        "before checking publication status. |"
    ) in text

    target_report = replace(report, release_mode="target", release_tag=None)
    target_report_path = tmp_path / "reports" / "target-readiness.md"
    release_readiness._write_markdown_report(target_report, target_report_path)

    target_text = target_report_path.read_text(encoding="utf-8")
    assert "| release_mode | `target` |" in target_text
    assert "| release_tag | `-` |" in target_text
    assert (
        "| What is the next smallest release slice? | Set an upstream branch for `master` "
        "before checking publication status. |"
    ) in target_text


def test_release_readiness_blocks_release_tag_not_at_head(tmp_path):
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
    _commit(repo, "notes/after-tag.md", "after tag", "2026-06-10")
    (repo / "pyproject.toml").write_text((repo / "pyproject.toml").read_text(encoding="utf-8"), encoding="utf-8")

    report = _build_report(repo, today=date(2026, 6, 10), min_commit_days=3, release_tag="v0.1.1")

    assert report.ok is False
    assert "release tag v0.1.1 does not point at HEAD" in report.blockers
    assert "Check out the release tag commit before running `--release-tag` preflight." in (
        report.to_dict()["next_actions"]
    )


def test_release_readiness_blocks_when_required_package_check_not_run(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)

    report = _build_report(
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
    assert report.package_gate.failed_count == 0
    assert report.package_gate.missing_count == 0
    assert report.package_gate.invalid_count == 0
    assert report.package_gate.repair_action_count == 0
    assert report.package_gate.primary_repair_action is None


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

    report = _build_report(
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
    assert report.package_gate.failed_count == 0
    assert report.package_gate.missing_count == 0
    assert report.package_gate.invalid_count == 0
    assert report.package_gate.repair_action_count == 0
    assert report.package_gate.primary_repair_action is None


def test_release_readiness_markdown_report_includes_case_package_checks(tmp_path, capsys):
    repo = _init_repo(tmp_path, with_draft=True)
    packages_dir = tmp_path / "packages"
    _write_package(
        packages_dir,
        "demo.example.com.cliany-adapter-v0.1.0.tar.gz",
        domain="other.example.com",
    )
    report = _build_report(
        repo,
        today=date(2026, 6, 10),
        min_commit_days=1,
        packages_dir=packages_dir,
        require_packages=True,
    )
    report_path = tmp_path / "reports" / "release-readiness.md"

    release_readiness._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "## Case Package Checks" in text
    assert "| `demo-case` | `invalid` |" in text
    assert "demo.example.com.cliany-adapter-v0.1.0.tar.gz" in text
    assert "domain mismatch: expected 'demo.example.com', got 'other.example.com'" in text
    assert "Regenerate the package for the manifest adapter_domain or fix the case adapter_domain." in text
    assert "| package_gate | `false` | required `true`, checked `true`, failed `1`, missing `0`, invalid `1` |" in text
    assert report.ok is False
    assert "case package validation failed" in report.blockers
    assert report.package_gate.ok is False
    assert report.package_gate.issues == ["case package validation failed: 1 failing package(s)"]
    assert report.package_gate.failed_count == 1
    assert report.package_gate.missing_count == 0
    assert report.package_gate.invalid_count == 1
    assert report.package_gate.repair_action_count == 1
    assert (
        report.package_gate.primary_repair_action
        == "Regenerate the package for the manifest adapter_domain or fix the case adapter_domain."
    )
    assert report.to_dict()["package_gate"]["failed_count"] == 1
    package_next_action = (
        "`demo-case` package: "
        "Regenerate the package for the manifest adapter_domain or fix the case adapter_domain."
    )
    assert package_next_action in report.to_dict()["next_actions"]
    assert (
        "Fix or rebuild the failing case packages listed in `Case Package Checks`, then rerun "
        "`python scripts/release_readiness.py --packages-dir ~/.cliany-site/packages --require-packages`."
    ) in report.to_dict()["next_actions"]

    release_readiness._print_text(report)

    output = capsys.readouterr().out
    assert "package_gate_summary: checked=true, failed=1, missing=0, invalid=1, repair_actions=1" in output
    assert (
        "package_gate_primary_repair_action: "
        "Regenerate the package for the manifest adapter_domain or fix the case adapter_domain."
    ) in output


def test_release_readiness_package_next_actions_dedupe_global_repairs(tmp_path):
    repo = _init_repo(tmp_path, with_draft=True)
    _append_active_case(repo, case_id="second-demo-case", domain="second.example.com")
    packages_dir = tmp_path / "packages"
    packages_dir.mkdir()

    report = _build_report(
        repo,
        today=date(2026, 6, 10),
        min_commit_days=1,
        packages_dir=packages_dir,
        require_packages=True,
    )

    next_actions = report.to_dict()["next_actions"]
    assert report.package_gate.failed_count == 2
    assert report.package_gate.missing_count == 2
    assert "Package checks: Rerun python scripts/validate_cases.py --packages-dir <dir> --strict." in next_actions
    assert (
        next_actions.count("Package checks: Rerun python scripts/validate_cases.py --packages-dir <dir> --strict.")
        == 1
    )
    assert not any(
        "`demo-case` package: Rerun python scripts/validate_cases.py --packages-dir <dir> --strict." in action
        for action in next_actions
    )
    assert any("demo.example.com.cliany-adapter-v0.1.0.tar.gz" in action for action in next_actions)
    assert any("second.example.com.cliany-adapter-v0.1.0.tar.gz" in action for action in next_actions)
