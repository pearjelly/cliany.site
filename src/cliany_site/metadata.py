import json
from pathlib import Path
from typing import Any, cast


class LegacyMetadataError(Exception):
    """旧版 metadata（无 schema_version 或 v1）"""


class MetadataParseError(Exception):
    """metadata.json 解析失败（JSON 语法错误、IO 错误等）"""


def load_metadata(path: str | Path) -> dict:
    """
    加载并验证 metadata.json。
    - 仅接受 schema_version == 2（整数）
    - 缺 schema_version 或值为 1 → 抛 LegacyMetadataError
    - JSON 解析失败 → 抛 MetadataParseError
    - 返回原始 dict（不做 jsonschema 全量验证，验证由 verify 命令负责）
    """
    try:
        with open(path, encoding='utf-8') as f:
            metadata = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise MetadataParseError(f"Failed to parse metadata.json: {e}") from e

    schema_version = metadata.get("schema_version")
    # 接受整数 2；缺字段、字符串 "1"、整数 1 均视为旧版
    if schema_version is None or schema_version in (1, "1", ""):
        raise LegacyMetadataError(f"Legacy metadata schema version: {schema_version}")

    if schema_version != 2:
        raise MetadataParseError(f"Unsupported schema version: {schema_version}")

    return cast(dict[str, Any], metadata)

