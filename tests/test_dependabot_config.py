from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_dependabot_groups_github_action_updates_without_stale_inventory():
    path = ROOT / ".github" / "dependabot.yml"
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)

    github_actions = next(
        item for item in data["updates"] if item["package-ecosystem"] == "github-actions"
    )

    assert github_actions["groups"] == {"github-actions": {"patterns": ["*"]}}
    assert "actions/checkout@v4" not in text
    assert "astral-sh/setup-uv@v5" not in text
    assert "actions/setup-python@v5" not in text
    assert "actions/upload-artifact@v4" not in text
    assert "actions/download-artifact@v4" not in text
