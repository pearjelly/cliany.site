import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SCRIPT = SCRIPTS / "plan_next_iteration.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("plan_next_iteration", SCRIPT)
assert SPEC is not None
plan_next_iteration = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = plan_next_iteration
SPEC.loader.exec_module(plan_next_iteration)


def _write_pyproject(root: Path, version: str = "0.16.1") -> None:
    (root / "pyproject.toml").write_text(
        f"""
[project]
name = "cliany-site"
version = "{version}"
""",
        encoding="utf-8",
    )


def _readiness_report() -> SimpleNamespace:
    return SimpleNamespace(
        ok=False,
        target_version="0.16.2",
        blockers=["release draft validation failed"],
        min_case_assets=8,
        cadence=SimpleNamespace(
            commit_day_count=2,
            min_commit_days=3,
        ),
        cases=SimpleNamespace(
            active=4,
            candidate=3,
            known_gap=1,
            total=8,
            cases=[
                SimpleNamespace(id="pypi-project-search", status="candidate"),
                SimpleNamespace(id="npm-package-search", status="candidate"),
                SimpleNamespace(id="search-extraction-gap", status="known-gap"),
            ],
        ),
    )


def _publication_report() -> SimpleNamespace:
    return SimpleNamespace(
        ok=False,
        branch="master",
        ahead_count=2,
        latest_tag="v0.16.1",
        tag_published=False,
    )


def test_plan_defaults_to_next_patch_version(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_publication_report(),
    )

    assert plan.current_version == "0.16.1"
    assert plan.target_version == "0.16.2"
    assert plan.recommended_theme == "发布可见性"
    assert "latest local release is not published" in plan.blockers
    assert plan.candidate_cases == ["pypi-project-search", "npm-package-search"]


def test_plan_json_keeps_actionable_validation_commands(tmp_path):
    _write_pyproject(tmp_path)

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_publication_report(),
    )
    data = plan.to_dict()

    assert data["release_draft_path"] == "docs/releases/v0.16.2-draft.md"
    assert "python scripts/check_release_publication.py --json" in data["validation_commands"]
    assert "python scripts/validate_cases.py --strict" in data["validation_commands"]
    assert any("push `master`" in action for action in data["next_actions"])


def test_plan_cli_writes_json_for_current_repo(capsys):
    exit_code = plan_next_iteration.main(["--json", "--target-version", "0.16.2"])

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["target_version"] == "0.16.2"
    assert "recommended_theme" in payload
    assert "next_actions" in payload
