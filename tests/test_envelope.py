import json
import pytest
from typing import Any

from cliany_site.envelope import ok, err, ErrorCode, Envelope
from cliany_site.errors import CdpError, SessionError, ExplorerError

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

if HAS_JSONSCHEMA:
    with open("schemas/envelope.v1.json", "r", encoding="utf-8") as f:
        SCHEMA = json.load(f)
    validate = jsonschema.validate
else:
    SCHEMA = None
    validate = lambda data, schema: None  # noop

def test_ok_returns_valid_envelope():
    """ok() 返回符合 schema 的 Envelope"""
    result = ok("test_cmd", {"key": "value"})
    assert isinstance(result, dict)
    assert result["ok"] is True
    assert result["version"] == "1"
    assert result["command"] == "test_cmd"
    assert result["data"] == {"key": "value"}
    assert result["error"] is None
    assert isinstance(result["meta"]["duration_ms"], int)
    assert result["meta"]["source"] == "builtin"
    if HAS_JSONSCHEMA:
        validate(result, SCHEMA)

def test_err_returns_valid_envelope():
    """err() 返回符合 schema 的 Envelope"""
    result = err("test_cmd", "E_TEST", "test message", hint="test hint", details={"extra": "info"})
    assert isinstance(result, dict)
    assert result["ok"] is False
    assert result["version"] == "1"
    assert result["command"] == "test_cmd"
    assert result["data"] is None
    assert result["error"]["code"] == "E_TEST"
    assert result["error"]["message"] == "test message"
    assert result["error"]["hint"] == "test hint"
    assert result["error"]["details"] == {"extra": "info"}
    assert isinstance(result["meta"]["duration_ms"], int)
    assert result["meta"]["source"] == "builtin"
    if HAS_JSONSCHEMA:
        validate(result, SCHEMA)

def test_err_raises_on_none_code():
    """err(code=None) 抛 ValueError('code is required')"""
    with pytest.raises(ValueError, match="code is required"):
        err("test_cmd", None, "message")

def test_err_raises_on_empty_code():
    """err(code="") 抛 ValueError('code is required')"""
    with pytest.raises(ValueError, match="code is required"):
        err("test_cmd", "", "message")

def test_from_exception_cdp_error():
    """from_exception(CdpError()) 返回 E_CDP_UNAVAILABLE"""
    code = ErrorCode.from_exception(CdpError("test"))
    assert code == ErrorCode.E_CDP_UNAVAILABLE

def test_from_exception_session_error():
    """from_exception(SessionError()) 返回 E_SESSION_EXPIRED"""
    code = ErrorCode.from_exception(SessionError("test"))
    assert code == ErrorCode.E_SESSION_EXPIRED

def test_from_exception_explorer_error():
    """from_exception(ExplorerError()) 返回 E_LLM_DISABLED"""
    code = ErrorCode.from_exception(ExplorerError("test"))
    assert code == ErrorCode.E_LLM_DISABLED

def test_from_exception_unknown_error():
    """from_exception(RuntimeError()) 返回 E_UNKNOWN"""
    code = ErrorCode.from_exception(RuntimeError("test"))
    assert code == ErrorCode.E_UNKNOWN

def test_ok_default_source():
    """ok 的 meta.source 默认为 'builtin'"""
    result = ok("test_cmd", None)
    assert result["meta"]["source"] == "builtin"

def test_err_default_source():
    """err 的 meta.source 默认为 'builtin'"""
    result = err("test_cmd", "E_TEST", "message")
    assert result["meta"]["source"] == "builtin"

def test_ok_version_is_one():
    """ok 的 version 字段为 '1'"""
    result = ok("test_cmd", None)
    assert result["version"] == "1"

def test_err_version_is_one():
    """err 的 version 字段为 '1'"""
    result = err("test_cmd", "E_TEST", "message")
    assert result["version"] == "1"

def test_schema_validation_fails_on_missing_ok():
    """schema 校验：缺 ok 字段的 dict 应校验失败"""
    if not HAS_JSONSCHEMA:
        pytest.skip("jsonschema not available")
    
    invalid_envelope = {
        "version": "1",
        "command": "test",
        "data": None,
        "error": None,
        "meta": {"duration_ms": 0, "source": "builtin"}
    }
    with pytest.raises(jsonschema.ValidationError):
        validate(invalid_envelope, SCHEMA)

def test_ok_with_custom_source():
    """ok 支持自定义 source"""
    result = ok("test_cmd", None, source="adapter")
    assert result["meta"]["source"] == "adapter"

def test_err_with_custom_source():
    """err 支持自定义 source"""
    result = err("test_cmd", "E_TEST", "message", source="atom")
    assert result["meta"]["source"] == "atom"