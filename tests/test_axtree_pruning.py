from __future__ import annotations

import json
from pathlib import Path

import pytest

from cliany_site.browser.axtree_pruning import (
    collapse_svg_icons,
    dedupe_by_bbox,
    is_occluded,
    is_visible,
    prune_selector_map,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_is_visible_normal_node_returns_true():
    node = {
        "ref": "1",
        "role": "button",
        "name": "确认",
        "attributes": {"style": {"display": "block"}, "class": "btn"},
        "bbox": {"x": 100, "y": 200, "width": 80, "height": 30},
    }
    assert is_visible(node) is True


def test_is_visible_display_none_returns_false():
    node = {
        "ref": "2",
        "role": "div",
        "name": "",
        "attributes": {"style": {"display": "none"}},
        "bbox": {"x": 0, "y": 0, "width": 0, "height": 0},
    }
    assert is_visible(node) is False


def test_is_visible_visibility_hidden_returns_false():
    node = {
        "ref": "3",
        "role": "div",
        "name": "invisible",
        "attributes": {"style": {"visibility": "hidden"}},
        "bbox": {"x": 10, "y": 10, "width": 80, "height": 30},
    }
    assert is_visible(node) is False


def test_is_visible_aria_hidden_true_returns_false():
    node = {
        "ref": "4",
        "role": "img",
        "name": "decorative icon",
        "attributes": {"aria-hidden": "true", "style": {"display": "block"}},
        "bbox": {"x": 5, "y": 5, "width": 24, "height": 24},
    }
    assert is_visible(node) is False


def test_is_visible_zero_bbox_returns_false():
    node = {
        "ref": "5",
        "role": "span",
        "name": "collapsed",
        "attributes": {},
        "bbox": {"x": 100, "y": 100, "width": 0, "height": 0},
    }
    assert is_visible(node) is False


def test_is_visible_hidden_attr_returns_false():
    node = {
        "ref": "6",
        "role": "input",
        "name": "",
        "attributes": {"hidden": "true"},
    }
    assert is_visible(node) is False


def test_is_visible_opacity_zero_returns_false():
    node = {
        "ref": "7",
        "role": "div",
        "name": "faded",
        "attributes": {"style": {"opacity": "0"}},
        "bbox": {"x": 0, "y": 0, "width": 100, "height": 50},
    }
    assert is_visible(node) is False


def test_is_visible_no_attributes_returns_true():
    node = {"ref": "8", "role": "button", "name": "ok"}
    assert is_visible(node) is True


def test_is_occluded_single_node_returns_false():
    node = {
        "ref": "1",
        "role": "button",
        "name": "ok",
        "attributes": {},
        "bbox": {"x": 0, "y": 0, "width": 100, "height": 50},
    }
    assert is_occluded(node, [node]) is False


def test_is_occluded_covered_by_higher_zindex_returns_true():
    node = {
        "ref": "1",
        "role": "button",
        "name": "ok",
        "attributes": {"style": {"z-index": "1"}},
        "bbox": {"x": 10, "y": 10, "width": 80, "height": 30},
    }
    overlay = {
        "ref": "2",
        "role": "div",
        "name": "modal backdrop",
        "attributes": {"style": {"z-index": "10"}},
        "bbox": {"x": 0, "y": 0, "width": 500, "height": 300},
    }
    assert is_occluded(node, [node, overlay]) is True


def test_is_occluded_lower_zindex_overlay_returns_false():
    node = {
        "ref": "1",
        "role": "button",
        "name": "top button",
        "attributes": {"style": {"z-index": "10"}},
        "bbox": {"x": 10, "y": 10, "width": 80, "height": 30},
    }
    underlay = {
        "ref": "2",
        "role": "div",
        "name": "background",
        "attributes": {"style": {"z-index": "1"}},
        "bbox": {"x": 0, "y": 0, "width": 500, "height": 300},
    }
    assert is_occluded(node, [node, underlay]) is False


def test_is_occluded_partial_overlap_returns_false():
    node = {
        "ref": "1",
        "role": "button",
        "name": "left",
        "attributes": {},
        "bbox": {"x": 0, "y": 0, "width": 100, "height": 50},
    }
    partial = {
        "ref": "2",
        "role": "div",
        "name": "partial cover",
        "attributes": {"style": {"z-index": "10"}},
        "bbox": {"x": 50, "y": 0, "width": 100, "height": 100},
    }
    assert is_occluded(node, [node, partial]) is False


def test_is_occluded_no_bbox_returns_false():
    node = {"ref": "1", "role": "button", "name": "no bbox", "attributes": {}}
    assert is_occluded(node, [node]) is False


def test_dedupe_by_bbox_keeps_longer_name_on_same_bbox():
    nodes = [
        {
            "ref": "1",
            "role": "button",
            "name": "OK",
            "attributes": {},
            "bbox": {"x": 0, "y": 0, "width": 80, "height": 30},
        },
        {
            "ref": "2",
            "role": "span",
            "name": "OK — confirm action",
            "attributes": {},
            "bbox": {"x": 0, "y": 0, "width": 80, "height": 30},
        },
    ]
    result = dedupe_by_bbox(nodes)
    assert len(result) == 1
    assert result[0]["name"] == "OK — confirm action"


def test_dedupe_by_bbox_keeps_nodes_without_bbox():
    nodes = [
        {"ref": "1", "role": "button", "name": "A", "attributes": {}},
        {"ref": "2", "role": "button", "name": "B", "attributes": {}},
    ]
    result = dedupe_by_bbox(nodes)
    assert len(result) == 2


def test_dedupe_by_bbox_different_bboxes_all_kept():
    nodes = [
        {
            "ref": "1",
            "role": "button",
            "name": "A",
            "attributes": {},
            "bbox": {"x": 0, "y": 0, "width": 80, "height": 30},
        },
        {
            "ref": "2",
            "role": "button",
            "name": "B",
            "attributes": {},
            "bbox": {"x": 100, "y": 0, "width": 80, "height": 30},
        },
    ]
    result = dedupe_by_bbox(nodes)
    assert len(result) == 2


def test_dedupe_by_bbox_empty_input():
    assert dedupe_by_bbox([]) == []


def test_dedupe_by_bbox_three_same_bbox_keeps_longest():
    nodes = [
        {"ref": "1", "name": "short", "role": "div", "attributes": {}, "bbox": {"x": 0, "y": 0, "width": 50, "height": 20}},
        {"ref": "2", "name": "medium name", "role": "div", "attributes": {}, "bbox": {"x": 0, "y": 0, "width": 50, "height": 20}},
        {"ref": "3", "name": "the longest name of all", "role": "div", "attributes": {}, "bbox": {"x": 0, "y": 0, "width": 50, "height": 20}},
    ]
    result = dedupe_by_bbox(nodes)
    assert len(result) == 1
    assert result[0]["name"] == "the longest name of all"


def test_collapse_svg_icons_merges_consecutive_imgs():
    nodes = [
        {"ref": "1", "role": "button", "name": "click", "attributes": {}},
        {"ref": "2", "role": "img", "name": "icon A", "attributes": {}},
        {"ref": "3", "role": "img", "name": "icon B", "attributes": {}},
        {"ref": "4", "role": "img", "name": "icon C", "attributes": {}},
        {"ref": "5", "role": "link", "name": "home", "attributes": {}},
    ]
    result = collapse_svg_icons(nodes)
    assert len(result) == 3
    assert result[1]["role"] == "icon_group"
    assert result[1]["_collapsed_count"] == 3


def test_collapse_svg_icons_single_img_not_collapsed():
    nodes = [{"ref": "1", "role": "img", "name": "single icon", "attributes": {}}]
    result = collapse_svg_icons(nodes)
    assert len(result) == 1
    assert result[0]["role"] == "img"


def test_collapse_svg_icons_no_svgs_unchanged():
    nodes = [
        {"ref": "1", "role": "button", "name": "A", "attributes": {}},
        {"ref": "2", "role": "link", "name": "B", "attributes": {}},
    ]
    result = collapse_svg_icons(nodes)
    assert len(result) == 2


def test_collapse_svg_icons_svg_tag_in_attributes():
    nodes = [
        {"ref": "1", "role": "generic", "name": "", "attributes": {"tag": "svg"}},
        {"ref": "2", "role": "generic", "name": "", "attributes": {"tag": "path"}},
        {"ref": "3", "role": "button", "name": "ok", "attributes": {}},
    ]
    result = collapse_svg_icons(nodes)
    assert len(result) == 2
    assert result[0]["role"] == "icon_group"
    assert result[0]["_collapsed_count"] == 2


def test_collapse_svg_icons_empty_input():
    assert collapse_svg_icons([]) == []


def test_prune_selector_map_empty_returns_empty_with_meta():
    pruned, meta = prune_selector_map({})
    assert pruned == {}
    assert meta["original_count"] == 0
    assert meta["pruned_count"] == 0
    assert meta["pruning_ratio"] == 0.0


def test_prune_selector_map_none_input_returns_empty():
    pruned, meta = prune_selector_map(None)  # type: ignore[arg-type]
    assert pruned == {}
    assert meta["original_count"] == 0


def test_prune_selector_map_meta_fields_present():
    sm = {
        "1": {"ref": "1", "role": "button", "name": "go", "attributes": {}},
        "2": {"ref": "2", "role": "div", "name": "x", "attributes": {"style": {"display": "none"}}},
    }
    pruned, meta = prune_selector_map(sm)
    assert "original_count" in meta
    assert "pruned_count" in meta
    assert "pruning_ratio" in meta


def test_prune_selector_map_removes_hidden_nodes():
    sm = {
        "1": {"ref": "1", "role": "button", "name": "visible", "attributes": {}},
        "2": {"ref": "2", "role": "div", "name": "hidden", "attributes": {"style": {"display": "none"}}},
        "3": {"ref": "3", "role": "span", "name": "aria", "attributes": {"aria-hidden": "true"}},
    }
    pruned, meta = prune_selector_map(sm)
    assert "1" in pruned
    assert "2" not in pruned
    assert "3" not in pruned
    assert meta["pruned_count"] == 1
    assert meta["original_count"] == 3


def test_prune_selector_map_pruning_ratio_correct():
    sm = {
        "1": {"ref": "1", "role": "button", "name": "visible", "attributes": {}},
        "2": {"ref": "2", "role": "div", "name": "h1", "attributes": {"style": {"display": "none"}}},
        "3": {"ref": "3", "role": "div", "name": "h2", "attributes": {"style": {"visibility": "hidden"}}},
        "4": {"ref": "4", "role": "div", "name": "h3", "attributes": {"hidden": "true"}},
    }
    pruned, meta = prune_selector_map(sm)
    expected_ratio = round(1.0 - meta["pruned_count"] / meta["original_count"], 4)
    assert meta["pruning_ratio"] == expected_ratio
    assert meta["pruning_ratio"] > 0.0


def test_prune_selector_map_fixture_200_elements():
    fixture_path = FIXTURES_DIR / "sample_selector_map.json"
    with fixture_path.open() as f:
        sm = json.load(f)

    assert len(sm) >= 200, "fixture should have 200+ elements"

    pruned, meta = prune_selector_map(sm)

    assert meta["original_count"] >= 200
    assert meta["pruned_count"] < meta["original_count"]
    assert 0.0 < meta["pruning_ratio"] <= 1.0
