import importlib.util
import io
import json
import shutil
import urllib.error
from pathlib import Path

from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.config import get_config
from cliany_site.loader import load_adapter_from_path
from cliany_site.marketplace import install_adapter, pack_adapter

SOURCE = Path(__file__).resolve().parents[1] / "curated_adapters" / "builds.apache.org"


def _group():
    spec = importlib.util.spec_from_file_location("curated_jenkins", SOURCE / "commands.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.cli


def test_list_jobs_reports_true_total_and_bounded_rows(monkeypatch):
    captured = {}

    def respond(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return io.BytesIO(json.dumps({"jobs": [
            {"name": "Spark", "url": "https://ci-builds.apache.org/job/Spark/", "color": "blue"},
            {"name": "Maven", "url": "https://ci-builds.apache.org/job/Maven/"},
            {"name": "Ant", "url": "https://ci-builds.apache.org/job/Ant/"},
        ]}).encode())

    monkeypatch.setattr("urllib.request.urlopen", respond)
    result = CliRunner().invoke(_group(), ["list-jobs", "--limit", "2", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data == {"jobs": [
        {"name": "Spark", "url": "https://ci-builds.apache.org/job/Spark/", "color": "blue"},
        {"name": "Maven", "url": "https://ci-builds.apache.org/job/Maven/", "color": None},
    ], "count": 2, "total": 3}
    assert captured["url"].startswith("https://ci-builds.apache.org/api/json?")
    assert captured["timeout"] == 15


def test_rejects_external_result_urls(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: io.BytesIO(
        b'{"jobs":[{"name":"bad","url":"https://example.com/job/bad/"}]}'
    ))
    result = CliRunner().invoke(_group(), ["list-jobs", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["error"]["code"] == "E_PARSE_FAILED"


def test_empty_list_inherits_root_json_mode(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: io.BytesIO(b'{"jobs":[]}'))
    result = CliRunner().invoke(_group(), ["list-jobs"], obj={"json_mode": True})
    assert result.exit_code == 0
    assert json.loads(result.output)["data"]["total"] == 0


def test_invalid_limit_rejected_before_request(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("network request must not happen")
    ))
    result = CliRunner().invoke(_group(), ["list-jobs", "--limit", "0", "--json"])
    assert result.exit_code != 0


def test_network_failure_is_nonzero_and_structured(monkeypatch):
    def fail(*args, **kwargs):
        raise urllib.error.URLError("unreachable")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    result = CliRunner().invoke(_group(), ["list-jobs", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["error"]["code"] == "E_PAGE_NOT_READY"


def test_package_installs_and_passes_strict_verification_in_isolated_home(tmp_home):
    target = get_config().adapters_dir / "builds.apache.org"
    shutil.copytree(SOURCE, target)
    package = pack_adapter("builds.apache.org", version="0.16.365", author="cliany.site")
    target.rename(tmp_home / "staged-source")
    manifest = install_adapter(package)
    assert manifest.domain == "builds.apache.org"
    installed, reason = load_adapter_from_path(target / "commands.py", "builds.apache.org")
    assert reason is None and installed is not None
    result = CliRunner().invoke(cli, ["verify", "builds.apache.org", "--strict", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["ok"] is True


def test_builder_handles_jenkins_without_user_adapter_writes(tmp_home, tmp_path):
    from scripts.build_curated_adapter import build

    output = build("builds.apache.org", "0.16.365", tmp_path / "dist")
    assert output.is_file()
    assert not get_config().adapters_dir.exists()
