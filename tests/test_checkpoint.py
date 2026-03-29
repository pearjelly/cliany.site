import json
import os
from pathlib import Path

import pytest

from cliany_site.checkpoint import clear_checkpoint, load_checkpoint, save_checkpoint


@pytest.fixture()
def _use_tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("CLIANY_HOME_DIR", str(tmp_path))
    from cliany_site.config import reset_config

    reset_config()

    from cliany_site import config as _cfg

    monkeypatch.setattr(_cfg, "_config", _cfg.ClanySiteConfig(home_dir=tmp_path))
    yield
    reset_config()


class TestSaveCheckpoint:
    def test_creates_checkpoint_file(self, _use_tmp_home, tmp_path):
        actions = [{"type": "click", "description": "btn"}]
        path_str = save_checkpoint("example.com", "search", actions, [0])
        assert os.path.exists(path_str)

    def test_checkpoint_content(self, _use_tmp_home, tmp_path):
        actions = [
            {"type": "navigate", "url": "https://example.com"},
            {"type": "click", "description": "btn"},
        ]
        path_str = save_checkpoint("example.com", "login", actions, [0], params={"user": "test"})
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
        assert data["domain"] == "example.com"
        assert data["command_name"] == "login"
        assert data["completed_indices"] == [0]
        assert data["total_actions"] == 2
        assert data["params"] == {"user": "test"}
        assert "saved_at" in data

    def test_deduplicates_indices(self, _use_tmp_home, tmp_path):
        actions = [{"type": "click"}, {"type": "click"}]
        path_str = save_checkpoint("d.com", "cmd", actions, [0, 0, 1, 1])
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
        assert data["completed_indices"] == [0, 1]

    def test_sorts_indices(self, _use_tmp_home, tmp_path):
        actions = [{"type": "click"}] * 5
        path_str = save_checkpoint("d.com", "cmd", actions, [3, 1, 4, 0])
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
        assert data["completed_indices"] == [0, 1, 3, 4]

    def test_safe_filename_special_chars(self, _use_tmp_home, tmp_path):
        actions = [{"type": "click"}]
        path_str = save_checkpoint("host:8080", "path/cmd", actions, [])
        assert os.path.exists(path_str)
        assert ":" not in os.path.basename(path_str)


class TestLoadCheckpoint:
    def test_load_existing(self, _use_tmp_home, tmp_path):
        actions = [{"type": "click"}]
        save_checkpoint("example.com", "cmd", actions, [0])
        result = load_checkpoint("example.com", "cmd")
        assert result is not None
        assert result["completed_indices"] == [0]

    def test_load_nonexistent(self, _use_tmp_home, tmp_path):
        assert load_checkpoint("no.com", "nothing") is None

    def test_load_corrupt_file(self, _use_tmp_home, tmp_path):
        ckpt_dir = tmp_path / "checkpoints"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        path = ckpt_dir / "bad.com_cmd.json"
        path.write_text("not valid json", encoding="utf-8")
        assert load_checkpoint("bad.com", "cmd") is None


class TestClearCheckpoint:
    def test_clear_existing(self, _use_tmp_home, tmp_path):
        actions = [{"type": "click"}]
        save_checkpoint("example.com", "cmd", actions, [0])
        assert clear_checkpoint("example.com", "cmd") is True
        assert load_checkpoint("example.com", "cmd") is None

    def test_clear_nonexistent(self, _use_tmp_home, tmp_path):
        assert clear_checkpoint("no.com", "nothing") is False

    def test_save_then_clear_then_load(self, _use_tmp_home, tmp_path):
        actions = [{"type": "click"}, {"type": "type"}]
        save_checkpoint("d.com", "c", actions, [0])
        assert load_checkpoint("d.com", "c") is not None
        clear_checkpoint("d.com", "c")
        assert load_checkpoint("d.com", "c") is None


class TestCheckpointOverwrite:
    def test_overwrite_existing(self, _use_tmp_home, tmp_path):
        actions = [{"type": "click"}, {"type": "type"}, {"type": "select"}]
        save_checkpoint("d.com", "cmd", actions, [0])
        save_checkpoint("d.com", "cmd", actions, [0, 1])
        result = load_checkpoint("d.com", "cmd")
        assert result is not None
        assert result["completed_indices"] == [0, 1]

    def test_default_command_name(self, _use_tmp_home, tmp_path):
        actions = [{"type": "click"}]
        save_checkpoint("d.com", "", actions, [0])
        result = load_checkpoint("d.com", "")
        assert result is not None
        assert result["completed_indices"] == [0]
