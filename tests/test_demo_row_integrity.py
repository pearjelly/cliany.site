import json

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.commands import demo


@pytest.mark.parametrize("case_id,rows_key,field,valid", [
    ("apache-jira-issues", "issues", "key", {"key": "SPARK-1", "summary": "Public issue"}),
    ("apache-jira-issues", "issues", "summary", {"key": "SPARK-1", "summary": "Public issue"}),
    ("apache-confluence-search", "results", "id", {"id": "123", "title": "Public page"}),
    ("apache-confluence-search", "results", "title", {"id": "123", "title": "Public page"}),
    ("apache-jenkins-jobs", "jobs", "name", {"name": "Public job", "url": "https://example.org/job/1"}),
    ("apache-jenkins-jobs", "jobs", "url", {"name": "Public job", "url": "https://example.org/job/1"}),
])
@pytest.mark.parametrize("bad_value", [None, "", " \t\n\u2003", False, 0, ["private-value"], {"private": "value"}])
def test_demo_rejects_each_invalid_required_field(
    tmp_home, monkeypatch, case_id, rows_key, field, valid, bad_value,
):
    invalid = {**valid, field: bad_value}
    replies = iter([
        (True, {"ok": True}), (True, {"ok": True}),
        (True, {"ok": True, "data": {rows_key: [valid, invalid, valid, invalid]}}),
    ])
    calls = []

    def step(argv):
        calls.append(argv)
        return next(replies)

    monkeypatch.setattr(demo, "_run_step", step)
    result = CliRunner().invoke(cli, ["--json", "demo", "--case-id", case_id])
    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_EMPTY_RESULT"
    assert payload["error"]["details"] == {
        "stage": "oracle", "row_count": 4, "min_count": 1,
        "field_invalid_rows": {field: [2, 4]},
    }
    assert "private" not in result.stdout
    assert "data" in payload and payload["data"] is None
    assert len(calls) == 3


@pytest.mark.parametrize("rows", [
    [{"summary": "Public issue"}],
    [{"unexpected": "private-value"}],
    [{"key": "SPARK-1", "summary": "Public issue"}, {"key": "SPARK-2"}],
])
def test_demo_rejects_missing_fields_in_any_row(tmp_home, monkeypatch, rows):
    replies = iter([
        (True, {"ok": True}), (True, {"ok": True}),
        (True, {"success": True, "data": {"issues": rows}}),
    ])
    monkeypatch.setattr(demo, "_run_step", lambda argv: next(replies))
    result = demo.run_demo("apache-jira-issues")
    assert result["ok"] is False
    assert result["error"]["code"] == "E_EMPTY_RESULT"
    assert result["error"]["details"]["stage"] == "oracle"
    assert result["error"]["details"]["field_invalid_rows"]
    assert "private" not in json.dumps(result)


@pytest.mark.parametrize("case_id,rows_key,rows", [
    ("apache-jira-issues", "issues", [{"key": "SPARK-1", "summary": "Public issue", "assignee": ""}]),
    ("apache-confluence-search", "results", [{"id": "123", "title": "Public page", "space": ""}]),
    ("apache-jenkins-jobs", "jobs", [{"name": "Public job", "url": "https://example.org/job/1", "color": None}]),
])
def test_demo_keeps_valid_rows_and_optional_fields_unchanged(tmp_home, monkeypatch, case_id, rows_key, rows):
    upstream = {"success": True, "data": {rows_key: rows}, "error": None}
    replies = iter([(True, {"ok": True}), (True, {"ok": True}), (True, upstream)])
    monkeypatch.setattr(demo, "_run_step", lambda argv: next(replies))
    result = demo.run_demo(case_id)
    assert result["ok"] is True
    assert result["data"]["row_count"] == 1
    assert result["data"]["result"] is upstream


@pytest.mark.parametrize("required_fields", [None, [], "key", [""], ["key", "key"], [False], [["key"]]])
def test_demo_rejects_missing_or_invalid_field_contract_before_install(
    tmp_home, monkeypatch, required_fields,
):
    cases, source, paths = demo._load_cases_manifest()
    case = json.loads(json.dumps(next(c for c in cases if c["id"] == "apache-jira-issues")))
    if required_fields is None:
        case["validation"]["expected_rows"].pop("required_fields", None)
    else:
        case["validation"]["expected_rows"]["required_fields"] = required_fields
    monkeypatch.setattr(demo, "_load_cases_manifest", lambda: ([case], source, paths))
    calls = []
    monkeypatch.setattr(demo, "_run_step", lambda argv: calls.append(argv))
    result = demo.run_demo("apache-jira-issues")
    assert result["ok"] is False
    assert result["error"]["code"] == "E_INVALID_PARAM"
    assert not calls


@pytest.mark.parametrize("rows", [None, {}, [], [{}], ["SPARK-1"], [None],
                                 [{"key": "SPARK-1", "summary": "Public issue"}, "SPARK-2"]])
def test_demo_preserves_invalid_row_shape_rejection(tmp_home, monkeypatch, rows):
    replies = iter([
        (True, {"ok": True}), (True, {"ok": True}),
        (True, {"ok": True, "data": {"issues": rows}}),
    ])
    monkeypatch.setattr(demo, "_run_step", lambda argv: next(replies))
    result = demo.run_demo("apache-jira-issues")
    assert result["error"]["code"] == "E_EMPTY_RESULT"
    assert result["error"]["details"] == {"stage": "oracle", "row_count": 0, "min_count": 1}
