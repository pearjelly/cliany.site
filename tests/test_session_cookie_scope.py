from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from cliany_site.session import load_session_data, save_session, save_session_data


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ["app.example.test", "APP.EXAMPLE.TEST:8443"])
async def test_save_session_only_captures_cookies_applicable_to_host(tmp_home, domain):
    cookies = [
        {"domain": "app.example.test", "name": "host", "value": "keep"},
        {"domain": ".example.test", "name": "parent", "value": "keep"},
        {"domain": "example.test", "name": "parent_host_only", "value": "drop"},
        {"domain": "other.example.test", "name": "sibling", "value": "drop"},
        {"domain": ".notexample.test", "name": "suffix", "value": "drop"},
        {"domain": "another.test", "name": "other_site", "value": "drop"},
        {"name": "missing_domain", "value": "drop"},
    ]
    session = SimpleNamespace(_cdp_get_cookies=AsyncMock(return_value=cookies))
    with patch("cliany_site.session.save_session_data", return_value="test-session") as persist:
        path, count = await save_session(domain, session)
    assert path == "test-session"
    assert count == 2
    assert persist.call_args.args[1]["cookies"] == cookies[:2]
    assert len(cookies) == 7


@pytest.mark.asyncio
async def test_zero_applicable_cookies_preserves_existing_session(tmp_home):
    domain = "app.example.test"
    old_cookies = [{"domain": domain, "name": "login", "value": "saved"}]
    with (
        patch("cliany_site.security._load_key_from_keyring", return_value=None),
        patch("cliany_site.security._save_key_to_keyring", return_value=False),
    ):
        path = save_session_data(domain, {"cookies": old_cookies})
        original = Path(path).read_bytes()
        session = SimpleNamespace(
            _cdp_get_cookies=AsyncMock(
                return_value=[{"domain": "other.example.test", "name": "other", "value": "ignored"}]
            )
        )

        saved_path, count = await save_session(domain, session)

        assert (saved_path, count) == ("", 0)
        assert load_session_data(domain)["cookies"] == old_cookies
        assert Path(path).read_bytes() == original
