from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cliany_site.config import get_config

logger = logging.getLogger(__name__)


def _snapshots_dir(domain: str) -> Path:
    safe = domain.replace("/", "_").replace(":", "_").strip() or "unknown-domain"
    return get_config().adapters_dir / safe / "snapshots"


def _snapshot_path(domain: str, command_name: str) -> Path:
    safe_cmd = command_name.replace("/", "_").replace(":", "_") or "default"
    return _snapshots_dir(domain) / f"{safe_cmd}.json"


def save_snapshot(
    domain: str,
    command_name: str,
    selector_entries: list[dict[str, Any]],
    page_url: str = "",
) -> str:
    snap_dir = _snapshots_dir(domain)
    snap_dir.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(domain, command_name)

    data = {
        "domain": domain,
        "command_name": command_name,
        "page_url": page_url,
        "element_count": len(selector_entries),
        "elements": selector_entries,
        "saved_at": datetime.now(UTC).isoformat(),
    }

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.debug("快照已保存: %s (%d 个元素)", path, len(selector_entries))
    return str(path)


def load_snapshot(domain: str, command_name: str) -> dict[str, Any] | None:
    path = _snapshot_path(domain, command_name)
    if not path.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        logger.debug("快照已加载: %s (%d 个元素)", path, data.get("element_count", 0))
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("快照加载失败: %s", exc)
        return None


def list_snapshots(domain: str) -> list[str]:
    snap_dir = _snapshots_dir(domain)
    if not snap_dir.exists():
        return []
    return [p.stem for p in snap_dir.glob("*.json")]


def save_explore_snapshots(
    domain: str,
    explore_result: Any,
    selector_maps: dict[str, list[dict[str, Any]]] | None = None,
) -> list[str]:
    if not explore_result or not hasattr(explore_result, "commands"):
        return []

    saved: list[str] = []

    for cmd in explore_result.commands:
        cmd_name = getattr(cmd, "name", "") or "default"

        elements: list[dict[str, Any]] = []
        page_url = ""
        action_steps = getattr(cmd, "action_steps", []) or []

        if selector_maps and cmd_name in selector_maps:
            elements = selector_maps[cmd_name]
        else:
            for step_idx in action_steps:
                actions = getattr(explore_result, "actions", [])
                if 0 <= step_idx < len(actions):
                    action = actions[step_idx]
                    entry: dict[str, Any] = {
                        "target_name": getattr(action, "target_name", ""),
                        "target_role": getattr(action, "target_role", ""),
                        "target_ref": getattr(action, "target_ref", ""),
                        "target_attributes": dict(getattr(action, "target_attributes", {}) or {}),
                        "description": getattr(action, "description", ""),
                        "action_type": getattr(action, "action_type", ""),
                    }
                    if not page_url:
                        page_url = getattr(action, "page_url", "")
                    elements.append(entry)

        if elements:
            path = save_snapshot(domain, cmd_name, elements, page_url)
            saved.append(path)

    return saved
