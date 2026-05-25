import time
from typing import Any, Literal, TypedDict


# TypedDict 定义
class ErrorObj(TypedDict):
    code: str
    message: str
    hint: str | None
    details: dict[str, Any] | None

class EnvelopeMeta(TypedDict):
    duration_ms: int
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
    E_LLM_DISABLED = "E_LLM_DISABLED"
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
            ExplorerError,
            SecurityError,
            SessionError,
            WorkflowError,
        )

        mapping = {
            CdpError: cls.E_CDP_UNAVAILABLE,
            SessionError: cls.E_SESSION_EXPIRED,
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

# 全局 start times 追踪（基于 command str）
_start_times: dict[str, float] = {}

def ok(command: str, data: Any, source: str = "builtin") -> SuccessEnvelope:
    """返回成功 Envelope，自动计算 duration_ms"""
    start_time = _start_times.pop(command, time.time())
    duration_ms = int((time.time() - start_time) * 1000)

    return {
        "ok": True,
        "version": "1",
        "command": command,
        "data": data,
        "error": None,
        "meta": {
            "duration_ms": duration_ms,
            "source": source,
        },
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

    start_time = _start_times.pop(command, time.time())
    duration_ms = int((time.time() - start_time) * 1000)

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
        "meta": {
            "duration_ms": duration_ms,
            "source": source,
        },
    }
