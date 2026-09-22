from __future__ import annotations

import pytest

from cliany_site.explorer.engine import (
    _infer_command_name_from_description,
    _infer_name_from_description,
    _normalize_openai_base_url,
    _parse_llm_response,
    _sanitize_actions_data,
    _to_snake_case,
    _to_text,
)


class TestToSnakeCase:
    def test_normal(self):
        assert _to_snake_case("hello world") == "hello_world"

    def test_special_chars(self):
        assert _to_snake_case("my-var.name") == "my_var_name"

    def test_consecutive_separators(self):
        assert _to_snake_case("a---b   c") == "a_b_c"

    def test_leading_trailing_stripped(self):
        assert _to_snake_case("  hello  ") == "hello"

    def test_uppercase_lowered(self):
        assert _to_snake_case("CamelCase") == "camelcase"

    def test_empty_string(self):
        assert _to_snake_case("") == ""

    def test_numbers_preserved(self):
        assert _to_snake_case("param_1") == "param_1"


class TestInferNameFromDescription:
    def test_title_keyword(self):
        assert _infer_name_from_description("请输入标题") == "title"

    def test_body_keyword(self):
        assert _infer_name_from_description("输入正文内容") == "body"

    def test_query_keyword(self):
        assert _infer_name_from_description("搜索关键词") == "query"

    def test_name_keyword(self):
        assert _infer_name_from_description("填写名称") == "name"

    def test_url_keyword(self):
        assert _infer_name_from_description("输入网址") == "url"

    def test_no_match(self):
        assert _infer_name_from_description("随便输入") == ""

    def test_empty(self):
        assert _infer_name_from_description("") == ""


class TestInferCommandNameFromDescription:
    def test_create_issue(self):
        assert _infer_command_name_from_description("创建 issue") == "create-issue"

    def test_search(self):
        assert _infer_command_name_from_description("搜索仓库") == "search"

    def test_login(self):
        assert _infer_command_name_from_description("登录系统") == "login"

    def test_delete(self):
        assert _infer_command_name_from_description("删除文件") == "delete"

    def test_edit(self):
        assert _infer_command_name_from_description("编辑文档") == "edit"

    def test_download(self):
        assert _infer_command_name_from_description("下载附件") == "download"

    def test_no_match(self):
        assert _infer_command_name_from_description("做一些事情") == ""

    def test_empty(self):
        assert _infer_command_name_from_description("") == ""

    def test_last_keyword_wins(self):
        result = _infer_command_name_from_description("搜索仓库然后删除文件")
        assert result == "delete"


class TestNormalizeOpenaiBaseUrl:
    def test_none_input(self):
        assert _normalize_openai_base_url(None) is None

    def test_non_string_input(self):
        assert _normalize_openai_base_url(123) is None

    def test_empty_string(self):
        assert _normalize_openai_base_url("") is None

    def test_whitespace_only(self):
        assert _normalize_openai_base_url("   ") is None

    def test_appends_v1(self):
        assert (
            _normalize_openai_base_url("https://api.example.com")
            == "https://api.example.com/v1"
        )

    def test_trailing_slash_stripped(self):
        assert (
            _normalize_openai_base_url("https://api.example.com/")
            == "https://api.example.com/v1"
        )

    def test_already_has_v1(self):
        assert (
            _normalize_openai_base_url("https://api.example.com/v1")
            == "https://api.example.com/v1"
        )

    def test_already_has_v1_trailing_slash(self):
        assert (
            _normalize_openai_base_url("https://api.example.com/v1/")
            == "https://api.example.com/v1"
        )

    def test_invalid_scheme_raises(self):
        with pytest.raises(EnvironmentError):
            _normalize_openai_base_url("ftp://example.com")

    def test_no_scheme_raises(self):
        with pytest.raises(EnvironmentError):
            _normalize_openai_base_url("example.com")

    def test_http_allowed(self):
        result = _normalize_openai_base_url("http://localhost:8080")
        assert result == "http://localhost:8080/v1"

    def test_custom_path_preserved(self):
        result = _normalize_openai_base_url("https://proxy.example.com/api/openai/v1")
        assert result == "https://proxy.example.com/api/openai/v1"


