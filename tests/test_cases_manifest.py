import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "cases" / "manifest.json"
ALLOWED_STATUSES = {"active", "degraded", "known-gap", "retired"}


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

        if case["status"] == "active":
            assert case["adapter_domain"]
            assert case["source_release"]
            assert case["commands"]
            assert all(command.startswith("cliany-site ") for command in case["commands"])


def test_cases_manifest_docs_links_exist_locally():
    for case in _load_cases():
        doc_path = case["docs"].split("#", 1)[0]
        assert (ROOT / doc_path).exists(), f"{case['id']} docs path does not exist: {doc_path}"

