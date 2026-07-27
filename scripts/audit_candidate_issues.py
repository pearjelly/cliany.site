"""Audit and explicitly refresh open candidate promotion issue bodies."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any

from cliany_site.commands import cases as cases_command

DEFAULT_REPO = "pearjelly/cliany.site"
ISSUE_TITLE_PREFIX = "Promote candidate case `"
ISSUE_TITLE_SUFFIX = "` toward active"


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


def _issue_title(case_id: str) -> str:
    return f"{ISSUE_TITLE_PREFIX}{case_id}{ISSUE_TITLE_SUFFIX}"


def candidate_issue_expectations(case_ids: list[str] | None = None) -> list[CandidateIssueExpectation]:
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
            body=cases_command._candidate_issue_template(candidates[case_id]),
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
) -> list[dict[str, Any]]:
    audits: list[dict[str, Any]] = []
    for expectation in expectations:
        matches = [issue for issue in open_issues if issue.get("title") == expectation.title]
        base = {
            "case_id": expectation.case_id,
            "expected_title": expectation.title,
            "expected_body_sha256": expectation.body_sha256,
        }
        if not matches:
            audits.append({**base, "status": "missing", "issue_numbers": []})
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
            }
        )
    return audits


def _report(
    repo: str,
    audits: list[dict[str, Any]],
    *,
    applied_issue_numbers: list[int] | None = None,
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
    return {
        "ok": all(audit.get("status") == "current" for audit in audits),
        "repo": repo,
        "candidate_count": len(audits),
        "status_counts": status_counts,
        "stale_issue_numbers": stale_issue_numbers,
        "applied_issue_numbers": applied_issue_numbers or [],
        "issues": audits,
    }


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
        print(f"- {audit['case_id']}: {audit['status']} {issue_numbers}")
    if report["applied_issue_numbers"]:
        numbers = ", ".join(f"#{number}" for number in report["applied_issue_numbers"])
        print(f"Rewrote: {numbers}")
    if not report["ok"]:
        print("Use --apply --confirm-rewrite only after reviewing stale issue bodies.")


def _print_error(message: str, *, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False, indent=2))
    else:
        print(f"Candidate public issue audit failed: {message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository in owner/name form")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="Limit the audit to one candidate case ID")
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
        expectations = candidate_issue_expectations(args.case_ids)
        audits = audit_candidate_issues(expectations, fetch_open_issues(args.repo))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        _print_error(str(exc), json_mode=args.json)
        return 2

    applied_issue_numbers: list[int] = []
    blocking_statuses = {"missing", "duplicate"}
    if args.apply and not any(audit["status"] in blocking_statuses for audit in audits):
        expectations_by_case = {expectation.case_id: expectation for expectation in expectations}
        try:
            for audit in audits:
                if audit["status"] != "stale":
                    continue
                issue_number = audit["issue_numbers"][0]
                _rewrite_issue(args.repo, issue_number, expectations_by_case[audit["case_id"]].body)
                applied_issue_numbers.append(issue_number)
            audits = audit_candidate_issues(expectations, fetch_open_issues(args.repo))
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            _print_error(str(exc), json_mode=args.json)
            return 2

    report = _report(args.repo, audits, applied_issue_numbers=applied_issue_numbers)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
