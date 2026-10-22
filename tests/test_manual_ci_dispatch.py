from pathlib import Path

import yaml


def test_manual_ci_reuses_the_existing_offline_release_gates():
    workflow = yaml.safe_load((Path(__file__).parents[1] / ".github/workflows/ci.yml").read_text())
    triggers = workflow.get("on", workflow.get(True))
    assert "workflow_dispatch" in triggers
    assert "workflow_call" in triggers
    assert triggers["push"]["branches"] == ["master"]
    assert triggers["pull_request"]["branches"] == ["master"]
    assert str(workflow["env"]["CLIANY_QA_OFFLINE"]) == "1"
