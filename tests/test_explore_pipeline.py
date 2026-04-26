import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cliany_site.explorer.models import ExploreResult, CommandSuggestion, ActionStep


def test_explore_result_has_smoke():
    result = ExploreResult()
    assert hasattr(result, "smoke")
    assert result.smoke == []


def test_explore_result_has_canonical_actions():
    result = ExploreResult()
    assert hasattr(result, "canonical_actions")
    assert result.canonical_actions == []
    result.canonical_actions = [{"name": "search", "description": "검색", "steps": []}]
    assert len(result.canonical_actions) == 1


def test_explore_result_has_selector_pool():
    result = ExploreResult()
    assert hasattr(result, "selector_pool")
    assert result.selector_pool == []
    result.selector_pool = [{"ref": "@ref1", "candidates": ["#q", "input[type=search]"]}]
    assert result.selector_pool[0]["ref"] == "@ref1"


def test_explore_pipeline_triggers_agent_md(tmp_home, monkeypatch):
    import cliany_site.agent_md as agent_md_mod

    calls: list = []

    def mock_regenerate(project_root, registry, version=1, force=False, env_skip=False):
        calls.append({"project_root": project_root, "force": force})
        from cliany_site.agent_md import AgentMdResult
        return AgentMdResult(written=True, conflict=False, path=project_root / "AGENT.md", version=version)

    monkeypatch.setattr(agent_md_mod, "regenerate", mock_regenerate)

    from cliany_site.commands.explore import _post_save_agent_md

    _post_save_agent_md("example.com", ["search", "login"])

    assert len(calls) == 1
    assert calls[0]["force"] is False


def test_explore_pipeline_no_leftover_on_failure(tmp_home, monkeypatch):
    import os as _os
    from cliany_site.codegen.generator import save_adapter
    from cliany_site.config import get_config

    domain = "failure-test.com"
    adapter_dir = get_config().adapters_dir / domain

    n = [0]
    original_replace = _os.replace

    def flaky_replace(src, dst):
        n[0] += 1
        if n[0] == 1:
            if _os.path.exists(src):
                _os.unlink(src)
            raise OSError("injected failure")
        return original_replace(src, dst)

    monkeypatch.setattr(_os, "replace", flaky_replace)

    with pytest.raises(OSError):
        save_adapter(domain, "# test", {}, ExploreResult())

    if adapter_dir.exists():
        leftover = list(adapter_dir.glob("*.tmp"))
        assert leftover == [], f"leftover .tmp files: {leftover}"
