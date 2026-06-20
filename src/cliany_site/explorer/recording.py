import dataclasses
import json
import os
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cliany_site.browser.console_capture import ConsoleCapture, start_console_capture, stop_console_capture
from cliany_site.browser.network_capture import NetworkCapture, start_network_capture, stop_network_capture
from cliany_site.explorer.models import RecordingManifest, StepRecord


class RecordingManager:
    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            base_dir = Path.home() / ".cliany-site" / "recordings"
        self.base_dir = base_dir
        self._net_cap: NetworkCapture | None = None
        self._con_cap: ConsoleCapture | None = None

    def _recording_dir(self, domain: str, session_id: str) -> Path:
        return self.base_dir / domain / session_id

    def start_recording(
        self,
        domain: str,
        url: str,
        workflow: str,
        session_id: str,
    ) -> RecordingManifest:
        rec_dir = self._recording_dir(domain, session_id)
        rec_dir.mkdir(parents=True, exist_ok=True)
        # 初始化 capture
        self._net_cap = start_network_capture(None) if os.environ.get("CLIANY_CAPTURE_NETWORK", "1") != "0" else None
        self._con_cap = start_console_capture(None) if os.environ.get("CLIANY_CAPTURE_CONSOLE", "1") != "0" else None
        return RecordingManifest(
            domain=domain,
            session_id=session_id,
            url=url,
            workflow=workflow,
            started_at=datetime.now(UTC).isoformat(),
        )

    def save_step(
        self,
        manifest: RecordingManifest,
        step_record: StepRecord,
        screenshot_bytes: bytes | None,
        axtree_json: dict | None,
    ) -> None:
        rec_dir = self._recording_dir(manifest.domain, manifest.session_id)
        n = step_record.step_index

        if screenshot_bytes is not None:
            png_path = rec_dir / f"step_{n}.png"
            self._write_bytes_atomic(png_path, screenshot_bytes)
            step_record.screenshot_path = str(png_path)
        else:
            step_record.screenshot_path = None

        if axtree_json is not None:
            ax_path = rec_dir / f"step_{n}_axtree.json"
            self._write_text_atomic(ax_path, json.dumps(axtree_json, ensure_ascii=False))
            step_record.axtree_snapshot_path = str(ax_path)
        else:
            step_record.axtree_snapshot_path = None

        # 填入 network snapshot
        if self._net_cap is not None:
            snapshot_data = stop_network_capture(self._net_cap)
            # 截断保护：序列化后超 100KB 则丢弃尾部请求
            import json as _json
            raw_json = _json.dumps(snapshot_data["requests"], ensure_ascii=False)
            if len(raw_json.encode()) > 100 * 1024:
                # 逐条添加直到超限
                kept = []
                total = 0
                for req in snapshot_data["requests"]:
                    req_bytes = len(_json.dumps(req, ensure_ascii=False).encode())
                    if total + req_bytes > 100 * 1024:
                        break
                    kept.append(req)
                    total += req_bytes
                step_record.network = {
                    "requests": kept,
                    "truncated": True,
                    "total_size": total,
                    "count": len(kept),
                }
            else:
                step_record.network = snapshot_data
        else:
            step_record.network = None

        # 填入 console snapshot
        if self._con_cap is not None:
            step_record.console = stop_console_capture(self._con_cap)
        else:
            step_record.console = None

        manifest.steps.append(step_record)
        self._write_manifest(manifest)

    def mark_rolled_back(self, manifest: RecordingManifest, step_index: int) -> None:
        for step in manifest.steps:
            if step.step_index == step_index:
                step.rolled_back = True
                break
        self._write_manifest(manifest)

    def finalize(self, manifest: RecordingManifest, completed: bool) -> None:
        manifest.completed = completed
        if self._net_cap is not None:
            net_data = stop_network_capture(self._net_cap)
            manifest.network_summary = {"count": net_data["count"], "total_size": net_data["total_size"]}
        else:
            manifest.network_summary = None
        if self._con_cap is not None:
            con_data = stop_console_capture(self._con_cap)
            manifest.console_summary = {"count": con_data["count"]}
        else:
            manifest.console_summary = None
        self._write_manifest(manifest)

    def list_recordings(self, domain: str) -> list[RecordingManifest]:
        domain_dir = self.base_dir / domain
        if not domain_dir.exists():
            return []

        results: list[RecordingManifest] = []
        for manifest_file in sorted(domain_dir.glob("*/manifest.json")):
            try:
                manifest = self._read_manifest(manifest_file)
                results.append(manifest)
            except (json.JSONDecodeError, OSError, KeyError, TypeError):
                continue

        results.sort(key=lambda m: m.started_at)
        return results

    def load_recording(self, domain: str, session_id: str) -> RecordingManifest:
        manifest_file = self._recording_dir(domain, session_id) / "manifest.json"
        return self._read_manifest(manifest_file)

    def load_step_screenshot(self, manifest: RecordingManifest, step_index: int) -> bytes:
        step = self._find_step(manifest, step_index)
        if step.screenshot_path is None:
            raise FileNotFoundError(f"步骤 {step_index} 没有截图 (screenshot_path is None)")
        path = Path(step.screenshot_path)
        if not path.exists():
            raise FileNotFoundError(f"截图文件不存在: {path}")
        return path.read_bytes()

    def load_step_axtree(self, manifest: RecordingManifest, step_index: int) -> dict:
        step = self._find_step(manifest, step_index)
        if step.axtree_snapshot_path is None:
            raise FileNotFoundError(f"步骤 {step_index} 没有 AXTree 快照 (axtree_snapshot_path is None)")
        path = Path(step.axtree_snapshot_path)
        if not path.exists():
            raise FileNotFoundError(f"AXTree 文件不存在: {path}")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise TypeError(f"AXTree 快照不是对象: {path}")
        return dict(loaded)

    def _find_step(self, manifest: RecordingManifest, step_index: int) -> StepRecord:
        for step in manifest.steps:
            if step.step_index == step_index:
                return step
        raise KeyError(f"步骤 {step_index} 不存在于 manifest")

    def _write_manifest(self, manifest: RecordingManifest) -> None:
        rec_dir = self._recording_dir(manifest.domain, manifest.session_id)
        manifest_file = rec_dir / "manifest.json"
        data = dataclasses.asdict(manifest)
        self._write_text_atomic(manifest_file, json.dumps(data, ensure_ascii=False, indent=2))

    def _read_manifest(self, manifest_file: Path) -> RecordingManifest:
        raw_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        if not isinstance(raw_data, dict):
            raise TypeError(f"manifest 格式错误: {manifest_file}")

        data: dict[str, Any] = dict(raw_data)
        raw_steps = data.pop("steps", [])
        if not isinstance(raw_steps, list):
            raise TypeError(f"manifest steps 格式错误: {manifest_file}")

        steps: list[StepRecord] = []
        for raw_step in raw_steps:
            if not isinstance(raw_step, Mapping):
                raise TypeError(f"step 记录格式错误: {manifest_file}")
            steps.append(StepRecord(**dict(raw_step)))

        manifest = RecordingManifest(**data)
        manifest.steps = steps
        return manifest

    def _write_bytes_atomic(self, target: Path, content: bytes) -> None:
        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=parent, delete=False, suffix=".tmp") as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)

    def _write_text_atomic(self, target: Path, content: str) -> None:
        self._write_bytes_atomic(target, content.encode("utf-8"))
