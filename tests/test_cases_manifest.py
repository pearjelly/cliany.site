import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "cases" / "manifest.json"
ALLOWED_STATUSES = {"active", "candidate", "degraded", "known-gap", "retired"}


def _load_cases() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_cases_manifest_has_unique_ids():
    cases = _load_cases()
    ids = [case["id"] for case in cases]

    assert cases
    assert len(ids) == len(set(ids))


def test_cases_manifest_entries_are_actionable():
    for case in _load_cases():
        assert case["id"]
        assert case["title"]
        assert case["category"]
        assert case["status"] in ALLOWED_STATUSES
        assert case["target_url"].startswith("https://")
        assert "offline" in case["validation"]
        assert case["validation"]["offline"]
        assert case["validation"]["offline_commands"]
        assert all(
            command.startswith(("python ", "pytest ", "CLIANY_QA_OFFLINE=1 ", "bash "))
            for command in case["validation"]["offline_commands"]
        )

        if case["status"] == "active":
            assert case["adapter_domain"]
            assert case["source_release"]
            assert case["commands"]
            assert case["example_output"]
            assert all(command.startswith("cliany-site ") for command in case["commands"])
        if case["status"] == "candidate":
            assert case["commands"]
            assert case["example_output"]
            assert all(command.startswith("cliany-site ") for command in case["commands"])
            assert case["promotion"]["adapter_package"]
            assert case["promotion"]["metadata_validation"]
            assert case["promotion"]["online_smoke"]


def test_cases_manifest_docs_links_exist_locally():
    for case in _load_cases():
        doc_path = case["docs"].split("#", 1)[0]
        assert (ROOT / doc_path).exists(), f"{case['id']} docs path does not exist: {doc_path}"


def test_active_and_candidate_cases_have_local_example_outputs():
    for case in _load_cases():
        if case["status"] not in {"active", "candidate"}:
            continue

        path = ROOT / case["example_output"]
        assert path.exists(), f"{case['id']} example_output does not exist: {case['example_output']}"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["ok"] is True
        assert payload["meta"]["case_id"] == case["id"]
        assert payload["meta"]["sample"] is True
        assert payload["data"]["quality"]["ok"] is True
        assert payload["data"]["quality"]["status"] == "ok"
        assert payload["data"]["quality"]["row_count"] > 0
