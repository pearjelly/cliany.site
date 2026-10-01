import json
from pathlib import Path


def test_benchmark_case_spec_is_complete():
    root = Path(__file__).parent / "embodied"
    spec = json.loads((root / "explore_benchmark_cases.json").read_text(encoding="utf-8"))
    assert spec["schema_version"] == 1
    cases = {case["id"]: case for case in spec["tasks"]}
    assert set(cases) == {"form-result", "filter-catalog", "semantic-reorder"}
    for case in cases.values():
        assert (root / "pages" / case["path"].lstrip("/")).is_file()
        assert case["workflow"]
        assert "extract" in case["required_actions"]
        assert case["replays"]
        for replay in case["replays"]:
            assert isinstance(replay["args"], dict)
            assert any(key.startswith("expected_") for key in replay)
