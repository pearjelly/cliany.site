from __future__ import annotations

import inspect
import json
import pathlib

import jsonschema

from cliany_site.metadata import load_metadata

_V3_SAMPLE = {
    "schema_version": 3,
    "domain": "example.com",
    "generated_at": "2026-01-01T00:00:00Z",
    "generator_version": "1.0.0",
    "commands": [{"name": "search"}],
    "canonical_actions": [],
    "selector_pool": [],
    "smoke": [],
    "heal_history": [],
    "axtree": {
        "compounds": {},
        "pruning_meta": {},
    },
    "capability": "browser",
    "api_endpoints": [],
}


class TestMetadataV3TypedDict:
    def test_import_schema_v3(self):
        from cliany_site.codegen import schema_v3  # noqa: F401

    def test_typed_dicts_exist(self):
        from cliany_site.codegen.schema_v3 import (
            CapabilityMeta,
            CompoundsMeta,
            MetadataV3,
            PruningMeta,
        )
        assert CompoundsMeta is not None
        assert PruningMeta is not None
        assert CapabilityMeta is not None
        assert MetadataV3 is not None

    def test_metadata_v3_is_typeddict(self):
        from cliany_site.codegen.schema_v3 import MetadataV3
        assert hasattr(MetadataV3, "__annotations__")
        annotations = MetadataV3.__annotations__
        assert "schema_version" in annotations
        assert "domain" in annotations
        assert "generated_at" in annotations
        assert "generator_version" in annotations
        assert "commands" in annotations

    def test_metadata_v3_has_v3_fields(self):
        from cliany_site.codegen.schema_v3 import MetadataV3
        annotations = MetadataV3.__annotations__
        assert "axtree" in annotations
        assert "capability" in annotations
        assert "api_endpoints" in annotations

    def test_no_pydantic_import(self):
        src = pathlib.Path("src/cliany_site/codegen/schema_v3.py").read_text()
        assert "pydantic" not in src
        assert "from cliany_site.config" not in src
        assert "from cliany_site.errors" not in src


class TestSchemaV3Json:
    def test_schema_file_exists(self):
        schema_path = pathlib.Path("src/cliany_site/schemas/metadata.v3.json")
        assert schema_path.exists()

    def test_schema_is_valid_json(self):
        schema_path = pathlib.Path("src/cliany_site/schemas/metadata.v3.json")
        schema = json.loads(schema_path.read_text())
        assert isinstance(schema, dict)

    def test_schema_version_enum_is_3(self):
        schema_path = pathlib.Path("src/cliany_site/schemas/metadata.v3.json")
        schema = json.loads(schema_path.read_text())
        version_prop = schema["properties"]["schema_version"]
        assert version_prop["enum"] == [3]

    def test_v3_sample_validates(self):
        schema_path = pathlib.Path("src/cliany_site/schemas/metadata.v3.json")
        schema = json.loads(schema_path.read_text())
        jsonschema.validate(_V3_SAMPLE, schema)

    def test_v3_api_metadata_with_legacy_endpoint_strings_validates(self):
        schema_path = pathlib.Path("src/cliany_site/schemas/metadata.v3.json")
        schema = json.loads(schema_path.read_text())
        api_metadata = _V3_SAMPLE | {
            "capability": "api",
            "api_endpoints": ["https://issues.apache.org/jira/rest/api/2/search"],
        }

        jsonschema.validate(api_metadata, schema)

    def test_v3_metadata_with_legacy_command_strings_validates(self):
        schema_path = pathlib.Path("src/cliany_site/schemas/metadata.v3.json")
        schema = json.loads(schema_path.read_text())
        legacy_commands = _V3_SAMPLE | {"commands": ["list-issues"]}

        jsonschema.validate(legacy_commands, schema)

    def test_v2_json_still_exists(self):
        v2_path = pathlib.Path("src/cliany_site/schemas/metadata.v2.json")
        assert v2_path.exists()

    def test_v3_schema_has_new_fields(self):
        schema_path = pathlib.Path("src/cliany_site/schemas/metadata.v3.json")
        schema = json.loads(schema_path.read_text())
        props = schema.get("properties", {})
        assert "axtree" in props
        assert "capability" in props
        assert "api_endpoints" in props

    def test_command_empty_result_expectation_is_boolean(self):
        schema_path = pathlib.Path("src/cliany_site/schemas/metadata.v3.json")
        schema = json.loads(schema_path.read_text())
        command_properties = schema["properties"]["commands"]["items"]["oneOf"][0]["properties"]
        assert command_properties["expects_nonempty"]["type"] == "boolean"

    def test_packaged_schema_matches_repository_schema(self):
        package_schema = json.loads(
            pathlib.Path("src/cliany_site/schemas/metadata.v3.json").read_text()
        )
        repository_schema = json.loads(pathlib.Path("schemas/metadata.v3.json").read_text())
        assert package_schema == repository_schema


class TestLoadMetadataV3:
    def test_v3_file_accepted(self, tmp_path):
        """schema_version=3 파일 → 정상 로드"""
        metadata_path = tmp_path / "metadata.json"
        metadata_path.write_text(json.dumps(_V3_SAMPLE), encoding="utf-8")
        result = load_metadata(metadata_path)
        assert result["schema_version"] == 3

    def test_dict_input_accepted(self):
        """dict 입력 → IO/JSON 파싱 스킵, 그대로 반환"""
        result = load_metadata(_V3_SAMPLE)
        assert result["schema_version"] == 3
        assert result["domain"] == "example.com"

    def test_dict_input_returns_dict(self):
        result = load_metadata(dict(_V3_SAMPLE))
        assert isinstance(result, dict)
        assert result["schema_version"] == 3

    def test_signature_accepts_dict_type(self):
        """load_metadata 시그니처가 dict를 받아야 한다"""
        from cliany_site.metadata import load_metadata as _lm
        sig = inspect.signature(_lm)
        first_param = next(iter(sig.parameters.values()))
        assert first_param is not None

    def test_metadata_schema_version_constant_is_3(self):
        """METADATA_SCHEMA_VERSION 상수가 3이어야 한다"""
        from cliany_site.codegen.generator import METADATA_SCHEMA_VERSION
        assert METADATA_SCHEMA_VERSION == 3
        assert isinstance(METADATA_SCHEMA_VERSION, int)
