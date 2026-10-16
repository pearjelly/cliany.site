import json
import ssl
from http.client import IncompleteRead
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

import pytest
from click.testing import CliRunner

from cliany_site import marketplace
from cliany_site.cli import cli
from cliany_site.commands import demo
from cliany_site.commands.market import market_group

PRIVATE = "PRIVATE_SENTINEL_DO_NOT_ECHO"
SOURCE = f"https://user:{PRIVATE}@downloads.example.test/adapter.tar.gz?token={PRIVATE}#fragment"


def download_error(kind):
    if isinstance(kind, int):
        return HTTPError(SOURCE, kind, PRIVATE, {"Authorization": PRIVATE}, None)
    if kind == "wrapped_timeout":
        return URLError(TimeoutError(PRIVATE))
    if kind == "timeout":
        return TimeoutError(PRIVATE)
    if kind == "certificate":
        return URLError(ssl.SSLCertVerificationError(1, PRIVATE))
    if kind == "direct_certificate":
        return ssl.SSLCertVerificationError(1, PRIVATE)
    if kind == "tls":
        return URLError(ssl.SSLEOFError(8, PRIVATE))
    if kind == "direct_tls":
        return ssl.SSLError(1, PRIVATE)
    if kind == "connection":
        return ConnectionResetError(PRIVATE)
    if kind == "url_error":
        return URLError(PRIVATE)
    if kind == "incomplete":
        return IncompleteRead(PRIVATE.encode(), 500)
    if kind == "local_io":
        return PermissionError(PRIVATE)
    return RuntimeError(PRIVATE)


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("kind,reason", [
    (401, "http_error"), (403, "http_error"), (404, "http_error"),
    (429, "http_error"), (503, "http_error"),
    ("timeout", "timeout"), ("wrapped_timeout", "timeout"),
    ("certificate", "tls_certificate_error"), ("direct_certificate", "tls_certificate_error"),
    ("tls", "tls_error"), ("direct_tls", "tls_error"),
    ("connection", "network_error"), ("url_error", "network_error"),
    ("incomplete", "incomplete_response"), ("local_io", "download_failed"),
    ("unknown", "download_failed"),
])
def test_download_failure_keeps_safe_category_without_installing(tmp_home, monkeypatch, dry_run, kind, reason):
    opener = MagicMock()
    opener.open.side_effect = download_error(kind)
    monkeypatch.setattr(marketplace.urllib.request, "build_opener", lambda *args: opener)
    install = MagicMock()
    inspect = MagicMock()
    monkeypatch.setattr("cliany_site.commands.market.install_adapter", install)
    monkeypatch.setattr("cliany_site.commands.market.inspect_adapter_package", inspect)
    args = ["install", SOURCE, "--sha256", "0" * 64, "--json"]
    if dry_run:
        args.append("--dry-run")

    result = CliRunner().invoke(market_group, args)

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False and payload["success"] is False
    error = payload["error"]
    assert error["code"] == "INSTALL_FAILED"
    expected = {"stage": "download", "reason": reason}
    if isinstance(kind, int):
        expected["status_code"] = kind
    assert error["details"] == expected
    assert error["message"] == "远程安装包下载失败: https://downloads.example.test/adapter.tar.gz"
    assert "检查安装包格式" not in error["fix"]
    assert "--sha256" in error["fix"]
    assert PRIVATE not in result.stdout and "fragment" not in result.stdout
    assert "Authorization" not in result.stdout and "user:" not in result.stdout
    opener.open.assert_called_once_with(SOURCE)
    install.assert_not_called()
    inspect.assert_not_called()


def test_human_certificate_failure_points_to_trust_not_archive_format(tmp_home, monkeypatch):
    opener = MagicMock()
    opener.open.side_effect = download_error("certificate")
    monkeypatch.setattr(marketplace.urllib.request, "build_opener", lambda *args: opener)

    result = CliRunner().invoke(market_group, ["install", SOURCE, "--sha256", "0" * 64])

    assert result.exit_code == 1
    assert "证书" in result.stdout and "不要关闭" in result.stdout
    assert "检查安装包格式" not in result.stdout and PRIVATE not in result.stdout


