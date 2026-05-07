import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

def _get_attr_or_dict(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

@dataclass
class ConsoleCapture:
    entries: List[Dict[str, Any]] = field(default_factory=list)
    truncated: bool = False
    _enabled: bool = True

    def _add_entry(self, entry: Dict[str, Any]) -> None:
        if not self._enabled:
            return
            
        self.entries.append(entry)
        if len(self.entries) > 500:
            self.entries.pop(0)
            self.truncated = True

    def _on_event(self, event_name: str, event: Any) -> None:
        if not self._enabled:
            return
            
        if event_name == "Runtime.consoleAPICalled":
            # level=args.type, text=args.args[0].value, source=stackTrace 第一帧 url（无则 ""）
            level = _get_attr_or_dict(event, "type", "log")
            
            args = _get_attr_or_dict(event, "args", [])
            text = ""
            if args and len(args) > 0:
                first_arg = args[0]
                text = str(_get_attr_or_dict(first_arg, "value", ""))
                
            source = ""
            stack_trace = _get_attr_or_dict(event, "stackTrace")
            if stack_trace:
                call_frames = _get_attr_or_dict(stack_trace, "callFrames", [])
                if call_frames and len(call_frames) > 0:
                    source = _get_attr_or_dict(call_frames[0], "url", "")
                    
            timestamp = _get_attr_or_dict(event, "timestamp", time.time())
            
            self._add_entry({
                "level": level,
                "text": text,
                "timestamp": timestamp,
                "source": source
            })
            
        elif event_name == "Log.entryAdded":
            # Log.entryAdded：level=entry.level, text=entry.text, source=entry.url or ""
            entry = _get_attr_or_dict(event, "entry")
            if not entry:
                return
                
            level = _get_attr_or_dict(entry, "level", "info")
            text = _get_attr_or_dict(entry, "text", "")
            source = _get_attr_or_dict(entry, "url", "")
            timestamp = _get_attr_or_dict(entry, "timestamp", time.time())
            
            self._add_entry({
                "level": level,
                "text": text,
                "timestamp": timestamp,
                "source": source
            })
            
        elif event_name == "Runtime.exceptionThrown":
            # Runtime.exceptionThrown：level="error", text=exception message, source=exception.scriptId or ""
            timestamp = _get_attr_or_dict(event, "timestamp", time.time())
            
            details = _get_attr_or_dict(event, "exceptionDetails")
            if not details:
                exception = _get_attr_or_dict(event, "exception")
                if exception:
                    text = _get_attr_or_dict(exception, "message", "Exception")
                    source = _get_attr_or_dict(exception, "scriptId", "")
                else:
                    return
            else:
                exception = _get_attr_or_dict(details, "exception")
                if exception:
                    text = _get_attr_or_dict(exception, "message", _get_attr_or_dict(exception, "description", ""))
                else:
                    text = _get_attr_or_dict(details, "text", "Exception")
                    
                source = _get_attr_or_dict(details, "scriptId", _get_attr_or_dict(details, "url", ""))
                if not source and exception:
                    source = _get_attr_or_dict(exception, "scriptId", "")
                
            self._add_entry({
                "level": "error",
                "text": text,
                "timestamp": timestamp,
                "source": source
            })

def start_console_capture(session: Any) -> ConsoleCapture:
    enabled_env = os.environ.get("CLIANY_CAPTURE_CONSOLE", "1")
    if enabled_env == "0":
        return ConsoleCapture(_enabled=False)
        
    capture = ConsoleCapture()
    
    if hasattr(session, "cdp_client"):
        client = getattr(session, "cdp_client")
        if hasattr(client, "on"):
            client.on("Runtime.consoleAPICalled", lambda e: capture._on_event("Runtime.consoleAPICalled", e))
            client.on("Log.entryAdded", lambda e: capture._on_event("Log.entryAdded", e))
            client.on("Runtime.exceptionThrown", lambda e: capture._on_event("Runtime.exceptionThrown", e))
            
    return capture

def stop_console_capture(capture: ConsoleCapture) -> Dict[str, Any]:
    return {
        "entries": capture.entries,
        "truncated": capture.truncated,
        "count": len(capture.entries)
    }
