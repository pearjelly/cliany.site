import pytest

from cliany_site.codegen import runtime_helpers
from cliany_site.commands.browser._common import fuzzy_find_by_text


@pytest.mark.parametrize("action,role", [
    ("click", "button"), ("type", "textbox"), ("select", "combobox"), ("submit", "textbox"),
])
def test_recorded_semantics_replace_stale_ref(monkeypatch, action, role):
    calls = []
    monkeypatch.setattr(runtime_helpers, "run_atom", lambda args, **kwargs: calls.append(args) or {"ok": True})
    runtime_helpers._execute_single_step({
        "type": action, "ref": "99", "target_name": "Name", "target_role": role, "value": "Ada",
    }, "example.com")
    assert "--ref" not in calls[0]
    assert calls[0][2:6] == ["--text", "Name", "--role", role]


def test_role_filters_before_text_ranking():
    selector_map = {
        "1": {"name": "Name", "role": "button"},
        "2": {"name": "Name", "role": "textbox", "tag_name": "input"},
    }
    assert fuzzy_find_by_text(selector_map, "Name", limit=1, role="textbox")[0]["ref"] == "2"
    assert fuzzy_find_by_text(selector_map, "Name", limit=1, role="combobox") == []
    assert fuzzy_find_by_text(selector_map, "Name", limit=1, role="input")[0]["ref"] == "2"
