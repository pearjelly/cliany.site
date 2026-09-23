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

    def test_structured_extract_identifies_client_challenge(self, no_llm, runner):
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(side_effect=[[], "Client Challenge"])
        mock_session = MagicMock()
        mock_session.get_current_page = AsyncMock(return_value=mock_page)
        with (
            patch("cliany_site.browser.cdp.CDPConnection.check_available", AsyncMock(return_value=True)),
            patch("cliany_site.browser.cdp.CDPConnection.connect", AsyncMock(return_value=mock_session)),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
        ):
            result = runner.invoke(
                cli,
                ["browser", "extract", "--selector", ".result", "--mode", "list", "--json"],
            )

        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "E_PAGE_NOT_READY"
        assert data["error"]["details"] == {"reason": "site_challenge", "title": "Client Challenge"}
        assert mock_page.evaluate.await_args_list[1].args == ("() => document.title",)

    def test_structured_extract_keeps_normal_empty_result(self, no_llm, runner):
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(side_effect=[[], "Search results"])
        mock_session = MagicMock()
        mock_session.get_current_page = AsyncMock(return_value=mock_page)
        with (
            patch("cliany_site.browser.cdp.CDPConnection.check_available", AsyncMock(return_value=True)),
            patch("cliany_site.browser.cdp.CDPConnection.connect", AsyncMock(return_value=mock_session)),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
        ):
            result = runner.invoke(
                cli,
                ["browser", "extract", "--selector", ".result", "--mode", "list", "--json"],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["quality"]["status"] == "empty"

    def test_structured_extract_keeps_empty_result_when_title_probe_fails(self, no_llm, runner):
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(side_effect=[[], RuntimeError("title unavailable")])
        mock_session = MagicMock()
        mock_session.get_current_page = AsyncMock(return_value=mock_page)
        with (
            patch("cliany_site.browser.cdp.CDPConnection.check_available", AsyncMock(return_value=True)),
            patch("cliany_site.browser.cdp.CDPConnection.connect", AsyncMock(return_value=mock_session)),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
        ):
            result = runner.invoke(
                cli,
                ["browser", "extract", "--selector", ".result", "--mode", "list", "--json"],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["quality"]["status"] == "empty"

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
            assert data["error"]["details"]["quality"]["field_blank_rows"] == {"url": [1]}


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
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value="2")
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
                ["browser", "eval", "--expr", "1+1", "--allow-eval", "--json"],
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["expr"] == "1+1"
            assert data["data"]["result"] == 2
            mock_page.evaluate.assert_awaited_once_with(
                "() => Promise.resolve((1+1)).then(value => JSON.stringify(value))"
            )

    @pytest.mark.parametrize(
        ("expr", "raw", "expected"),
        [
            ("document.title", '"Example"', "Example"),
            ("({ok: true, count: 2})", '{"ok":true,"count":2}', {"ok": True, "count": 2}),
            ('Promise.resolve("ready")', '"ready"', "ready"),
            ("undefined", "", None),
        ],
    )
    def test_eval_preserves_json_result_types(self, no_llm, runner, expr, raw, expected):
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value=raw)
        mock_session = MagicMock()
        mock_session.get_current_page = AsyncMock(return_value=mock_page)
        with (
            patch("cliany_site.browser.cdp.CDPConnection.check_available", AsyncMock(return_value=True)),
            patch("cliany_site.browser.cdp.CDPConnection.connect", AsyncMock(return_value=mock_session)),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
        ):
            result = runner.invoke(cli, ["browser", "eval", "--expr", expr, "--allow-eval", "--json"])

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["data"]["result"] == expected

    def test_eval_rejects_blank_expression_before_cdp(self, no_llm, runner):
        with patch("cliany_site.browser.cdp.CDPConnection.check_available", AsyncMock(side_effect=AssertionError)):
            result = runner.invoke(cli, ["browser", "eval", "--expr", "  ", "--allow-eval", "--json"])

        assert result.exit_code != 0
        assert json.loads(result.output)["error"]["code"] == "E_INVALID_PARAM"

    def test_eval_requires_current_page(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.get_current_page = AsyncMock(return_value=None)
        with (
            patch("cliany_site.browser.cdp.CDPConnection.check_available", AsyncMock(return_value=True)),
            patch("cliany_site.browser.cdp.CDPConnection.connect", AsyncMock(return_value=mock_session)),
            patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
        ):
            result = runner.invoke(cli, ["browser", "eval", "--expr", "1+1", "--allow-eval", "--json"])

        assert result.exit_code != 0
        assert json.loads(result.output)["error"]["code"] == "E_PAGE_NOT_READY"

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
