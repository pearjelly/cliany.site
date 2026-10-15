import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "first-use-trial.md"
FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "first_use.yml"


def test_first_use_form_collects_failures_without_requiring_success_or_logs():
    form = yaml.safe_load(FORM.read_text(encoding="utf-8"))
    fields = {field["id"]: field for field in form["body"] if "id" in field}
    assert set(fields) == {
        "environment", "track", "independence", "help", "first_attempt", "result", "retries", "privacy"
    }
    for name in ("environment", "track", "independence", "help", "first_attempt"):
        assert fields[name]["validations"]["required"] is True
    assert fields["result"]["validations"]["required"] is False
    assert fields["retries"]["validations"]["required"] is False
    assert len(fields["independence"]["attributes"]["options"]) == 3
    assert len(fields["help"]["attributes"]["options"]) == 3
    text = FORM.read_text(encoding="utf-8")
    for snippet in ("#33", "#55", "first-use-trial.md", "首次失败", "不要上传", "doctor", "原记录"):
        assert snippet in text
    assert "auto-reproduce" not in form.get("labels", [])


def test_trial_guide_pins_public_baseline_and_keeps_runtime_and_browser_separate():
    text = GUIDE.read_text(encoding="utf-8")
    for snippet in (
        "cliany-site==0.16.387", "python3 -m venv", "py -3 -m venv",
        "CLIANY_RUNTIME_HOME", "HOME", "USERPROFILE", "不需要 LLM key",
        "cliany-site demo --case-id apache-jira-issues --json",
        "cliany-site verify issues.apache.org --strict --json",
        "cliany-site verify docs.python.org --strict --json", "verdict=ok",
        "--headless --cdp-url http://127.0.0.1:19223", "端口", "先停止",
        "29f1ece48fd6749e53cf7384f5be0878c1617d1d8344641e284b6c37150f6592",
        "v0.16.373/docs.python.org-0.1.0.cliany-adapter.tar.gz",
        "https://docs.python.org/3/search.html?q=pathlib", "limit_reached", "100",
        "issues/33", "issues/55", "first_use.yml", "首次失败", "重试",
        "至少两位", "至少一位", "维护者", "不覆盖", "不算", "墙钟",
    ):
        assert snippet in text
    assert "--force" not in text
    assert not re.search(r"(?:export|\$env:)\s*(?:HOME|USERPROFILE)\s*=", text)


def test_trial_entry_is_reachable_from_quickstart():
    text = (ROOT / "docs" / "quickstart-10min.md").read_text(encoding="utf-8")
    assert "first-use-trial.md" in text


def test_trial_maintainer_policy_does_not_rescore_failed_first_attempts():
    text = GUIDE.read_text(encoding="utf-8")
    for snippet in ("0/2", "独立用户", "脱敏", "不可重写", "另增", "第三方", "未复现", "不晋级"):
        assert snippet in text


def test_first_result_row_gate_docs_keep_independent_check_and_error_boundaries():
    for path in (GUIDE, ROOT / "README.md", ROOT / "README.zh.md", ROOT / "site/docs/index.html"):
        text = path.read_text(encoding="utf-8")
        for snippet in ("v0.16.387", "field_invalid_rows", "E_EMPTY_RESULT", "stage=oracle"):
            assert snippet in text
    guide = GUIDE.read_text(encoding="utf-8")
    assert "blob/v0.16.386/docs/first-use-trial.md" in guide
    assert "不包含错误值" in guide and "正常公开 Jira issue" in guide
