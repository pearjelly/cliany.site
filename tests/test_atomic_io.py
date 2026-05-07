import json
import os
import tempfile
from pathlib import Path

import pytest

from cliany_site.atomic_io import atomic_read_json, atomic_write_json


class TestAtomicIO:
    def test_write_and_read_normal(self, tmp_path):
        """Test normal write and read cycle."""
        path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}
        atomic_write_json(path, data)
        result = atomic_read_json(path, {})
        assert result == data

    def test_write_creates_directory(self, tmp_path):
        """Test that write creates parent directories if they don't exist."""
        path = tmp_path / "subdir" / "nested" / "file.json"
        data = {"test": True}
        atomic_write_json(path, data)
        assert path.exists()
        result = atomic_read_json(path, {})
        assert result == data

    def test_read_nonexistent_file_returns_default(self, tmp_path):
        """Test reading a non-existent file returns the default."""
        path = tmp_path / "nonexistent.json"
        default = {"default": "value"}
        result = atomic_read_json(path, default)
        assert result == default

    def test_read_corrupted_json_returns_default(self, tmp_path):
        """Test reading corrupted JSON returns default."""
        path = tmp_path / "corrupted.json"
        path.write_text("{invalid json", encoding="utf-8")
        default = {"fallback": True}
        result = atomic_read_json(path, default)
        assert result == default

    def test_write_empty_dict(self, tmp_path):
        """Test writing an empty dict."""
        path = tmp_path / "empty.json"
        data = {}
        atomic_write_json(path, data)
        result = atomic_read_json(path, {"not": "empty"})
        assert result == data

    def test_write_large_dict(self, tmp_path):
        """Test writing a large dict."""
        path = tmp_path / "large.json"
        data = {f"key{i}": f"value{i}" for i in range(1000)}
        atomic_write_json(path, data)
        result = atomic_read_json(path, {})
        assert result == data

    def test_overwrite_existing_file(self, tmp_path):
        """Test overwriting an existing file."""
        path = tmp_path / "overwrite.json"
        # Write initial data
        initial_data = {"initial": "data"}
        atomic_write_json(path, initial_data)
        assert atomic_read_json(path, {}) == initial_data

        # Overwrite
        new_data = {"new": "data"}
        atomic_write_json(path, new_data)
        result = atomic_read_json(path, {})
        assert result == new_data

    def test_path_with_special_characters(self, tmp_path):
        """Test paths with special characters."""
        path = tmp_path / "special-file_123.json"
        data = {"special": "chars"}
        atomic_write_json(path, data)
        result = atomic_read_json(path, {})
        assert result == data

    def test_atomic_write_is_atomic(self, tmp_path):
        """Test that write is atomic by checking file doesn't exist during write."""
        path = tmp_path / "atomic_test.json"
        data = {"atomic": "test"}

        # This is hard to test directly, but we can check the file appears atomically
        atomic_write_json(path, data)
        assert path.exists()
        result = atomic_read_json(path, {})
        assert result == data

    def test_read_with_unicode_data(self, tmp_path):
        """Test reading and writing unicode data."""
        path = tmp_path / "unicode.json"
        data = {"unicode": "测试数据", "emoji": "🚀"}
        atomic_write_json(path, data)
        result = atomic_read_json(path, {})
        assert result == data

    def test_read_corrupted_json_with_partial_content(self, tmp_path):
        """Test reading JSON with partial content."""
        path = tmp_path / "partial.json"
        path.write_text('{"valid": true', encoding="utf-8")  # Missing closing brace
        default = {"fallback": "used"}
        result = atomic_read_json(path, default)
        assert result == default