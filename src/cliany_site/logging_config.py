# ---------------------------------------------------------------------------
# 结构化日志配置
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

# ---------------------------------------------------------------------------
# 敏感信息脱敏
# ---------------------------------------------------------------------------

_SENSITIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # sk-ant-XXXXXX... → sk-ant-XXXXXX***
    (re.compile(r"(sk-ant-[A-Za-z0-9_-]{6})[A-Za-z0-9_-]+"), r"\1***"),
    # sk-XXXX... → sk-XXXX***
    (re.compile(r"(sk-[A-Za-z0-9]{4})[A-Za-z0-9-]+"), r"\1***"),
    # "api_key": "XXXXXXXX..." / token=XXXXXXXX... → 保留前8字符
    (
        re.compile(
            r'(["\']?(?:api[_-]?key|token|password|secret|cookie|authorization)'
            r'["\']?\s*[:=]\s*["\']?)([^"\'\s,}{]{8})[^"\'\s,}{]*',
            re.IGNORECASE,
        ),
        r"\1\2***",
    ),
    # Bearer XXXXXX... → Bearer XXXXXX***
    (re.compile(r"(Bearer\s+[A-Za-z0-9]{6})[A-Za-z0-9_.+-]+"), r"\1***"),
]


def redact_sensitive(text: str) -> str:
    """对文本中的敏感信息做脱敏处理。"""
    result = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class SensitiveFilter(logging.Filter):
    """日志过滤器：自动脱敏 record.getMessage() 中的敏感字段。"""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_sensitive(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_sensitive(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        if isinstance(record.msg, str):
            record.msg = redact_sensitive(record.msg)
        return True


# ---------------------------------------------------------------------------
# 格式化器
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """将日志记录序列化为单行 JSON，便于日志聚合。"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        for key in ("duration_ms", "action", "step", "domain", "url"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """人类可读的彩色终端日志格式。"""

    _LEVEL_COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[1;31m",
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self._LEVEL_COLORS.get(record.levelname, "")
        reset = self._RESET if color else ""
        level = f"{color}{record.levelname:<8}{reset}"
        name = record.name.replace("cliany_site.", "")
        msg = record.getMessage()
        duration = getattr(record, "duration_ms", None)
        suffix = f" [{duration:.0f}ms]" if duration is not None else ""

        base = f"{level} {name}: {msg}{suffix}"

        if record.exc_info and record.exc_info[1] is not None:
            base += "\n" + self.formatException(record.exc_info)
        return base


# ---------------------------------------------------------------------------
# 配置入口
# ---------------------------------------------------------------------------

LEVEL_QUIET = logging.WARNING
LEVEL_VERBOSE = logging.INFO
LEVEL_DEBUG = logging.DEBUG


def setup_logging(
    *,
    level: int = LEVEL_QUIET,
    json_format: bool = False,
) -> None:
    root_logger = logging.getLogger("cliany_site")

    if level > logging.DEBUG:
        # 第三方 cdp_use 会自行忽略重复的 CDP 响应；这里将其 WARNING 噪音静默掉。
        # 参考 .venv/.../cdp_use/client.py:312-327
        logging.getLogger("cdp_use.client").setLevel(logging.ERROR)

    if root_logger.handlers:
        root_logger.setLevel(level)
        for handler in root_logger.handlers:
            handler.setLevel(level)
        return

    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(HumanFormatter())

    handler.addFilter(SensitiveFilter())

    root_logger.addHandler(handler)
    root_logger.propagate = False


# ---------------------------------------------------------------------------
# 耗时计量辅助
# ---------------------------------------------------------------------------


def log_duration(
    logger: logging.Logger,
    action: str = "",
    level: int = logging.INFO,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            logger.log(level, "%s 开始", action or func.__name__)
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.log(
                    level,
                    "%s 完成",
                    action or func.__name__,
                    extra={"duration_ms": elapsed_ms, "action": action},
                )
                return result
            except Exception:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.log(
                    logging.ERROR,
                    "%s 失败",
                    action or func.__name__,
                    exc_info=True,
                    extra={"duration_ms": elapsed_ms, "action": action},
                )
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            logger.log(level, "%s 开始", action or func.__name__)
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.log(
                    level,
                    "%s 完成",
                    action or func.__name__,
                    extra={"duration_ms": elapsed_ms, "action": action},
                )
                return result
            except Exception:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.log(
                    logging.ERROR,
                    "%s 失败",
                    action or func.__name__,
                    exc_info=True,
                    extra={"duration_ms": elapsed_ms, "action": action},
                )
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
