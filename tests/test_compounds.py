import pytest

from cliany_site.browser.compounds import (
    extract_compounds,
    extract_date_format,
    extract_file_accept,
    extract_select_options,
)

_MAX_OPTIONS = 50


def _make_node(role: str = "button", attributes: dict | None = None) -> dict:
    return {
        "ref": "1",
        "role": role,
        "name": "",
        "attributes": attributes if attributes is not None else {},
    }


def _make_options(n: int) -> list[dict]:
    return [{"value": str(i), "text": f"Option {i}"} for i in range(n)]


class TestExtractSelectOptions:
    def test_happy_combobox_with_options(self):
        node = _make_node("combobox", {"options": _make_options(3)})
        result = extract_select_options(node)
        assert result is not None
        assert len(result["options"]) == 3
        assert result["truncated"] is False

    def test_happy_select_role(self):
        node = _make_node("select", {"options": _make_options(5)})
        result = extract_select_options(node)
        assert result is not None
        assert len(result["options"]) == 5
        assert result["truncated"] is False

    def test_happy_listbox_role(self):
        node = _make_node("listbox", {"options": _make_options(2)})
        result = extract_select_options(node)
        assert result is not None
        assert result["truncated"] is False

    def test_truncate_at_50(self):
        node = _make_node("combobox", {"options": _make_options(60)})
        result = extract_select_options(node)
        assert result is not None
        assert len(result["options"]) == _MAX_OPTIONS
        assert result["truncated"] is True

    def test_exactly_50_not_truncated(self):
        node = _make_node("combobox", {"options": _make_options(50)})
        result = extract_select_options(node)
        assert result is not None
        assert len(result["options"]) == 50
        assert result["truncated"] is False

    def test_empty_options_still_returns_dict(self):
        node = _make_node("combobox", {})
        result = extract_select_options(node)
        assert result is not None
        assert result["options"] == []
        assert result["truncated"] is False

    def test_none_for_non_select_role(self):
        for role in ("button", "textbox", "link", "img", "checkbox", "radio"):
            node = _make_node(role, {"options": _make_options(3)})
            assert extract_select_options(node) is None, f"expected None for role={role}"

    def test_none_for_missing_attributes_key(self):
        node = {"ref": "1", "role": "combobox", "name": ""}
        result = extract_select_options(node)
        assert result is not None
        assert result["options"] == []

    def test_options_not_list_treated_as_empty(self):
        node = _make_node("combobox", {"options": "not-a-list"})
        result = extract_select_options(node)
        assert result is not None
        assert result["options"] == []


class TestExtractDateFormat:
    def test_happy_date_type(self):
        node = _make_node("textbox", {"type": "date", "min": "2020-01-01", "max": "2025-12-31"})
        result = extract_date_format(node)
        assert result is not None
        assert result["type"] == "date"
        assert result["min"] == "2020-01-01"
        assert result["max"] == "2025-12-31"
        assert "pattern" not in result

    def test_happy_datetime_local(self):
        node = _make_node("textbox", {"type": "datetime-local"})
        result = extract_date_format(node)
        assert result is not None
        assert result["type"] == "datetime-local"

    def test_happy_time_with_pattern(self):
        node = _make_node("textbox", {"type": "time", "pattern": "[0-9]{2}:[0-9]{2}"})
        result = extract_date_format(node)
        assert result is not None
        assert result["type"] == "time"
        assert result["pattern"] == "[0-9]{2}:[0-9]{2}"

    def test_none_for_text_type(self):
        node = _make_node("textbox", {"type": "text"})
        assert extract_date_format(node) is None

    def test_none_for_number_type(self):
        node = _make_node("textbox", {"type": "number"})
        assert extract_date_format(node) is None

    def test_none_for_no_type(self):
        node = _make_node("textbox", {})
        assert extract_date_format(node) is None

    def test_none_for_missing_attributes_key(self):
        node = {"ref": "1", "role": "textbox", "name": ""}
        assert extract_date_format(node) is None

    def test_only_existing_fields_included(self):
        node = _make_node("textbox", {"type": "date"})
        result = extract_date_format(node)
        assert result == {"type": "date"}
        assert "min" not in result
        assert "max" not in result
        assert "pattern" not in result


class TestExtractFileAccept:
    def test_happy_file_with_accept(self):
        node = _make_node("input", {"type": "file", "accept": ".pdf,.jpg"})
        result = extract_file_accept(node)
        assert result is not None
        assert result["accept"] == ".pdf,.jpg"
        assert result["multiple"] is False

    def test_happy_multiple_file(self):
        node = _make_node("input", {"type": "file", "accept": "image/*", "multiple": True})
        result = extract_file_accept(node)
        assert result is not None
        assert result["accept"] == "image/*"
        assert result["multiple"] is True

    def test_no_accept_returns_empty_string(self):
        node = _make_node("input", {"type": "file"})
        result = extract_file_accept(node)
        assert result is not None
        assert result["accept"] == ""
        assert result["multiple"] is False

    def test_none_for_text_input(self):
        node = _make_node("textbox", {"type": "text"})
        assert extract_file_accept(node) is None

    def test_none_for_no_type(self):
        node = _make_node("input", {})
        assert extract_file_accept(node) is None

    def test_none_for_missing_attributes_key(self):
        node = {"ref": "1", "role": "input", "name": ""}
        assert extract_file_accept(node) is None


class TestExtractCompounds:
    def test_empty_selector_map(self):
        assert extract_compounds({}) == {}

    def test_button_excluded(self):
        sm = {"1": _make_node("button", {})}
        assert extract_compounds(sm) == {}

    def test_link_excluded(self):
        sm = {"1": _make_node("link", {})}
        assert extract_compounds(sm) == {}

    def test_select_included(self):
        sm = {"1": _make_node("combobox", {"options": _make_options(3)})}
        result = extract_compounds(sm)
        assert "1" in result
        assert "select_options" in result["1"]

    def test_date_included(self):
        sm = {"2": _make_node("textbox", {"type": "date", "min": "2020-01-01"})}
        result = extract_compounds(sm)
        assert "2" in result
        assert "date_format" in result["2"]

    def test_file_included(self):
        sm = {"3": _make_node("input", {"type": "file", "accept": ".pdf"})}
        result = extract_compounds(sm)
        assert "3" in result
        assert "file_accept" in result["3"]

    def test_mixed_selector_map(self):
        sm = {
            "1": _make_node("button", {}),
            "2": _make_node("combobox", {"options": _make_options(5)}),
            "3": _make_node("textbox", {"type": "date"}),
            "4": _make_node("input", {"type": "file"}),
            "5": _make_node("link", {}),
        }
        result = extract_compounds(sm)
        assert "1" not in result
        assert "2" in result
        assert "3" in result
        assert "4" in result
        assert "5" not in result

    def test_truncated_select_in_compounds(self):
        sm = {"1": _make_node("combobox", {"options": _make_options(60)})}
        result = extract_compounds(sm)
        select_info = result["1"]["select_options"]
        assert len(select_info["options"]) == _MAX_OPTIONS
        assert select_info["truncated"] is True

    def test_ref_ids_are_strings(self):
        sm = {
            1: _make_node("combobox", {"options": _make_options(2)}),
            "2": _make_node("input", {"type": "file"}),
        }
        result = extract_compounds(sm)
        for key in result:
            assert isinstance(key, str)

    def test_plain_textbox_excluded(self):
        sm = {"1": _make_node("textbox", {"type": "text"})}
        assert extract_compounds(sm) == {}
