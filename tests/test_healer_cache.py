from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cliany_site.healer import HealResult, Healer
from cliany_site.repair_cache import compute_subtree_hash


DOMAIN = "test.com"

FAILURE_ENVELOPE_WITH_DATA = {
    "ok": False,
    "command": "search",
    "data": {"page": "context", "ref": "ref_1"},
    "error": {
        "code": "E_SELECTOR_NOT_FOUND",
        "message": "element not found",
        "details": {"selector": "#submit-btn"},
        "hint": None,
    },
    "meta": {"duration_ms": 10, "source": "builtin"},
}

FAILURE_ENVELOPE_DIFFERENT_DATA = {
    **FAILURE_ENVELOPE_WITH_DATA,
    "data": {"page": "different-context", "ref": "ref_2"},
}

LLM_RESPONSE_JSON = '{"new_selectors": {"ref_1": "#new-btn"}, "new_actions": [{"type": "click", "ref": "ref_1"}]}'


def _make_llm_mock():
    response = MagicMock()
    response.content = LLM_RESPONSE_JSON
    response.usage_metadata = {"total_tokens": 50}
    llm = MagicMock()
    llm.invoke.return_value = response
    return llm


@pytest.fixture()
def adapters_dir(tmp_home):
    d = tmp_home / ".cliany-site" / "adapters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_cache_miss_calls_llm_once(tmp_home, adapters_dir):
    llm_mock = _make_llm_mock()
    with patch.object(Healer, "_get_llm", return_value=llm_mock):
        result = Healer().heal(
            domain=DOMAIN,
            command="search",
            failure_envelope=FAILURE_ENVELOPE_WITH_DATA,
        )

    assert result.ok is True
    assert result.cache_hit is False
    assert llm_mock.invoke.call_count == 1
    assert result.new_selectors == {"ref_1": "#new-btn"}


def test_cache_hit_skips_llm(tmp_home, adapters_dir):
    llm_mock = _make_llm_mock()
    with patch.object(Healer, "_get_llm", return_value=llm_mock):
        first = Healer().heal(
            domain=DOMAIN,
            command="search",
            failure_envelope=FAILURE_ENVELOPE_WITH_DATA,
        )
        assert first.ok is True
        assert first.cache_hit is False
        assert llm_mock.invoke.call_count == 1

        second = Healer().heal(
            domain=DOMAIN,
            command="search",
            failure_envelope=FAILURE_ENVELOPE_WITH_DATA,
        )

    assert second.ok is True
    assert second.cache_hit is True
    assert llm_mock.invoke.call_count == 1
    assert second.new_selectors == {"ref_1": "#new-btn"}
    assert second.new_actions == [{"type": "click", "ref": "ref_1"}]


def test_different_subtree_hash_causes_cache_miss(tmp_home, adapters_dir):
    llm_mock = _make_llm_mock()
    with patch.object(Healer, "_get_llm", return_value=llm_mock):
        first = Healer().heal(
            domain=DOMAIN,
            command="search",
            failure_envelope=FAILURE_ENVELOPE_WITH_DATA,
        )
        assert first.ok is True
        assert first.cache_hit is False
        assert llm_mock.invoke.call_count == 1

        third = Healer().heal(
            domain=DOMAIN,
            command="search",
            failure_envelope=FAILURE_ENVELOPE_DIFFERENT_DATA,
        )

    assert third.ok is True
    assert third.cache_hit is False
    assert llm_mock.invoke.call_count == 2


def test_cache_key_uses_selector_from_details(tmp_home, adapters_dir):
    envelope_a = {
        **FAILURE_ENVELOPE_WITH_DATA,
        "error": {
            "code": "E_SELECTOR_NOT_FOUND",
            "message": "not found",
            "details": {"selector": "#btn-a"},
            "hint": None,
        },
    }
    envelope_b = {
        **FAILURE_ENVELOPE_WITH_DATA,
        "error": {
            "code": "E_SELECTOR_NOT_FOUND",
            "message": "not found",
            "details": {"selector": "#btn-b"},
            "hint": None,
        },
    }
    llm_mock = _make_llm_mock()
    with patch.object(Healer, "_get_llm", return_value=llm_mock):
        r1 = Healer().heal(domain=DOMAIN, command="search", failure_envelope=envelope_a)
        r2 = Healer().heal(domain=DOMAIN, command="search", failure_envelope=envelope_b)

    assert r1.cache_hit is False
    assert r2.cache_hit is False
    assert llm_mock.invoke.call_count == 2


def test_same_selector_same_data_cache_hit(tmp_home, adapters_dir):
    envelope_a = {
        **FAILURE_ENVELOPE_WITH_DATA,
        "error": {
            "code": "E_SELECTOR_NOT_FOUND",
            "message": "not found",
            "details": {"selector": "#shared-btn"},
            "hint": None,
        },
    }
    llm_mock = _make_llm_mock()
    with patch.object(Healer, "_get_llm", return_value=llm_mock):
        r1 = Healer().heal(domain=DOMAIN, command="search", failure_envelope=envelope_a)
        r2 = Healer().heal(domain=DOMAIN, command="search", failure_envelope=envelope_a)

    assert r1.cache_hit is False
    assert r2.cache_hit is True
    assert llm_mock.invoke.call_count == 1


def test_none_data_field_treated_as_empty_dict(tmp_home, adapters_dir):
    envelope_no_data = {
        "ok": False,
        "command": "search",
        "data": None,
        "error": {
            "code": "E_SELECTOR_NOT_FOUND",
            "message": "not found",
            "details": {"selector": "#btn"},
            "hint": None,
        },
        "meta": {"duration_ms": 5, "source": "builtin"},
    }
    expected_hash = compute_subtree_hash({})
    actual_hash = compute_subtree_hash(
        envelope_no_data.get("data") if isinstance(envelope_no_data.get("data"), dict) else {}
    )
    assert actual_hash == expected_hash

    llm_mock = _make_llm_mock()
    with patch.object(Healer, "_get_llm", return_value=llm_mock):
        r1 = Healer().heal(domain=DOMAIN, command="search", failure_envelope=envelope_no_data)
        r2 = Healer().heal(domain=DOMAIN, command="search", failure_envelope=envelope_no_data)

    assert r1.cache_hit is False
    assert r2.cache_hit is True
    assert llm_mock.invoke.call_count == 1
