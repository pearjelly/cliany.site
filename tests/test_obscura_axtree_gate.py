from cliany_site.providers import CapabilitySnapshot, assess_axtree_capability


OBSCURA_DOMAINS = ["Target", "Page", "Runtime", "DOM", "Network", "Fetch", "Storage", "Input", "LP"]
CHROME_DOMAINS = ["Target", "Page", "Runtime", "DOM", "Network", "Fetch", "Storage", "Input", "Accessibility"]


class TestAXTreeGateWithoutAccessibility:
    def test_gate_returns_false_without_accessibility(self):
        snapshot = assess_axtree_capability(OBSCURA_DOMAINS)
        assert snapshot.supports_axtree is False
        assert snapshot.supports_explore is False

    def test_empty_domains_returns_false(self):
        snapshot = assess_axtree_capability([])
        assert snapshot.supports_axtree is False
        assert snapshot.supports_explore is False

    def test_lp_getmarkdown_domain_is_not_accessibility_substitute(self):
        domains_with_lp_only = ["Target", "Page", "Runtime", "DOM", "LP"]
        snapshot = assess_axtree_capability(domains_with_lp_only)
        assert snapshot.supports_axtree is False, "LP.getMarkdown 不得被视为 Accessibility 域的等价替代"
        assert snapshot.supports_explore is False


class TestAXTreeGateWithAccessibility:
    def test_gate_returns_true_with_accessibility(self):
        snapshot = assess_axtree_capability(CHROME_DOMAINS)
        assert snapshot.supports_axtree is True

    def test_supports_explore_true_when_accessibility_present(self):
        snapshot = assess_axtree_capability(CHROME_DOMAINS)
        assert snapshot.supports_explore is True

    def test_accessibility_alone_sufficient_for_axtree(self):
        snapshot = assess_axtree_capability(["Accessibility"])
        assert snapshot.supports_axtree is True
        assert snapshot.supports_explore is True


class TestCapabilitySnapshotContract:
    def test_snapshot_has_required_fields(self):
        snapshot = CapabilitySnapshot(supports_axtree=True, supports_explore=True)
        assert hasattr(snapshot, "supports_axtree")
        assert hasattr(snapshot, "supports_explore")

    def test_snapshot_fields_are_independent(self):
        s1 = CapabilitySnapshot(supports_axtree=True, supports_explore=False)
        s2 = CapabilitySnapshot(supports_axtree=False, supports_explore=False)
        assert s1.supports_axtree != s2.supports_axtree
        assert s1.supports_explore == s2.supports_explore
