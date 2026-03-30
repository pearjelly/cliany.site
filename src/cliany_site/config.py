# ---------------------------------------------------------------------------
# 统一配置中心
# ---------------------------------------------------------------------------
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key, "")
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key, "")
    if not raw:
        return default
    return raw.lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class ClanySiteConfig:
    cdp_port: int = 9222
    cdp_timeout: float = 2.0
    cdp_url: str = ""
    headless: bool = False

    post_navigate_delay: float = 1.5
    post_click_nav_delay: float = 2.0
    new_tab_settle_delay: float = 2.5

    resolve_retry_delay: float = 1.0
    resolve_max_retries: int = 2

    llm_retry_max_attempts: int = 3
    llm_retry_base_delay: float = 2.0
    llm_retry_backoff_factor: float = 2.0

    adaptive_repair_enabled: bool = False
    adaptive_repair_max_attempts: int = 3

    explore_max_steps: int = 10

    cross_origin_iframes: bool = True
    max_iframes: int = 100
    max_iframe_depth: int = 5

    home_dir: Path = field(default_factory=lambda: Path.home() / ".cliany-site")

    @property
    def adapters_dir(self) -> Path:
        return self.home_dir / "adapters"

    @property
    def sessions_dir(self) -> Path:
        return self.home_dir / "sessions"

    @property
    def reports_dir(self) -> Path:
        return self.home_dir / "reports"

    @property
    def logs_dir(self) -> Path:
        return self.home_dir / "logs"

    @property
    def activity_log_path(self) -> Path:
        return self.home_dir / "activity.log"

    def to_dict(self) -> dict:
        return {
            "cdp_port": self.cdp_port,
            "cdp_timeout": self.cdp_timeout,
            "cdp_url": self.cdp_url,
            "headless": self.headless,
            "post_navigate_delay": self.post_navigate_delay,
            "post_click_nav_delay": self.post_click_nav_delay,
            "new_tab_settle_delay": self.new_tab_settle_delay,
            "resolve_retry_delay": self.resolve_retry_delay,
            "resolve_max_retries": self.resolve_max_retries,
            "llm_retry_max_attempts": self.llm_retry_max_attempts,
            "llm_retry_base_delay": self.llm_retry_base_delay,
            "llm_retry_backoff_factor": self.llm_retry_backoff_factor,
            "adaptive_repair_enabled": self.adaptive_repair_enabled,
            "adaptive_repair_max_attempts": self.adaptive_repair_max_attempts,
            "explore_max_steps": self.explore_max_steps,
            "cross_origin_iframes": self.cross_origin_iframes,
            "max_iframes": self.max_iframes,
            "max_iframe_depth": self.max_iframe_depth,
            "home_dir": str(self.home_dir),
            "adapters_dir": str(self.adapters_dir),
            "sessions_dir": str(self.sessions_dir),
            "reports_dir": str(self.reports_dir),
            "logs_dir": str(self.logs_dir),
            "activity_log_path": str(self.activity_log_path),
        }


def load_config() -> ClanySiteConfig:
    return ClanySiteConfig(
        cdp_port=_env_int("CLIANY_CDP_PORT", 9222),
        cdp_timeout=_env_float("CLIANY_CDP_TIMEOUT", 2.0),
        cdp_url=os.environ.get("CLIANY_CDP_URL", ""),
        headless=_env_bool("CLIANY_HEADLESS", False),
        post_navigate_delay=_env_float("CLIANY_POST_NAVIGATE_DELAY", 1.5),
        post_click_nav_delay=_env_float("CLIANY_POST_CLICK_NAV_DELAY", 2.0),
        new_tab_settle_delay=_env_float("CLIANY_NEW_TAB_SETTLE_DELAY", 2.5),
        resolve_retry_delay=_env_float("CLIANY_RESOLVE_RETRY_DELAY", 1.0),
        resolve_max_retries=_env_int("CLIANY_RESOLVE_MAX_RETRIES", 2),
        llm_retry_max_attempts=_env_int("CLIANY_LLM_RETRY_MAX_ATTEMPTS", 3),
        llm_retry_base_delay=_env_float("CLIANY_LLM_RETRY_BASE_DELAY", 2.0),
        llm_retry_backoff_factor=_env_float("CLIANY_LLM_RETRY_BACKOFF_FACTOR", 2.0),
        adaptive_repair_enabled=_env_bool("CLIANY_ADAPTIVE_REPAIR", False),
        adaptive_repair_max_attempts=_env_int("CLIANY_ADAPTIVE_REPAIR_MAX_ATTEMPTS", 3),
        explore_max_steps=_env_int("CLIANY_EXPLORE_MAX_STEPS", 10),
        cross_origin_iframes=_env_bool("CLIANY_CROSS_ORIGIN_IFRAMES", True),
        max_iframes=_env_int("CLIANY_MAX_IFRAMES", 100),
        max_iframe_depth=_env_int("CLIANY_MAX_IFRAME_DEPTH", 5),
    )


_config: ClanySiteConfig | None = None


def get_config() -> ClanySiteConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    global _config
    _config = None
