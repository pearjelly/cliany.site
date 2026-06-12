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
            "online": "read-only command returns rows",
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
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is True
    assert report.active == 0
    assert report.candidate == 1
    assert report.cases[0].promotion == case["promotion"]
    assert report.cases[0].to_dict()["promotion"]["online_smoke"].startswith("cliany-site demo.example.com")


def test_cases_report_rejects_candidate_case_without_expected_commands(tmp_path):
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["commands"] = []
    case["promotion"] = {
        "adapter_package": "publish demo.example.com-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages --strict",
        "online_smoke": "cliany-site demo.example.com list-items --json",
    }
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


def test_cases_report_rejects_incomplete_candidate_promotion_checklist(tmp_path):
    case = _case("candidate-case")
    case["status"] = "candidate"
    case["commands"] = ["cliany-site demo.example.com list-items --json"]
    case["promotion"] = {"adapter_package": "publish package"}
    _write_cases(tmp_path, [case])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert "candidate promotion.metadata_validation is required" in report.cases[0].issues
    assert "candidate promotion.online_smoke is required" in report.cases[0].issues


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
    _write_cases(tmp_path, [_case("demo-case"), candidate])
    report = validate_cases.build_report(tmp_path)
    report_path = tmp_path / "reports" / "case-catalog-report.md"

    validate_cases._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "# cliany-site Case Catalog Validation" in text
    assert "| ok | `true` |" in text
    assert "| candidate | `1` |" in text
    assert "| Case | Status | Result | Issues | Package | Promotion |" in text
    assert "| `demo-case` | `active` | `ok` | - | - | - |" in text
    assert "| `candidate-case` | `candidate` | `ok` | - | - |" in text
    assert "adapter_package: publish demo.example.com-<version>.cliany-adapter.tar.gz" in text
    assert f"metadata_validation: {metadata_validation}" in text
    assert "online_smoke: cliany-site demo.example.com list-items --json" in text


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
    _write_cases(tmp_path, [case])
    report = validate_cases.build_report(tmp_path)

    validate_cases._print_text(report)

    text = capsys.readouterr().out
    assert "promotion:" in text
    assert "adapter_package: publish demo.example.com-<version>.cliany-adapter.tar.gz" in text
    assert f"metadata_validation: {metadata_validation}" in text
    assert "online_smoke: cliany-site demo.example.com list-items --json" in text


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
