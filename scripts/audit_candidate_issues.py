"""Audit and explicitly refresh open candidate promotion issue bodies."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cliany_site.commands import cases as cases_command

DEFAULT_REPO = "pearjelly/cliany.site"
ISSUE_TITLE_PREFIX = "Promote candidate case `"
ISSUE_TITLE_SUFFIX = "` toward active"
DOCTOR_PREFLIGHT_EVIDENCE_HEADER = "## Doctor Preflight Evidence"
DOCTOR_PREFLIGHT_VALUES_SHA256_RE = re.compile(r"(?m)^- values_sha256: `([0-9a-f]{64})`$")
GITHUB_UNAVAILABLE_CODE = "E_GITHUB_UNAVAILABLE"


class GitHubUnavailableError(RuntimeError):
    """The GitHub API could not be read, so issue state is not auditable."""

    code = GITHUB_UNAVAILABLE_CODE
    retryable = True


def _is_github_transport_error(message: str) -> bool:
    normalized = message.lower()
    return any(
        marker in normalized
        for marker in (
            "error connecting to api.github.com",
            "check your internet connection",
            "network is unreachable",
            "connection refused",
            "could not resolve host",
            'api.github.com/graphql": eof',
            "unexpected eof",
            "http 500",
            "http 502",
            "http 503",
            "http 504",
            "500 internal server error",
            "502 bad gateway",
            "503 service unavailable",
            "504 gateway timeout",
        )
    )


@dataclass(frozen=True)
class CandidateIssueExpectation:
    case_id: str
    title: str
    body: str

    @property
    def body_sha256(self) -> str:
        return _sha256_text(self.body)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _has_attached_doctor_preflight_evidence(body: str) -> bool:
    return DOCTOR_PREFLIGHT_EVIDENCE_HEADER in body and bool(DOCTOR_PREFLIGHT_VALUES_SHA256_RE.search(body))


def _issue_title(case_id: str) -> str:
    return f"{ISSUE_TITLE_PREFIX}{case_id}{ISSUE_TITLE_SUFFIX}"


def _missing_issue_handoff(case_id: str) -> dict[str, str]:
    command = f"cliany-site cases --case-id {case_id} --issue-template --json"
    return {
        "issue_template_command": command,
        "next_action": (
            f"Review the generated template with `{command}` and create the issue manually; "
            "this audit never creates issues."
        ),
    }


def candidate_issue_expectations(
    case_ids: list[str] | None = None,
    *,
    doctor_preflight_evidence: dict[str, Any] | None = None,
) -> list[CandidateIssueExpectation]:
    catalog_cases, source_path, _checked_paths = cases_command._load_cases_manifest()
    if source_path is None:
        raise ValueError("cases/manifest.json is unavailable")

    candidates = {
        str(case.get("id") or ""): case
        for case in catalog_cases
        if case.get("status") == "candidate" and str(case.get("id") or "")
    }
    selected_ids = case_ids if case_ids else sorted(candidates)
    unknown_case_ids = [case_id for case_id in selected_ids if case_id not in candidates]
    if unknown_case_ids:
        raise ValueError(f"unknown candidate case IDs: {', '.join(unknown_case_ids)}")

    return [
        CandidateIssueExpectation(
            case_id=case_id,
            title=_issue_title(case_id),
            body=cases_command._candidate_issue_template(
                candidates[case_id],
                doctor_preflight_evidence=doctor_preflight_evidence,
            ),
        )
        for case_id in selected_ids
    ]


def _run_gh(arguments: list[str]) -> str:
    completed = subprocess.run(
        ["gh", *arguments],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "gh command failed"
        if _is_github_transport_error(message):
            raise GitHubUnavailableError(message)
        raise RuntimeError(message)
    return completed.stdout


def fetch_open_issues(repo: str) -> list[dict[str, Any]]:
    output = _run_gh(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--label",
            "case-proposal",
            "--limit",
            "100",
            "--json",
            "number,title,body,url",
        ]
    )
    payload = json.loads(output)
    if not isinstance(payload, list):
        raise ValueError("gh issue list did not return a JSON array")
    return [item for item in payload if isinstance(item, dict)]


def audit_candidate_issues(
    expectations: list[CandidateIssueExpectation],
    open_issues: list[dict[str, Any]],
    *,
    known_titles: set[str] | None = None,
) -> list[dict[str, Any]]:
    audits: list[dict[str, Any]] = []
    known_titles = known_titles or {expectation.title for expectation in expectations}
    for expectation in expectations:
        matches = [issue for issue in open_issues if issue.get("title") == expectation.title]
        base = {
            "case_id": expectation.case_id,
            "expected_title": expectation.title,
            "expected_body_sha256": expectation.body_sha256,
        }
        if not matches:
            audits.append(
                {
                    **base,
                    "status": "missing",
                    "issue_numbers": [],
                    **_missing_issue_handoff(expectation.case_id),
                }
            )
            continue
        if len(matches) > 1:
            audits.append(
                {
                    **base,
                    "status": "duplicate",
                    "issue_numbers": [
                        int(issue["number"])
                        for issue in matches
                        if isinstance(issue.get("number"), int)
                    ],
                }
            )
            continue

        issue = matches[0]
        body = str(issue.get("body") or "")
        issue_number = issue.get("number")
        audits.append(
            {
                **base,
                "status": "current" if body == expectation.body else "stale",
                "issue_numbers": [issue_number] if isinstance(issue_number, int) else [],
                "issue_url": str(issue.get("url") or ""),
                "actual_body_sha256": _sha256_text(body),
                "attached_doctor_preflight_evidence": _has_attached_doctor_preflight_evidence(body),
            }
        )

    for issue in open_issues:
        title = str(issue.get("title") or "")
        if title in known_titles:
            continue
        body = str(issue.get("body") or "")
        issue_number = issue.get("number")
        audits.append(
            {
                "case_id": "unmatched_case_proposal_issue",
                "status": "unexpected",
                "actual_title": title,
                "issue_numbers": [issue_number] if isinstance(issue_number, int) else [],
                "issue_url": str(issue.get("url") or ""),
                "actual_body_sha256": _sha256_text(body),
            }
        )
    return audits


def _report(
    repo: str,
    audits: list[dict[str, Any]],
    *,
    applied_issue_numbers: list[int] | None = None,
    doctor_preflight_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for audit in audits:
        status = str(audit.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    stale_issue_numbers = [
        number
        for audit in audits
        if audit.get("status") == "stale"
        for number in audit.get("issue_numbers", [])
        if isinstance(number, int)
    ]
    unexpected_issue_numbers = [
        number
        for audit in audits
        if audit.get("status") == "unexpected"
        for number in audit.get("issue_numbers", [])
        if isinstance(number, int)
    ]
    doctor_json_required_issue_numbers = [
        number
        for audit in audits
        if audit.get("status") == "stale" and audit.get("attached_doctor_preflight_evidence") is True
        for number in audit.get("issue_numbers", [])
        if isinstance(number, int)
    ]
    report = {
        "ok": all(audit.get("status") == "current" for audit in audits),
        "repo": repo,
        "candidate_count": sum(audit.get("status") != "unexpected" for audit in audits),
        "unexpected_issue_count": len(unexpected_issue_numbers),
        "status_counts": status_counts,
        "stale_issue_numbers": stale_issue_numbers,
        "unexpected_issue_numbers": unexpected_issue_numbers,
        "doctor_json_required_issue_numbers": doctor_json_required_issue_numbers,
        "applied_issue_numbers": applied_issue_numbers or [],
        "issues": audits,
    }
    if doctor_preflight_evidence is not None:
        state = doctor_preflight_evidence.get("doctor_preflight_state")
        state = state if isinstance(state, dict) else {}
        report["doctor_preflight_evidence"] = {
            "source_path": str(
                doctor_preflight_evidence.get("doctor_preflight_evidence_source_path") or ""
            ),
            "values_sha256": str(
                doctor_preflight_evidence.get("doctor_preflight_evidence_values_sha256") or ""
            ),
            "state_status": str(state.get("status") or ""),
            "ready_for_adapter_package": state.get("ready_for_adapter_package"),
        }
    return report


def _rewrite_issue(repo: str, issue_number: int, body: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md") as body_file:
        body_file.write(body)
        body_file.flush()
        _run_gh(
            [
                "issue",
                "edit",
                str(issue_number),
                "--repo",
                repo,
                "--body-file",
                body_file.name,
            ]
        )


def _print_human_report(report: dict[str, Any]) -> None:
    print(f"Candidate public issue audit: {report['repo']}")
    for audit in report["issues"]:
        issue_numbers = ", ".join(f"#{number}" for number in audit.get("issue_numbers", [])) or "(none)"
        line = f"- {audit['case_id']}: {audit['status']} {issue_numbers}"
        if audit.get("status") == "missing":
            line += f": review template with {audit['issue_template_command']} (audit never creates issues)"
        if audit.get("status") == "unexpected":
            actual_title = str(audit.get("actual_title") or "(untitled)")
            issue_url = str(audit.get("issue_url") or "(no URL)")
            line += f": {actual_title} {issue_url}"
        print(line)
    if report["applied_issue_numbers"]:
        numbers = ", ".join(f"#{number}" for number in report["applied_issue_numbers"])
        print(f"Rewrote: {numbers}")
    if not report["ok"]:
        print("Resolve missing, duplicate, or unexpected issues before applying stale-body rewrites.")
    if report.get("doctor_json_required_issue_numbers"):
        numbers = ", ".join(f"#{number}" for number in report["doctor_json_required_issue_numbers"])
        print(
            f"Refused to rewrite {numbers}: attached Doctor Preflight Evidence requires "
            "--doctor-json with the current saved preflight."
        )


def _print_error(
    message: str,
    *,
    json_mode: bool,
    code: str | None = None,
    retryable: bool = False,
) -> None:
    if json_mode:
        error: str | dict[str, Any] = message
        if code is not None:
            error = {
                "code": code,
                "message": message,
                "retryable": retryable,
                "next_action": (
                    "检查 GitHub API/网络后重试；未成功读取远端 issue 时不要将其判为 missing，"
                    "也不要执行 --apply。"
                ),
            }
        print(json.dumps({"ok": False, "error": error}, ensure_ascii=False, indent=2))
    else:
        prefix = f" [{code}, retryable]" if code is not None and retryable else ""
        print(f"Candidate public issue audit failed{prefix}: {message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository in owner/name form")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="Limit the audit to one candidate case ID")
    parser.add_argument(
        "--doctor-json",
        type=Path,
        help=(
            "Use saved cliany-site doctor --llm-live --require-capability "
            "generate_adapters --json evidence when rendering expected issue bodies"
        ),
    )
    parser.add_argument("--apply", action="store_true", help="Rewrite only stale issue bodies")
    parser.add_argument(
        "--confirm-rewrite",
        action="store_true",
        help="Required together with --apply because issue bodies are replaced",
    )
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    args = parser.parse_args(argv)

    if args.apply and not args.confirm_rewrite:
        parser.error("--apply requires --confirm-rewrite")

    try:
        doctor_preflight_evidence = (
            cases_command._load_doctor_preflight_evidence(args.doctor_json)
            if args.doctor_json is not None
            else None
        )
        all_expectations = (
            candidate_issue_expectations(doctor_preflight_evidence=doctor_preflight_evidence)
            if doctor_preflight_evidence is not None
            else candidate_issue_expectations()
        )
        expectations_by_case = {expectation.case_id: expectation for expectation in all_expectations}
        selected_case_ids = args.case_ids or list(expectations_by_case)
        unknown_case_ids = [case_id for case_id in selected_case_ids if case_id not in expectations_by_case]
        if unknown_case_ids:
            raise ValueError(f"unknown candidate case IDs: {', '.join(unknown_case_ids)}")
        expectations = [expectations_by_case[case_id] for case_id in selected_case_ids]
        audits = audit_candidate_issues(
            expectations,
            fetch_open_issues(args.repo),
            known_titles={expectation.title for expectation in all_expectations},
        )
    except GitHubUnavailableError as exc:
        _print_error(str(exc), json_mode=args.json, code=exc.code, retryable=exc.retryable)
        return 2
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        _print_error(str(exc), json_mode=args.json)
        return 2

    applied_issue_numbers: list[int] = []
    blocking_statuses = {"missing", "duplicate", "unexpected"}
    if args.apply and not any(audit["status"] in blocking_statuses for audit in audits):
        report = _report(args.repo, audits, doctor_preflight_evidence=doctor_preflight_evidence)
        if args.doctor_json is None and report["doctor_json_required_issue_numbers"]:
            report["ok"] = False
            report["error"] = "doctor_json_required_before_rewrite"
            report["next_action"] = (
                "Rerun with the current saved cliany-site doctor --llm-live "
                "--require-capability generate_adapters --json output and "
                "--doctor-json <path> before --apply --confirm-rewrite."
            )
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                _print_human_report(report)
            return 1
        expectations_by_case = {expectation.case_id: expectation for expectation in expectations}
        try:
            for audit in audits:
                if audit["status"] != "stale":
                    continue
                issue_number = audit["issue_numbers"][0]
                _rewrite_issue(args.repo, issue_number, expectations_by_case[audit["case_id"]].body)
                applied_issue_numbers.append(issue_number)
            audits = audit_candidate_issues(
                expectations,
                fetch_open_issues(args.repo),
                known_titles={expectation.title for expectation in all_expectations},
            )
        except GitHubUnavailableError as exc:
            _print_error(str(exc), json_mode=args.json, code=exc.code, retryable=exc.retryable)
            return 2
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            _print_error(str(exc), json_mode=args.json)
            return 2

    report = _report(
        args.repo,
        audits,
        applied_issue_numbers=applied_issue_numbers,
        doctor_preflight_evidence=doctor_preflight_evidence,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
