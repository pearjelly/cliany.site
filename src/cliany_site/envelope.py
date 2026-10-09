import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict


# TypedDict 定义
class ErrorObj(TypedDict):
    code: str
    message: str
    hint: str | None
    details: dict[str, Any] | None

class EnvelopeMeta(TypedDict):
    duration_ms: int
    duration_measured: NotRequired[bool]
    source: str  # "builtin"|"atom"|"adapter"

class SuccessEnvelope(TypedDict):
    ok: Literal[True]
    version: str
    command: str
    data: Any
    error: None
    meta: EnvelopeMeta


class ErrorEnvelope(TypedDict):
    ok: Literal[False]
    version: str
    command: str
    data: None
    error: ErrorObj
    meta: EnvelopeMeta


Envelope = SuccessEnvelope | ErrorEnvelope

# ErrorCode 类（class，不是枚举）
class ErrorCode:
    E_CDP_UNAVAILABLE = "E_CDP_UNAVAILABLE"
    E_SESSION_EXPIRED = "E_SESSION_EXPIRED"
    E_SELECTOR_NOT_FOUND = "E_SELECTOR_NOT_FOUND"
    E_PAGE_NOT_READY = "E_PAGE_NOT_READY"
    E_PARSE_FAILED = "E_PARSE_FAILED"
    E_EMPTY_RESULT = "E_EMPTY_RESULT"
    E_LLM_DISABLED = "E_LLM_DISABLED"
    E_LLM_AUTH_FAILED = "E_LLM_AUTH_FAILED"
    E_LLM_UNAVAILABLE = "E_LLM_UNAVAILABLE"
    E_LEGACY_ADAPTER = "E_LEGACY_ADAPTER"
    E_VERIFY_STATIC = "E_VERIFY_STATIC"
    E_VERIFY_SMOKE = "E_VERIFY_SMOKE"
    E_HEAL_CAP_EXCEEDED = "E_HEAL_CAP_EXCEEDED"
    E_AGENT_MD_CONFLICT = "E_AGENT_MD_CONFLICT"
    E_REGISTRY_CONFLICT = "E_REGISTRY_CONFLICT"
    E_INVALID_PARAM = "E_INVALID_PARAM"
    E_TIMEOUT = "E_TIMEOUT"
    E_CDP_DISCONNECTED = "E_CDP_DISCONNECTED"
    E_EVAL_DISABLED = "E_EVAL_DISABLED"
    E_EVAL_BLACKLIST = "E_EVAL_BLACKLIST"
    E_SANDBOX_VIOLATION = "E_SANDBOX_VIOLATION"
    E_UNKNOWN = "E_UNKNOWN"
    E_QA_OFFLINE_MISSING_FAKE_LLM = "E_QA_OFFLINE_MISSING_FAKE_LLM"
    E_DIAGNOSE = "E_DIAGNOSE"
    E_UNSUPPORTED_PLATFORM = "E_UNSUPPORTED_PLATFORM"
    E_MISSING_CAPABILITY = "E_MISSING_CAPABILITY"
    E_PROVIDER_NOT_FOUND = "E_PROVIDER_NOT_FOUND"
    E_PROVIDER_VERSION_TOO_OLD = "E_PROVIDER_VERSION_TOO_OLD"
    E_BINARY_NOT_FOUND = "E_BINARY_NOT_FOUND"
    E_STALE_PID = "E_STALE_PID"
    E_PORT_CONFLICT = "E_PORT_CONFLICT"
    E_DOWNLOAD_FAILED = "E_DOWNLOAD_FAILED"
    E_VERSION_MISMATCH = "E_VERSION_MISMATCH"

    @classmethod
    def from_exception(cls, exc: Exception) -> str:
        """将现有 errors.py 的异常类映射到 ErrorCode 常量"""
        from cliany_site.errors import (
            AdapterLoadError,
            CdpError,
            CodegenError,
            DataCommandQualityError,
            ExplorerError,
            LlmUnavailableError,
            SecurityError,
            SessionError,
            WorkflowError,
        )

        mapping = {
            CdpError: cls.E_CDP_UNAVAILABLE,
            SessionError: cls.E_SESSION_EXPIRED,
            LlmUnavailableError: cls.E_LLM_UNAVAILABLE,
            DataCommandQualityError: cls.E_EMPTY_RESULT,
            ExplorerError: cls.E_LLM_DISABLED,
            CodegenError: cls.E_UNKNOWN,
            AdapterLoadError: cls.E_LEGACY_ADAPTER,
            WorkflowError: cls.E_UNKNOWN,
            SecurityError: cls.E_UNKNOWN,
        }

        for exc_type, code in mapping.items():
            if isinstance(exc, exc_type):
                return code

        return cls.E_UNKNOWN

@dataclass
class _CommandTimer:
    started_ns: int | None


_command_timer: ContextVar[_CommandTimer | None] = ContextVar("command_timer", default=None)


@contextmanager
def command_timing() -> Iterator[None]:
    """为本次调用建立单调时钟，嵌套调用独立计时。"""
    timer = _CommandTimer(time.monotonic_ns())
    token = _command_timer.set(timer)
    try:
        yield
    finally:
        # 已结束的调用不能为继承此 context 的后台任务继续计时。
        timer.started_ns = None
        _command_timer.reset(token)


def _meta(source: str) -> EnvelopeMeta:
    timer = _command_timer.get()
    started_ns = timer.started_ns if timer is not None else None
    return {
        "duration_ms": (time.monotonic_ns() - started_ns) // 1_000_000 if started_ns is not None else 0,
        "duration_measured": started_ns is not None,
        "source": source,
    }

def ok(command: str, data: Any, source: str = "builtin") -> SuccessEnvelope:
    """返回成功 Envelope；无调用时钟时明确标记耗时未测量。"""
    return {
        "ok": True,
        "version": "1",
        "command": command,
        "data": data,
        "error": None,
        "meta": _meta(source),
    }

def err(
    command: str,
    code: str,
    message: str,
    *,
    hint: str | None = None,
    details: dict[str, Any] | None = None,
    source: str = "builtin",
) -> ErrorEnvelope:
    """返回错误 Envelope；code 为 None/空时 raise ValueError('code is required')"""
    if not code:
        raise ValueError("code is required")

    return {
        "ok": False,
        "version": "1",
        "command": command,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "hint": hint,
            "details": details,
        },
        "meta": _meta(source),
    }
