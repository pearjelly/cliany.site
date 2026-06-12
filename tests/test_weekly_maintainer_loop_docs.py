from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "weekly-maintainer-loop.md"


def test_weekly_maintainer_loop_doc_has_required_sections():
    text = DOC.read_text(encoding="utf-8")

    required = [
        "# 每周维护者循环",
        "## 1. 周初：选一个可发布主题",
        "## 2. 周中：实现一个可验证切片",
        "## 3. 周末：发版或明确阻塞",
        "## 4. 周复盘问题",
        "python scripts/plan_next_iteration.py --json",
        "python scripts/plan_next_iteration.py --report",
        "python scripts/plan_next_iteration.py --issues-dir",
        "publication audit",
        "publication_publish_commands",
        "publication_publish_script_command",
        "branch/tag push",
        "python scripts/check_release_publication.py --remote --json",
        "--publish-script /tmp/cliany-publish-release.sh",
        "Candidate Promotion Tasks",
        "Candidate Issue Metadata",
        "Candidate Issue Body Templates",
        "Reproduction Context",
        "target URL",
        "candidate commands",
        "offline validation commands",
        "issue-metadata.json",
        "publication-handoff.json",
        "README.md",
        "create-issues.sh",
        "publish commands",
        "python scripts/check_release_publication.py --strict --json",
        "/tmp/cliany-issue-publication-check.json",
        "如果 preflight 失败",
        "issue_artifacts_command",
        "复现命令",
        "/tmp/cliany-candidate-issues",
        "GitHub issue body",
        "issue title",
        "labels",
        "adapter_package",
        "metadata_validation",
        "online_smoke",
        "python scripts/release_readiness.py --json",
        "python scripts/release_readiness.py --report",
        "Weekly Review",
        "python scripts/validate_cases.py --strict",
        "CLIANY_QA_OFFLINE=1 pytest tests/ -q --no-cov",
        "commit days N/3",
    ]
    for snippet in required:
        assert snippet in text


def test_weekly_maintainer_loop_referenced_paths_exist():
    text = DOC.read_text(encoding="utf-8")

    required_paths = [
        "docs/roadmap-2026-q3.md",
        "docs/release-cadence.md",
        "scripts/plan_next_iteration.py",
        "scripts/release_readiness.py",
        "scripts/validate_cases.py",
        "CHANGELOG.md",
    ]
    for path in required_paths:
        assert (ROOT / path).exists(), f"missing referenced path: {path}"
        assert path.split("/", 1)[-1] in text or path in text


def test_roadmap_and_release_cadence_link_weekly_loop():
    for path in (ROOT / "docs/roadmap-2026-q3.md", ROOT / "docs/release-cadence.md"):
        text = path.read_text(encoding="utf-8")
        assert "weekly-maintainer-loop.md" in text
