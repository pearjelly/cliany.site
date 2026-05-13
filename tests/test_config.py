from pathlib import Path

import pytest

from cliany_site.config import (
    ClanySiteConfig,
    _env_bool,
    _env_float,
    _env_int,
    get_config,
    load_config,
    reset_config,
)


class TestEnvParsers:
    def test_env_int_returns_default_when_missing(self, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_KEY", raising=False)
        assert _env_int("NONEXISTENT_KEY", 42) == 42

    def test_env_int_parses_valid_value(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "100")
        assert _env_int("TEST_INT", 0) == 100

    def test_env_int_returns_default_on_invalid(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "not_a_number")
        assert _env_int("TEST_INT", 7) == 7

    def test_env_int_returns_default_on_empty(self, monkeypatch):
        monkeypatch.setenv("TEST_INT", "")
        assert _env_int("TEST_INT", 5) == 5

    def test_env_float_parses_valid_value(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "3.14")
        assert _env_float("TEST_FLOAT", 0.0) == pytest.approx(3.14)

    def test_env_float_returns_default_on_invalid(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT", "abc")
        assert _env_float("TEST_FLOAT", 1.5) == 1.5

    def test_env_bool_truthy_values(self, monkeypatch):
        for val in ("1", "true", "True", "TRUE", "yes", "Yes", "YES"):
            monkeypatch.setenv("TEST_BOOL", val)
            assert _env_bool("TEST_BOOL", False) is True

    def test_env_bool_falsy_values(self, monkeypatch):
        for val in ("0", "false", "no", "whatever"):
            monkeypatch.setenv("TEST_BOOL", val)
            assert _env_bool("TEST_BOOL", True) is False

    def test_env_bool_returns_default_on_empty(self, monkeypatch):
        monkeypatch.setenv("TEST_BOOL", "")
        assert _env_bool("TEST_BOOL", True) is True
        assert _env_bool("TEST_BOOL", False) is False


class TestClanySiteConfig:
    def test_defaults(self):
        cfg = ClanySiteConfig()
        assert cfg.cdp_port == 9222
        assert cfg.cdp_timeout == 2.0
        assert cfg.explore_max_steps == 10
        assert cfg.adaptive_repair_enabled is False
        assert cfg.home_dir == Path.home() / ".cliany-site"

    def test_derived_paths(self):
        cfg = ClanySiteConfig(home_dir=Path("/tmp/test-home"))
        assert cfg.adapters_dir == Path("/tmp/test-home/adapters")
        assert cfg.sessions_dir == Path("/tmp/test-home/sessions")
        assert cfg.reports_dir == Path("/tmp/test-home/reports")
        assert cfg.activity_log_path == Path("/tmp/test-home/activity.log")

    def test_frozen(self):
        cfg = ClanySiteConfig()
        with pytest.raises(AttributeError):
            cfg.cdp_port = 9999  # type: ignore[misc]

    def test_to_dict_keys(self):
        cfg = ClanySiteConfig()
        d = cfg.to_dict()
        expected_keys = {
            "cdp_port",
            "cdp_timeout",
            "cdp_url",
            "headless",
            "post_navigate_delay",
            "post_click_nav_delay",
            "new_tab_settle_delay",
            "resolve_retry_delay",
            "resolve_max_retries",
            "llm_retry_max_attempts",
            "llm_retry_base_delay",
            "llm_retry_backoff_factor",
            "adaptive_repair_enabled",
            "adaptive_repair_max_attempts",
            "vision_enabled",
            "screenshot_format",
            "screenshot_quality",
            "vision_min_confidence",
            "vision_som_max_labels",
            "explore_max_steps",
            "cross_origin_iframes",
            "max_iframes",
            "max_iframe_depth",
            "home_dir",
            "adapters_dir",
            "sessions_dir",
            "reports_dir",
            "logs_dir",
            "activity_log_path",
            "browser_provider",
            "obscura_port",
            "obscura_version",
            "obscura_ready_timeout",
            "obscura_auto_upgrade",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_path_values_are_strings(self):
        cfg = ClanySiteConfig()
        d = cfg.to_dict()
        assert isinstance(d["home_dir"], str)
        assert isinstance(d["adapters_dir"], str)


class TestLoadConfig:
    def test_load_config_reads_env_vars(self, monkeypatch, clean_env):
        monkeypatch.setenv("CLIANY_CDP_PORT", "9333")
        monkeypatch.setenv("CLIANY_CDP_TIMEOUT", "5.0")
        monkeypatch.setenv("CLIANY_EXPLORE_MAX_STEPS", "20")
        monkeypatch.setenv("CLIANY_ADAPTIVE_REPAIR", "true")

        cfg = load_config()
        assert cfg.cdp_port == 9333
        assert cfg.cdp_timeout == pytest.approx(5.0)
        assert cfg.explore_max_steps == 20
        assert cfg.adaptive_repair_enabled is True

    def test_load_config_uses_defaults_when_no_env(self, clean_env):
        cfg = load_config()
        assert cfg.cdp_port == 9222
        assert cfg.cdp_timeout == pytest.approx(2.0)

    def test_load_config_ignores_invalid_env(self, monkeypatch, clean_env):
        monkeypatch.setenv("CLIANY_CDP_PORT", "not_a_port")
        monkeypatch.setenv("CLIANY_CDP_TIMEOUT", "bad")
        cfg = load_config()
        assert cfg.cdp_port == 9222
        assert cfg.cdp_timeout == pytest.approx(2.0)


class TestGetConfigSingleton:
    def test_returns_same_instance(self, clean_env):
        a = get_config()
        b = get_config()
        assert a is b

    def test_reset_config_clears_singleton(self, clean_env):
        a = get_config()
        reset_config()
        b = get_config()
        assert a is not b

    def test_env_change_after_reset(self, monkeypatch, clean_env):
        cfg1 = get_config()
        assert cfg1.cdp_port == 9222

        reset_config()
        monkeypatch.setenv("CLIANY_CDP_PORT", "8888")
        cfg2 = get_config()
        assert cfg2.cdp_port == 8888
