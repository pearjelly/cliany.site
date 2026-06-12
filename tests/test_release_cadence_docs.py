from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "release-cadence.md"


def test_release_cadence_doc_explains_readiness_triage():
    text = DOC.read_text(encoding="utf-8")

    required = [
        "python scripts/release_readiness.py --report /tmp/cliany-release-readiness.md",
        "Gate Issues",
        "release-readiness-report",
        "next_actions",
        "publish_commands",
        "git push origin master",
        "git push origin vX.Y.Z",
        "python scripts/check_release_publication.py --remote --json",
        "--publish-script /tmp/cliany-publish-release.sh",
        "可审阅的 shell 脚本",
        "Publication context",
        "latest_tag",
        "local_head",
        "tag_commit",
        "remote_checked",
        "missing_commit_days",
        "先修具体 gate 失败原因",
        "python scripts/release_readiness.py --strict",
        "project_metadata",
        "package_gate",
    ]
    for snippet in required:
        assert snippet in text
