import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cliany_site.snapshot import (
    list_snapshots,
    load_snapshot,
    save_explore_snapshots,
    save_snapshot,
)


@pytest.fixture()
def _use_tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIANY_HOME_DIR", str(tmp_path))
    from cliany_site.config import reset_config

    reset_config()

    from cliany_site import config as _cfg

    monkeypatch.setattr(_cfg, "_config", _cfg.ClanySiteConfig(home_dir=tmp_path))
    yield
    reset_config()


class TestSaveSnapshot:
    def test_creates_snapshot_file(self, _use_tmp_home, tmp_path):
        elements = [{"target_name": "Search", "target_role": "button", "target_ref": "42"}]
        path = save_snapshot("example.com", "search", elements, "https://example.com")
        assert Path(path).exists()

    def test_snapshot_content(self, _use_tmp_home, tmp_path):
        elements = [
            {"target_name": "Login", "target_role": "link", "target_ref": "10"},
            {"target_name": "Register", "target_role": "link", "target_ref": "11"},
        ]
        path = save_snapshot("example.com", "login", elements, "https://example.com/login")
        data = json.loads(Path(path).read_text(encoding="utf-8"))

        assert data["domain"] == "example.com"
        assert data["command_name"] == "login"
        assert data["page_url"] == "https://example.com/login"
        assert data["element_count"] == 2
        assert len(data["elements"]) == 2
        assert "saved_at" in data

    def test_safe_domain_filename(self, _use_tmp_home, tmp_path):
        elements = [{"target_name": "btn", "target_ref": "1"}]
        path = save_snapshot("host:8080", "path/cmd", elements)
        assert Path(path).exists()
        assert ":" not in Path(path).parent.parent.name

    def test_empty_elements(self, _use_tmp_home, tmp_path):
        path = save_snapshot("example.com", "empty", [])
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["element_count"] == 0
        assert data["elements"] == []

    def test_overwrites_existing(self, _use_tmp_home, tmp_path):
        save_snapshot("example.com", "cmd", [{"target_ref": "1"}])
        save_snapshot("example.com", "cmd", [{"target_ref": "2"}, {"target_ref": "3"}])
        snap = load_snapshot("example.com", "cmd")
        assert snap is not None
        assert snap["element_count"] == 2


class TestLoadSnapshot:
    def test_returns_none_when_missing(self, _use_tmp_home, tmp_path):
        result = load_snapshot("nonexistent.com", "nothing")
        assert result is None

    def test_round_trip(self, _use_tmp_home, tmp_path):
        elements = [{"target_name": "Submit", "target_role": "button", "target_ref": "99"}]
        save_snapshot("test.org", "submit", elements, "https://test.org/form")
        loaded = load_snapshot("test.org", "submit")

        assert loaded is not None
        assert loaded["domain"] == "test.org"
        assert loaded["command_name"] == "submit"
        assert loaded["page_url"] == "https://test.org/form"
        assert len(loaded["elements"]) == 1
        assert loaded["elements"][0]["target_name"] == "Submit"

    def test_returns_none_for_corrupt_json(self, _use_tmp_home, tmp_path):
        from cliany_site.config import get_config

        snap_dir = get_config().adapters_dir / "bad.com" / "snapshots"
        snap_dir.mkdir(parents=True)
        (snap_dir / "broken.json").write_text("{invalid json", encoding="utf-8")
        result = load_snapshot("bad.com", "broken")
        assert result is None


class TestListSnapshots:
    def test_empty_when_no_dir(self, _use_tmp_home, tmp_path):
        result = list_snapshots("nonexistent.com")
        assert result == []

    def test_lists_saved_snapshots(self, _use_tmp_home, tmp_path):
        save_snapshot("example.com", "search", [{"target_ref": "1"}])
        save_snapshot("example.com", "login", [{"target_ref": "2"}])
        save_snapshot("example.com", "register", [{"target_ref": "3"}])

        result = list_snapshots("example.com")
        assert set(result) == {"search", "login", "register"}

    def test_does_not_include_other_domain(self, _use_tmp_home, tmp_path):
        save_snapshot("a.com", "cmd1", [{"target_ref": "1"}])
        save_snapshot("b.com", "cmd2", [{"target_ref": "2"}])

        assert list_snapshots("a.com") == ["cmd1"]
        assert list_snapshots("b.com") == ["cmd2"]


class TestSaveExploreSnapshots:
    def _make_explore_result(self, commands, actions):
        result = MagicMock()
        result.commands = commands
        result.actions = actions
        return result

    def _make_command(self, name, action_steps):
        cmd = MagicMock()
        cmd.name = name
        cmd.action_steps = action_steps
        return cmd

    def _make_action(self, target_name, target_role, target_ref, page_url="", action_type="click"):
        action = MagicMock()
        action.target_name = target_name
        action.target_role = target_role
        action.target_ref = target_ref
        action.target_attributes = {"id": f"attr-{target_ref}"}
        action.description = f"操作 {target_name}"
        action.action_type = action_type
        action.page_url = page_url
        return action

    def test_saves_from_action_steps(self, _use_tmp_home, tmp_path):
        actions = [
            self._make_action("Search", "button", "42", "https://example.com"),
            self._make_action("Input", "textbox", "43"),
        ]
        commands = [self._make_command("search", [0, 1])]
        explore = self._make_explore_result(commands, actions)

        saved = save_explore_snapshots("example.com", explore)
        assert len(saved) == 1

        snap = load_snapshot("example.com", "search")
        assert snap is not None
        assert snap["element_count"] == 2

    def test_uses_selector_maps_when_provided(self, _use_tmp_home, tmp_path):
        commands = [self._make_command("cmd1", [0])]
        explore = self._make_explore_result(commands, [self._make_action("X", "btn", "1")])

        selector_maps = {
            "cmd1": [
                {"target_name": "Override", "target_role": "link", "target_ref": "99"},
            ]
        }
        saved = save_explore_snapshots("example.com", explore, selector_maps)
        assert len(saved) == 1

        snap = load_snapshot("example.com", "cmd1")
        assert snap is not None
        assert snap["elements"][0]["target_name"] == "Override"

    def test_skips_commands_without_elements(self, _use_tmp_home, tmp_path):
        commands = [self._make_command("empty_cmd", [])]
        explore = self._make_explore_result(commands, [])

        saved = save_explore_snapshots("example.com", explore)
        assert saved == []

    def test_returns_empty_for_none_result(self, _use_tmp_home, tmp_path):
        assert save_explore_snapshots("example.com", None) == []

    def test_returns_empty_for_no_commands_attr(self, _use_tmp_home, tmp_path):
        obj = MagicMock(spec=[])  # no 'commands' attribute
        assert save_explore_snapshots("example.com", obj) == []
