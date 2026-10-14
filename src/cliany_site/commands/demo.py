"""Run a published, read-only case through its declared first-result path."""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from typing import Any, cast

import click

from cliany_site.case_results import check_case_rows
from cliany_site.commands.cases import _active_case_quickstart_commands, _load_cases_manifest
from cliany_site.config import get_config
from cliany_site.envelope import Envelope, ErrorCode, err, ok
from cliany_site.response import print_response


def _command_argv(command: str, prefix: list[str]) -> list[str]:
    parts = shlex.split(command)
    if parts[:len(prefix)] != prefix or "--json" not in parts:
        raise ValueError("案例命令不符合只读首跑契约")
    return [sys.executable, "-m", "cliany_site", *parts[1:]]


def _step_failure(
    code: str, message: str, reason: str, returncode: int | None = None,
) -> tuple[bool, dict[str, Any]]:
    details: dict[str, Any] = {"reason": reason}
    if reason == "timeout":
        details["timeout_seconds"] = 90
    if returncode is not None:
        details["returncode"] = returncode
    return False, cast(dict[str, Any], err("demo step", code, message, details=details))


def _run_step(argv: list[str]) -> tuple[bool, dict[str, Any] | None]:
    try:
        env = {**os.environ, "CLIANY_RUNTIME_HOME": str(get_config().home_dir.resolve()),
               "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        completed = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", timeout=90, check=False, env=env,
        )
    except subprocess.TimeoutExpired:
        return _step_failure(ErrorCode.E_TIMEOUT, "首跑子命令超过 90 秒；未继续后续步骤", "timeout")
    except OSError:
        return _step_failure(ErrorCode.E_UNKNOWN, "首跑子命令无法启动或读取；检查本机 Python 环境", "start_failed")
    except UnicodeError:
        return _step_failure(ErrorCode.E_PARSE_FAILED, "首跑子命令输出不是有效 UTF-8；未读取业务结果", "invalid_utf8")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return _step_failure(ErrorCode.E_PARSE_FAILED, "首跑子命令未返回有效 JSON；不要把日志当作结果",
                             "invalid_json", completed.returncode)
    if not isinstance(payload, dict):
        return _step_failure(ErrorCode.E_PARSE_FAILED, "首跑子命令未返回 JSON 对象信封；未读取业务结果",
                             "invalid_envelope", completed.returncode)
    succeeded = payload.get("ok", payload.get("success")) is True
    return completed.returncode == 0 and succeeded, payload


def _check_rows(payload: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    expected = validation.get("expected_rows")
    if not isinstance(expected, dict):
        raise ValueError("案例缺少结果行数验收定义")
    minimum = expected.get("min_count")
    if type(minimum) is not int or minimum < 1:
        raise ValueError("案例结果行数验收定义无效")
    if "required_fields" not in expected:
        raise ValueError("案例缺少有效的非空文本字段验收定义")
    return check_case_rows(payload, expected)


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
        _check_rows({}, validation)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return err("demo", ErrorCode.E_INVALID_PARAM, str(exc),
                   hint="运行 cliany-site cases --status active 查看可用案例")

    target = get_config().adapters_dir / domain
    installed = target.exists() or target.is_symlink()
    if not installed:
        passed, payload = _run_step(install_argv)
        if not passed:
            return err("demo", ErrorCode.E_DOWNLOAD_FAILED, "固定哈希 adapter 安装失败；未执行查询",
                       hint="检查 GitHub 发布资产是否可达；不要移除 --sha256 或使用 --force 跳过校验",
                       details={"stage": "install", "upstream_error": (payload or {}).get("error")})
    passed, payload = _run_step(verify_argv)
    if not passed:
        return err("demo", ErrorCode.E_VERIFY_STATIC, "严格验证失败；未执行查询",
                   hint=f"运行 cliany-site verify {domain} --strict --json 查看诊断；不会覆盖已有 adapter",
                   details={"stage": "verify", "upstream_error": (payload or {}).get("error")})
    passed, payload = _run_step(query_argv)
    if not passed or payload is None:
        return err("demo", ErrorCode.E_UNKNOWN, "只读查询失败",
                   hint=f"检查公开 {domain} 服务是否可达，稍后重试；安装和校验不会因此重做",
                   details={"stage": "query", "upstream_error": (payload or {}).get("error")})
    row_check = _check_rows(payload, validation)
    row_count, minimum = row_check.get("row_count") or 0, row_check["min_count"]
    invalid_fields = row_check.get("field_invalid_rows")
    if not row_check["ok"]:
        details: dict[str, Any] = {"stage": "oracle", "row_count": row_count, "min_count": minimum}
        if invalid_fields:
            details["field_invalid_rows"] = invalid_fields
        message = "只读查询含缺失、空白或非文本的关键字段" if invalid_fields else "只读查询未达到案例结果门槛"
        hint = (f"检查 {domain} 返回内容和错误行号；关键字段未通过，不能当作业务成功" if invalid_fields
                else f"查询成功但没有足够的结果；检查 {domain} 返回内容和案例条件")
        return err("demo", ErrorCode.E_EMPTY_RESULT, message,
                   hint=hint, details=details)
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
    result = run_demo(case_id)
    if effective_json or not result.get("ok"):
        print_response(result, json_mode=effective_json)
        return
    data = cast(dict[str, Any], result["data"])
    click.echo(f"✓ {data['case_id']}: {data['row_count']} 条结果")
    query_data = data["result"].get("data")
    for rows_key, id_key, title_key in (("issues", "key", "summary"), ("results", "id", "title")):
        rows = query_data.get(rows_key) if isinstance(query_data, dict) else None
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    identifier = json.dumps(str(row.get(id_key, "")), ensure_ascii=False)
                    title = json.dumps(str(row.get(title_key, "")), ensure_ascii=False)
                    click.echo(f"  {identifier}  {title}")
            break
