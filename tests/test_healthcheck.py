
from cliany_site.healthcheck import (
    DIFF_THRESHOLD,
    MATCH_THRESHOLD,
    ElementDiff,
    HealthCheckResult,
    _normalize_text,
    _score_element_match,
    apply_selector_fixes,
    compare_elements,
)


class TestNormalizeText:
    def test_strips_and_casefolds(self):
        assert _normalize_text("  Hello World  ") == "hello world"

    def test_collapses_whitespace(self):
        assert _normalize_text("a   b\t\nc") == "a b c"

    def test_handles_none(self):
        assert _normalize_text(None) == ""

    def test_handles_empty_string(self):
        assert _normalize_text("") == ""


class TestScoreElementMatch:
    def test_exact_name_match(self):
        snap = {"target_name": "Search", "target_role": "button"}
        cand = {"name": "Search", "role": "button"}
        score = _score_element_match(snap, cand)
        assert score >= 40 + 15

    def test_partial_name_match(self):
        snap = {"target_name": "Search", "target_role": "button"}
        cand = {"name": "Search Results", "role": "button"}
        score = _score_element_match(snap, cand)
        assert score >= 20 + 15

    def test_role_only_match(self):
        snap = {"target_name": "Foo", "target_role": "button"}
        cand = {"name": "Bar", "role": "button"}
        assert _score_element_match(snap, cand) == 15

    def test_no_match(self):
        snap = {"target_name": "Alpha", "target_role": "link"}
        cand = {"name": "Beta", "role": "button"}
        assert _score_element_match(snap, cand) == 0

    def test_attribute_id_match(self):
        snap = {"target_name": "X", "target_role": "button", "target_attributes": {"id": "search-btn"}}
        cand = {"name": "X", "role": "button", "attributes": {"id": "search-btn"}}
        score = _score_element_match(snap, cand)
        assert score >= 40 + 15 + 30

    def test_multiple_attribute_matches(self):
        snap = {
            "target_name": "X",
            "target_role": "textbox",
            "target_attributes": {"id": "q", "placeholder": "Type here"},
        }
        cand = {
            "name": "X",
            "role": "textbox",
            "attributes": {"id": "q", "placeholder": "Type here"},
        }
        score = _score_element_match(snap, cand)
        assert score >= 40 + 15 + 30 + 18

    def test_empty_elements(self):
        assert _score_element_match({}, {}) == 0

    def test_case_insensitive_name_match(self):
        snap = {"target_name": "SEARCH"}
        cand = {"name": "search"}
        score = _score_element_match(snap, cand)
        assert score >= 40

    def test_uses_alt_keys_name_and_role(self):
        snap = {"name": "Login", "role": "link"}
        cand = {"name": "Login", "role": "link"}
        score = _score_element_match(snap, cand)
        assert score >= 55

    def test_uses_alt_key_attributes(self):
        snap = {"attributes": {"id": "main"}}
        cand = {"attributes": {"id": "main"}}
        score = _score_element_match(snap, cand)
        assert score >= 30


