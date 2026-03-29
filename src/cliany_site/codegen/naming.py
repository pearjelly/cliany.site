"""命名转换和文本清洗工具函数。

提供 Click 命令名、Python 函数名、参数名的规范化转换，
以及行内文本 / docstring 文本的安全清洗。
"""

from __future__ import annotations

import re


def to_command_name(name: str, index: int) -> str:
    """将原始名称转换为 Click 命令名（小写、连字符分隔）。"""
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", (name or "").strip().lower())
    normalized = re.sub(r"[_-]+", "-", normalized).strip("-")
    if not normalized:
        return f"command-{index + 1}"
    if normalized[0].isdigit():
        normalized = f"cmd-{normalized}"
    return normalized


def to_function_name(command_name: str) -> str:
    """将 Click 命令名转换为合法的 Python 函数名。"""
    function_name = command_name.replace("-", "_")
    function_name = re.sub(r"[^a-zA-Z0-9_]", "_", function_name)
    function_name = re.sub(r"_+", "_", function_name).strip("_")
    if not function_name:
        return "generated_command"
    if function_name[0].isdigit():
        return f"cmd_{function_name}"
    return function_name


def to_parameter_name(raw_name: str) -> str:
    """将原始参数名转换为合法的 Python 标识符。"""
    parameter_name = raw_name.replace("-", "_")
    parameter_name = re.sub(r"[^a-zA-Z0-9_]", "_", parameter_name)
    parameter_name = re.sub(r"_+", "_", parameter_name).strip("_")
    if not parameter_name:
        parameter_name = "arg"
    if parameter_name[0].isdigit():
        parameter_name = f"arg_{parameter_name}"
    return parameter_name


def unique_parameter_name(base_name: str, used_names: set[str]) -> str:
    """在已有名称集合中生成唯一的参数名。"""
    if base_name not in used_names:
        return base_name
    index = 2
    while f"{base_name}_{index}" in used_names:
        index += 1
    return f"{base_name}_{index}"


def sanitize_inline_text(value: str) -> str:
    """清洗行内文本：去除换行、首尾空白。"""
    return str(value or "").replace("\n", " ").replace("\r", " ").strip()


def sanitize_docstring_text(value: str) -> str:
    """清洗 docstring 文本：去除换行 + 转义三引号。"""
    return sanitize_inline_text(value).replace('"""', '\\"\\"\\"')


__all__ = [
    "to_command_name",
    "to_function_name",
    "to_parameter_name",
    "unique_parameter_name",
    "sanitize_inline_text",
    "sanitize_docstring_text",
]