def test_demo_keeps_actual_market_category_and_stops_before_verify_or_query(tmp_home, monkeypatch):
    opener = MagicMock()
    opener.open.side_effect = download_error(503)
    monkeypatch.setattr(marketplace.urllib.request, "build_opener", lambda *args: opener)
    market_result = CliRunner().invoke(market_group, ["install", SOURCE, "--sha256", "0" * 64, "--json"])
    market_payload = json.loads(market_result.stdout)
    step = MagicMock(return_value=(False, market_payload))
    monkeypatch.setattr(demo, "_run_step", step)

    result = CliRunner().invoke(cli, ["demo", "--case-id", "apache-jira-issues", "--json"])

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["error"]["code"] == "E_DOWNLOAD_FAILED"
    assert payload["error"]["details"]["stage"] == "install"
    assert payload["error"]["details"]["upstream_error"]["details"] == {
        "stage": "download", "reason": "http_error", "status_code": 503,
    }
    step.assert_called_once()
    assert PRIVATE not in result.stdout


@pytest.mark.parametrize("reason", ["incomplete_response", "network_error"])
def test_partial_response_is_diagnosed_and_temp_file_removed_before_force_install(tmp_home, monkeypatch, reason):
    response = MagicMock()
    response.headers = {"Content-Length": "1000"}
    failure = (
        IncompleteRead(PRIVATE.encode(), 1000) if reason == "incomplete_response" else ConnectionResetError(PRIVATE)
    )
    response.read.side_effect = [b"partial archive bytes", failure]
    opener = MagicMock()
    opener.open.return_value.__enter__.return_value = response
    monkeypatch.setattr(marketplace.urllib.request, "build_opener", lambda *args: opener)
    mkstemp = marketplace.tempfile.mkstemp
    monkeypatch.setattr(marketplace.tempfile, "mkstemp", lambda **kwargs: mkstemp(dir=tmp_home, **kwargs))
    install = MagicMock()
    monkeypatch.setattr("cliany_site.commands.market.install_adapter", install)
    existing = tmp_home / ".cliany-site/adapters/keep.test/commands.py"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"keep existing user data")

    result = CliRunner().invoke(market_group, ["install", SOURCE, "--sha256", "0" * 64, "--force", "--json"])

    error = json.loads(result.stdout)["error"]
    assert result.exit_code == 1
    assert error["details"] == {"stage": "download", "reason": reason}
    assert PRIVATE not in result.stdout
    assert list(tmp_home.glob("cliany-site-*.cliany-adapter.tar.gz")) == []
    assert existing.read_bytes() == b"keep existing user data"
    install.assert_not_called()


@pytest.mark.parametrize("status", [True, PRIVATE])
def test_http_error_never_copies_non_status_data(tmp_home, monkeypatch, status):
    opener = MagicMock()
    opener.open.side_effect = HTTPError(SOURCE, status, PRIVATE, {}, None)
    monkeypatch.setattr(marketplace.urllib.request, "build_opener", lambda *args: opener)

    result = CliRunner().invoke(market_group, ["install", SOURCE, "--sha256", "0" * 64, "--json"])

    error = json.loads(result.stdout)["error"]
    assert error["details"] == {"stage": "download", "reason": "http_error"}
    assert PRIVATE not in result.stdout


def test_invalid_redirect_does_not_echo_unparseable_credentials():
    handler = marketplace._HTTPSOnlyRedirectHandler()
    with pytest.raises(ValueError) as failure:
        handler.redirect_request(None, None, 302, "Found", {}, f"https://user:{PRIVATE}@[broken")
    assert PRIVATE not in str(failure.value)


def test_root_json_also_receives_download_diagnostics(tmp_home, monkeypatch):
    opener = MagicMock()
    opener.open.side_effect = download_error(404)
    monkeypatch.setattr(marketplace.urllib.request, "build_opener", lambda *args: opener)

    result = CliRunner().invoke(cli, ["--json", "market", "install", SOURCE, "--sha256", "0" * 64])

    error = json.loads(result.stdout)["error"]
    assert result.exit_code == 1
    assert error["details"]["status_code"] == 404
    assert "发布资产存在" in error["fix"]
    assert PRIVATE not in result.stdout


@pytest.mark.parametrize("kind", ["url_credentials", "certificate_body"])
def test_failure_never_echoes_url_login_or_certificate_body(tmp_home, monkeypatch, kind):
    opener = MagicMock()
    opener.open.side_effect = download_error("url_error" if kind == "url_credentials" else "direct_certificate")
    monkeypatch.setattr(marketplace.urllib.request, "build_opener", lambda *args: opener)
    source = SOURCE if kind == "url_credentials" else "https://downloads.example.test/adapter.tar.gz"

    result = CliRunner().invoke(market_group, ["install", source, "--sha256", "0" * 64, "--json"])

    assert result.exit_code == 1
    assert PRIVATE not in result.stdout
