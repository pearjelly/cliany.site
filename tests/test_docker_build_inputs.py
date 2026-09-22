import tomllib
from pathlib import Path


def test_docker_copies_required_package_inputs_before_install():
    root = Path(__file__).resolve().parents[1]
    metadata = tomllib.loads((root / "pyproject.toml").read_text())
    before_install = (root / "Dockerfile").read_text().split("RUN pip install", 1)[0]
    assert metadata["project"]["readme"] == "README.md"
    assert "COPY pyproject.toml uv.lock README.md ./" in before_install
    assert metadata["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"] == {
        "cases": "cliany_site/cases",
    }
    assert "COPY cases/ cases/" in before_install
