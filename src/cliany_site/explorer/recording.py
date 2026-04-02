import dataclasses
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from cliany_site.explorer.models import RecordingManifest, StepRecord


class RecordingManager:
    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            base_dir = Path.home() / ".cliany-site" / "recordings"
        self.base_dir = base_dir

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
        return json.loads(path.read_text(encoding="utf-8"))

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
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        raw_steps = data.pop("steps", [])
        steps = [StepRecord(**s) for s in raw_steps]
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
