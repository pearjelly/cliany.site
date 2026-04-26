import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli

_MOCK_AXTREE = {
    "url": "http://test.example.com",
    "title": "Test Page",
    "element_tree": "<button @ref=1>Click me</button>",
    "selector_map": {},
    "screenshot": b"",
    "iframe_count": 0,
    "shadow_root_count": 0,
}


@pytest.fixture()
def runner():
    return CliRunner()


class TestBrowserState:
    def test_state_success(self, no_llm, runner):
        mock_session = MagicMock()
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
            result = runner.invoke(cli, ["browser", "state", "--json"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["url"] == "http://test.example.com"
            assert data["data"]["title"] == "Test Page"
            assert "elements" in data["data"]
            assert "truncated" in data["data"]

    def test_state_cdp_unavailable(self, no_llm, runner):
        with patch(
            "cliany_site.browser.cdp.CDPConnection.check_available",
            AsyncMock(return_value=False),
        ):
            result = runner.invoke(cli, ["browser", "state", "--json"])
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_CDP_UNAVAILABLE"


class TestBrowserNavigate:
    def test_navigate_success(self, no_llm, runner):
        mock_session = MagicMock()
        mock_session.navigate_to = AsyncMock()
        mock_page = MagicMock()
        mock_page.wait_for_load_state = AsyncMock()
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
                cli, ["browser", "navigate", "http://example.com", "--json"]
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["url"] == "http://example.com"
            assert data["data"]["status"] == "navigated"

    def test_navigate_cdp_unavailable(self, no_llm, runner):
        with patch(
            "cliany_site.browser.cdp.CDPConnection.check_available",
            AsyncMock(return_value=False),
        ):
            result = runner.invoke(
                cli, ["browser", "navigate", "http://example.com", "--json"]
            )
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["ok"] is False


class TestBrowserWait:
    def test_wait_networkidle_success(self, no_llm, runner):
        mock_page = MagicMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
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
            result = runner.invoke(cli, ["browser", "wait", "--json"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["waited"] is True
            assert "elapsed_ms" in data["data"]

    def test_wait_selector_success(self, no_llm, runner):
        mock_page = MagicMock()
        mock_page.wait_for_selector = AsyncMock()
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
                cli, ["browser", "wait", "--selector", "button#submit", "--json"]
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["selector"] == "button#submit"


class TestBrowserScreenshot:
    def test_screenshot_success(self, no_llm, runner, tmp_path):
        out_file = str(tmp_path / "snap.png")
        mock_session = MagicMock()

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
                "cliany_site.browser.screenshot.capture_screenshot",
                AsyncMock(return_value=b"fake_png_data"),
            ),
        ):
            result = runner.invoke(
                cli, ["browser", "screenshot", "--out", out_file, "--json"]
            )
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["path"] == out_file
            assert data["data"]["size_bytes"] == len(b"fake_png_data")
            assert Path(out_file).read_bytes() == b"fake_png_data"

    def test_screenshot_default_path(self, no_llm, runner, tmp_home):
        mock_session = MagicMock()

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
                "cliany_site.browser.screenshot.capture_screenshot",
                AsyncMock(return_value=b"fake_png_data"),
            ),
        ):
            result = runner.invoke(cli, ["browser", "screenshot", "--json"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["ok"] is True
            assert data["data"]["path"].endswith(".png")
            assert Path(data["data"]["path"]).exists()
