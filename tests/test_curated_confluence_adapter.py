import importlib.util
import io
import json
import shutil
import urllib.error
import urllib.parse
from pathlib import Path

from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.config import get_config
from cliany_site.loader import load_adapter_from_path
from cliany_site.marketplace import install_adapter, pack_adapter

SOURCE = Path(__file__).resolve().parents[1] / "curated_adapters" / "cwiki.apache.org"


def _group():
    spec = importlib.util.spec_from_file_location("curated_cwiki", SOURCE / "commands.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.cli


def test_keyword_search_uses_cql_and_clean_content_title(monkeypatch):
    captured = {}

    def respond(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return io.BytesIO(
            json.dumps(
                {
                    "results": [
                        {
                            "title": "<em>Preparing</em> Spark Releases",
                            "content": {
                                "id": "38572314",
                                "title": "Preparing Spark Releases",
                                "url": "/spaces/SPARK/pages/38572314/Preparing+Spark+Releases",
                            },
                        }
                    ]
                }
            ).encode()
        )

    monkeypatch.setattr("urllib.request.urlopen", respond)
    result = CliRunner().invoke(_group(), ["search-pages", "--space", "SPARK", "--query", "release", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["count"] == 1
    assert payload["data"]["results"] == [{
        "id": "38572314",
        "title": "Preparing Spark Releases",
        "url": "https://cwiki.apache.org/spaces/SPARK/pages/38572314/Preparing+Spark+Releases",
        "space": "SPARK",
    }]
    parsed = urllib.parse.parse_qs(urllib.parse.urlsplit(captured["url"]).query)
    assert parsed == {"cql": ['space="SPARK" AND type=page AND siteSearch~"release"'], "limit": ["10"]}
    assert captured["timeout"] == 15


def test_query_cannot_escape_cql_scope(monkeypatch):
    captured = {}

    def respond(request, timeout):
        captured["url"] = request.full_url
        return io.BytesIO(b'{"results": []}')

    monkeypatch.setattr("urllib.request.urlopen", respond)
    query = 'release" OR space=PRIVATE \\ test'
    result = CliRunner().invoke(_group(), ["search-pages", "--query", query, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["ok"] is True
    cql = urllib.parse.parse_qs(urllib.parse.urlsplit(captured["url"]).query)["cql"][0]
    assert cql == 'space="SPARK" AND type=page AND siteSearch~"release\\" OR space=PRIVATE \\\\ test"'


def test_rejects_invalid_space_without_request(monkeypatch):
    def no_request(*args, **kwargs):
        raise AssertionError("network request must not happen")

    monkeypatch.setattr("urllib.request.urlopen", no_request)
    result = CliRunner().invoke(_group(), ["search-pages", "--space", 'SPARK" OR space=PRIVATE', "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["error"]["code"] == "E_INVALID_PARAM"


def test_network_failure_is_nonzero_and_structured(monkeypatch):
    def fail(*args, **kwargs):
        raise urllib.error.URLError("unreachable")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    result = CliRunner().invoke(_group(), ["search-pages", "--query", "release", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["error"]["code"] == "E_PAGE_NOT_READY"


def test_nonempty_unusable_results_fail_instead_of_silent_empty(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: io.BytesIO(b'{"results": [{}]}'))
    result = CliRunner().invoke(_group(), ["search-pages", "--query", "release", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["error"]["code"] == "E_PARSE_FAILED"


def test_empty_results_are_valid_and_inherit_root_json_mode(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: io.BytesIO(b'{"results": []}'))
    result = CliRunner().invoke(_group(), ["search-pages", "--query", "unknown"], obj={"json_mode": True})
    assert result.exit_code == 0
    assert json.loads(result.output)["data"]["count"] == 0


def test_package_passes_strict_verification_in_isolated_home(tmp_home):
    target = get_config().adapters_dir / "cwiki.apache.org"
    shutil.copytree(SOURCE, target)
    pack_path = pack_adapter("cwiki.apache.org", version="0.16.364", author="cliany.site")
    assert pack_path.is_file()
    target.rename(tmp_home / "staged-source")
    manifest = install_adapter(pack_path)
    assert manifest.domain == "cwiki.apache.org"
    installed_group, reason = load_adapter_from_path(target / "commands.py", "cwiki.apache.org")
    assert reason is None and installed_group is not None
    installed_result = CliRunner().invoke(installed_group, ["search-pages", "--space", "bad space", "--json"])
    assert installed_result.exit_code == 1
    assert json.loads(installed_result.output)["error"]["code"] == "E_INVALID_PARAM"
    result = CliRunner().invoke(cli, ["verify", "cwiki.apache.org", "--strict", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["ok"] is True


def test_build_does_not_write_user_adapter_dir(tmp_home, tmp_path):
    from scripts.build_curated_confluence_adapter import build

    output = build("0.16.365", tmp_path / "dist")
    assert output.is_file()
    assert not get_config().adapters_dir.exists()
    try:
        build("0.16.365", tmp_path / "dist")
    except FileExistsError:
        pass
    else:
        raise AssertionError("builder overwrote an existing archive")
