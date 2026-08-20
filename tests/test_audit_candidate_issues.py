import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

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


def _write_blocked_doctor_json(tmp_path: Path) -> Path:
    path = tmp_path / "doctor.json"
    path.write_text(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "checks": [
                        {
                            "name": "cdp",
                            "status": "ok",
                            "action": "Chrome/CDP is available.",
                        },
                        {
                            "name": "llm_live",
                            "status": "warning",
                            "details": {
                                "error_code": "E_LLM_UNAVAILABLE",
                                "retryable": True,
                                "status_code": 502,
                                "phase": "llm_preflight",
                                "message": "LLM upstream unavailable.",
                            },
                        }
                    ],
                    "summary": {
                        "ready_for_explore": False,
                        "llm_live_preflight": {"ready": False, "status": "warning"},
                        "capabilities": {
                            "run_browser_workflows": {"ready": True},
                            "generate_adapters": {
                                "ready": False,
                                "local_ready": True,
                                "local_blockers": [],
                            }
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return path


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


def test_missing_issue_exposes_manual_template_handoff(capsys):
    expectation = _expectation("npm-package-search")

    audits = audit_candidate_issues.audit_candidate_issues([expectation], [])

    assert audits[0]["status"] == "missing"
    command = "cliany-site cases --case-id npm-package-search --issue-template --json"
    assert audits[0]["issue_template_command"] == command
    assert "this audit never creates issues" in audits[0]["next_action"]

    audit_candidate_issues._print_human_report(
        audit_candidate_issues._report("owner/repo", audits)
    )

    output = capsys.readouterr().out
    assert f"review template with {command}" in output
    assert "audit never creates issues" in output


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


def test_human_report_prints_unexpected_issue_title_and_url(capsys):
    expectation = _expectation()
    audits = audit_candidate_issues.audit_candidate_issues(
        [expectation],
        [
            {
                "number": 99,
                "title": "Old candidate handoff",
                "body": "unmatched issue body",
                "url": "https://example.test/99",
            }
        ],
    )

    audit_candidate_issues._print_human_report(
        audit_candidate_issues._report("owner/repo", audits)
    )

    output = capsys.readouterr().out
    assert "- unmatched_case_proposal_issue: unexpected #99: Old candidate handoff https://example.test/99" in output


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


def test_candidate_expectations_can_render_saved_doctor_preflight_evidence(tmp_path):
    doctor_json = _write_blocked_doctor_json(tmp_path)
    evidence = audit_candidate_issues.cases_command._load_doctor_preflight_evidence(doctor_json)

    expectations = audit_candidate_issues.candidate_issue_expectations(
        ["pypi-project-search"],
        doctor_preflight_evidence=evidence,
    )

    assert str(doctor_json) not in expectations[0].body
    assert (
        f"- values_sha256: `{evidence['doctor_preflight_evidence_values_sha256']}`"
        in expectations[0].body
    )
    assert "- Current execution gate: `blocked`" in expectations[0].body
    assert "| `checks[llm_live].details.error_code` | `E_LLM_UNAVAILABLE` |" in expectations[0].body


def test_report_includes_saved_doctor_evidence_identity(tmp_path):
    doctor_json = _write_blocked_doctor_json(tmp_path)
    evidence = audit_candidate_issues.cases_command._load_doctor_preflight_evidence(doctor_json)
    expectation = _expectation()
    audits = audit_candidate_issues.audit_candidate_issues(
        [expectation],
        [{"number": 14, "title": expectation.title, "body": expectation.body, "url": "https://example.test/14"}],
    )

    report = audit_candidate_issues._report(
        "owner/repo",
        audits,
        doctor_preflight_evidence=evidence,
    )

    assert report["doctor_preflight_evidence"]["source_path"] == str(doctor_json)
    assert report["doctor_preflight_evidence"]["state_status"] == "blocked"
    assert report["doctor_preflight_evidence"]["ready_for_adapter_package"] is False
    assert len(report["doctor_preflight_evidence"]["values_sha256"]) == 64


def test_main_uses_doctor_json_for_expectations_and_report(monkeypatch, tmp_path, capsys):
    doctor_json = _write_blocked_doctor_json(tmp_path)
    captured = {}

    def fake_expectations(_case_ids=None, *, doctor_preflight_evidence=None):
        captured["evidence"] = doctor_preflight_evidence
        return [_expectation()]

    monkeypatch.setattr(audit_candidate_issues, "candidate_issue_expectations", fake_expectations)
    monkeypatch.setattr(
        audit_candidate_issues,
        "fetch_open_issues",
        lambda _repo: [
            {
                "number": 14,
                "title": _expectation().title,
                "body": _expectation().body,
                "url": "https://example.test/14",
            }
        ],
    )

    exit_code = audit_candidate_issues.main(
        ["--repo", "owner/repo", "--doctor-json", str(doctor_json), "--json"]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["evidence"]["doctor_preflight_state"]["status"] == "blocked"
    assert payload["doctor_preflight_evidence"]["source_path"] == str(doctor_json)


def test_main_reports_invalid_doctor_json_as_an_input_error(tmp_path, capsys):
    missing_path = tmp_path / "missing-doctor.json"

    exit_code = audit_candidate_issues.main(["--doctor-json", str(missing_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["ok"] is False
    assert str(missing_path) in payload["error"]


def test_run_gh_classifies_github_api_transport_failure(monkeypatch):
    completed = subprocess.CompletedProcess(
        args=["gh"],
        returncode=1,
        stdout="",
        stderr="error connecting to api.github.com\ncheck your internet connection",
    )
    monkeypatch.setattr(audit_candidate_issues.subprocess, "run", lambda *args, **kwargs: completed)

    with pytest.raises(audit_candidate_issues.GitHubUnavailableError) as exc_info:
        audit_candidate_issues._run_gh(["issue", "list"])

    assert exc_info.value.code == "E_GITHUB_UNAVAILABLE"
    assert exc_info.value.retryable is True


def test_run_gh_classifies_graphql_eof_as_github_unavailable(monkeypatch):
    completed = subprocess.CompletedProcess(
        args=["gh"],
        returncode=1,
        stdout="",
        stderr='Post "https://api.github.com/graphql": EOF',
    )
    monkeypatch.setattr(audit_candidate_issues.subprocess, "run", lambda *args, **kwargs: completed)

    with pytest.raises(audit_candidate_issues.GitHubUnavailableError) as exc_info:
        audit_candidate_issues._run_gh(["issue", "list"])

    assert exc_info.value.code == "E_GITHUB_UNAVAILABLE"
    assert exc_info.value.retryable is True


@pytest.mark.parametrize(
    "stderr",
    [
        "HTTP 500: Internal Server Error",
        "HTTP 502: Bad Gateway",
        "HTTP 503: Service Unavailable",
        "HTTP 504: Gateway Timeout",
    ],
)
def test_run_gh_classifies_github_http_5xx_as_unavailable(monkeypatch, stderr):
    completed = subprocess.CompletedProcess(
        args=["gh"],
        returncode=1,
        stdout="",
        stderr=stderr,
    )
    monkeypatch.setattr(audit_candidate_issues.subprocess, "run", lambda *args, **kwargs: completed)

    with pytest.raises(audit_candidate_issues.GitHubUnavailableError) as exc_info:
        audit_candidate_issues._run_gh(["issue", "list"])

    assert exc_info.value.code == "E_GITHUB_UNAVAILABLE"
    assert exc_info.value.retryable is True


def test_run_gh_does_not_classify_auth_failure_as_unavailable(monkeypatch):
    completed = subprocess.CompletedProcess(
        args=["gh"],
        returncode=1,
        stdout="",
        stderr="HTTP 401: Bad credentials",
    )
    monkeypatch.setattr(audit_candidate_issues.subprocess, "run", lambda *args, **kwargs: completed)

    with pytest.raises(RuntimeError, match="HTTP 401: Bad credentials"):
        audit_candidate_issues._run_gh(["issue", "list"])


def test_main_reports_github_api_transport_failure_without_issue_states(monkeypatch, capsys):
    monkeypatch.setattr(
        audit_candidate_issues,
        "candidate_issue_expectations",
        lambda _case_ids=None: [_expectation()],
    )
    monkeypatch.setattr(
        audit_candidate_issues,
        "fetch_open_issues",
        lambda _repo: (_ for _ in ()).throw(
            audit_candidate_issues.GitHubUnavailableError(
                "error connecting to api.github.com"
            )
        ),
    )

    exit_code = audit_candidate_issues.main(["--repo", "owner/repo", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["error"] == {
        "code": "E_GITHUB_UNAVAILABLE",
        "message": "error connecting to api.github.com",
        "retryable": True,
        "next_action": (
            "检查 GitHub API/网络后重试；未成功读取远端 issue 时不要将其判为 missing，"
            "也不要执行 --apply。"
        ),
    }


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


def test_apply_refuses_to_erase_attached_doctor_evidence_without_doctor_json(monkeypatch, capsys):
    expectation = _expectation()
    attached_evidence_body = "\n".join(
        [
            "## Doctor Preflight Evidence",
            "- values_sha256: `" + ("a" * 64) + "`",
        ]
    )
    rewrites = []

    monkeypatch.setattr(audit_candidate_issues, "candidate_issue_expectations", lambda _case_ids=None: [expectation])
    monkeypatch.setattr(
        audit_candidate_issues,
        "fetch_open_issues",
        lambda _repo: [
            {
                "number": 14,
                "title": expectation.title,
                "body": attached_evidence_body,
                "url": "https://example.test/14",
            }
        ],
    )
    monkeypatch.setattr(
        audit_candidate_issues,
        "_rewrite_issue",
        lambda repo, number, body: rewrites.append((repo, number, body)),
    )

    exit_code = audit_candidate_issues.main(["--repo", "owner/repo", "--apply", "--confirm-rewrite", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert rewrites == []
    assert payload["error"] == "doctor_json_required_before_rewrite"
    assert payload["doctor_json_required_issue_numbers"] == [14]
    assert payload["issues"][0]["attached_doctor_preflight_evidence"] is True


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
