"""Read-only job listing for the public ASF Jenkins controller."""

import json
import urllib.error
import urllib.parse
import urllib.request

import click

from cliany_site.envelope import ErrorCode, err, ok
from cliany_site.response import print_response

DOMAIN = "builds.apache.org"
COMMAND = f"{DOMAIN} list-jobs"
API_URL = "https://ci-builds.apache.org/api/json?tree=jobs%5Bname%2Curl%2Ccolor%5D"
ALLOWED_HOSTS = {"builds.apache.org", "ci-builds.apache.org"}


@click.group()
def cli() -> None:
    """ASF Jenkins read-only commands."""


def _json_mode(local: bool | None) -> bool:
    if local is not None:
        return local
    obj = click.get_current_context().find_root().obj
    return bool(obj.get("json_mode")) if isinstance(obj, dict) else False


def _public_job_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    try:
        parsed = urllib.parse.urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return ""
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS or port not in (None, 443):
        return ""
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return ""
    return value


@cli.command("list-jobs")
@click.option("--limit", type=click.IntRange(1, 100), default=20, show_default=True)
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
def list_jobs(limit: int, json_mode: bool | None) -> None:
    """列出 ASF Jenkins 的公开顶层 job 和文件夹。"""
    output_json = _json_mode(json_mode)
    request = urllib.request.Request(API_URL, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print_response(
            err(
                COMMAND,
                ErrorCode.E_PAGE_NOT_READY,
                "ASF Jenkins 暂不可用",
                details={"reason": type(exc).__name__},
                source="adapter",
            ),
            output_json,
        )
        return
    except (ValueError, UnicodeDecodeError):
        print_response(
            err(COMMAND, ErrorCode.E_PARSE_FAILED, "Jenkins 返回了无法解析的数据", source="adapter"),
            output_json,
        )
        return

    if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
        print_response(
            err(COMMAND, ErrorCode.E_PARSE_FAILED, "Jenkins job 列表格式异常", source="adapter"),
            output_json,
        )
        return
    jobs = []
    for item in body["jobs"][:limit]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"]:
            continue
        url = _public_job_url(item.get("url"))
        if not url:
            continue
        jobs.append({"name": item["name"], "url": url, "color": item.get("color")})
    if body["jobs"] and not jobs:
        print_response(
            err(COMMAND, ErrorCode.E_PARSE_FAILED, "Jenkins 返回了无法使用的 job 条目", source="adapter"),
            output_json,
        )
        return
    print_response(
        ok(COMMAND, {"jobs": jobs, "count": len(jobs), "total": len(body["jobs"])}, source="adapter"),
        output_json,
    )
