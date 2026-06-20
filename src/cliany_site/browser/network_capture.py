import os
import time
from dataclasses import dataclass, field
from typing import Any

_SIZE_CAP = 1_048_576  # 1 MB hard limit — not configurable


def _get_attr_or_dict(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@dataclass
class NetworkCapture:
    requests: list[dict[str, Any]] = field(default_factory=list)
    truncated: bool = False
    total_size: int = 0
    _enabled: bool = True

    def _add_request(self, entry: dict[str, Any]) -> None:
        if not self._enabled or self.truncated:
            return

        entry_size = int(entry.get("size", 0))
        if self.total_size + entry_size > _SIZE_CAP:
            self.truncated = True
            return

        self.requests.append(entry)
        self.total_size += entry_size

    def _on_event(self, event_name: str, event: Any) -> None:
        if not self._enabled or self.truncated:
            return

        if event_name == "Network.responseReceived":
            response = _get_attr_or_dict(event, "response")
            if not response:
                return

            url = _get_attr_or_dict(response, "url", "")
            method_val = _get_attr_or_dict(event, "method", "")
            if not method_val:
                req_obj = _get_attr_or_dict(event, "request")
                if req_obj:
                    method_val = _get_attr_or_dict(req_obj, "method", "")

            status = int(_get_attr_or_dict(response, "status", 0))
            mime = _get_attr_or_dict(response, "mimeType", "")
            size = int(_get_attr_or_dict(response, "encodedDataLength", 0))
            timestamp = float(_get_attr_or_dict(event, "timestamp", time.time()))

            self._add_request({
                "url": url,
                "method": method_val,
                "status": status,
                "mime": mime,
                "size": size,
                "timestamp": timestamp,
            })

        elif event_name == "Network.loadingFailed":
            request = _get_attr_or_dict(event, "request")
            url = ""
            method_val = ""
            if request:
                url = _get_attr_or_dict(request, "url", "")
                method_val = _get_attr_or_dict(request, "method", "")

            timestamp = float(_get_attr_or_dict(event, "timestamp", time.time()))

            self._add_request({
                "url": url,
                "method": method_val,
                "status": -1,
                "mime": "",
                "size": 0,
                "timestamp": timestamp,
            })


def start_network_capture(session: Any) -> NetworkCapture:
    enabled_env = os.environ.get("CLIANY_CAPTURE_NETWORK", "1")
    if enabled_env == "0":
        return NetworkCapture(_enabled=False)

    capture = NetworkCapture()

    if hasattr(session, "cdp_client"):
        client = session.cdp_client
        if hasattr(client, "on"):
            client.on(
                "Network.responseReceived",
                lambda e: capture._on_event("Network.responseReceived", e),
            )
            client.on(
                "Network.loadingFailed",
                lambda e: capture._on_event("Network.loadingFailed", e),
            )

    return capture


def stop_network_capture(capture: NetworkCapture) -> dict[str, Any]:
    return {
        "requests": capture.requests,
        "truncated": capture.truncated,
        "total_size": capture.total_size,
        "count": len(capture.requests),
    }
