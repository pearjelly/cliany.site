import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import portalocker

if TYPE_CHECKING:
    from browser_use.browser.session import BrowserSession

from cliany_site.config import get_config

logger = logging.getLogger(__name__)


def _session_path(domain: str) -> Path:
    sessions_dir = get_config().sessions_dir
    sessions_dir.mkdir(parents=True, exist_ok=True)
    # 将 domain 中的非法文件名字符替换为 _
    safe_domain = domain.replace("/", "_").replace(":", "_")
    return sessions_dir / f"{safe_domain}.json"


# =========== 低层（纯数据 I/O，不依赖浏览器）===========


def save_session_data(domain: str, data: dict) -> str:
    """将 Session 数据 dict 写入 ~/.cliany-site/sessions/<domain>.json，返回文件路径

    默认使用加密存储，加密失败时回退到明文。
    """
    try:
        from cliany_site.security import save_encrypted_session

        return save_encrypted_session(domain, data)
    except Exception:  # noqa: BLE001
        logger.debug("加密存储不可用，回退到明文: domain=%s", domain)

    path = _session_path(domain)
    payload = {
        "domain": domain,
        "cookies": data.get("cookies", []),
        "localStorage": data.get("localStorage", {}),
        "saved_at": datetime.now(UTC).isoformat(),
        "expires_hint": data.get("expires_hint"),
    }
    lock_file = path.with_suffix(".lock")
    with portalocker.Lock(str(lock_file), timeout=10, mode="a"):
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, indent=2))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, str(path))
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    return str(path)


def load_session_data(domain: str) -> dict | None:
    """从文件加载 Session 数据（自动识别加密/明文），不存在时返回 None"""
    try:
        from cliany_site.security import load_encrypted_session

        result = load_encrypted_session(domain)
        if result is not None:
            return result
    except Exception:  # noqa: BLE001
        logger.debug("加密读取失败，尝试明文: domain=%s", domain)

    path = _session_path(domain)
    if not path.exists():
        return None
    try:
        data: dict | None = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return None


def check_session(domain: str) -> dict:
    """检查 Session 文件是否存在及其有效期信息"""
    path = _session_path(domain)
    if not path.exists():
        return {"exists": False, "domain": domain, "path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "exists": True,
            "domain": domain,
            "path": str(path),
            "saved_at": data.get("saved_at"),
            "expires_hint": data.get("expires_hint"),
        }
    except (json.JSONDecodeError, OSError):
        return {
            "exists": False,
            "domain": domain,
            "path": str(path),
            "error": "parse_error",
        }


def clear_session(domain: str) -> bool:
    """删除 Session 文件，成功返回 True，文件不存在返回 False"""
    path = _session_path(domain)
    if path.exists():
        path.unlink()
        return True
    return False


# =========== 高层（浏览器交互）===========


async def save_session(domain: str, browser_session: "BrowserSession") -> tuple[str, int]:
    """从 BrowserSession 通过 CDP 提取 cookies，保存到文件。

    Returns:
        (文件路径, cookies 数量) 的元组

    Raises:
        RuntimeError: 无法从浏览器获取 cookies 时抛出
    """
    try:
        cookies: list[Any] = await browser_session._cdp_get_cookies()
    except Exception as e:
        raise RuntimeError(f"无法从浏览器获取 Cookie: {e}") from e

    cookie_list = [
        c.model_dump() if hasattr(c, "model_dump") else dict(c)
        for c in cookies
    ]
    data = {
        "cookies": cookie_list,
        "localStorage": {},
    }
    path = save_session_data(domain, data)
    logger.info("Session 已保存: domain=%s cookies=%d path=%s", domain, len(cookie_list), path)
    return path, len(cookie_list)


async def load_session(domain: str, browser_session: "BrowserSession") -> bool:
    """从文件加载 Session 数据，通过 CDP 注入 cookies 到浏览器"""
    session_data = load_session_data(domain)
    if not session_data:
        logger.debug("Session 不存在: domain=%s", domain)
        return False

    cookies = session_data.get("cookies", [])
    if not cookies:
        return True

    try:
        await browser_session._cdp_set_cookies(cookies)
        return True
    except (OSError, RuntimeError, ValueError):
        return False
