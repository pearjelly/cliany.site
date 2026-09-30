import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.commands.browser._common import site_challenge_error

CLOUDFLARE_TREE = {
    "title": "请稍候…",
    "selector_map": {
        "1": {"role": "link", "name": "帮助", "attributes": {"href": "/cdn-cgi/challenge-platform/help"}},
        "2": {"role": "image", "name": "Cloudflare", "attributes": {}},
    },
}


def test_cloudflare_challenge_requires_both_platform_path_and_brand():
    assert site_challenge_error("browser navigate", CLOUDFLARE_TREE)["error"]["code"] == "E_PAGE_NOT_READY"
    partial_tree = {"title": "请稍候…", "selector_map": {
        "1": {"role": "link", "name": "Cloudflare，在新标签页中打开", "attributes": {}},
    }}
    assert site_challenge_error("browser navigate", partial_tree)["error"]["code"] == "E_PAGE_NOT_READY"
    assert site_challenge_error("browser navigate", {"title": "普通页面", "selector_map": {
        "1": {"role": "link", "name": "Cloudflare", "attributes": {}},
    }}) is None
    assert site_challenge_error("browser navigate", {"title": "请稍候…", "selector_map": {
        "1": {"role": "link", "name": "帮助", "attributes": {}},
    }}) is None


def test_navigate_reports_observed_cloudflare_challenge(no_llm, tmp_home):
    session = MagicMock()
    session.navigate_to = AsyncMock()
    with (
        patch("cliany_site.browser.cdp.CDPConnection.check_available", AsyncMock(return_value=True)),
        patch("cliany_site.browser.cdp.CDPConnection.connect", AsyncMock(return_value=session)),
        patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
        patch("cliany_site.browser.axtree.capture_axtree", AsyncMock(return_value=CLOUDFLARE_TREE)),
    ):
        result = CliRunner().invoke(cli, ["browser", "navigate", "https://www.npmjs.com/search", "--json"])

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["error"]["code"] == "E_PAGE_NOT_READY"
    assert payload["error"]["details"] == {"reason": "site_challenge", "title": "请稍候…"}


@pytest.mark.parametrize(
    ("action", "extra_args"),
    [
        ("type", ["--value", "query"]),
        ("click", []),
        ("select", ["--value", "option"]),
        ("submit", []),
    ],
)
@pytest.mark.parametrize(
    ("title", "expected_code"),
    [
        ("Client Challenge", "E_PAGE_NOT_READY"),
        ("Normal page", "E_SELECTOR_NOT_FOUND"),
    ],
)
def test_missing_action_target_distinguishes_site_challenge(
    no_llm, action, extra_args, title, expected_code
):
    tree = {"title": title, "selector_map": {}}
    with (
        patch("cliany_site.browser.cdp.CDPConnection.check_available", AsyncMock(return_value=True)),
        patch("cliany_site.browser.cdp.CDPConnection.connect", AsyncMock(return_value=MagicMock())),
        patch("cliany_site.browser.cdp.CDPConnection.disconnect", AsyncMock()),
        patch("cliany_site.browser.axtree.capture_axtree", AsyncMock(return_value=tree)),
    ):
        result = CliRunner().invoke(
            cli,
            ["browser", action, "--text", "missing", *extra_args, "--json"],
        )

    assert result.exit_code != 0, result.output
    payload = json.loads(result.output)
    assert payload["error"]["code"] == expected_code
    if title == "Client Challenge":
        assert payload["error"]["details"] == {"reason": "site_challenge", "title": title}
