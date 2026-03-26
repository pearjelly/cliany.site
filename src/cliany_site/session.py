import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_use.browser.session import BrowserSession


SESSIONS_DIR = Path.home() / ".cliany-site" / "sessions"


def _session_path(domain: str) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    # 将 domain 中的非法文件名字符替换为 _
    safe_domain = domain.replace("/", "_").replace(":", "_")
    return SESSIONS_DIR / f"{safe_domain}.json"


# =========== 低层（纯数据 I/O，不依赖浏览器）===========


def save_session_data(domain: str, data: dict) -> str:
    """将 Session 数据 dict 写入 ~/.cliany-site/sessions/<domain>.json，返回文件路径"""
    path = _session_path(domain)
    payload = {
        "domain": domain,
        "cookies": data.get("cookies", []),
        "localStorage": data.get("localStorage", {}),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "expires_hint": data.get("expires_hint", None),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_session_data(domain: str) -> dict | None:
    """从文件加载 Session 数据，不存在时返回 None"""
    path = _session_path(domain)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
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
    except Exception:
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


async def save_session(
    domain: str, browser_session: "BrowserSession"
) -> tuple[str, int]:
    """从 BrowserSession 通过 CDP 提取 cookies，保存到文件。

    Returns:
        (文件路径, cookies 数量) 的元组

    Raises:
        RuntimeError: 无法从浏览器获取 cookies 时抛出
    """
    try:
        cookies = await browser_session._cdp_get_cookies()
    except Exception as e:
        raise RuntimeError(f"无法从浏览器获取 Cookie: {e}") from e

    cookie_list = [
        c.model_dump() if hasattr(c, "model_dump") else dict(c)  # type: ignore[union-attr]
        for c in cookies
    ]
    data = {
        "cookies": cookie_list,
        "localStorage": {},
    }
    path = save_session_data(domain, data)
    return path, len(cookie_list)


async def load_session(domain: str, browser_session: "BrowserSession") -> bool:
    """从文件加载 Session 数据，通过 CDP 注入 cookies 到浏览器"""
    session_data = load_session_data(domain)
    if not session_data:
        return False

    cookies = session_data.get("cookies", [])
    if not cookies:
        return True

    try:
        await browser_session._cdp_set_cookies(cookies)
        return True
    except Exception:
        return False
