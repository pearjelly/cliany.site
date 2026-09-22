from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from cliany_site.session import save_session


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
