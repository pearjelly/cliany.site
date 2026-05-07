import json
from pathlib import Path
from typing import Any, cast


class LegacyMetadataError(Exception):
    """旧版 metadata（无 schema_version 或 v1/v2）"""


class MetadataParseError(Exception):
    """metadata.json 解析失败（JSON 语法错误、IO 错误等）"""


def load_metadata(source: str | Path | dict) -> dict:
    if isinstance(source, dict):
        metadata = source
    else:
        try:
            with open(source, encoding='utf-8') as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise MetadataParseError(f"Failed to parse metadata.json: {e}") from e

    schema_version = metadata.get("schema_version")
    if schema_version is None or schema_version in (1, 2, "1", "2", ""):
        raise LegacyMetadataError(f"Legacy metadata schema version: {schema_version}")

    if schema_version != 3:
        raise MetadataParseError(f"Unsupported schema version: {schema_version}")

    return cast(dict[str, Any], metadata)

