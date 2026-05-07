from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from cliany_site.browser.axtree import capture_axtree


def _make_mock_element(ref: str, visible: bool = True) -> MagicMock:
    el = MagicMock()
    el.tag_name = "button"
    el.ax_node = MagicMock()
    el.ax_node.name = f"按钮-{ref}"
    el.node_value = ""
    el.frame_id = None
    el.target_id = None
    el.shadow_root_type = None
    el.attributes = {} if visible else {"style": {"display": "none"}}
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
    page.title = AsyncMock(return_value="Example Page")
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


async def test_pruning_enabled_by_default(monkeypatch):
    monkeypatch.delenv("CLIANY_AXTREE_PRUNE", raising=False)

    raw_elements = {
        "1": _make_mock_element("1", visible=True),
        "2": _make_mock_element("2", visible=False),
        "3": _make_mock_element("3", visible=True),
    }
    dom_service = _make_dom_service(raw_elements)
    bs = _make_browser_session()
    cfg = _make_cfg()

    with (
        patch("browser_use.dom.service.DomService", return_value=dom_service),
        patch("cliany_site.config.get_config", return_value=cfg),
    ):
        tree = await capture_axtree(bs)

    assert "pruning_meta" in tree
    meta = tree["pruning_meta"]
    assert meta["original_count"] == 3
    assert meta["pruned_count"] == 2
    assert meta["pruning_ratio"] > 0.0


async def test_pruning_disabled_when_env_zero(monkeypatch):
    monkeypatch.setenv("CLIANY_AXTREE_PRUNE", "0")

    raw_elements = {
        "1": _make_mock_element("1", visible=True),
        "2": _make_mock_element("2", visible=False),
    }
    dom_service = _make_dom_service(raw_elements)
    bs = _make_browser_session()
    cfg = _make_cfg()

    with (
        patch("browser_use.dom.service.DomService", return_value=dom_service),
        patch("cliany_site.config.get_config", return_value=cfg),
    ):
        tree = await capture_axtree(bs)

    assert "pruning_meta" in tree
    meta = tree["pruning_meta"]
    assert meta["original_count"] == 0
    assert meta["pruned_count"] == 0
    assert meta["pruning_ratio"] == 0.0


async def test_pruning_meta_keys_always_present(monkeypatch):
    for env_val in ("1", "0"):
        monkeypatch.setenv("CLIANY_AXTREE_PRUNE", env_val)

        dom_service = _make_dom_service({"1": _make_mock_element("1")})
        bs = _make_browser_session()
        cfg = _make_cfg()

        with (
            patch("browser_use.dom.service.DomService", return_value=dom_service),
            patch("cliany_site.config.get_config", return_value=cfg),
        ):
            tree = await capture_axtree(bs)

        meta = tree["pruning_meta"]
        assert "original_count" in meta, f"env={env_val} 缺少 original_count"
        assert "pruned_count" in meta, f"env={env_val} 缺少 pruned_count"
        assert "pruning_ratio" in meta, f"env={env_val} 缺少 pruning_ratio"


async def test_nested_stats_not_broken_after_pruning(monkeypatch):
    monkeypatch.setenv("CLIANY_AXTREE_PRUNE", "1")

    dom_service = _make_dom_service({"1": _make_mock_element("1")})
    bs = _make_browser_session()
    cfg = _make_cfg()

    with (
        patch("browser_use.dom.service.DomService", return_value=dom_service),
        patch("cliany_site.config.get_config", return_value=cfg),
    ):
        tree = await capture_axtree(bs)

    assert "iframe_count" in tree
    assert "shadow_root_count" in tree
    assert tree["iframe_count"] == 0
    assert tree["shadow_root_count"] == 0


async def test_all_invisible_nodes_pruned(monkeypatch):
    monkeypatch.setenv("CLIANY_AXTREE_PRUNE", "1")

    raw_elements = {
        "1": _make_mock_element("1", visible=False),
        "2": _make_mock_element("2", visible=False),
    }
    dom_service = _make_dom_service(raw_elements)
    bs = _make_browser_session()
    cfg = _make_cfg()

    with (
        patch("browser_use.dom.service.DomService", return_value=dom_service),
        patch("cliany_site.config.get_config", return_value=cfg),
    ):
        tree = await capture_axtree(bs)

    meta = tree["pruning_meta"]
    assert meta["original_count"] == 2
    assert meta["pruned_count"] == 0
    assert meta["pruning_ratio"] == 1.0
