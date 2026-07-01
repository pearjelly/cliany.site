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
        "repo_root",
        "worktree_clean",
        "worktree_status",
        "REPO_ROOT",
        "git rev-parse --show-toplevel",
        "latest_tag",
        "local_head",
        "tag_commit",
        "remote_checked",
        "EXPECTED_LOCAL_HEAD",
        "EXPECTED_LATEST_TAG",
        "EXPECTED_TAG_COMMIT",
        "git status --porcelain",
        "worktree",
        "提交、stash 或丢弃本地改动",
        "stale preflight",
        "Publish script is stale",
        "missing_commit_days",
        "primary_next_action",
        "next_actions_sha256",
        "纯文本 `next_actions`",
        "先修具体 gate 失败原因",
        "python scripts/release_readiness.py --strict",
        "每天至少发布 1 个可验证版本",
        "每天最多发布 3 个版本",
        "release_count_today",
        "max_daily_releases",
        "daily_release_limit_ok",
        "weekly_commit_cadence_ok",
        "--max-daily-releases",
        "超过 3 个版本/日",
        "每日发布循环",
        "standard_release_flow_primary_next_action",
        "GitHub Release 和 PyPI",
        "project_metadata",
        "package_gate",
    ]
    for snippet in required:
        assert snippet in text
