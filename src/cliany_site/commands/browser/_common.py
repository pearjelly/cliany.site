"""browser 命令共享工具"""
from __future__ import annotations

import json
from typing import Any

import click

from cliany_site.envelope import Envelope


def resolve_ref(selector_map: dict, ref: str) -> Any | None:
    """从 selector_map 查找 ref；不存在返回 None"""
    return selector_map.get(str(ref))


def fuzzy_find_by_text(selector_map: dict, text: str, limit: int = 5) -> list[dict]:
    """按文本模糊查找元素，返回 [{ref, role, name, score, snippet}]"""
    text_lower = text.lower()
    results: list[dict] = []
    for ref_id, element in selector_map.items():
        name = element.get("name", "")
        if text_lower in name.lower():
            exact = text_lower == name.lower()
            results.append(
                {
                    "ref": str(ref_id),
                    "role": element.get("role", "unknown"),
                    "name": name,
                    "score": 1.0 if exact else 0.5,
                    "snippet": name[:80],
                }
            )
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def print_envelope(result: Envelope, json_mode: bool) -> None:
    """统一输出 envelope（供各子命令复用）"""
    if json_mode:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        data = result.get("data")
        click.echo(f"✓ {result.get('command', '')}  {data}")
    else:
        error_info = result.get("error")
        error_code = error_info.get("code", "ERROR") if error_info else "ERROR"
        error_msg = error_info.get("message", "") if error_info else ""
        click.echo(
            f"✗ {error_code}: {error_msg}",
            err=True,
        )
