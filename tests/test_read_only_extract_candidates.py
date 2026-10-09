from types import SimpleNamespace

from cliany_site.browser.selector import (
    collect_read_only_extract_candidates,
    format_read_only_extract_candidates,
    is_grounded_extract_selector,
)


class Node:
    def __init__(self, tag, role, text, attributes=None, *, visible=True, children=None):
        self.tag_name = tag
        self.ax_node = SimpleNamespace(role=role, name="")
        self.attributes = attributes or {}
        self.is_visible = visible
        self.children_nodes = children or []
        self.text = text

    def get_all_children_text(self):
        return self.text


def legacy_candidates(root):
    return [
        {key: item[key] for key in ("role", "name", "text", "selectors")}
        for item in collect_read_only_extract_candidates(root)
    ]


def test_read_only_candidates_use_observed_semantic_nodes_and_stable_attributes():
    root = Node("body", "generic", "", children=[
        Node("output", "status", "1 matches", {"id": "summary"}),
        Node("ul", "list", "Beta runner", {"id": "results", "aria-label": "Package results"}),
        Node("output", "status", "Hidden", {"id": "hidden"}, visible=False),
        Node("div", "generic", "", visible=False, children=[
            Node("output", "status", "Hidden child", {"id": "hidden-child"}),
        ]),
        Node("output", "status", "Unaddressable"),
        Node("button", "button", "Search", {"id": "search"}),
    ])

    candidates = collect_read_only_extract_candidates(root)

    assert legacy_candidates(root) == [
        {"role": "status", "name": "", "text": "1 matches", "selectors": ["#summary"]},
        {
            "role": "list", "name": "", "text": "Beta runner",
            "selectors": ["#results", '[aria-label="Package results"]'],
        },
    ]
    rendered = format_read_only_extract_candidates(candidates)
    assert '[status "" text="1 matches"] → #summary' in rendered
    assert '[list "" text="Beta runner"] → #results' in rendered
    assert "hidden" not in rendered.lower()
    assert candidates[1]["semantic_name"] == "Package results"
    assert candidates[1]["anchor_attributes"] == {"id": "results", "aria-label": "Package results"}
    assert candidates[1]["root_selector"] == "#results"


def test_empty_semantic_list_remains_addressable():
    root = Node("ul", "list", "", {"id": "results"})
    assert legacy_candidates(root) == [
        {"role": "list", "name": "", "text": "", "selectors": ["#results"]}
    ]


def test_unique_semantic_output_without_id_is_a_candidate():
    root = Node("body", "generic", "", children=[Node("output", "status", "Ready")])
    assert legacy_candidates(root) == [
        {"role": "status", "name": "", "text": "Ready", "selectors": ["output"]}
    ]
    root.children_nodes.append(Node("output", "generic", "Other"))
    assert collect_read_only_extract_candidates(root) == []


def test_list_can_use_observed_unique_parent_anchor():
    result_list = Node("ul", "list", "pathlib", children=[Node("li", "listitem", "pathlib")])
    parent = Node("div", "generic", "pathlib", {"id": "search-results"}, children=[result_list])
    root = Node("body", "generic", "", children=[Node("ul", "list", "sidebar"), parent])

    assert legacy_candidates(root) == [
        {"role": "list", "name": "", "text": "pathlib", "selectors": ["#search-results li"]}
    ]
    assert is_grounded_extract_selector("#search-results li", {}, collect_read_only_extract_candidates(root))
    assert collect_read_only_extract_candidates(root)[0]["root_selector"] == "#search-results > ul"

    parent.children_nodes.append(Node("ul", "list", "other"))
    assert collect_read_only_extract_candidates(root) == []


def test_table_can_use_observed_unique_parent_anchor():
    table = Node("table", "table", "Ada", children=[Node("tr", "row", "Ada")])
    parent = Node("section", "generic", "Ada", {"data-testid": "records"}, children=[table])
    root = Node("body", "generic", "", children=[Node("table", "table", "sidebar"), parent])

    assert legacy_candidates(root) == [
        {"role": "table", "name": "", "text": "Ada", "selectors": ['[data-testid="records"] tr']}
    ]


def test_extract_selector_requires_observed_candidate_or_semantic_child():
    selector_map = {"1": {"css_candidates": ["#count"]}}
    candidates = [
        {"role": "list", "selectors": ["#results"]},
        {"role": "table", "selectors": ["#records"]},
    ]
    assert is_grounded_extract_selector("#count", selector_map, candidates)
    assert is_grounded_extract_selector("#results li", selector_map, candidates)
    assert is_grounded_extract_selector("#records tr", selector_map, candidates)
    assert not is_grounded_extract_selector("#guessed li", selector_map, candidates)
    assert not is_grounded_extract_selector("#results a", selector_map, candidates)
    assert not is_grounded_extract_selector("#count li", selector_map, candidates)
