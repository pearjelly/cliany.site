from __future__ import annotations

import json
import pathlib

import pytest

from cliany_site.metadata import LegacyMetadataError, MetadataParseError, load_metadata


class TestLoadMetadataV3RejectionFromFile:
    @pytest.mark.parametrize("version", [1, 2, "1", "2", ""])
    def test_old_versions_raise_legacy_error(self, tmp_path, version):
        """schema_version 1/2 (정수·문자열) → LegacyMetadataError"""
        metadata_path = tmp_path / "metadata.json"
        metadata_path.write_text(
            json.dumps({"schema_version": version, "domain": "test.com"}),
            encoding="utf-8",
        )
        with pytest.raises(LegacyMetadataError):
            load_metadata(metadata_path)

    def test_missing_schema_version_raises_legacy(self, tmp_path):
        """schema_version 필드 없음 → LegacyMetadataError"""
        metadata_path = tmp_path / "metadata.json"
        metadata_path.write_text(
            json.dumps({"domain": "test.com"}),
            encoding="utf-8",
        )
        with pytest.raises(LegacyMetadataError):
            load_metadata(metadata_path)

    def test_none_schema_version_raises_legacy(self, tmp_path):
        """schema_version=null → LegacyMetadataError"""
        metadata_path = tmp_path / "metadata.json"
        metadata_path.write_text(
            json.dumps({"schema_version": None, "domain": "test.com"}),
            encoding="utf-8",
        )
        with pytest.raises(LegacyMetadataError):
            load_metadata(metadata_path)

    def test_unknown_high_version_raises_parse_error(self, tmp_path):
        """schema_version=99 (미지원 미래 버전) → MetadataParseError"""
        metadata_path = tmp_path / "metadata.json"
        metadata_path.write_text(
            json.dumps({"schema_version": 99, "domain": "test.com"}),
            encoding="utf-8",
        )
        with pytest.raises(MetadataParseError):
            load_metadata(metadata_path)


class TestLoadMetadataV3RejectionFromDict:
    @pytest.mark.parametrize("version", [1, 2, "1", "2", ""])
    def test_dict_old_versions_raise_legacy_error(self, version):
        """dict 입력으로도 schema_version 1/2 → LegacyMetadataError"""
        with pytest.raises(LegacyMetadataError):
            load_metadata({"schema_version": version, "domain": "test.com"})

    def test_dict_missing_schema_version_raises_legacy(self):
        """dict 입력, schema_version 없음 → LegacyMetadataError"""
        with pytest.raises(LegacyMetadataError):
            load_metadata({"domain": "test.com"})

    def test_dict_none_schema_version_raises_legacy(self):
        """dict 입력, schema_version=None → LegacyMetadataError"""
        with pytest.raises(LegacyMetadataError):
            load_metadata({"schema_version": None, "domain": "test.com"})

    def test_dict_unknown_high_version_raises_parse_error(self):
        """dict 입력, schema_version=99 → MetadataParseError"""
        with pytest.raises(MetadataParseError):
            load_metadata({"schema_version": 99, "domain": "test.com"})
