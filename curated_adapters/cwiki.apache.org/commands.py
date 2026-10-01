"""Read-only keyword search for the public ASF Confluence wiki."""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

import click

from cliany_site.envelope import ErrorCode, err, ok
from cliany_site.response import print_response

DOMAIN = "cwiki.apache.org"
BASE_URL = "https://cwiki.apache.org"
SEARCH_URL = f"{BASE_URL}/confluence/rest/api/search"
COMMAND = f"{DOMAIN} search-pages"


@click.group()
def cli() -> None:
    """ASF Confluence read-only commands."""


def _json_mode(local: bool | None) -> bool:
    if local is not None:
        return local
    obj = click.get_current_context().find_root().obj
    return bool(obj.get("json_mode")) if isinstance(obj, dict) else False


def _cql_literal(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _page_url(item: dict) -> str:
    content = item.get("content")
    if not isinstance(content, dict):
        return ""
    path = content.get("url")
    if not isinstance(path, str) or not path.startswith("/") or path.startswith("//"):
        links = content.get("_links")
        webui = links.get("webui") if isinstance(links, dict) else None
        path = f"/confluence{webui}" if isinstance(webui, str) and webui.startswith("/") else ""
    return urllib.parse.urljoin(BASE_URL, path) if path else ""


@cli.command("search-pages")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.option("--space", default="SPARK", show_default=True, help="Confluence 空间 key")
@click.option("--query", default="", help="页面关键词")
@click.option("--limit", type=click.IntRange(1, 50), default=10, show_default=True)
def search_pages(json_mode: bool | None, space: str, query: str, limit: int) -> None:
    """按关键词搜索公开页面；不需要登录，也不会修改页面。"""
    output_json = _json_mode(json_mode)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", space):
        print_response(
            err(COMMAND, ErrorCode.E_INVALID_PARAM, "空间 key 无效", source="adapter"), output_json
        )
        return
    if len(query) > 200 or any(ord(char) < 32 and char not in "\t\n\r" for char in query):
        print_response(
            err(COMMAND, ErrorCode.E_INVALID_PARAM, "关键词无效或超过 200 字符", source="adapter"),
            output_json,
        )
        return

    normalized_query = " ".join(query.split())
    cql = f"space={_cql_literal(space)} AND type=page"
    if normalized_query:
        cql += f" AND siteSearch~{_cql_literal(normalized_query)}"
    url = f"{SEARCH_URL}?{urllib.parse.urlencode({'cql': cql, 'limit': limit})}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print_response(
            err(
                COMMAND,
                ErrorCode.E_PAGE_NOT_READY,
                "Confluence 搜索服务暂不可用",
                details={"reason": type(exc).__name__},
                source="adapter",
            ),
            output_json,
        )
        return
    except (ValueError, UnicodeDecodeError):
        print_response(
            err(COMMAND, ErrorCode.E_PARSE_FAILED, "Confluence 返回了无法解析的数据", source="adapter"),
            output_json,
        )
        return

    if not isinstance(body, dict) or not isinstance(body.get("results"), list):
        print_response(
            err(COMMAND, ErrorCode.E_PARSE_FAILED, "Confluence 搜索结果格式异常", source="adapter"),
            output_json,
        )
        return
    pages = []
    for item in body["results"]:
        if not isinstance(item, dict) or not isinstance(item.get("content"), dict):
            continue
        content = item["content"]
        title = content.get("title")
        page_url = _page_url(item)
        if not isinstance(title, str) or not title or not page_url:
            continue
        pages.append({"id": str(content.get("id", "")), "title": title, "url": page_url, "space": space})
    if body["results"] and not pages:
        print_response(
            err(COMMAND, ErrorCode.E_PARSE_FAILED, "Confluence 返回了无法使用的页面结果", source="adapter"),
            output_json,
        )
        return
    print_response(
        ok(
            COMMAND,
            {"space": space, "query": normalized_query, "count": len(pages), "results": pages},
            source="adapter",
        ),
        output_json,
    )
