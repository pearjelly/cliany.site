import hashlib
import importlib.util
import json
import sys
import tarfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_cases.py"
SPEC = importlib.util.spec_from_file_location("validate_cases", SCRIPT)
assert SPEC is not None
validate_cases = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = validate_cases
SPEC.loader.exec_module(validate_cases)


def _write_cases(root: Path, cases: list[dict]) -> None:
    cases_dir = root / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    (cases_dir / "manifest.json").write_text(json.dumps(cases), encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    for case in cases:
        example_output = case.get("example_output")
        if not example_output:
            continue
        example_path = root / example_output
        example_path.parent.mkdir(parents=True, exist_ok=True)
        example_path.write_text(
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
                        "case_id": case["id"],
                        "sample": True,
                    },
                }
            ),
            encoding="utf-8",
        )


def _case(case_id: str = "demo-case", *, domain: str = "demo.example.com") -> dict:
    return {
        "id": case_id,
        "title": "Demo case",
        "category": "demo",
        "status": "active",
        "target_url": "https://demo.example.com/",
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


def _promotion_evidence() -> dict:
    return {
        "adapter_package": {
            "status": "pending",
            "evidence": None,
            "next_action": "Generate the adapter package.",
        },
        "metadata_validation": {
            "status": "pending",
            "evidence": None,
            "next_action": "Run validate_cases with --packages-dir.",
        },
        "online_smoke": {
            "status": "pending",
            "evidence": None,
            "next_action": "Run the read-only smoke command.",
        },
    }


def _write_package(
    packages_dir: Path,
    filename: str,
    *,
    domain: str,
    metadata_schema_version: int = 3,
    bad_hash: bool = False,
) -> None:
    packages_dir.mkdir(parents=True, exist_ok=True)
    commands_content = b"import click\n\n@click.group()\ndef cli():\n    pass\n"
    metadata_content = json.dumps(
        {
            "schema_version": metadata_schema_version,
            "domain": domain,
            "generated_at": "2026-06-10T00:00:00Z",
            "generator_version": "test",
            "commands": [{"name": "list-items"}],
        }
    ).encode("utf-8")
    commands_hash = hashlib.sha256(commands_content).hexdigest()
    metadata_hash = hashlib.sha256(metadata_content).hexdigest()
    if bad_hash:
        metadata_hash = "0" * 64

    manifest = {
        "manifest_version": "1",
        "domain": domain,
        "files": ["commands.py", "metadata.json"],
        "file_hashes": {"commands.py": commands_hash, "metadata.json": metadata_hash},
    }
    with tarfile.open(packages_dir / filename, "w:gz") as tar:
        data = json.dumps(manifest).encode("utf-8")
        info = tarfile.TarInfo(name="manifest.json")
        info.size = len(data)
        tar.addfile(info, BytesIO(data))

        commands_info = tarfile.TarInfo(name="commands.py")
        commands_info.size = len(commands_content)
        tar.addfile(commands_info, BytesIO(commands_content))

        metadata_info = tarfile.TarInfo(name="metadata.json")
        metadata_info.size = len(metadata_content)
        tar.addfile(metadata_info, BytesIO(metadata_content))


def test_current_cases_manifest_validates_without_packages():
    report = validate_cases.build_report(ROOT)

    assert report.ok is True
    assert report.active >= 4
    assert report.candidate >= 1
    assert report.known_gap >= 1
    assert report.checked_packages is False
    assert report.promotion_evidence_summary["candidate_count"] == report.candidate
    assert report.promotion_evidence_summary["pending_count"] == report.candidate * 3
    assert report.promotion_evidence_summary["primary_next_action"]
    assert report.promotion_command_plan_summary == {
        "candidate_count": report.candidate,
        "command_count": report.candidate * 4,
        "expected_command_count": report.candidate * 4,
        "missing_command_count": 0,
        "ready_candidate_count": report.candidate,
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
    candidate_cases = [case for case in report.to_dict()["cases"] if case["status"] == "candidate"]
    assert candidate_cases
    for case in candidate_cases:
        assert case["promotion_command_plan_count"] == 4
        assert case["promotion_command_plan_missing_tasks"] == []
        assert [item["task"] for item in case["promotion_command_plan"]] == [
            "llm_live_preflight",
            "adapter_package",
            "metadata_validation",
            "online_smoke",
        ]


def test_cases_report_flags_duplicate_ids(tmp_path):
    _write_cases(tmp_path, [_case("dup"), _case("dup")])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert all("duplicate case id" in case.issues for case in report.cases)


def test_cases_report_accepts_existing_docs_anchor(tmp_path):
    case = _case()
    case["docs"] = "README.md#suitecrm-demo-enterprise-crm"
    _write_cases(tmp_path, [case])
    (tmp_path / "README.md").write_text("# Demo\n\n### SuiteCRM Demo (Enterprise CRM)\n", encoding="utf-8")

    report = validate_cases.build_report(tmp_path)

    assert report.ok is True


def test_cases_report_rejects_missing_docs_anchor(tmp_path):
    _write_cases(tmp_path, [_case()])
    (tmp_path / "README.md").write_text("# Other project\n\n## Other heading\n", encoding="utf-8")

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "docs anchor does not exist: README.md#demo" in report.cases[0].issues


def test_cases_report_rejects_install_package_domain_mismatch(tmp_path):
    case = _case(domain="demo.example.com")
    case["commands"][0] = "cliany-site market install ./other.example.com.cliany-adapter-v0.1.0.tar.gz"
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "install package domain mismatch" in report.cases[0].issues[0]


def test_cases_report_rejects_adapter_command_domain_mismatch(tmp_path):
    case = _case(domain="demo.example.com")
    case["commands"][1] = "cliany-site other.example.com list-items --json"
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "adapter command domain mismatch" in report.cases[0].issues[0]


def test_cases_report_rejects_active_case_without_example_output(tmp_path):
    case = _case()
    del case["example_output"]
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "active case requires example_output" in report.cases[0].issues


def test_cases_report_accepts_candidate_case_with_expected_commands(tmp_path):
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["source_release"] = None
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    case["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is True
    assert report.active == 0
    assert report.candidate == 1
    assert report.cases[0].target_url == "https://demo.example.com/"
    assert report.cases[0].commands == ["cliany-site demo.example.com list-items --json"]
    assert report.cases[0].promotion == case["promotion"]
    assert report.cases[0].promotion_evidence == case["promotion_evidence"]
    assert report.cases[0].to_dict()["promotion"]["online_smoke"].startswith("cliany-site demo.example.com")
    assert report.cases[0].to_dict()["promotion_evidence"]["adapter_package"]["status"] == "pending"
    assert report.cases[0].to_dict()["promotion_command_plan"] == [
        {
            "task": "llm_live_preflight",
            "command": "cliany-site doctor --llm-live --json",
            "source": "doctor.llm_live",
            "missing": False,
        },
        {
            "task": "adapter_package",
            "command": "",
            "source": "commands.explore",
            "missing": True,
        },
        {
            "task": "metadata_validation",
            "command": (
                "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
                "--include-candidate-packages --strict"
            ),
            "source": "candidate_package_validation_command",
            "missing": False,
        },
        {
            "task": "online_smoke",
            "command": "cliany-site demo.example.com list-items --json",
            "source": "commands.adapter",
            "missing": False,
        },
    ]
    assert report.cases[0].to_dict()["promotion_command_plan_count"] == 4
    assert report.cases[0].to_dict()["promotion_command_plan_missing_tasks"] == ["adapter_package"]
    assert report.to_dict()["promotion_command_plan_summary"] == {
        "candidate_count": 1,
        "command_count": 4,
        "expected_command_count": 4,
        "missing_command_count": 1,
        "ready_candidate_count": 0,
        "all_declared": False,
        "task_missing_counts": {
            "llm_live_preflight": 0,
            "adapter_package": 1,
            "metadata_validation": 0,
            "online_smoke": 0,
        },
        "missing_tasks": [
            {
                "case_id": "candidate-case",
                "task": "adapter_package",
                "source": "commands.explore",
            }
        ],
        "missing_cases": [
            {
                "case_id": "candidate-case",
                "missing_task_count": 1,
                "missing_tasks": ["adapter_package"],
            }
        ],
        "primary_missing_task": {
            "case_id": "candidate-case",
            "task": "adapter_package",
            "source": "commands.explore",
        },
    }
    summary = report.to_dict()["promotion_evidence_summary"]
    assert summary["candidate_count"] == 1
    assert summary["task_count"] == 3
    assert summary["status_counts"] == {"blocked": 0, "complete": 0, "pending": 3}
    assert summary["pending_count"] == 3
    assert summary["primary_task"] == {
        "case_id": "candidate-case",
        "task": "adapter_package",
        "status": "pending",
        "evidence": "",
        "next_action": "Generate the adapter package.",
        "priority_rank": 1,
        "priority_reason": "rank 1: complete 0/3, pending 3, blocked 0, missing commands 1",
        "acceptance_criteria": (
            "Attach the generated <domain>-<version>.cliany-adapter.tar.gz "
            "package path or GitHub Release asset name."
        ),
    }
    assert summary["primary_task_detail"] == summary["primary_task"]
    assert summary["primary_next_task"] == summary["primary_task_detail"]
    assert summary["primary_next_task_runbook"] == [
        {
            "step": "llm_live_preflight",
            "command": "cliany-site doctor --llm-live --json",
            "required": True,
            "handoff": validate_cases.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE,
        },
        {
            "step": "adapter_package",
            "command": "",
            "required": False,
            "handoff": (
                "No executable command declared for `adapter_package`; "
                "Generate the adapter package."
            ),
        },
        {
            "step": "acceptance",
            "command": "",
            "required": True,
            "handoff": (
                "Attach the generated <domain>-<version>.cliany-adapter.tar.gz "
                "package path or GitHub Release asset name."
            ),
        },
    ]
    assert summary["primary_next_task_runbook_first_step"] == "llm_live_preflight"
    assert (
        summary["primary_next_task_runbook_first_command"]
        == "cliany-site doctor --llm-live --json"
    )
    assert summary["primary_next_task_runbook_first_command_sha256"] == hashlib.sha256(
        b"cliany-site doctor --llm-live --json"
    ).hexdigest()
    assert summary["primary_next_task_acceptance_criteria"].startswith("Attach the generated")
    assert summary["primary_next_action"] == "Generate the adapter package."
    assert report.cases[0].to_dict()["offline_commands"] == ["python scripts/validate_cases.py --strict"]
    assert report.cases[0].to_dict()["target_url"] == "https://demo.example.com/"
    assert report.cases[0].to_dict()["commands"] == ["cliany-site demo.example.com list-items --json"]


def test_cases_report_rejects_case_without_offline_commands(tmp_path):
    case = _case()
    del case["validation"]["offline_commands"]
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "validation.offline_commands is required" in report.cases[0].issues


def test_cases_report_rejects_non_local_offline_command(tmp_path):
    case = _case()
    case["validation"]["offline_commands"] = ["curl https://example.com"]
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert (
        "validation.offline_commands entry is not a local validation command: curl https://example.com"
        in report.cases[0].issues
    )


def test_cases_report_rejects_candidate_case_without_expected_commands(tmp_path):
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["commands"] = []
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    case["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "candidate case requires expected commands" in report.cases[0].issues


def test_cases_report_rejects_candidate_case_without_example_output(tmp_path):
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    del case["example_output"]
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "candidate case requires example_output" in report.cases[0].issues


def test_cases_report_rejects_candidate_case_without_promotion_checklist(tmp_path):
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "candidate case requires promotion checklist" in report.cases[0].issues


def test_cases_report_rejects_candidate_case_without_promotion_evidence(tmp_path):
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "candidate case requires promotion_evidence" in report.cases[0].issues


def test_cases_report_rejects_incomplete_candidate_promotion_checklist(tmp_path):
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    case["promotion"] = {"adapter_package": "publish package"}
    case["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "candidate promotion.metadata_validation is required" in report.cases[0].issues
    assert "candidate promotion.online_smoke is required" in report.cases[0].issues


def test_cases_report_rejects_invalid_candidate_promotion_evidence(tmp_path):
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    evidence = _promotion_evidence()
    evidence["adapter_package"] = {"status": "complete", "evidence": None, "next_action": None}
    evidence["metadata_validation"] = {"status": "waiting", "evidence": None, "next_action": "Run validation."}
    evidence["online_smoke"] = {"status": "pending", "evidence": None, "next_action": ""}
    case["promotion_evidence"] = evidence
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    issues = report.cases[0].issues
    assert "candidate promotion_evidence.adapter_package.evidence is required when status is complete" in issues
    assert (
        "candidate promotion_evidence.metadata_validation.status must be one of: blocked, complete, pending"
        in issues
    )
    assert "candidate promotion_evidence.online_smoke.next_action is required when status is pending" in issues


def test_cases_report_prioritizes_candidate_with_more_complete_evidence(tmp_path):
    empty = _case("empty-candidate", domain="empty.example")
    empty["status"] = "candidate"
    empty["source_release"] = None
    empty["commands"] = [
        'cliany-site explore "https://empty.example" "search empty" --json',
        "cliany-site empty.example list-items --json",
    ]
    empty["promotion"] = {
        "adapter_package": "publish empty.example-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site empty.example list-items --json",
    }
    empty["promotion_evidence"] = _promotion_evidence()

    nearly_ready = _case("nearly-ready-candidate", domain="ready.example")
    nearly_ready["status"] = "candidate"
    nearly_ready["source_release"] = None
    nearly_ready["commands"] = [
        'cliany-site explore "https://ready.example" "search ready" --json',
        "cliany-site ready.example list-items --json",
    ]
    nearly_ready["promotion"] = {
        "adapter_package": "publish ready.example-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site ready.example list-items --json",
    }
    nearly_ready["promotion_evidence"] = _promotion_evidence()
    nearly_ready["promotion_evidence"]["adapter_package"] = {
        "status": "complete",
        "evidence": "ready.example-0.16.251.cliany-adapter.tar.gz",
        "next_action": "",
    }

    _write_cases(tmp_path, [empty, nearly_ready])

    report = validate_cases.build_report(tmp_path)
    summary = report.to_dict()["promotion_evidence_summary"]

    assert report.ok is True
    assert summary["primary_task"] == {
        "case_id": "nearly-ready-candidate",
        "task": "metadata_validation",
        "status": "pending",
        "evidence": "",
        "next_action": "Run validate_cases with --packages-dir.",
        "priority_rank": 1,
        "priority_reason": "rank 1: complete 1/3, pending 2, blocked 0, missing commands 0",
        "acceptance_criteria": (
            "Paste `python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
            "--include-candidate-packages --strict` output showing the candidate package "
            "passed schema v3, manifest hash, and adapter_domain validation."
        ),
    }
    assert summary["pending_tasks"][0]["case_id"] == "nearly-ready-candidate"
    assert summary["pending_tasks"][0]["task"] == "metadata_validation"
    assert summary["pending_tasks"][0]["priority_rank"] == 1
    assert summary["pending_tasks"][0]["priority_reason"] == (
        "rank 1: complete 1/3, pending 2, blocked 0, missing commands 0"
    )
    assert summary["pending_tasks"][2]["case_id"] == "empty-candidate"
    assert summary["pending_tasks"][2]["priority_rank"] == 2
    assert summary["pending_tasks"][2]["priority_reason"] == (
        "rank 2: complete 0/3, pending 3, blocked 0, missing commands 0"
    )


def test_cases_report_rejects_candidate_legacy_package_hint(tmp_path):
    metadata_validation = "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict"
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["source_release"] = None
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    case["promotion"] = {
        "adapter_package": "publish demo.example.com.cliany-adapter-v0.1.0.tar.gz",
        "metadata_validation": metadata_validation,
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    case["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert (
        "candidate promotion.adapter_package uses legacy package naming; "
        "expected demo.example.com-<version>.cliany-adapter.tar.gz"
    ) in report.cases[0].issues


def test_cases_report_rejects_candidate_version_pinned_package_hint(tmp_path):
    metadata_validation = "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict"
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["source_release"] = None
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-0.1.0.cliany-adapter.tar.gz",
        "metadata_validation": metadata_validation,
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    case["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert (
        "candidate promotion.adapter_package must use version placeholder: "
        "demo.example.com-<version>.cliany-adapter.tar.gz"
    ) in report.cases[0].issues


def test_cases_report_rejects_example_output_case_id_mismatch(tmp_path):
    case = _case("demo-case")
    _write_cases(tmp_path, [case])
    (tmp_path / case["example_output"]).write_text(
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
                    "case_id": "other-case",
                    "sample": True,
                },
            }
        ),
        encoding="utf-8",
    )

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "example_output.meta.case_id must be 'demo-case'" in report.cases[0].issues


def test_cases_report_rejects_example_output_command_mismatch(tmp_path):
    case = _case("demo-case")
    _write_cases(tmp_path, [case])
    (tmp_path / case["example_output"]).write_text(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "command": "other-items",
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

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "example_output.data.command must match manifest commands" in report.cases[0].issues[0]
    assert "'other-items' not in list-items" in report.cases[0].issues[0]


def test_cases_report_rejects_example_output_without_quality(tmp_path):
    case = _case("demo-case")
    _write_cases(tmp_path, [case])
    (tmp_path / case["example_output"]).write_text(
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

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "example_output.data.quality must be an object" in report.cases[0].issues


def test_cases_report_rejects_example_output_failed_quality(tmp_path):
    case = _case("demo-case")
    _write_cases(tmp_path, [case])
    (tmp_path / case["example_output"]).write_text(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "command": "list-items",
                    "results": [{"ok": True, "data": {"items": [{"name": "Example"}]}}],
                    "quality": {"ok": False, "status": "partial", "row_count": 1},
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

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "example_output.data.quality.ok must be true" in report.cases[0].issues
    assert "example_output.data.quality.status must be 'ok'" in report.cases[0].issues


def test_cases_report_rejects_example_output_non_positive_quality_row_count(tmp_path):
    case = _case("demo-case")
    _write_cases(tmp_path, [case])
    (tmp_path / case["example_output"]).write_text(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "command": "list-items",
                    "results": [{"ok": True, "data": {"items": [{"name": "Example"}]}}],
                    "quality": {"ok": True, "status": "ok", "row_count": 0},
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

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "example_output.data.quality.row_count must be positive" in report.cases[0].issues


def test_cases_report_checks_optional_packages_dir(tmp_path):
    case = _case(domain="demo.example.com")
    _write_cases(tmp_path, [case])
    packages_dir = tmp_path / "packages"
    _write_package(
        packages_dir,
        "demo.example.com.cliany-adapter-v0.1.0.tar.gz",
        domain="other.example.com",
    )

    report = validate_cases.build_report(tmp_path, packages_dir=packages_dir)

    assert report.ok is False
    assert report.checked_packages is True
    package = report.cases[0].package
    assert package is not None
    assert package["status"] == "invalid"
    assert "domain mismatch" in package["issues"][0]
    assert (
        "Regenerate the package for the manifest adapter_domain or fix the case adapter_domain."
        in package["next_actions"]
    )


def test_cases_report_accepts_valid_package(tmp_path):
    case = _case(domain="demo.example.com")
    _write_cases(tmp_path, [case])
    packages_dir = tmp_path / "packages"
    _write_package(
        packages_dir,
        "demo.example.com.cliany-adapter-v0.1.0.tar.gz",
        domain="demo.example.com",
    )

    report = validate_cases.build_report(tmp_path, packages_dir=packages_dir)

    assert report.ok is True
    assert report.checked_packages is True
    assert report.cases[0].package["status"] == "ok"
    assert report.cases[0].package["next_actions"] == []


def test_cases_report_skips_candidate_packages_by_default(tmp_path):
    case = _case("candidate-case", domain="demo.example.com")
    case["status"] = "candidate"
    case["source_release"] = None
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    case["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path, packages_dir=tmp_path / "packages")

    assert report.ok is True
    assert report.checked_packages is True
    assert report.checked_candidate_packages is False
    assert report.cases[0].package is None


def test_cases_report_checks_candidate_package_when_requested(tmp_path):
    case = _case("candidate-case", domain="demo.example.com")
    case["status"] = "candidate"
    case["source_release"] = None
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    case["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [case])
    packages_dir = tmp_path / "packages"
    _write_package(
        packages_dir,
        "demo.example.com-0.1.0.cliany-adapter.tar.gz",
        domain="demo.example.com",
    )

    report = validate_cases.build_report(
        tmp_path,
        packages_dir=packages_dir,
        include_candidate_packages=True,
    )

    assert report.ok is True
    assert report.checked_candidate_packages is True
    assert report.cases[0].package["status"] == "ok"


def test_cases_report_reports_missing_candidate_package_when_requested(tmp_path):
    case = _case("candidate-case", domain="demo.example.com")
    case["status"] = "candidate"
    case["source_release"] = None
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    case["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(
        tmp_path,
        packages_dir=tmp_path / "packages",
        include_candidate_packages=True,
    )

    assert report.ok is False
    package = report.cases[0].package
    assert package["status"] == "missing"
    assert package["issue"] == "candidate package file not found"
    assert "demo.example.com-<version>.cliany-adapter.tar.gz" in package["path"]
    assert (
        "Rerun python scripts/validate_cases.py --packages-dir <dir> "
        "--include-candidate-packages --strict."
    ) in package["next_actions"]


def test_cases_report_writes_markdown_report(tmp_path):
    metadata_validation = "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict"
    candidate = _case("candidate-case")
    candidate["status"] = "candidate"
    candidate["source_release"] = None
    candidate["commands"] = ["cliany-site demo.example.com list-items --json"]
    candidate["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": metadata_validation,
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    candidate["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [_case("demo-case"), candidate])
    report = validate_cases.build_report(tmp_path)
    report_path = tmp_path / "reports" / "case-catalog-report.md"

    validate_cases._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "# cliany-site Case Catalog Validation" in text
    assert "| ok | `true` |" in text
    assert "| candidate | `1` |" in text
    assert "| Case | Status | Result | Issues | Package | Promotion | Promotion Evidence |" in text
    assert "| `demo-case` | `active` | `ok` | - | - | - | - |" in text
    assert "| `candidate-case` | `candidate` | `ok` | - | - |" in text
    assert "adapter_package: publish demo.example.com-<version>.cliany-adapter.tar.gz" in text
    assert "adapter_package: pending; next: Generate the adapter package." in text
    assert f"metadata_validation: {metadata_validation}" in text
    assert "online_smoke: cliany-site demo.example.com list-items --json" in text
    assert "## Offline Validation Commands" in text
    assert "| `candidate-case` | python scripts/validate_cases.py --strict |" in text
    assert "## Candidate Handoff Matrix" in text
    assert "| `candidate-case` | https://demo.example.com/ | cliany-site demo.example.com list-items --json |" in text
    assert "without reopening `cases/manifest.json`" in text
    assert "## Candidate Evidence Bundle Commands" in text
    assert "cliany-site cases --case-id candidate-case --evidence-bundle" in text
    assert "cliany-site cases --case-id candidate-case --evidence-bundle --json" in text
    assert "## Candidate Promotion Evidence Summary" in text
    assert "| pending_count | `3` |" in text
    assert "| primary_next_action | Generate the adapter package. |" in text
    assert "| primary_next_task_acceptance_criteria | Attach the generated" in text
    assert "primary_task_detail" in text
    assert "primary_next_task" in text
    assert "## Candidate Primary Runbook" in text
    assert "| `llm_live_preflight` | `cliany-site doctor --llm-live --json` | `true` |" in text
    assert (
        "| `adapter_package` | No command. | `false` | "
        "No executable command declared for `adapter_package`; Generate the adapter package. |"
    ) in text
    assert (
        "| `acceptance` | No command. | `true` | "
        "Attach the generated <domain>-<version>.cliany-adapter.tar.gz"
    ) in text
    assert (
        "| `candidate-case` | `adapter_package` | `pending` | - | "
        "Generate the adapter package. | Attach the generated"
    ) in text
    assert "## Candidate Promotion Command Plan Summary" in text
    assert "| command_count | `4` |" in text
    assert "- `llm_live_preflight`: `cliany-site doctor --llm-live --json`" in text
    assert "| missing_command_count | `1` |" in text
    assert "| all_declared | `false` |" in text
    assert "| `candidate-case` | `adapter_package` |" in text
    assert "## Candidate Promotion Tasks" in text
    assert "### `candidate-case`" in text
    assert "- [ ] `adapter_package`: publish demo.example.com-<version>.cliany-adapter.tar.gz" in text
    assert "  - Status: `pending`" in text
    assert "  - Evidence: Not attached yet." in text
    assert "  - Next action: Generate the adapter package." in text
    assert "  - Acceptance criteria: Attach the generated <domain>-<version>.cliany-adapter.tar.gz" in text
    assert f"- [ ] `metadata_validation`: {metadata_validation}" in text
    assert "- [ ] `online_smoke`: cliany-site demo.example.com list-items --json" in text
    assert "data.quality.ok=true" in text
    assert "row_count>0" in text
    assert "#### Issue Body Template" in text
    assert "## Scope: promote candidate case `candidate-case`" in text
    assert "## Reproduction Context" in text
    assert "- Target URL: https://demo.example.com/" in text
    assert "- Candidate commands:\n  - `cliany-site demo.example.com list-items --json`" in text
    assert "- Offline validation commands:\n  - `python scripts/validate_cases.py --strict`" in text
    assert "## Promotion Command Plan" in text
    assert "- `adapter_package`: `Not declared.`" in text
    assert (
        "- `metadata_validation`: `python scripts/validate_cases.py "
        "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict`"
        in text
    )
    assert "- `online_smoke`: `cliany-site demo.example.com list-items --json`" in text
    assert "## LLM Preflight Gate" in text
    assert "- Command: `cliany-site doctor --llm-live --json`" in text
    assert "generate_adapters.ready=false" in text
    assert "llm_live reports warning/error" in text
    assert "E_LLM_UNAVAILABLE" in text
    assert "provider connection failure" in text
    assert "## Acceptance Criteria" in text
    assert "`metadata_validation`: Paste `python scripts/validate_cases.py" in text
    assert "  - Current status: `pending`" in text
    assert "  - Current evidence: Not attached yet." in text
    assert "  - Acceptance criteria: Paste the read-only adapter command JSON envelope summary" in text
    assert "## Evidence Bundle" in text
    assert "cliany-site cases --case-id candidate-case --evidence-bundle" in text
    assert "cliany-site cases --case-id candidate-case --evidence-bundle --json" in text
    assert "Attach or paste the JSON output in the issue once evidence changes." in text
    assert "## Validation Evidence" in text
    assert "## Non-goals" in text
    assert "Do not mark the case `active` until all three promotion tasks are complete." in text
    assert "Do not require real LLM keys or write runtime state into the repository." in text


def test_cases_report_prints_candidate_promotion_checklist(tmp_path, capsys):
    metadata_validation = "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict"
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["source_release"] = None
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": metadata_validation,
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
    case["promotion_evidence"] = _promotion_evidence()
    _write_cases(tmp_path, [case])
    report = validate_cases.build_report(tmp_path)

    validate_cases._print_text(report)

    text = capsys.readouterr().out
    assert "promotion_evidence_pending: 3" in text
    assert "promotion_evidence_blocked: 0" in text
    assert "promotion_evidence_complete: 0" in text
    assert "promotion_evidence_primary_next_task: candidate-case/adapter_package (pending)" in text
    assert "promotion_evidence_primary: candidate-case/adapter_package (pending)" in text
    assert "promotion_evidence_evidence: Not attached yet." in text
    assert "promotion_evidence_next: Generate the adapter package." in text
    assert "promotion_evidence_primary_runbook: llm_live_preflight -> adapter_package -> acceptance" in text
    assert "promotion:" in text
    assert "adapter_package: publish demo.example.com-<version>.cliany-adapter.tar.gz" in text
    assert f"metadata_validation: {metadata_validation}" in text
    assert "online_smoke: cliany-site demo.example.com list-items --json" in text
    assert "promotion_evidence:" in text
    assert "adapter_package: pending" in text


def test_cases_report_rejects_package_with_legacy_metadata(tmp_path):
    case = _case(domain="demo.example.com")
    _write_cases(tmp_path, [case])
    packages_dir = tmp_path / "packages"
    _write_package(
        packages_dir,
        "demo.example.com.cliany-adapter-v0.1.0.tar.gz",
        domain="demo.example.com",
        metadata_schema_version=2,
    )

    report = validate_cases.build_report(tmp_path, packages_dir=packages_dir)

    assert report.ok is False
    assert "metadata.schema_version must be 3" in report.cases[0].package["issues"]
    assert "Regenerate the adapter metadata with schema_version 3." in report.cases[0].package["next_actions"]


def test_cases_report_rejects_package_hash_mismatch(tmp_path):
    case = _case(domain="demo.example.com")
    _write_cases(tmp_path, [case])
    packages_dir = tmp_path / "packages"
    _write_package(
        packages_dir,
        "demo.example.com.cliany-adapter-v0.1.0.tar.gz",
        domain="demo.example.com",
        bad_hash=True,
    )

    report = validate_cases.build_report(tmp_path, packages_dir=packages_dir)

    assert report.ok is False
    assert "file hash mismatch: metadata.json" in report.cases[0].package["issues"]
    assert (
        "Rebuild the adapter package so manifest.file_hashes match the packaged files."
        in report.cases[0].package["next_actions"]
    )


def test_cases_report_includes_package_next_actions_in_markdown(tmp_path):
    case = _case(domain="demo.example.com")
    _write_cases(tmp_path, [case])
    packages_dir = tmp_path / "packages"
    _write_package(
        packages_dir,
        "demo.example.com.cliany-adapter-v0.1.0.tar.gz",
        domain="other.example.com",
    )
    report = validate_cases.build_report(tmp_path, packages_dir=packages_dir)
    report_path = tmp_path / "reports" / "case-catalog-report.md"

    validate_cases._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "fail: invalid" in text
    assert "domain mismatch" in text
    assert "next: Regenerate the package for the manifest adapter_domain or fix the case adapter_domain." in text