class TestParseLlmResponse:
    def test_plain_json(self):
        text = '{"done": true, "actions": [], "commands": []}'
        result = _parse_llm_response(text)
        assert result["done"] is True

    def test_json_in_code_block(self):
        text = '```json\n{"done": false, "actions": [{"type": "click"}]}\n```'
        result = _parse_llm_response(text)
        assert result["done"] is False
        assert len(result["actions"]) == 1

    def test_json_with_surrounding_text(self):
        text = 'Here is the plan:\n{"done": true, "actions": []}\nDone.'
        result = _parse_llm_response(text)
        assert result["done"] is True

    @pytest.mark.parametrize("text", ["not json at all", "", '{"done":'])
    def test_invalid_json_never_signals_completion(self, text):
        with pytest.raises(ValueError, match="解析失败"):
            _parse_llm_response(text)

    @pytest.mark.parametrize("text", ['[]', '[{"done": true}]', 'null', '42',
                                      '{"done": "false"}', '{"done": 1}', '{"done": null}'])
    def test_invalid_response_shape_is_rejected(self, text):
        with pytest.raises(ValueError, match="JSON 对象"):
            _parse_llm_response(text)


class TestToText:
    def test_string_passthrough(self):
        assert _to_text("hello") == "hello"

    def test_list_of_strings(self):
        assert _to_text(["a", "b"]) == "a\nb"

    def test_list_of_dicts_with_text(self):
        content = [{"text": "part1"}, {"text": "part2"}]
        assert _to_text(content) == "part1\npart2"

    def test_list_of_dicts_with_content(self):
        content = [{"content": "hello"}]
        assert _to_text(content) == "hello"

    def test_mixed_list(self):
        content = ["raw", {"text": "from_dict"}]
        assert _to_text(content) == "raw\nfrom_dict"

    def test_non_string_non_list(self):
        assert _to_text(42) == "42"

    def test_none(self):
        assert _to_text(None) == "None"

    def test_empty_list(self):
        assert _to_text([]) == ""


class TestSanitizeActionsData:
    def test_non_list_returns_empty(self):
        assert _sanitize_actions_data("not a list", "https://example.com") == []
        assert _sanitize_actions_data(None, "https://example.com") == []
        assert _sanitize_actions_data(42, "https://example.com") == []

    def test_non_dict_items_skipped(self):
        assert _sanitize_actions_data(["string", 42], "https://example.com") == []

    def test_action_type_lowered(self):
        result = _sanitize_actions_data(
            [{"type": "CLICK", "ref": "@1"}], "https://example.com"
        )
        assert result[0]["type"] == "click"

    def test_input_renamed_to_type(self):
        result = _sanitize_actions_data(
            [{"type": "input", "value": "hello"}], "https://example.com"
        )
        assert result[0]["type"] == "type"

    def test_navigate_with_valid_url(self):
        result = _sanitize_actions_data(
            [{"type": "navigate", "url": "https://example.com/page"}],
            "https://example.com",
        )
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com/page"

    def test_navigate_with_invalid_url_dropped(self):
        result = _sanitize_actions_data(
            [{"type": "navigate", "url": ""}],
            "https://example.com",
        )
        assert len(result) == 0

    def test_value_alt_key_text(self):
        result = _sanitize_actions_data(
            [{"type": "type", "text": "hello"}], "https://example.com"
        )
        assert result[0]["value"] == "hello"

    def test_value_alt_key_content(self):
        result = _sanitize_actions_data(
            [{"type": "type", "content": "world"}], "https://example.com"
        )
        assert result[0]["value"] == "world"

    def test_value_alt_key_query(self):
        result = _sanitize_actions_data(
            [{"type": "type", "query": "search term"}], "https://example.com"
        )
        assert result[0]["value"] == "search term"

    def test_existing_value_not_overridden(self):
        result = _sanitize_actions_data(
            [{"type": "type", "value": "original", "text": "alt"}],
            "https://example.com",
        )
        assert result[0]["value"] == "original"

    def test_multiple_actions_preserved(self):
        actions = [
            {"type": "click", "ref": "@1"},
            {"type": "type", "ref": "@2", "value": "test"},
        ]
        result = _sanitize_actions_data(actions, "https://example.com")
        assert len(result) == 2

    def test_navigate_relative_url_resolved(self):
        result = _sanitize_actions_data(
            [{"type": "navigate", "url": "/about"}],
            "https://example.com/page",
        )
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com/about"
