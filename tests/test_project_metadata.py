import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_metadata_has_pypi_description():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]

    assert project["description"]
    readme = project["readme"]
    assert readme == "README.md"
    assert (ROOT / readme).exists()
