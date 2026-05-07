import json
from pathlib import Path
from unittest.mock import patch
import pytest

from cliany_site.repair_cache import cache_path, load, lookup, record, compute_subtree_hash


class TestRepairCache:
    @patch('cliany_site.repair_cache.Path.home')
    def test_cache_path(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        path = cache_path('example.com')
        expected = tmp_path / '.cliany-site' / 'adapters' / 'example.com' / 'repair-cache.json'
        assert path == expected

    @patch('cliany_site.repair_cache.Path.home')
    def test_load_nonexistent(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        result = load('example.com')
        assert result == {}

    @patch('cliany_site.repair_cache.Path.home')
    def test_load_existing(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        path = cache_path('example.com')
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {'key': 'value'}
        path.write_text(json.dumps(data), encoding='utf-8')
        result = load('example.com')
        assert result == data

    @patch('cliany_site.repair_cache.Path.home')
    def test_lookup_none(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        result = lookup('example.com', 'old_selector', 'hash123')
        assert result is None

    @patch('cliany_site.repair_cache.Path.home')
    def test_lookup_found(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        record('example.com', 'old_selector', 'new_selector', 'hash123')
        result = lookup('example.com', 'old_selector', 'hash123')
        assert result == 'new_selector'

    @patch('cliany_site.repair_cache.Path.home')
    def test_record_new(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        record('example.com', 'old', 'new', 'hash')
        data = load('example.com')
        key = 'old:hash'
        assert key in data
        entry = data[key]
        assert entry['selector_old'] == 'old'
        assert entry['selector_new'] == 'new'
        assert entry['axtree_subtree_hash'] == 'hash'
        assert entry['success_count'] == 1
        assert 'last_used_iso' in entry

    @patch('cliany_site.repair_cache.Path.home')
    def test_record_update(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        record('example.com', 'old', 'new', 'hash')
        record('example.com', 'old', 'new', 'hash')
        data = load('example.com')
        entry = data['old:hash']
        assert entry['success_count'] == 2

    @patch('cliany_site.repair_cache.Path.home')
    def test_lru_limit(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        for i in range(105):
            record('example.com', f'selector_{i}', f'new_{i}', 'same_hash')
        data = load('example.com')
        assert len(data) == 100

    def test_compute_hash_same(self):
        node = {'key': 'value'}
        hash1 = compute_subtree_hash(node)
        hash2 = compute_subtree_hash(node)
        assert hash1 == hash2

    def test_compute_hash_different(self):
        node1 = {'key': 'value1'}
        node2 = {'key': 'value2'}
        hash1 = compute_subtree_hash(node1)
        hash2 = compute_subtree_hash(node2)
        assert hash1 != hash2

    def test_compute_hash_order_independent(self):
        node1 = {'a': 1, 'b': 2}
        node2 = {'b': 2, 'a': 1}
        hash1 = compute_subtree_hash(node1)
        hash2 = compute_subtree_hash(node2)
        assert hash1 == hash2

    @patch('cliany_site.repair_cache.Path.home')
    def test_record_different_hashes(self, mock_home, tmp_path):
        mock_home.return_value = tmp_path
        record('example.com', 'old', 'new1', 'hash1')
        record('example.com', 'old', 'new2', 'hash2')
        data = load('example.com')
        assert 'old:hash1' in data
        assert 'old:hash2' in data
        assert data['old:hash1']['selector_new'] == 'new1'
        assert data['old:hash2']['selector_new'] == 'new2'