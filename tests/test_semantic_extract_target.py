import pytest

from cliany_site.browser.selector import ground_extract_target, resolve_extract_target


def candidate(role, name, selector, attributes=None):
    return {
        "role": role,
        "name": name,
        "text": "",
        "selectors": [selector],
        "root_selector": selector,
        "anchor_attributes": attributes or {},
    }


def test_recorded_target_comes_from_observed_read_only_semantics():
    observed = candidate("list", "Package results", "#results", {"id": "results", "aria-label": "Package results"})
    target = ground_extract_target("#results li", {}, [observed])
    assert target == {
        "role": "list",
        "name": "Package results",
        "attributes": {"id": "results", "aria-label": "Package results"},
        "suffix": " li",
    }
    assert ground_extract_target("#guessed", {}, [observed]) is None


def test_renamed_result_region_resolves_by_semantic_name_not_stale_id():
    target = {"role": "list", "name": "Package results", "attributes": {"id": "results"}, "suffix": " li"}
    current = [
        candidate("list", "Favorites", "#results", {"id": "results"}),
        candidate("list", "Package results", "#packages", {"id": "packages"}),
    ]
    assert resolve_extract_target(target, {}, current) == ("#packages", " li")


def test_dynamic_count_content_is_not_used_as_an_identity():
    observed = candidate("status", "", "#summary", {"id": "summary"})
    observed["text"] = "1 matches"
    target = ground_extract_target("#summary", {}, [observed])
    current = candidate("status", "", "#total", {"id": "total"})
    current["text"] = "0 matches"
    assert resolve_extract_target(target, {}, [current]) == ("#total", "")


def test_parent_mapped_rows_retain_the_semantic_container():
    observed = candidate("list", "", "#search-results li", {"id": "search-results"})
    observed["root_selector"] = "#search-results > ul"
    target = ground_extract_target("#search-results li", {}, [observed])
    assert target["suffix"] == " li"
    current = candidate("list", "", "#new-results li", {"id": "new-results"})
    current["root_selector"] = "#new-results > ul"
    assert resolve_extract_target(target, {}, [current]) == ("#new-results > ul", " li")


def test_unnamed_regions_use_observed_anchor_attributes_to_break_ties():
    target = {"role": "list", "name": "", "attributes": {"id": "results"}, "suffix": ""}
    current = [
        candidate("list", "", "#navigation", {"id": "navigation"}),
        candidate("list", "", "#results", {"id": "results"}),
    ]
    assert resolve_extract_target(target, {}, current) == ("#results", "")


def test_ambiguous_or_missing_semantics_never_return_a_guessed_selector():
    target = {"role": "list", "name": "Package results", "attributes": {}, "suffix": ""}
    current = [candidate("list", "Package results", "#one"), candidate("list", "Package results", "#two")]
    assert resolve_extract_target(target, {}, current) is None
    assert resolve_extract_target(target, {}, []) is None
    assert resolve_extract_target(target, {}, [candidate("status", "Package results", "#status")]) is None
    duplicate = candidate("list", "Package results", "#same", {"id": "same"})
    assert ground_extract_target("#same", {}, [duplicate, duplicate]) is None


def test_name_matching_normalizes_case_and_whitespace():
    target = {"role": "list", "name": "package results", "attributes": {}, "suffix": ""}
    assert resolve_extract_target(target, {}, [candidate("list", "Package   Results", "#results")]) == ("#results", "")


def test_interactive_ax_target_can_be_recorded_for_attribute_extraction():
    selector_map = {
        "12": {"role": "link", "name": "Documentation", "attributes": {"id": "docs"}, "css_candidates": ["#docs", "a"]}
    }
    target = ground_extract_target("#docs", selector_map, [])
    assert resolve_extract_target(target, {"91": {**selector_map["12"], "css_candidates": ["#new-docs"]}}, []) == (
        "#new-docs",
        "",
    )


@pytest.mark.parametrize("suffix", [" a", "; body", " li:not(*)"])
def test_only_observed_semantic_list_table_suffixes_are_supported(suffix):
    target = {"role": "list", "name": "Package results", "attributes": {}, "suffix": suffix}
    assert resolve_extract_target(target, {}, [candidate("list", "Package results", "#results")]) is None
