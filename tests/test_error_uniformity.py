import cliany_site.errors as errors_module


def test_all_error_codes_have_hints():
    codes = [
        v for k, v in vars(errors_module).items()
        if not k.startswith("_") and isinstance(v, str) and v.isupper()
    ]
    assert codes, "errors.py 中未找到任何错误码常量（全大写字符串）"
    for code in codes:
        assert code in errors_module.ERROR_FIX_HINTS, f"ErrorCode {code!r} 没有对应 hint"
        assert errors_module.ERROR_FIX_HINTS[code], f"ErrorCode {code!r} 的 hint 为空"
