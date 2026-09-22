from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.commands.browser.navigate import _run_navigate


@pytest.mark.asyncio
@pytest.mark.parametrize("expired", [False, True])
async def test_session_is_checked_and_restored_before_navigation(monkeypatch, expired, tmp_home):
    browser = AsyncMock()
    cdp = SimpleNamespace(check_available=AsyncMock(return_value=True),
                          connect=AsyncMock(return_value=browser), disconnect=AsyncMock())
    cookies = [{"name": "test", "value": "fixture"}]
    monkeypatch.setattr("cliany_site.session.load_session_data", lambda name: {
        "cookies": cookies, "expires_hint": "expired" if expired else None,
    })
    monkeypatch.setattr("cliany_site.commands.browser.navigate.get_config",
                        lambda: SimpleNamespace(browser_provider="chrome"))
    observed = []
    browser._cdp_set_cookies.side_effect = lambda value: observed.append(("cookies", value))
    browser.navigate_to.side_effect = lambda url: observed.append(("navigate", url))

    result = await _run_navigate(cdp, "https://example.com", "load", 30, "example.com")

    cdp.disconnect.assert_awaited_once()
    if expired:
        assert result["error"]["code"] == "E_SESSION_EXPIRED"
        assert observed == []
    else:
        assert result["ok"] is True
        assert observed == [("cookies", cookies), ("navigate", "https://example.com")]
