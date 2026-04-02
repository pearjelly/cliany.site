"""TDD tests for RecordingManager — recording lifecycle, persistence, and loading."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from cliany_site.explorer.models import RecordingManifest, StepRecord
from cliany_site.explorer.recording import RecordingManager


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _make_step(index: int, action_type: str = "click") -> StepRecord:
    return StepRecord(
        step_index=index,
        action_data={"type": action_type, "target": f"btn-{index}"},
        llm_response_raw=f"LLM response {index}",
        timestamp=f"2024-01-01T00:0{index}:00Z",
    )


def _manager(tmp_path: Path) -> RecordingManager:
    return RecordingManager(base_dir=tmp_path / "recordings")


# ──────────────────────────────────────────────────────────────
# 1. 目录创建
# ──────────────────────────────────────────────────────────────


class TestStartRecording:
    def test_start_recording_creates_directory(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording(
            domain="example.com",
            url="https://example.com",
            workflow="测试工作流",
            session_id="sess-001",
        )
        rec_dir = tmp_path / "recordings" / "example.com" / "sess-001"
        assert rec_dir.exists(), f"录像目录未创建: {rec_dir}"

    def test_start_recording_returns_manifest(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording(
            domain="example.com",
            url="https://example.com",
            workflow="搜索流程",
            session_id="sess-002",
        )
        assert isinstance(manifest, RecordingManifest)
        assert manifest.domain == "example.com"
        assert manifest.session_id == "sess-002"
        assert manifest.url == "https://example.com"
        assert manifest.workflow == "搜索流程"
        assert manifest.steps == []
        assert manifest.completed is False
        assert manifest.started_at  # non-empty


# ──────────────────────────────────────────────────────────────
# 2. 保存步骤
# ──────────────────────────────────────────────────────────────


class TestSaveStep:
    def test_save_step_with_screenshot(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-010")
        step = _make_step(0)
        screenshot_bytes = b"\x89PNG\r\nfake_image_data"

        mgr.save_step(manifest, step, screenshot_bytes=screenshot_bytes, axtree_json=None)

        assert len(manifest.steps) == 1
        saved_step = manifest.steps[0]
        assert saved_step.screenshot_path is not None
        screenshot_file = Path(saved_step.screenshot_path)
        assert screenshot_file.exists()
        assert screenshot_file.read_bytes() == screenshot_bytes

    def test_save_step_without_screenshot(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-011")
        step = _make_step(0)

        mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        assert len(manifest.steps) == 1
        assert manifest.steps[0].screenshot_path is None

    def test_save_step_without_axtree(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-012")
        step = _make_step(0)

        mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        assert len(manifest.steps) == 1
        assert manifest.steps[0].axtree_snapshot_path is None

    def test_save_step_with_axtree(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-013")
        step = _make_step(0)
        axtree = {"role": "button", "name": "Submit", "children": []}

        mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=axtree)

        assert len(manifest.steps) == 1
        saved_step = manifest.steps[0]
        assert saved_step.axtree_snapshot_path is not None
        axtree_file = Path(saved_step.axtree_snapshot_path)
        assert axtree_file.exists()
        loaded = json.loads(axtree_file.read_text(encoding="utf-8"))
        assert loaded == axtree

    def test_save_step_writes_manifest_json(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-014")
        step = _make_step(0)

        mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        manifest_file = tmp_path / "recordings" / "ex.com" / "sess-014" / "manifest.json"
        assert manifest_file.exists()
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert data["domain"] == "ex.com"
        assert len(data["steps"]) == 1


# ──────────────────────────────────────────────────────────────
# 3. 完整生命周期
# ──────────────────────────────────────────────────────────────


class TestRecordingLifecycle:
    def test_recording_lifecycle(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("github.com", "https://github.com", "搜索仓库", "sess-100")

        for i in range(3):
            step = _make_step(i)
            screenshot = f"fake_png_{i}".encode()
            axtree = {"step": i, "role": "button"}
            mgr.save_step(manifest, step, screenshot_bytes=screenshot, axtree_json=axtree)

        mgr.finalize(manifest, completed=True)

        loaded = mgr.load_recording("github.com", "sess-100")
        assert len(loaded.steps) == 3
        assert loaded.completed is True
        assert loaded.domain == "github.com"
        assert loaded.session_id == "sess-100"
        for i, step in enumerate(loaded.steps):
            assert step.step_index == i

    def test_finalize_sets_completed(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-200")
        step = _make_step(0)
        mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        mgr.finalize(manifest, completed=True)

        loaded = mgr.load_recording("ex.com", "sess-200")
        assert loaded.completed is True

    def test_finalize_sets_not_completed(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-201")
        step = _make_step(0)
        mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        mgr.finalize(manifest, completed=False)

        loaded = mgr.load_recording("ex.com", "sess-201")
        assert loaded.completed is False


# ──────────────────────────────────────────────────────────────
# 4. 回滚标记
# ──────────────────────────────────────────────────────────────


class TestMarkRolledBack:
    def test_mark_rolled_back(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-300")
        for i in range(3):
            mgr.save_step(manifest, _make_step(i), screenshot_bytes=None, axtree_json=None)

        mgr.mark_rolled_back(manifest, step_index=1)

        assert manifest.steps[1].rolled_back is True
        assert manifest.steps[0].rolled_back is False
        assert manifest.steps[2].rolled_back is False

        # 持久化验证
        loaded = mgr.load_recording("ex.com", "sess-300")
        assert loaded.steps[1].rolled_back is True
        assert loaded.steps[0].rolled_back is False


# ──────────────────────────────────────────────────────────────
# 5. 列出录像
# ──────────────────────────────────────────────────────────────


class TestListRecordings:
    def test_list_recordings(self, tmp_path):
        mgr = _manager(tmp_path)
        for sess in ["sess-a", "sess-b"]:
            m = mgr.start_recording("ex.com", "https://ex.com", "wf", sess)
            mgr.save_step(m, _make_step(0), screenshot_bytes=None, axtree_json=None)

        recordings = mgr.list_recordings("ex.com")
        assert len(recordings) == 2
        session_ids = {r.session_id for r in recordings}
        assert session_ids == {"sess-a", "sess-b"}

    def test_nonexistent_domain_list(self, tmp_path):
        mgr = _manager(tmp_path)
        result = mgr.list_recordings("nonexistent.com")
        assert result == []

    def test_list_recordings_only_domain(self, tmp_path):
        mgr = _manager(tmp_path)
        m1 = mgr.start_recording("a.com", "https://a.com", "wf", "sess-x")
        mgr.save_step(m1, _make_step(0), screenshot_bytes=None, axtree_json=None)
        m2 = mgr.start_recording("b.com", "https://b.com", "wf", "sess-y")
        mgr.save_step(m2, _make_step(0), screenshot_bytes=None, axtree_json=None)

        assert len(mgr.list_recordings("a.com")) == 1
        assert len(mgr.list_recordings("b.com")) == 1


# ──────────────────────────────────────────────────────────────
# 6. 加载截图 / AXTree
# ──────────────────────────────────────────────────────────────


class TestLoadStepAssets:
    def test_load_step_screenshot(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-400")
        original_bytes = b"\x89PNG\r\nactual_image_data_here"
        mgr.save_step(manifest, _make_step(0), screenshot_bytes=original_bytes, axtree_json=None)

        loaded_bytes = mgr.load_step_screenshot(manifest, step_index=0)
        assert loaded_bytes == original_bytes

    def test_load_step_axtree(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-401")
        original_axtree = {"role": "button", "name": "Click me", "children": [1, 2, 3]}
        mgr.save_step(manifest, _make_step(0), screenshot_bytes=None, axtree_json=original_axtree)

        loaded_axtree = mgr.load_step_axtree(manifest, step_index=0)
        assert loaded_axtree == original_axtree

    def test_load_step_screenshot_missing_raises(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-402")
        # 保存步骤时不带截图
        mgr.save_step(manifest, _make_step(0), screenshot_bytes=None, axtree_json=None)

        with pytest.raises(FileNotFoundError):
            mgr.load_step_screenshot(manifest, step_index=0)

    def test_load_step_axtree_missing_raises(self, tmp_path):
        mgr = _manager(tmp_path)
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-403")
        # 保存步骤时不带 axtree
        mgr.save_step(manifest, _make_step(0), screenshot_bytes=None, axtree_json=None)

        with pytest.raises(FileNotFoundError):
            mgr.load_step_axtree(manifest, step_index=0)
