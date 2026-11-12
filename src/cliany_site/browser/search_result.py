"""Query-bound evidence for an explicitly declared empty search result."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from cliany_site.browser.selector import MAIN_RESULT_LIST_BOUNDARY, MAIN_RESULT_LIST_ROOT

EMPTY_SEARCH_ROOT = "main"
_QUERY_PLACEHOLDER = re.compile(r"\{\{\w+\}\}")
_RECIPE_KEYS = frozenset({"page", "parameter", "heading_prefix", "heading_suffix", "message", "query"})


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _page_identity(url: str) -> tuple[str, list[tuple[str, str]]] | None:
    try:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None:
            return None
        # Validate the port before treating the origin as observed evidence.
        _ = parts.port
        query = parse_qsl(parts.query, keep_blank_values=True, max_num_fields=64)
    except ValueError:
        return None
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", "", "")), query


def valid_empty_result_recipe(recipe: Any, *, bound: bool = False) -> bool:
    if not isinstance(recipe, dict) or set(recipe) != _RECIPE_KEYS:
        return False
    if any(not isinstance(value, str) or len(value) > 512 for value in recipe.values()):
        return False
    identity = _page_identity(recipe["page"])
    return bool(
        identity is not None and identity[0] == recipe["page"] and not identity[1]
        and recipe["parameter"].strip() and _normalized(recipe["query"])
        and _normalized(recipe["heading_prefix"] + recipe["heading_suffix"])
        and 0 < len(recipe["message"]) <= 160 and _normalized(recipe["message"]) == recipe["message"]
        and (not bound or not _QUERY_PLACEHOLDER.fullmatch(recipe["query"]))
    )


def ground_empty_result_recipe(
    start_url: str, result_url: str, heading: str, typed_value: str, binding: str, message: str,
) -> dict[str, str] | None:
    start, observed = _page_identity(start_url), _page_identity(result_url)
    normalized_query = _normalized(typed_value)
    if start is None or observed is None or not normalized_query or not _QUERY_PLACEHOLDER.fullmatch(binding):
        return None
    start_parts, result_parts = urlsplit(start[0]), urlsplit(observed[0])
    if (start_parts.scheme, start_parts.netloc) != (result_parts.scheme, result_parts.netloc):
        return None
    keys = [key for key, value in observed[1] if value == typed_value]
    if len(keys) != 1 or any(key == keys[0] for key, _ in start[1]):
        return None
    if sum(key == keys[0] for key, _ in observed[1]) != 1 or heading.count(normalized_query) != 1:
        return None
    prefix, _, suffix = heading.partition(normalized_query)
    recipe = {
        "page": observed[0], "parameter": keys[0], "heading_prefix": prefix, "heading_suffix": suffix,
        "message": _normalized(message), "query": binding,
    }
    return recipe if valid_empty_result_recipe(recipe) else None


def observed_search_outcome(snapshot: dict[str, Any], recipe: dict[str, Any]) -> str | None:
    observed = _page_identity(str(snapshot.get("url") or ""))
    if observed is None or observed[0] != recipe["page"]:
        return None
    if [value for key, value in observed[1] if key == recipe["parameter"]] != [recipe["query"]]:
        return None
    context = snapshot.get("main_result_context") or {}
    expected_heading = _normalized(recipe["heading_prefix"] + _normalized(recipe["query"]) + recipe["heading_suffix"])
    if context.get("heading") != expected_heading or context.get("busy") is not False:
        return None
    messages = context.get("messages") or []
    if context.get("collections") == 0 and messages.count(recipe["message"]) == 1:
        return "empty"
    if context.get("collections") == 1 and recipe["message"] not in messages:
        return "rows"
    return None


def build_search_outcome_js(recipe: dict[str, Any]) -> str:
    """Repeat the query and outcome checks atomically on the live DOM before reading."""
    if not valid_empty_result_recipe(recipe, bound=True):
        return "() => null"
    return f"""() => {{
        const wanted = {json.dumps(recipe)};
        const url = new URL(location.href);
        const params = url.searchParams.getAll(wanted.parameter);
        if (url.origin + url.pathname !== wanted.page || params.length !== 1 || params[0] !== wanted.query) return null;
        const mains = document.querySelectorAll('main,[role="main"]');
        if (mains.length !== 1 || mains[0].tagName !== 'MAIN') return null;
        const main = mains[0];
        const norm = text => text.trim().replace(/\\s+/g, ' ');
        const hidden = e => {{
            const style = getComputedStyle(e);
            return !!e.closest('[hidden],[inert],[aria-hidden=true]') || style.display === 'none'
                || ['hidden','collapse'].includes(style.visibility) || style.opacity === '0';
        }};
        const visible = e => !hidden(e) && e.checkVisibility({{checkOpacity:true,checkVisibilityCSS:true}});
        const inScope = e => !e.closest({json.dumps(MAIN_RESULT_LIST_BOUNDARY)}) && visible(e);
        const select = selector => [...main.querySelectorAll(selector)].filter(inScope);
        const summaryText = root => {{
            let text = '';
            function visit(node) {{
                if (node.nodeType === Node.TEXT_NODE) text += node.nodeValue;
                if (node.nodeType !== Node.ELEMENT_NODE || hidden(node)) return true;
                if (node.matches('a,button,[role=link],[role=button]')) return false;
                for (const child of node.childNodes) if (!visit(child)) return false;
                return true;
            }}
            visit(root);
            return norm(text);
        }};
        const heading = level => `h${{level}}:not([role]):not([aria-level]),[role=heading][aria-level="${{level}}"],`
            + `h${{level}}[role=heading]:not([aria-level])`;
        const headings = select(heading(1));
        if (headings.length !== 1 || summaryText(headings[0]) !==
            norm(wanted.heading_prefix + norm(wanted.query) + wanted.heading_suffix)) return null;
        const messages = select(heading(2) + ',[role=status]').map(summaryText);
        const loading = new Set(['searching','loading','fetching','正在搜索','加载中']);
        if (main.getAttribute('aria-busy') === 'true' || select('[aria-busy=true],[role=progressbar],progress').length
            || messages.some(text => loading.has(text.toLowerCase().replace(/[. …]+$/g, '')))) return null;
        const collections = document.querySelectorAll({json.dumps(MAIN_RESULT_LIST_ROOT)});
        const markers = messages.filter(text => text === wanted.message).length;
        if (!collections.length && markers === 1) return {{kind:'empty', count:0}};
        if (collections.length !== 1 || markers) return null;
        const count = [...collections[0].children].filter(row => row.tagName === 'LI').length;
        return count ? {{kind:'rows', count}} : null;
    }}"""
