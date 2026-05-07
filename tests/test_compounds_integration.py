from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from cliany_site.browser.axtree import capture_axtree, extract_interactive_elements


def _make_mock_element(
    tag_name: str,
    attributes: dict | None = None,
    ax_name: str = "",
) -> MagicMock:
    el = MagicMock()
    el.tag_name = tag_name
    el.ax_node = MagicMock()
    el.ax_node.name = ax_name
    el.node_value = ""
    el.frame_id = None
    el.target_id = None
    el.shadow_root_type = None
    el.attributes = attributes if attributes is not None else {}
    return el


def _make_cfg(vision: bool = False) -> MagicMock:
    cfg = MagicMock()
    cfg.vision_enabled = vision
    cfg.cross_origin_iframes = False
    cfg.max_iframes = 10
    cfg.max_iframe_depth = 3
    return cfg


def _make_browser_session() -> AsyncMock:
    bs = AsyncMock()
    page = AsyncMock()
    page.url = "https://example.com"
    page.title = AsyncMock(return_value="Test Page")
    bs.get_current_page = AsyncMock(return_value=page)
    bs.update_cached_selector_map = MagicMock()
    return bs


def _make_dom_service(raw_elements: dict) -> AsyncMock:
    serialized = MagicMock()
    serialized.selector_map = raw_elements
    serialized.llm_representation.return_value = "mock element tree"

    dom_service = AsyncMock()
    dom_service.get_serialized_dom_tree = AsyncMock(
        return_value=(serialized, MagicMock(), {})
    )
    return dom_service


class TestCaptureAxtreeCompounds:
    async def test_compounds_key_always_present(self, monkeypatch):
        monkeypatch.delenv("CLIANY_AXTREE_PRUNE", raising=False)

        raw_elements = {"1": _make_mock_element("button", {})}
        dom_service = _make_dom_service(raw_elements)
        bs = _make_browser_session()
        cfg = _make_cfg()

        with (
            patch("browser_use.dom.service.DomService", return_value=dom_service),
            patch("cliany_site.config.get_config", return_value=cfg),
        ):
            tree = await capture_axtree(bs)

        assert "compounds" in tree

    async def test_compounds_is_dict(self, monkeypatch):
        monkeypatch.delenv("CLIANY_AXTREE_PRUNE", raising=False)

        raw_elements = {"1": _make_mock_element("button", {})}
        dom_service = _make_dom_service(raw_elements)
        bs = _make_browser_session()
        cfg = _make_cfg()

        with (
            patch("browser_use.dom.service.DomService", return_value=dom_service),
            patch("cliany_site.config.get_config", return_value=cfg),
        ):
            tree = await capture_axtree(bs)

        assert isinstance(tree["compounds"], dict)

    async def test_no_compound_elements_yields_empty_dict(self, monkeypatch):
        monkeypatch.delenv("CLIANY_AXTREE_PRUNE", raising=False)

        raw_elements = {
            "1": _make_mock_element("button", {}),
            "2": _make_mock_element("link", {}),
        }
        dom_service = _make_dom_service(raw_elements)
        bs = _make_browser_session()
        cfg = _make_cfg()

        with (
            patch("browser_use.dom.service.DomService", return_value=dom_service),
            patch("cliany_site.config.get_config", return_value=cfg),
        ):
            tree = await capture_axtree(bs)

        assert tree["compounds"] == {}

    async def test_select_element_detected_as_compound(self, monkeypatch):
        monkeypatch.setenv("CLIANY_AXTREE_PRUNE", "0")

        options = [{"value": "a", "text": "A"}, {"value": "b", "text": "B"}]
        raw_elements = {
            "1": _make_mock_element("select", {"options": options}),
        }
        dom_service = _make_dom_service(raw_elements)
        bs = _make_browser_session()
        cfg = _make_cfg()

        with (
            patch("browser_use.dom.service.DomService", return_value=dom_service),
            patch("cliany_site.config.get_config", return_value=cfg),
        ):
            tree = await capture_axtree(bs)

        assert "1" in tree["compounds"]
        assert "select_options" in tree["compounds"]["1"]

    async def test_compounds_keys_are_strings(self, monkeypatch):
        monkeypatch.setenv("CLIANY_AXTREE_PRUNE", "0")

        options = [{"value": "x", "text": "X"}]
        raw_elements = {
            "42": _make_mock_element("select", {"options": options}),
        }
        dom_service = _make_dom_service(raw_elements)
        bs = _make_browser_session()
        cfg = _make_cfg()

        with (
            patch("browser_use.dom.service.DomService", return_value=dom_service),
            patch("cliany_site.config.get_config", return_value=cfg),
        ):
            tree = await capture_axtree(bs)

        for key in tree["compounds"]:
            assert isinstance(key, str), f"compounds 键 {key!r} 不是字符串"

    async def test_mixed_elements_only_compound_in_compounds(self, monkeypatch):
        monkeypatch.setenv("CLIANY_AXTREE_PRUNE", "0")

        options = [{"value": "1", "text": "One"}]
        raw_elements = {
            "1": _make_mock_element("button", {}),
            "2": _make_mock_element("select", {"options": options}),
            "3": _make_mock_element("input", {"type": "file", "accept": ".pdf"}),
        }
        dom_service = _make_dom_service(raw_elements)
        bs = _make_browser_session()
        cfg = _make_cfg()

        with (
            patch("browser_use.dom.service.DomService", return_value=dom_service),
            patch("cliany_site.config.get_config", return_value=cfg),
        ):
            tree = await capture_axtree(bs)

        compounds = tree["compounds"]
        assert "1" not in compounds
        assert "2" in compounds
        assert "3" in compounds

    async def test_compounds_present_when_pruning_disabled(self, monkeypatch):
        monkeypatch.setenv("CLIANY_AXTREE_PRUNE", "0")

        raw_elements = {"1": _make_mock_element("button", {})}
        dom_service = _make_dom_service(raw_elements)
        bs = _make_browser_session()
        cfg = _make_cfg()

        with (
            patch("browser_use.dom.service.DomService", return_value=dom_service),
            patch("cliany_site.config.get_config", return_value=cfg),
        ):
            tree = await capture_axtree(bs)

        assert "compounds" in tree
        assert isinstance(tree["compounds"], dict)


