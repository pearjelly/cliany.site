from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.commands.browser.extract import _do_structured_extract
from cliany_site.envelope import ErrorCode


@pytest.mark.asyncio
async def test_unsettled_list_atom_fails_before_extract(mocker):
    page = SimpleNamespace(evaluate=AsyncMock())
    session = SimpleNamespace(get_current_page=AsyncMock(return_value=page))
    mocker.patch("cliany_site.commands.browser.extract._wait_for_list_settle", new=AsyncMock(return_value=False))

    result = await _do_structured_extract(session, "li.result", "list", {"title": ""})

    assert result["ok"] is False
    assert result["error"]["code"] == ErrorCode.E_PAGE_NOT_READY
    page.evaluate.assert_not_awaited()
