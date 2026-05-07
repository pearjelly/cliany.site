"""CapabilityRouter — API endpoint sniffing and action routing.

零外部依赖：仅使用 Python stdlib。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ApiEndpoint:
    url: str
    method: str
    status: int
    sample_response_keys: list[str]
    content_type: str


@dataclass
class RouteDecision:
    mode: str
    endpoint: ApiEndpoint | None
    reason: str


def sniff_api_endpoints(
    network_requests: list[dict],
    action_step: dict,
) -> list[ApiEndpoint]:
    """从 action_step 前后 ±2s 的网络请求中筛选 JSON XHR/fetch 请求。

    Args:
        network_requests: 网络请求列表，每个 dict 含 url/method/status/content_type/timestamp 等字段。
        action_step: 操作步骤 dict，须含 timestamp（unix 秒）字段。

    Returns:
        符合条件的 ApiEndpoint 列表。
    """
    step_ts: float = float(action_step.get("timestamp", 0))
    results: list[ApiEndpoint] = []

    for req in network_requests:
        try:
            req_ts = float(req.get("timestamp", 0))
        except (TypeError, ValueError):
            continue

        if abs(req_ts - step_ts) > 2.0:
            continue

        content_type: str = req.get("content_type", "") or ""
        mime: str = req.get("mime", "") or ""
        if "json" not in content_type and "json" not in mime:
            continue

        sample_keys: list[str] = req.get("response_keys") or []

        results.append(
            ApiEndpoint(
                url=req.get("url", ""),
                method=req.get("method", "GET"),
                status=int(req.get("status", 0)),
                sample_response_keys=list(sample_keys),
                content_type=content_type,
            )
        )

    return results


def route_action(
    action: dict,
    endpoints: list[ApiEndpoint],
    force_browser: bool = False,
) -> RouteDecision:
    """根据探测到的 API 端点决定走 API 还是浏览器模式。

    Args:
        action: 操作步骤 dict（当前逻辑中未直接使用，留给扩展）。
        endpoints: sniff_api_endpoints 返回的列表。
        force_browser: 强制使用浏览器模式。

    Returns:
        RouteDecision，mode 仅为 "api" 或 "browser"。
    """
    if force_browser:
        return RouteDecision(mode="browser", endpoint=None, reason="force_browser")

    if not endpoints:
        return RouteDecision(mode="browser", endpoint=None, reason="no_endpoints")

    return RouteDecision(mode="api", endpoint=endpoints[0], reason="json_xhr_detected")
