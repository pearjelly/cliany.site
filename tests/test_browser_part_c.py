import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli

_MOCK_AXTREE = {
    "url": "http://test.example.com",
    "title": "Test Page",
    "element_tree": '<button @ref=1>提交</button>',
    "selector_map": {
        "1": {"ref": "1", "role": "button", "name": "提交", "attributes": {}},
    },
    "screenshot": b"",
    "iframe_count": 0,
    "shadow_root_count": 0,
}


@pytest.fixture()
def runner():
    return CliRunner()


class TestBrowserExtract:
    def test_extract_success(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.execute_action = AsyncMock(return_value={"content": "Hello World"})
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
        ):
            result = runner.invoke(
                cli, ["browser", "extract", "--format", "text", "--json"]
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["content"] == "Hello World"
            assert data["data"]["format"] == "text"
            assert data["data"]["selector"] is None

    def test_extract_cdp_unavailable(self, no_llm, runner):
        with patch(
            "cliany_site.browser.cdp.CDPConnection.check_available",
            AsyncMock(return_value=False),
        ):
            result = runner.invoke(
                cli, ["browser", "extract", "--format", "text", "--json"]
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_CDP_UNAVAILABLE"

    def test_extract_with_selector(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.execute_action = AsyncMock(
            return_value={"content": "section content"}
        )
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
        ):
            result = runner.invoke(
                cli,
                ["browser", "extract", "--selector", "main", "--format", "markdown", "--json"],
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["selector"] == "main"
            assert data["data"]["format"] == "markdown"

    def test_structured_extract_list_with_fields(self, no_llm, runner):
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(
            return_value=[{"title": "cliany-site", "url": "https://example.com"}]
        )
        mock_session = MagicMock()
        mock_session.get_current_page = AsyncMock(return_value=mock_page)
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
        ):
            result = runner.invoke(
                cli,
                [
                    "browser",
                    "extract",
                    "--selector",
                    ".result",
                    "--mode",
                    "list",
                    "--fields-json",
                    '{"title": "h3", "url": "a@href"}',
                    "--json",
                ],
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["content"] == [{"title": "cliany-site", "url": "https://example.com"}]
            assert data["data"]["mode"] == "list"
            assert data["data"]["fields"] == {"title": "h3", "url": "a@href"}
            assert data["data"]["quality"]["status"] == "ok"
            assert data["data"]["quality"]["row_count"] == 1

    def test_structured_extract_reports_empty_quality(self, no_llm, runner):
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value=[{"title": "", "url": ""}])
        mock_session = MagicMock()
        mock_session.get_current_page = AsyncMock(return_value=mock_page)
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
        ):
            result = runner.invoke(
                cli,
                [
                    "browser",
                    "extract",
                    "--selector",
                    ".result",
                    "--mode",
                    "list",
                    "--fields-json",
                    '{"title": "h3", "url": "a@href"}',
                    "--json",
                ],
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["quality"]["status"] == "empty"
            assert "all rows are blank" in data["data"]["quality"]["issues"]

    def test_structured_extract_strict_quality_fails_on_empty(self, no_llm, runner):
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value=[{"title": "", "url": ""}])
        mock_session = MagicMock()
        mock_session.get_current_page = AsyncMock(return_value=mock_page)
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
        ):
            result = runner.invoke(
                cli,
                [
                    "browser",
                    "extract",
                    "--selector",
                    ".result",
                    "--mode",
                    "list",
                    "--fields-json",
                    '{"title": "h3", "url": "a@href"}',
                    "--strict-quality",
                    "--json",
                ],
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_EMPTY_RESULT"
            assert data["error"]["details"]["quality"]["status"] == "empty"

    def test_structured_extract_strict_quality_fails_on_partial(self, no_llm, runner):
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value=[{"title": "cliany-site", "url": ""}])
        mock_session = MagicMock()
        mock_session.get_current_page = AsyncMock(return_value=mock_page)
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
        ):
            result = runner.invoke(
                cli,
                [
                    "browser",
                    "extract",
                    "--selector",
                    ".result",
                    "--mode",
                    "list",
                    "--fields-json",
                    '{"title": "h3", "url": "a@href"}',
                    "--strict-quality",
                    "--json",
                ],
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_EMPTY_RESULT"
            assert data["error"]["details"]["quality"]["status"] == "partial"
            assert "field is blank in all rows: url" in data["error"]["details"]["quality"]["issues"]


class TestBrowserEval:
    def test_eval_disabled_by_default(self, no_llm, runner):
        with patch(
            "cliany_site.browser.cdp.CDPConnection.check_available",
            AsyncMock(side_effect=AssertionError("不应调用 CDP")),
        ):
            result = runner.invoke(
                cli, ["browser", "eval", "--expr", "1+1", "--json"]
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_EVAL_DISABLED"

    def test_eval_success_with_flag(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.execute_action = AsyncMock(return_value=2)
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
        ):
            result = runner.invoke(
                cli,
                ["browser", "eval", "--expr", "1+1", "--allow-eval", "--json"],
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["expr"] == "1+1"
            assert data["data"]["result"] == 2

    def test_eval_cdp_unavailable_with_flag(self, no_llm, runner):
        with patch(
            "cliany_site.browser.cdp.CDPConnection.check_available",
            AsyncMock(return_value=False),
        ):
            result = runner.invoke(
                cli,
                ["browser", "eval", "--expr", "document.title", "--allow-eval", "--json"],
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_CDP_UNAVAILABLE"
