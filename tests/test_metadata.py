import json
import pathlib
import pytest
import tempfile

from cliany_site.metadata import LegacyMetadataError, MetadataParseError, load_metadata


class TestLoadMetadata:
    def test_v2_is_now_legacy(self):
        """schema_version=2 (fixture) → LegacyMetadataError (v3 업그레이드 후)"""
        sample_path = pathlib.Path("tests/fixtures/metadata.v2.sample.json")
        with pytest.raises(LegacyMetadataError):
            load_metadata(sample_path)

    def test_v1_raises_legacy(self, tmp_path):
        """schema_version=1 → 抛 LegacyMetadataError"""
        metadata = {"schema_version": 1, "domain": "test.com"}
        metadata_path = tmp_path / "metadata.json"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        with pytest.raises(LegacyMetadataError):
            load_metadata(metadata_path)

    def test_missing_schema_version_raises_legacy(self, tmp_path):
        """缺 schema_version 字段 → 抛 LegacyMetadataError"""
        metadata = {"domain": "test.com"}
        metadata_path = tmp_path / "metadata.json"
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

        with pytest.raises(LegacyMetadataError):
            load_metadata(metadata_path)

    def test_bad_json_raises_parse_error(self, tmp_path):
        """非法 JSON 文件 → 抛 MetadataParseError"""
        metadata_path = tmp_path / "metadata.json"
        metadata_path.write_text("{invalid json", encoding="utf-8")

        with pytest.raises(MetadataParseError):
            load_metadata(metadata_path)

    def test_missing_file_raises_parse_error(self, tmp_path):
        """文件不存在 → 抛 MetadataParseError"""
        metadata_path = tmp_path / "nonexistent.json"

        with pytest.raises(MetadataParseError):
            load_metadata(metadata_path)

    def test_jsonschema_validate_sample(self):
        """用 jsonschema 验证 sample.json 符合 schemas/metadata.v2.json"""
        import jsonschema

        schema_path = pathlib.Path("schemas/metadata.v2.json")
        sample_path = pathlib.Path("tests/fixtures/metadata.v2.sample.json")

        schema = json.loads(schema_path.read_text())
        sample = json.loads(sample_path.read_text())

        jsonschema.validate(sample, schema)  # 不抛错即通过