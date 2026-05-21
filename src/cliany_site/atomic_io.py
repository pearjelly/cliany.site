import logging
from pathlib import Path
import json
import os
import tempfile

logger = logging.getLogger(__name__)


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, suffix='.tmp', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path = Path(f.name)
    os.replace(temp_path, path)


def atomic_read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        with path.open(encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.error("解析失败: %s", path, exc_info=True)
        return default