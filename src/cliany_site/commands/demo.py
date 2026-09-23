"""Run a published, read-only case through its declared first-result path."""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from typing import Any

import click

from cliany_site.commands.cases import _active_case_quickstart_commands, _load_cases_manifest
from cliany_site.config import get_config
from cliany_site.envelope import Envelope, ErrorCode, err, ok
from cliany_site.response import print_response


def _command_argv(command: str, prefix: list[str]) -> list[str]:
    parts = shlex.split(command)
    if parts[:len(prefix)] != prefix or "--json" not in parts:
        raise ValueError("案例命令不符合只读首跑契约")
    return [sys.executable, "-m", "cliany_site", *parts[1:]]


def _run_step(argv: list[str]) -> tuple[bool, dict[str, Any] | None]:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=90, check=False)
        payload = json.loads(completed.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return False, None
    if not isinstance(payload, dict):
        return False, None
    succeeded = payload.get("ok", payload.get("success")) is True
    return completed.returncode == 0 and succeeded, payload


def _row_count(payload: dict[str, Any], validation: dict[str, Any]) -> tuple[int, int]:
    expected = validation.get("expected_rows")
    if not isinstance(expected, dict):
        raise ValueError("案例缺少结果行数验收定义")
    path, minimum = expected.get("path"), expected.get("min_count")
    if (not isinstance(path, list) or not path or not all(isinstance(key, str) and key for key in path)
            or type(minimum) is not int or minimum < 1):
        raise ValueError("案例结果行数验收定义无效")
    rows: Any = payload
    for key in path:
        rows = rows.get(key) if isinstance(rows, dict) else None
    if not isinstance(rows, list) or not all(isinstance(row, dict) and row for row in rows):
        return 0, minimum
    return len(rows), minimum


def run_demo(case_id: str) -> Envelope:
    try:
        cases, source, _ = _load_cases_manifest()
        if source is None:
            raise ValueError("未找到内置案例索引")
        case = next((item for item in cases if item.get("id") == case_id), None)
        if case is None or case.get("status") != "active":
            raise ValueError("仅支持已发布的 active 案例")
        domain = case.get("adapter_domain")
        if not isinstance(domain, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", domain):
            raise ValueError("案例 adapter_domain 无效")
        validation = case.get("validation")
        if not isinstance(validation, dict) or "read-only" not in str(validation.get("online", "")).lower():
            raise ValueError("案例未声明只读在线验收")
        raw_commands = case.get("commands")
        if not isinstance(raw_commands, list) or any(
            isinstance(command, str) and command.startswith("cliany-site login ") for command in raw_commands
        ):
            raise ValueError("需要登录的案例不支持一键首跑")
        commands = _active_case_quickstart_commands(case)
        if len(commands) != 3:
            raise ValueError("案例缺少固定哈希安装或只读命令")
        install, verify, query = commands
        install_argv = _command_argv(install + " --json", ["cliany-site", "market", "install"])
        verify_argv = _command_argv(verify, ["cliany-site", "verify", domain, "--strict"])
        query_argv = _command_argv(query, ["cliany-site", domain])
        _row_count({}, validation)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return err("demo", ErrorCode.E_INVALID_PARAM, str(exc))

    target = get_config().adapters_dir / domain
    installed = target.exists() or target.is_symlink()
    if not installed:
        passed, payload = _run_step(install_argv)
        if not passed:
            return err("demo", ErrorCode.E_DOWNLOAD_FAILED, "固定哈希 adapter 安装失败；未执行查询",
                       details={"stage": "install", "upstream_error": (payload or {}).get("error")})
    passed, payload = _run_step(verify_argv)
    if not passed:
        return err("demo", ErrorCode.E_VERIFY_STATIC, "严格验证失败；未执行查询",
                   details={"stage": "verify", "upstream_error": (payload or {}).get("error")})
    passed, payload = _run_step(query_argv)
    if not passed or payload is None:
        return err("demo", ErrorCode.E_UNKNOWN, "只读查询失败",
                   details={"stage": "query", "upstream_error": (payload or {}).get("error")})
    row_count, minimum = _row_count(payload, validation)
    if row_count < minimum:
        return err("demo", ErrorCode.E_EMPTY_RESULT, "只读查询未达到案例结果门槛",
                   details={"stage": "oracle", "row_count": row_count, "min_count": minimum})
    return ok("demo", {"case_id": case_id, "adapter_domain": domain, "installed_now": not installed,
                       "row_count": row_count, "result": payload})


@click.command("demo")
@click.option("--case-id", required=True, help="已发布且无需登录的只读案例 ID")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
def demo_cmd(ctx: click.Context, case_id: str, json_mode: bool | None) -> None:
    """安装、严格验证并运行一个公开只读案例。"""
    root_obj = ctx.find_root().obj if isinstance(ctx.find_root().obj, dict) else {}
    effective_json = json_mode if json_mode is not None else bool(root_obj.get("json_mode"))
    print_response(run_demo(case_id), json_mode=effective_json)
