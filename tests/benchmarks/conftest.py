# pyright: reportMissingImports=false
import json
from pathlib import Path

import pytest

from cliany_site.testing.fake_llm import FakeChatModel


BENCHMARKS_DATA = Path(__file__).parent / "data"
SCENARIOS = ["simple-search", "multi-step"]


@pytest.fixture(params=SCENARIOS)
def scenario(request, monkeypatch):
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    name = request.param
    d = BENCHMARKS_DATA / name
    fake_responses_path = d / "fake_llm_responses.json"
    monkeypatch.setenv("CLIANY_QA_FAKE_LLM_RESPONSES", str(fake_responses_path))
    fake_responses = json.loads(fake_responses_path.read_text(encoding="utf-8"))
    return {
        "name": name,
        "dir": d,
        "axtree": json.loads((d / "axtree.json").read_text(encoding="utf-8")),
        "fake_responses": fake_responses,
        "fake_model": FakeChatModel(responses=fake_responses),
        "expected_parsed": json.loads((d / "expected_parsed.json").read_text(encoding="utf-8")),
        "expected_sanitized": json.loads((d / "expected_sanitized.json").read_text(encoding="utf-8")),
        "expected": json.loads((d / "expected.json").read_text(encoding="utf-8")),
    }
