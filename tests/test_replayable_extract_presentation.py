import copy

import pytest

from cliany_site.browser.selector import (
    format_read_only_extract_candidates,
    format_selector_candidates_section,
    ground_extract_target,
    replayable_extract_selectors,
    resolve_extract_target,
)


def _snapshot():
    selectors = {
        "1": {"role": "list", "name": "", "attributes": {"class": "search"},
              "css_candidates": ["ul.search", "ul"]},
        "2": {"role": "list", "name": "", "attributes": {}, "css_candidates": ["ul"]},
        "3": {"role": "link", "name": "Documentation", "attributes": {"id": "docs"},
              "css_candidates": ["#docs", "a"]},
        "4": {"role": "link", "name": "Home", "attributes": {"id": "home"},
              "css_candidates": ["#home", "a"]},
    }
    candidates = [{"role": "list", "name": "", "semantic_name": "", "text": "Results",
                   "selectors": ["#results li"], "root_selector": "#results > ul",
                   "anchor_attributes": {"id": "results"}}]
    return selectors, candidates


def test_ambiguous_class_is_not_offered_but_observed_anchor_and_attributes_remain():
    selectors, candidates = _snapshot()
    before = copy.deepcopy((selectors, candidates))
    allowed = replayable_extract_selectors(selectors, candidates)
    assert allowed == {"#results li", "#docs", "#home"}
    rendered = format_selector_candidates_section(selectors, allowed_selectors=allowed)
    assert "ul.search" not in rendered and "#docs" in rendered
    assert "#results li" in format_read_only_extract_candidates(candidates, allowed_selectors=allowed)
    assert (selectors, candidates) == before
    assert "ul.search" in format_selector_candidates_section(selectors)


@pytest.mark.parametrize("role,selector", [("table", "#rows tr"), ("status", "#count"), ("heading", "#title")])
def test_read_only_modes_keep_the_same_unique_identity_gate(role, selector):
    candidate = {"role": role, "name": "", "selectors": [selector],
                 "anchor_attributes": {"id": "region"}, "root_selector": selector}
    allowed = replayable_extract_selectors({}, [candidate])
    assert allowed == {selector}
    assert selector in format_read_only_extract_candidates([candidate], allowed_selectors=allowed)


def test_every_offered_selector_is_observed_grounded_and_uniquely_resolvable():
    selectors, candidates = _snapshot()
    for selector in replayable_extract_selectors(selectors, candidates):
        target = ground_extract_target(selector, selectors, candidates)
        assert target is not None and resolve_extract_target(target, selectors, candidates) is not None
    assert "#guessed" not in replayable_extract_selectors(selectors, candidates)
    assert replayable_extract_selectors({}, []) == set()


def test_filtering_does_not_break_formatter_limits_or_invent_rows():
    selectors, candidates = _snapshot()
    assert format_selector_candidates_section(selectors, allowed_selectors=set()) == ""
    assert format_read_only_extract_candidates(candidates, allowed_selectors=set()) == ""
    assert len(format_selector_candidates_section(selectors, max_chars=25,
               allowed_selectors=replayable_extract_selectors(selectors, candidates))) <= 25
    assert "#results li" not in format_read_only_extract_candidates(candidates, max_chars=1)
