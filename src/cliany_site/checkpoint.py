from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cliany_site.config import get_config

logger = logging.getLogger(__name__)


def _checkpoints_dir() -> Path:
    return get_config().home_dir / "checkpoints"


def _checkpoint_path(domain: str, command_name: str) -> Path:
    safe_domain = domain.replace("/", "_").replace(":", "_")
    safe_cmd = command_name.replace("/", "_").replace(":", "_") or "default"
    return _checkpoints_dir() / f"{safe_domain}_{safe_cmd}.json"


def save_checkpoint(
    domain: str,
    command_name: str,
    actions_data: list[dict[str, Any]],
    completed_indices: list[int],
    params: dict[str, Any] | None = None,
) -> str:
    ckpt_dir = _checkpoints_dir()
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    path = _checkpoint_path(domain, command_name)

    data = {
        "domain": domain,
        "command_name": command_name,
        "completed_indices": sorted(set(completed_indices)),
        "total_actions": len(actions_data),
        "params": params,
        "saved_at": datetime.now(UTC).isoformat(),
    }

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.debug("断点已保存: %s (已完成 %d/%d)", path, len(completed_indices), len(actions_data))
    return str(path)


def load_checkpoint(domain: str, command_name: str) -> dict[str, Any] | None:
    path = _checkpoint_path(domain, command_name)
    if not path.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        logger.debug(
            "断点已加载: %s (已完成 %d/%d)",
            path,
            len(data.get("completed_indices", [])),
            data.get("total_actions", 0),
        )
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("断点加载失败: %s", exc)
        return None


def clear_checkpoint(domain: str, command_name: str) -> bool:
    path = _checkpoint_path(domain, command_name)
    if path.exists():
        path.unlink()
        logger.debug("断点已清除: %s", path)
        return True
    return False
