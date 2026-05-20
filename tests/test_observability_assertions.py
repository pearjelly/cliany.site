from __future__ import annotations

import json
import logging


def test_logging_masking_redacts_secrets() -> None:
    from cliany_site.logging_config import SensitiveFilter, redact_sensitive

    assert "supersecretvalue123" not in redact_sensitive("api_key=supersecretvalue123")
    assert "***" in redact_sensitive("api_key=supersecretvalue123")
    assert "mypassword12345" not in redact_sensitive("password=mypassword12345")
    assert "***" in redact_sensitive("password=mypassword12345")

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="token=mysecrettoken123",
        args=(),
        exc_info=None,
    )
    SensitiveFilter().filter(record)
    assert "mysecrettoken123" not in record.msg
    assert "***" in record.msg


def test_json_formatter_emits_valid_json() -> None:
    from cliany_site.logging_config import JSONFormatter

    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    data = json.loads(JSONFormatter().format(record))

    assert "ts" in data, f"缺少 ts 字段，实际 keys={list(data.keys())}"
    assert "level" in data, f"缺少 level 字段，实际 keys={list(data.keys())}"
    assert "msg" in data, f"缺少 msg 字段，实际 keys={list(data.keys())}"
    assert data["level"] == "INFO"
    assert data["msg"] == "hello world"


def test_error_codes_have_fix_hints() -> None:
    import cliany_site.errors as errors_module
    from cliany_site.errors import ERROR_FIX_HINTS

    for code, hint in ERROR_FIX_HINTS.items():
        assert isinstance(hint, str) and hint.strip(), f"错误码 {code} 的 hint 为空"

    all_code_consts = {
        k
        for k, v in vars(errors_module).items()
        if k.isupper() and isinstance(v, str) and not k.startswith("_")
    }
    for code in all_code_consts:
        assert code in ERROR_FIX_HINTS, f"错误码常量 {code!r} 未在 ERROR_FIX_HINTS 中登记"


def test_envelope_ok_success_compat() -> None:
    from cliany_site.envelope import ok as envelope_ok
    from cliany_site.response import success_response

    new_resp = envelope_ok("test_cmd", {"test": 1})
    assert new_resp["ok"] is True, "envelope.ok() 应返回 ok=True"

    old_resp = success_response({"test": 1})
    assert old_resp["success"] is True, "success_response() 应返回 success=True"

    new_success = new_resp.get("ok", new_resp.get("success", False))
    old_success = old_resp.get("ok", old_resp.get("success", False))
    assert new_success is True
    assert old_success is True
    assert new_success == old_success
