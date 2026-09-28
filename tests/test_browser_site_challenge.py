import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli


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
