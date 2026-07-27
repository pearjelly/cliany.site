import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_candidate_issues.py"
SPEC = importlib.util.spec_from_file_location("audit_candidate_issues", SCRIPT)
assert SPEC is not None
audit_candidate_issues = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = audit_candidate_issues
SPEC.loader.exec_module(audit_candidate_issues)


def _expectation(case_id: str = "pypi-project-search"):
    return audit_candidate_issues.CandidateIssueExpectation(
        case_id=case_id,
        title=f"Promote candidate case `{case_id}` toward active",
        body="current issue body",
    )


def test_audit_reports_current_candidate_issue_contract():
    expectation = _expectation()

    audits = audit_candidate_issues.audit_candidate_issues(
        [expectation],
        [{"number": 14, "title": expectation.title, "body": expectation.body, "url": "https://example.test/14"}],
    )

    assert audits[0]["status"] == "current"
    assert audits[0]["issue_numbers"] == [14]
    report = audit_candidate_issues._report("owner/repo", audits)
    assert report["ok"] is True
    assert report["stale_issue_numbers"] == []
    assert report["unexpected_issue_numbers"] == []


def test_audit_reports_stale_missing_and_duplicate_contracts():
    current = _expectation("pypi-project-search")
    missing = _expectation("npm-package-search")
    duplicate = _expectation("crates-io-crate-search")

    audits = audit_candidate_issues.audit_candidate_issues(
        [current, missing, duplicate],
        [
            {"number": 14, "title": current.title, "body": "old issue body", "url": "https://example.test/14"},
            {"number": 16, "title": duplicate.title, "body": duplicate.body, "url": "https://example.test/16"},
            {"number": 17, "title": duplicate.title, "body": duplicate.body, "url": "https://example.test/17"},
        ],
    )

    assert [audit["status"] for audit in audits] == ["stale", "missing", "duplicate"]
    report = audit_candidate_issues._report("owner/repo", audits)
    assert report["ok"] is False
    assert report["stale_issue_numbers"] == [14]
    assert report["status_counts"] == {"stale": 1, "missing": 1, "duplicate": 1}


def test_audit_reports_unexpected_case_proposal_issue_and_its_body_hash():
    expectation = _expectation()
    unexpected = {
        "number": 99,
        "title": "Old candidate handoff",
        "body": "unmatched issue body",
        "url": "https://example.test/99",
    }

    audits = audit_candidate_issues.audit_candidate_issues(
        [expectation],
        [
            {"number": 14, "title": expectation.title, "body": expectation.body, "url": "https://example.test/14"},
            unexpected,
        ],
    )

    assert [audit["status"] for audit in audits] == ["current", "unexpected"]
    assert audits[1]["actual_title"] == "Old candidate handoff"
    assert audits[1]["actual_body_sha256"] == audit_candidate_issues._sha256_text("unmatched issue body")
    report = audit_candidate_issues._report("owner/repo", audits)
    assert report["ok"] is False
    assert report["candidate_count"] == 1
    assert report["unexpected_issue_count"] == 1
    assert report["unexpected_issue_numbers"] == [99]


def test_scoped_audit_does_not_flag_other_known_candidate_titles_as_unexpected():
    selected = _expectation("pypi-project-search")
    other = _expectation("npm-package-search")

    audits = audit_candidate_issues.audit_candidate_issues(
        [selected],
        [{"number": 15, "title": other.title, "body": other.body, "url": "https://example.test/15"}],
        known_titles={selected.title, other.title},
    )

    assert [audit["status"] for audit in audits] == ["missing"]


def test_candidate_expectations_use_the_strict_live_preflight_contract():
    expectations = audit_candidate_issues.candidate_issue_expectations(["pypi-project-search"])

    assert len(expectations) == 1
    assert expectations[0].title == "Promote candidate case `pypi-project-search` toward active"
    assert "cliany-site doctor --llm-live --require-capability generate_adapters --json" in expectations[0].body


def test_apply_rechecks_after_rewriting_stale_issue(monkeypatch):
    expectation = _expectation()
    responses = [
        [{"number": 14, "title": expectation.title, "body": "old issue body", "url": "https://example.test/14"}],
        [{"number": 14, "title": expectation.title, "body": expectation.body, "url": "https://example.test/14"}],
    ]
    rewrites = []

    monkeypatch.setattr(audit_candidate_issues, "candidate_issue_expectations", lambda _case_ids=None: [expectation])
    monkeypatch.setattr(audit_candidate_issues, "fetch_open_issues", lambda _repo: responses.pop(0))
    monkeypatch.setattr(
        audit_candidate_issues,
        "_rewrite_issue",
        lambda repo, number, body: rewrites.append((repo, number, body)),
    )

    exit_code = audit_candidate_issues.main(["--repo", "owner/repo", "--apply", "--confirm-rewrite", "--json"])

    assert exit_code == 0
    assert rewrites == [("owner/repo", 14, expectation.body)]


def test_apply_does_not_rewrite_when_issue_title_is_ambiguous(monkeypatch):
    expectation = _expectation()
    rewrites = []

    monkeypatch.setattr(audit_candidate_issues, "candidate_issue_expectations", lambda _case_ids=None: [expectation])
    monkeypatch.setattr(
        audit_candidate_issues,
        "fetch_open_issues",
        lambda _repo: [
            {"number": 14, "title": expectation.title, "body": expectation.body, "url": "https://example.test/14"},
            {"number": 15, "title": expectation.title, "body": expectation.body, "url": "https://example.test/15"},
        ],
    )
    monkeypatch.setattr(
        audit_candidate_issues,
        "_rewrite_issue",
        lambda repo, number, body: rewrites.append((repo, number, body)),
    )

    exit_code = audit_candidate_issues.main(["--repo", "owner/repo", "--apply", "--confirm-rewrite", "--json"])

    assert exit_code == 1
    assert rewrites == []


def test_apply_does_not_rewrite_when_unexpected_case_proposal_issue_exists(monkeypatch):
    expectation = _expectation()
    rewrites = []

    monkeypatch.setattr(audit_candidate_issues, "candidate_issue_expectations", lambda _case_ids=None: [expectation])
    monkeypatch.setattr(
        audit_candidate_issues,
        "fetch_open_issues",
        lambda _repo: [
            {"number": 14, "title": expectation.title, "body": "old issue body", "url": "https://example.test/14"},
            {"number": 99, "title": "Old candidate handoff", "body": "legacy", "url": "https://example.test/99"},
        ],
    )
    monkeypatch.setattr(
        audit_candidate_issues,
        "_rewrite_issue",
        lambda repo, number, body: rewrites.append((repo, number, body)),
    )

    exit_code = audit_candidate_issues.main(["--repo", "owner/repo", "--apply", "--confirm-rewrite", "--json"])

    assert exit_code == 1
    assert rewrites == []
