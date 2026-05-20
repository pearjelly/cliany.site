from __future__ import annotations

import urllib.error
from unittest.mock import MagicMock, call, patch

import pytest

from cliany_site.commands.obscura import _download_with_retry


def _make_mock_response(data: bytes) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.read.return_value = data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_download_retries_on_network_error():
    mock_resp = _make_mock_response(b"binary_data")
    side_effects = [
        urllib.error.URLError("timeout"),
        urllib.error.URLError("timeout"),
        mock_resp,
    ]

    with patch("urllib.request.urlopen", side_effect=side_effects):
        result = _download_with_retry("http://example.com/bin", max_attempts=3, base_backoff=0)

    assert result == b"binary_data"


def test_download_gives_up_after_max_retries():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("network fail")):
        with pytest.raises(Exception):
            _download_with_retry("http://example.com/bin", max_attempts=3, base_backoff=0)


def test_download_respects_exponential_backoff():
    mock_resp = _make_mock_response(b"binary_data")
    side_effects = [
        urllib.error.URLError("timeout"),
        urllib.error.URLError("timeout"),
        mock_resp,
    ]

    with patch("urllib.request.urlopen", side_effect=side_effects), \
         patch("time.sleep") as mock_sleep:
        _download_with_retry("http://example.com/bin", max_attempts=3, base_backoff=1.0)

    assert mock_sleep.call_args_list == [call(1.0), call(2.0)]
