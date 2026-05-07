import pytest

from cliany_site.explorer.prompts import format_compounds_section

_SECTION_HEADER = "## Compound Controls"


class TestFormatCompoundsSectionEmpty:
    def test_empty_dict_returns_empty_string(self):
        assert format_compounds_section({}) == ""

    def test_empty_dict_no_header(self):
        result = format_compounds_section({})
        assert _SECTION_HEADER not in result

    def test_non_dict_values_only_returns_empty(self):
        result = format_compounds_section({"ref1": None, "ref2": "bad"})
        assert _SECTION_HEADER not in result


class TestFormatCompoundsSectionNonEmpty:
    def test_select_with_options_contains_header(self):
        compounds = {"ref1": {"kind": "select", "options": [{"value": "a", "text": "A"}]}}
        result = format_compounds_section(compounds)
        assert _SECTION_HEADER in result

    def test_select_with_options_contains_ref(self):
        compounds = {"ref1": {"kind": "select", "options": [{"value": "a", "text": "A"}]}}
        result = format_compounds_section(compounds)
        assert "@ref1" in result

    def test_select_with_options_contains_kind(self):
        compounds = {"ref1": {"kind": "select", "options": [{"value": "a", "text": "A"}]}}
        result = format_compounds_section(compounds)
        assert "select" in result

    def test_select_options_appear_in_output(self):
        compounds = {"ref1": {"kind": "select", "options": [{"value": "a", "text": "A"}]}}
        result = format_compounds_section(compounds)
        assert "A=a" in result

    def test_multiple_options_rendered(self):
        compounds = {
            "ref1": {
                "kind": "select",
                "options": [{"value": "x", "text": "X"}, {"value": "y", "text": "Y"}],
            }
        }
        result = format_compounds_section(compounds)
        assert "X=x" in result
        assert "Y=y" in result

    def test_extract_compounds_select_format(self):
        compounds = {
            "42": {"select_options": {"options": [{"value": "v1", "text": "Option1"}], "truncated": False}}
        }
        result = format_compounds_section(compounds)
        assert _SECTION_HEADER in result
        assert "@42" in result
        assert "select" in result

    def test_extract_compounds_date_format(self):
        compounds = {"10": {"date_format": {"type": "date", "min": "2020-01-01", "max": "2025-12-31"}}}
        result = format_compounds_section(compounds)
        assert _SECTION_HEADER in result
        assert "@10" in result
        assert "date" in result

    def test_extract_compounds_file_format(self):
        compounds = {"20": {"file_accept": {"accept": ".pdf,.jpg", "multiple": False}}}
        result = format_compounds_section(compounds)
        assert _SECTION_HEADER in result
        assert "@20" in result
        assert "file" in result

    def test_truncated_select_shows_suffix(self):
        compounds = {
            "5": {
                "select_options": {
                    "options": [{"value": str(i), "text": f"Opt{i}"} for i in range(5)],
                    "truncated": True,
                }
            }
        }
        result = format_compounds_section(compounds)
        assert "truncated" in result

    def test_multiple_compounds_all_appear(self):
        compounds = {
            "ref1": {"kind": "select", "options": [{"value": "a", "text": "A"}]},
            "ref2": {"date_format": {"type": "date"}},
        }
        result = format_compounds_section(compounds)
        assert "@ref1" in result
        assert "@ref2" in result

    def test_arrow_separator_present(self):
        compounds = {"ref1": {"kind": "select", "options": [{"value": "a", "text": "A"}]}}
        result = format_compounds_section(compounds)
        assert "→" in result

    def test_options_capped_at_five(self):
        compounds = {
            "ref1": {
                "kind": "select",
                "options": [{"value": str(i), "text": f"Opt{i}"} for i in range(10)],
            }
        }
        result = format_compounds_section(compounds)
        assert "Opt0=0" in result
        assert "Opt4=4" in result
        assert "Opt5=5" not in result
