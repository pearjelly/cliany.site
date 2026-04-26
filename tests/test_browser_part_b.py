import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli

_MOCK_AXTREE = {
    "url": "http://test.example.com",
    "title": "Test Page",
    "element_tree": '<button @ref=1>提交</button><input @ref=2 type="text">',
    "selector_map": {
        "1": {"ref": "1", "role": "button", "name": "提交", "attributes": {"id": "btn"}},
        "2": {"ref": "2", "role": "textbox", "name": "搜索框", "attributes": {"type": "text"}},
    },
    "screenshot": b"",
    "iframe_count": 0,
    "shadow_root_count": 0,
}


@pytest.fixture()
def runner():
    return CliRunner()


class TestBrowserFind:
    def test_find_success(self, no_llm, runner):
        with (
            patch(
                "cliany_site.browser.cdp.CDPConnection.check_available",
                AsyncMock(return_value=True),
            ),
            patch(
                "cliany_site.browser.cdp.CDPConnection.connect",
                AsyncMock(return_value=MagicMock()),
            ),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
            patch(
                "cliany_site.browser.axtree.capture_axtree",
                AsyncMock(return_value=_MOCK_AXTREE),
            ),
        ):
            result = runner.invoke(
                cli, ["browser", "find", "--by", "role", "--value", "button", "--json"]
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert isinstance(data["data"], list)
            assert len(data["data"]) == 1
            assert data["data"][0]["role"] == "button"
            assert data["data"][0]["ref"] == "1"

    def test_find_no_results(self, no_llm, runner):
        with (
            patch(
                "cliany_site.browser.cdp.CDPConnection.check_available",
                AsyncMock(return_value=True),
            ),
            patch(
                "cliany_site.browser.cdp.CDPConnection.connect",
                AsyncMock(return_value=MagicMock()),
            ),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
            patch(
                "cliany_site.browser.axtree.capture_axtree",
                AsyncMock(return_value=_MOCK_AXTREE),
            ),
        ):
            result = runner.invoke(
                cli,
                ["browser", "find", "--by", "text", "--value", "NOTFOUND_XYZ", "--json"],
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"] == []

    def test_find_cdp_unavailable(self, no_llm, runner):
        with patch(
            "cliany_site.browser.cdp.CDPConnection.check_available",
            AsyncMock(return_value=False),
        ):
            result = runner.invoke(
                cli, ["browser", "find", "--by", "role", "--value", "button", "--json"]
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_CDP_UNAVAILABLE"


class TestBrowserClick:
    def test_click_success(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.execute_action = AsyncMock()
        with (
            patch(
                "cliany_site.browser.cdp.CDPConnection.check_available",
                AsyncMock(return_value=True),
            ),
            patch(
                "cliany_site.browser.cdp.CDPConnection.connect",
                AsyncMock(return_value=mock_session),
            ),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
            patch(
                "cliany_site.browser.axtree.capture_axtree",
                AsyncMock(return_value=_MOCK_AXTREE),
            ),
        ):
            result = runner.invoke(cli, ["browser", "click", "--ref", "1", "--json"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["ref"] == "1"
            assert data["data"]["status"] == "clicked"

    def test_click_invalid_ref(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.execute_action = AsyncMock()
        with (
            patch(
                "cliany_site.browser.cdp.CDPConnection.check_available",
                AsyncMock(return_value=True),
            ),
            patch(
                "cliany_site.browser.cdp.CDPConnection.connect",
                AsyncMock(return_value=mock_session),
            ),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
            patch(
                "cliany_site.browser.axtree.capture_axtree",
                AsyncMock(return_value=_MOCK_AXTREE),
            ),
        ):
            result = runner.invoke(
                cli, ["browser", "click", "--ref", "nonexistent", "--json"]
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_SELECTOR_NOT_FOUND"
            assert data["error"]["hint"] is not None

    def test_click_by_text(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.execute_action = AsyncMock()
        with (
            patch(
                "cliany_site.browser.cdp.CDPConnection.check_available",
                AsyncMock(return_value=True),
            ),
            patch(
                "cliany_site.browser.cdp.CDPConnection.connect",
                AsyncMock(return_value=mock_session),
            ),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
            patch(
                "cliany_site.browser.axtree.capture_axtree",
                AsyncMock(return_value=_MOCK_AXTREE),
            ),
        ):
            result = runner.invoke(
                cli, ["browser", "click", "--text", "提交", "--json"]
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["name"] == "提交"


class TestBrowserType:
    def test_type_success(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.execute_action = AsyncMock()
        with (
            patch(
                "cliany_site.browser.cdp.CDPConnection.check_available",
                AsyncMock(return_value=True),
            ),
            patch(
                "cliany_site.browser.cdp.CDPConnection.connect",
                AsyncMock(return_value=mock_session),
            ),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
            patch(
                "cliany_site.browser.axtree.capture_axtree",
                AsyncMock(return_value=_MOCK_AXTREE),
            ),
        ):
            result = runner.invoke(
                cli,
                ["browser", "type", "--ref", "2", "--value", "hello", "--json"],
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["value"] == "hello"
            assert data["data"]["status"] == "typed"
            assert data["data"]["ref"] == "2"

    def test_type_with_submit(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.execute_action = AsyncMock()
        with (
            patch(
                "cliany_site.browser.cdp.CDPConnection.check_available",
                AsyncMock(return_value=True),
            ),
            patch(
                "cliany_site.browser.cdp.CDPConnection.connect",
                AsyncMock(return_value=mock_session),
            ),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
            patch(
                "cliany_site.browser.axtree.capture_axtree",
                AsyncMock(return_value=_MOCK_AXTREE),
            ),
        ):
            result = runner.invoke(
                cli,
                [
                    "browser",
                    "type",
                    "--ref",
                    "2",
                    "--value",
                    "search query",
                    "--submit",
                    "--json",
                ],
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["submitted"] is True

    def test_type_invalid_ref(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.execute_action = AsyncMock()
        with (
            patch(
                "cliany_site.browser.cdp.CDPConnection.check_available",
                AsyncMock(return_value=True),
            ),
            patch(
                "cliany_site.browser.cdp.CDPConnection.connect",
                AsyncMock(return_value=mock_session),
            ),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
            patch(
                "cliany_site.browser.axtree.capture_axtree",
                AsyncMock(return_value=_MOCK_AXTREE),
            ),
        ):
            result = runner.invoke(
                cli,
                ["browser", "type", "--ref", "nonexistent", "--value", "hello", "--json"],
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_SELECTOR_NOT_FOUND"
