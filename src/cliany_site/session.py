import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from browser_use.browser.session import BrowserSession

from cliany_site.config import get_config

logger = logging.getLogger(__name__)


def _session_path(domain: str) -> Path:
    sessions_dir = get_config().sessions_dir
    sessions_dir.mkdir(parents=True, exist_ok=True)
    # 将 domain 中的非法文件名字符替换为 _
    safe_domain = domain.replace("/", "_").replace("\\", "_").replace(":", "_")
    return sessions_dir / f"{safe_domain}.json"


# =========== 低层（纯数据 I/O，不依赖浏览器）===========


def save_session_data(domain: str, data: dict) -> str:
    """将 Session 数据 dict 写入 ~/.cliany-site/sessions/<domain>.json，返回文件路径

    仅使用加密存储；失败时不写入明文 Cookie。
    """
    try:
        from cliany_site.security import save_encrypted_session

        return save_encrypted_session(domain, data)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Session 加密保存失败，未写入明文: {exc}") from exc


def load_session_data(domain: str) -> dict | None:
    """加载加密 Session；旧版明文须成功迁移后才能使用。"""
    try:
        from cliany_site.security import load_encrypted_session

        return load_encrypted_session(domain)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Session 加密读取失败: domain=%s error=%s", domain, exc)
        return None


def check_session(domain: str) -> dict:
    """检查 Session 文件是否存在及其有效期信息"""
    path = _session_path(domain)
    if not path.exists():
        return {"exists": False, "domain": domain, "path": str(path)}
    data = load_session_data(domain)
    if data is None:
        return {
            "exists": False,
            "domain": domain,
            "path": str(path),
            "error": "parse_error",
        }
    return {
        "exists": True,
        "domain": domain,
        "path": str(path),
        "saved_at": data.get("saved_at"),
        "expires_hint": data.get("expires_hint"),
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
    """从 BrowserSession 提取适用于指定主机的 cookies，保存到文件。

    Returns:
        (文件路径, cookies 数量) 的元组

    Raises:
        RuntimeError: 无法从浏览器获取 cookies 时抛出
    """
    host = urlparse(f"//{domain}").hostname
    if not host:
        raise RuntimeError("保存 Session 需要有效的站点主机名")
    host = host.encode("idna").decode("ascii").lower()
    try:
        cookies: list[Any] = await browser_session._cdp_get_cookies()
    except Exception as e:
        raise RuntimeError(f"无法从浏览器获取 Cookie: {e}") from e

    all_cookies = [
        c.model_dump() if hasattr(c, "model_dump") else dict(c)
        for c in cookies
    ]
    cookie_list = []
    for cookie in all_cookies:
        cookie_domain = cookie.get("domain")
        if not isinstance(cookie_domain, str) or not cookie_domain:
            continue
        cookie_host = cookie_domain.lstrip(".").strip("[]").lower()
        if cookie_host == host or (cookie_domain.startswith(".") and host.endswith(f".{cookie_host}")):
            cookie_list.append(cookie)
    if not cookie_list:
        return "", 0
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
