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
