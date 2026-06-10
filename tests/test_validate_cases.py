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
        "commands": [
            f"cliany-site market install ./{domain}.cliany-adapter-v0.1.0.tar.gz",
            f"cliany-site {domain} list-items --json",
        ],
        "validation": {
            "offline": "metadata validates",
            "online": "read-only command returns rows",
        },
    }


def _write_package(packages_dir: Path, filename: str, *, domain: str) -> None:
    packages_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest_version": "1",
        "domain": domain,
        "files": ["commands.py", "metadata.json"],
        "file_hashes": {"commands.py": "a" * 64, "metadata.json": "b" * 64},
    }
    with tarfile.open(packages_dir / filename, "w:gz") as tar:
        data = json.dumps(manifest).encode("utf-8")
        info = tarfile.TarInfo(name="manifest.json")
        info.size = len(data)
        tar.addfile(info, BytesIO(data))


def test_current_cases_manifest_validates_without_packages():
    report = validate_cases.build_report(ROOT)

    assert report.ok is True
    assert report.active >= 4
    assert report.known_gap >= 1
    assert report.checked_packages is False


def test_cases_report_flags_duplicate_ids(tmp_path):
    _write_cases(tmp_path, [_case("dup"), _case("dup")])

    report = validate_cases.build_report(tmp_path)

    assert report.ok is False
    assert all("duplicate case id" in case.issues for case in report.cases)


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
