import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli


@pytest.mark.parametrize(
    ("failure", "code", "reason"),
    [
        (
            RuntimeError("Page.navigate() timed out after 20.0s (20002ms) for https://crates.io/search?q=serde"),
            "E_PAGE_NOT_READY",
            "navigation_timeout",
        ),
        (
            TimeoutError("Event handler BrowserSession.on_NavigateToUrlEvent#2576 timed out after 30.0s"),
            "E_PAGE_NOT_READY",
            "navigation_timeout",
        ),
        (TimeoutError("unrelated timeout"), "E_UNKNOWN", None),
        (RuntimeError("unrelated runtime failure"), "E_UNKNOWN", None),
    ],
)
def test_explore_classifies_navigation_timeout_without_hiding_other_errors(
    tmp_home, clean_env, monkeypatch, failure, code, reason
):
    import cliany_site.browser.cdp as cdp_mod
    import cliany_site.explorer.engine as engine_mod

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / "config"))
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(engine_mod, "_load_dotenv", lambda: None)

    cdp = MagicMock()
    cdp.check_available = AsyncMock(return_value=True)
    monkeypatch.setattr(cdp_mod, "cdp_from_context", lambda _: cdp)
    monkeypatch.setattr(engine_mod.WorkflowExplorer, "explore", AsyncMock(side_effect=failure))

    result = CliRunner().invoke(
        cli,
        ["explore", "https://crates.io/search?q=serde", "read-only search", "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == code
    if reason is None:
        assert payload["error"]["details"] is None
    else:
        assert payload["error"]["details"] == {
            "reason": reason,
            "phase": "navigation",
            "url": "https://crates.io/search?q=serde",
        }


def test_explore_returns_invocable_group_for_local_port(tmp_home, clean_env, monkeypatch):
    import cliany_site.activity_log as activity_log
    import cliany_site.browser.cdp as cdp_mod
    import cliany_site.codegen.generator as generator_mod
    import cliany_site.commands.explore as explore_mod
    import cliany_site.explorer.engine as engine_mod
    from cliany_site.explorer.models import ExploreResult

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / "config"))
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(engine_mod, "_load_dotenv", lambda: None)
    cdp = MagicMock()
    cdp.check_available = AsyncMock(return_value=True)
    monkeypatch.setattr(cdp_mod, "cdp_from_context", lambda _: cdp)
    explorer = MagicMock()
    explorer.explore = AsyncMock(return_value=ExploreResult())
    monkeypatch.setattr(engine_mod, "WorkflowExplorer", lambda **kwargs: explorer)
    monkeypatch.setattr(generator_mod, "save_adapter", lambda *args, **kwargs: "/tmp/adapter.py")
    monkeypatch.setattr(explore_mod, "_post_save_agent_md", lambda *args: None)
    monkeypatch.setattr(activity_log, "write_log", lambda *args: None)

    result = CliRunner().invoke(
        cli,
        ["explore", "http://127.0.0.1:48765/action_replay.html", "read result", "--json"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["domain"] == "127.0.0.1:48765"
    assert payload["data"]["command_group"] == "127.0.0.1_48765"