class TestExtractInteractiveElementsCompound:
    def _make_tree(self, selector_map: dict, compounds: dict) -> dict:
        return {
            "element_tree": "mock",
            "selector_map": selector_map,
            "compounds": compounds,
            "url": "https://example.com",
            "title": "Test",
            "iframe_count": 0,
            "shadow_root_count": 0,
            "screenshot": b"",
            "pruning_meta": {"original_count": 0, "pruned_count": 0, "pruning_ratio": 0.0},
        }

    def test_compound_field_attached_when_ref_in_compounds(self):
        selector_map = {
            "1": {"ref": "1", "role": "select", "name": "Country", "attributes": {"options": []}},
        }
        compounds = {
            "1": {"select_options": {"options": [], "truncated": False}},
        }
        tree = self._make_tree(selector_map, compounds)
        elements = extract_interactive_elements(tree)

        assert len(elements) == 1
        elem = elements[0]
        assert "compound" in elem
        assert elem["compound"] == compounds["1"]

    def test_no_compound_field_for_non_compound_element(self):
        selector_map = {
            "1": {"ref": "1", "role": "button", "name": "Submit", "attributes": {}},
        }
        compounds: dict = {}
        tree = self._make_tree(selector_map, compounds)
        elements = extract_interactive_elements(tree)

        assert len(elements) == 1
        assert "compound" not in elements[0]

    def test_mixed_elements_only_compound_ones_get_field(self):
        selector_map = {
            "1": {"ref": "1", "role": "button", "name": "OK", "attributes": {}},
            "2": {"ref": "2", "role": "select", "name": "City", "attributes": {}},
            "3": {"ref": "3", "role": "link", "name": "Home", "attributes": {}},
        }
        compounds = {
            "2": {"select_options": {"options": [], "truncated": False}},
        }
        tree = self._make_tree(selector_map, compounds)
        elements = extract_interactive_elements(tree)

        by_ref = {e["ref"]: e for e in elements}
        assert "compound" not in by_ref["1"]
        assert "compound" in by_ref["2"]
        assert by_ref["2"]["compound"] == compounds["2"]
        assert "compound" not in by_ref["3"]

    def test_empty_selector_map_returns_empty_list(self):
        tree = self._make_tree({}, {})
        assert extract_interactive_elements(tree) == []

    def test_empty_compounds_in_tree_means_no_compound_field(self):
        selector_map = {
            "1": {"ref": "1", "role": "button", "name": "X", "attributes": {}},
            "2": {"ref": "2", "role": "textbox", "name": "Y", "attributes": {}},
        }
        tree = self._make_tree(selector_map, {})
        elements = extract_interactive_elements(tree)
        for elem in elements:
            assert "compound" not in elem

    def test_missing_compounds_key_in_tree_gracefully_handled(self):
        selector_map = {
            "1": {"ref": "1", "role": "button", "name": "X", "attributes": {}},
        }
        tree = {
            "element_tree": "mock",
            "selector_map": selector_map,
        }
        elements = extract_interactive_elements(tree)
        assert len(elements) == 1
        assert "compound" not in elements[0]

    def test_compound_data_is_correct_value(self):
        compound_data = {
            "select_options": {"options": [{"value": "a", "text": "A"}], "truncated": False},
        }
        selector_map = {
            "5": {"ref": "5", "role": "combobox", "name": "Region", "attributes": {}},
        }
        compounds = {"5": compound_data}
        tree = self._make_tree(selector_map, compounds)
        elements = extract_interactive_elements(tree)

        assert elements[0]["compound"] is compound_data
