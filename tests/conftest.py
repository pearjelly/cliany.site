import json
import os
from unittest.mock import MagicMock

import pytest

from cliany_site.config import reset_config


@pytest.fixture(autouse=True)
def _reset_config_singleton():
    """每个测试前后重置 config 单例，避免测试间状态泄漏"""
    reset_config()
    yield
    reset_config()


@pytest.fixture()
def clean_env(monkeypatch):
    """清除所有 CLIANY_ 开头的环境变量"""
    for key in list(os.environ):
        if key.startswith("CLIANY_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def tmp_adapters_dir(tmp_path):
    d = tmp_path / "adapters"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def mock_cdp():
    return MagicMock()


@pytest.fixture
def sample_metadata():
    return {"domain": "example.com", "commands": [], "schema_version": "1"}


@pytest.fixture
def sample_adapter_dir(tmp_path, sample_metadata):
    d = tmp_path / "adapters" / "example.com"
    d.mkdir(parents=True)
    (d / "metadata.json").write_text(json.dumps(sample_metadata))
    (d / "commands.py").write_text(
        "import click\n\n@click.group()\ndef cli():\n    pass\n"
    )
    return d


@pytest.fixture
def no_llm(monkeypatch):
    """阻断所有 LLM 客户端调用，防止测试意外触发真实 LLM"""
    import cliany_site.explorer.engine as engine_mod
    
    def _raise(*args, **kwargs):
        raise RuntimeError("LLM disabled in tests")
    
    # 用 monkeypatch 替换 LLM 客户端初始化
    monkeypatch.setattr(engine_mod, "_create_llm_client", _raise, raising=False)
    # 也 patch 常见的 LLM 调用入口
    try:
        import langchain_openai
        monkeypatch.setattr(langchain_openai, "ChatOpenAI", _raise)
    except ImportError:
        pass
    try:
        import langchain_anthropic
        monkeypatch.setattr(langchain_anthropic, "ChatAnthropic", _raise)
    except ImportError:
        pass
    return _raise


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """用临时目录替换 ~/.cliany-site，避免测试污染用户主目录"""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    # 重置 config 单例让其重新读取 HOME
    from cliany_site.config import reset_config
    reset_config()
    yield fake_home
    reset_config()
