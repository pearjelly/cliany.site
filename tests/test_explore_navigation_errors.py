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
