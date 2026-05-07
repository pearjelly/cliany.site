from cliany_site.browser.axtree import axtree_to_markdown


class TestAxtreeMetaOutput:
    def test_pruning_meta_included_when_ratio_gt_zero(self):
        tree = {
            "url": "https://example.com",
            "title": "Test Page",
            "element_tree": "button 'Submit' @ref=1",
            "iframe_count": 0,
            "shadow_root_count": 0,
            "pruning_meta": {
                "original_count": 100,
                "pruned_count": 20,
                "pruning_ratio": 0.2,
            },
        }
        result = axtree_to_markdown(tree)
        assert "Pruning: 20/100 (20.0% reduced)" in result

    def test_pruning_meta_not_included_when_ratio_zero(self):
        tree = {
            "url": "https://example.com",
            "title": "Test Page",
            "element_tree": "button 'Submit' @ref=1",
            "iframe_count": 0,
            "shadow_root_count": 0,
            "pruning_meta": {
                "original_count": 100,
                "pruned_count": 0,
                "pruning_ratio": 0.0,
            },
        }
        result = axtree_to_markdown(tree)
        assert "Pruning:" not in result

    def test_pruning_meta_not_included_when_missing(self):
        tree = {
            "url": "https://example.com",
            "title": "Test Page",
            "element_tree": "button 'Submit' @ref=1",
            "iframe_count": 0,
            "shadow_root_count": 0,
        }
        result = axtree_to_markdown(tree)
        assert "Pruning:" not in result