class TestCompareElements:
    def _snap_elem(self, name, role, ref, attrs=None):
        return {
            "target_name": name,
            "target_role": role,
            "target_ref": ref,
            "target_attributes": attrs or {},
        }

    def _curr_elem(self, name, role, ref, attrs=None):
        return {
            "name": name,
            "role": role,
            "ref": ref,
            "attributes": attrs or {},
        }

    def test_all_matched_is_healthy(self):
        snap = [self._snap_elem("Search", "button", "1")]
        curr = [self._curr_elem("Search", "button", "10", {"id": "s"})]
        result = compare_elements(snap, curr, "example.com", "search")

        assert result.healthy
        assert result.matched == 1
        assert result.missing == 0
        assert result.changed == 0

    def test_all_missing_is_unhealthy(self):
        snap = [
            self._snap_elem("A", "button", "1"),
            self._snap_elem("B", "link", "2"),
            self._snap_elem("C", "textbox", "3"),
        ]
        curr = [self._curr_elem("X", "img", "99")]
        result = compare_elements(snap, curr, "test.com", "cmd")

        assert not result.healthy
        assert result.missing == 3
        assert result.diff_ratio == 1.0

    def test_below_threshold_is_healthy(self):
        snap = [
            self._snap_elem("A", "button", "1"),
            self._snap_elem("B", "button", "2"),
            self._snap_elem("C", "button", "3"),
            self._snap_elem("D", "button", "4"),
        ]
        curr = [
            self._curr_elem("A", "button", "11"),
            self._curr_elem("B", "button", "12"),
            self._curr_elem("C", "button", "13"),
            self._curr_elem("ZZZZZ", "img", "99"),
        ]
        result = compare_elements(snap, curr)

        assert result.matched == 3
        assert result.missing == 1
        assert result.diff_ratio == 0.25
        assert result.diff_ratio == 0.25
        assert result.diff_ratio < DIFF_THRESHOLD
        assert result.healthy

    def test_generates_fixes_for_changed(self):
        snap = [self._snap_elem("Search", "button", "1")]
        curr = [self._curr_elem("Search", "link", "42")]
        result = compare_elements(snap, curr)

        if result.changed > 0:
            assert len(result.fixes) > 0
            fix = result.fixes[0]
            assert fix["old_ref"] == "1"
            assert fix["new_ref"] == "42"

    def test_empty_snapshot_is_healthy(self):
        result = compare_elements([], [self._curr_elem("A", "btn", "1")])
        assert result.healthy
        assert result.snapshot_count == 0

    def test_empty_current_all_missing(self):
        snap = [self._snap_elem("A", "button", "1")]
        result = compare_elements(snap, [])
        assert result.missing == 1
        assert not result.healthy

    def test_greedy_matching_no_double_use(self):
        snap = [
            self._snap_elem("Submit", "button", "1"),
            self._snap_elem("Submit", "button", "2"),
        ]
        curr = [self._curr_elem("Submit", "button", "10")]
        result = compare_elements(snap, curr)

        assert result.matched + result.changed <= 1
        assert result.missing >= 1

    def test_to_dict(self):
        result = HealthCheckResult(
            domain="d.com",
            command_name="cmd",
            snapshot_count=2,
            current_count=3,
            matched=1,
            missing=1,
            diff_ratio=0.5,
            healthy=False,
            diffs=[
                ElementDiff(ref="1", name="A", role="btn", status="matched", best_match_score=60),
                ElementDiff(ref="2", name="B", role="link", status="missing"),
            ],
        )
        d = result.to_dict()
        assert d["domain"] == "d.com"
        assert d["healthy"] is False
        assert len(d["diffs"]) == 2


class TestApplySelectorFixes:
    def test_fix_by_ref(self):
        actions = [{"ref": "1", "target_ref": "1", "target_name": "Old"}]
        fixes = [{"old_ref": "1", "old_name": "Old", "new_ref": "42", "new_name": "New"}]
        result = apply_selector_fixes(actions, fixes)

        assert result[0]["ref"] == "42"
        assert result[0]["target_ref"] == "42"
        assert result[0]["target_name"] == "New"

    def test_fix_by_name_fallback(self):
        actions = [{"target_ref": "999", "target_name": "Submit"}]
        fixes = [{"old_ref": "", "old_name": "Submit", "new_ref": "55", "new_name": "Send"}]
        result = apply_selector_fixes(actions, fixes)

        assert result[0]["target_ref"] == "55"
        assert result[0]["target_name"] == "Send"

    def test_no_fixes_returns_unchanged(self):
        actions = [{"ref": "1", "target_name": "A"}]
        result = apply_selector_fixes(actions, [])
        assert result[0]["ref"] == "1"

    def test_unmatched_action_unchanged(self):
        actions = [{"ref": "99", "target_name": "Unmatched"}]
        fixes = [{"old_ref": "1", "old_name": "Other", "new_ref": "42", "new_name": "X"}]
        result = apply_selector_fixes(actions, fixes)
        assert result[0]["ref"] == "99"

    def test_mutates_in_place(self):
        actions = [{"ref": "1", "target_ref": "1", "target_name": "Old"}]
        fixes = [{"old_ref": "1", "new_ref": "42", "new_name": "New"}]
        returned = apply_selector_fixes(actions, fixes)
        assert returned is actions

    def test_skips_non_dict_actions(self):
        actions = ["not a dict", {"ref": "1", "target_name": "A"}]  # type: ignore[list-item]
        fixes = [{"old_ref": "1", "new_ref": "2", "new_name": "B"}]
        result = apply_selector_fixes(actions, fixes)
        assert result[0] == "not a dict"
        assert result[1]["ref"] == "2"

    def test_multiple_fixes(self):
        actions = [
            {"ref": "1", "target_ref": "1", "target_name": "A"},
            {"ref": "2", "target_ref": "2", "target_name": "B"},
        ]
        fixes = [
            {"old_ref": "1", "new_ref": "10", "new_name": "A2"},
            {"old_ref": "2", "new_ref": "20", "new_name": "B2"},
        ]
        result = apply_selector_fixes(actions, fixes)
        assert result[0]["ref"] == "10"
        assert result[1]["ref"] == "20"


class TestThresholdConstants:
    def test_diff_threshold_value(self):
        assert DIFF_THRESHOLD == 0.30

    def test_match_threshold_value(self):
        assert MATCH_THRESHOLD == 30
