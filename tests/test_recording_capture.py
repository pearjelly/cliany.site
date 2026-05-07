import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cliany_site.browser.console_capture import ConsoleCapture
from cliany_site.browser.network_capture import NetworkCapture
from cliany_site.explorer.models import StepRecord
from cliany_site.explorer.recording import RecordingManager


def _manager(tmp_path: Path) -> RecordingManager:
    return RecordingManager(base_dir=tmp_path / "recordings")


def _make_step(index: int) -> StepRecord:
    return StepRecord(
        step_index=index,
        action_data={"type": "click", "target": f"btn-{index}"},
        llm_response_raw=f"LLM response {index}",
        timestamp=f"2024-01-01T00:0{index}:00Z",
    )


def _net_request(url: str = "https://api.ex.com/data", size: int = 100) -> dict:
    return {"url": url, "method": "GET", "status": 200, "mime": "application/json", "size": size, "timestamp": 1.0}


def _con_entry(text: str = "page loaded") -> dict:
    return {"level": "info", "text": text, "timestamp": 1.0, "source": "script.js"}


class TestStepHasNetworkConsole:
    def test_step_has_network_and_console_fields(self, tmp_path):
        net_cap = NetworkCapture()
        con_cap = ConsoleCapture()

        with patch("cliany_site.explorer.recording.start_network_capture", return_value=net_cap), \
             patch("cliany_site.explorer.recording.start_console_capture", return_value=con_cap):
            mgr = _manager(tmp_path)
            manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-cap-01")

            net_cap._add_request(_net_request())
            con_cap._add_entry(_con_entry())

            step = _make_step(0)
            mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        record = manifest.steps[0]
        assert record.network is not None
        assert record.console is not None
        assert len(record.network["requests"]) == 1
        assert record.network["requests"][0]["url"] == "https://api.ex.com/data"
        assert record.network["truncated"] is False
        assert len(record.console["entries"]) == 1
        assert record.console["entries"][0]["text"] == "page loaded"
        assert record.console["truncated"] is False

    def test_step_network_console_persisted_in_manifest_json(self, tmp_path):
        import json

        net_cap = NetworkCapture()
        con_cap = ConsoleCapture()

        with patch("cliany_site.explorer.recording.start_network_capture", return_value=net_cap), \
             patch("cliany_site.explorer.recording.start_console_capture", return_value=con_cap):
            mgr = _manager(tmp_path)
            manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-cap-02")
            net_cap._add_request(_net_request("https://ex.com/api/v1"))
            mgr.save_step(manifest, _make_step(0), screenshot_bytes=None, axtree_json=None)

        manifest_file = tmp_path / "recordings" / "ex.com" / "sess-cap-02" / "manifest.json"
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        step_data = data["steps"][0]
        assert step_data["network"]["requests"][0]["url"] == "https://ex.com/api/v1"


class TestDisabledNoFields:
    def test_disabled_network_no_field(self, tmp_path):
        with patch.dict(os.environ, {"CLIANY_CAPTURE_NETWORK": "0", "CLIANY_CAPTURE_CONSOLE": "0"}):
            mgr = _manager(tmp_path)
            manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-dis-01")
            step = _make_step(0)
            mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        record = manifest.steps[0]
        assert record.network is None
        assert record.console is None

    def test_disabled_network_only(self, tmp_path):
        con_cap = ConsoleCapture()

        with patch.dict(os.environ, {"CLIANY_CAPTURE_NETWORK": "0"}), \
             patch("cliany_site.explorer.recording.start_console_capture", return_value=con_cap):
            mgr = _manager(tmp_path)
            manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-dis-02")
            con_cap._add_entry(_con_entry("hello"))
            step = _make_step(0)
            mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        record = manifest.steps[0]
        assert record.network is None
        assert record.console is not None
        assert record.console["entries"][0]["text"] == "hello"


class TestSnapshotTruncation:
    def test_100kb_truncation_network(self, tmp_path):
        net_cap = NetworkCapture()
        con_cap = ConsoleCapture()

        large_url = "https://ex.com/" + "x" * 1000
        with patch("cliany_site.explorer.recording.start_network_capture", return_value=net_cap), \
             patch("cliany_site.explorer.recording.start_console_capture", return_value=con_cap):
            mgr = _manager(tmp_path)
            manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-trunc-01")

            for i in range(200):
                net_cap._add_request({
                    "url": f"{large_url}/{i}",
                    "method": "GET",
                    "status": 200,
                    "mime": "application/json",
                    "size": 0,
                    "timestamp": float(i),
                })

            step = _make_step(0)
            mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        record = manifest.steps[0]
        assert record.network is not None
        assert record.network["truncated"] is True
        assert len(record.network["requests"]) < 200

    def test_small_payload_not_truncated(self, tmp_path):
        net_cap = NetworkCapture()
        con_cap = ConsoleCapture()

        with patch("cliany_site.explorer.recording.start_network_capture", return_value=net_cap), \
             patch("cliany_site.explorer.recording.start_console_capture", return_value=con_cap):
            mgr = _manager(tmp_path)
            manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-trunc-02")

            for i in range(5):
                net_cap._add_request(_net_request(f"https://ex.com/{i}"))

            step = _make_step(0)
            mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)

        record = manifest.steps[0]
        assert record.network is not None
        assert record.network["truncated"] is False
        assert len(record.network["requests"]) == 5


class TestFinalizeCaptureSummary:
    def test_finalize_stores_network_and_console_summary(self, tmp_path):
        net_cap = NetworkCapture()
        con_cap = ConsoleCapture()

        with patch("cliany_site.explorer.recording.start_network_capture", return_value=net_cap), \
             patch("cliany_site.explorer.recording.start_console_capture", return_value=con_cap):
            mgr = _manager(tmp_path)
            manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-fin-01")
            net_cap._add_request(_net_request("https://ex.com/api"))
            con_cap._add_entry(_con_entry("init"))
            mgr.save_step(manifest, _make_step(0), screenshot_bytes=None, axtree_json=None)
            mgr.finalize(manifest, completed=True)

        assert manifest.network_summary is not None
        assert manifest.network_summary["count"] == 1
        assert manifest.console_summary is not None
        assert manifest.console_summary["count"] == 1

    def test_finalize_disabled_no_summaries(self, tmp_path):
        with patch.dict(os.environ, {"CLIANY_CAPTURE_NETWORK": "0", "CLIANY_CAPTURE_CONSOLE": "0"}):
            mgr = _manager(tmp_path)
            manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-fin-02")
            mgr.save_step(manifest, _make_step(0), screenshot_bytes=None, axtree_json=None)
            mgr.finalize(manifest, completed=True)

        assert manifest.network_summary is None
        assert manifest.console_summary is None
