import pytest
from cliany_site.browser.console_capture import (
    ConsoleCapture,
    start_console_capture,
    stop_console_capture
)

def test_console_capture_disabled(monkeypatch):
    monkeypatch.setenv("CLIANY_CAPTURE_CONSOLE", "0")
    
    class MockSession:
        pass
        
    capture = start_console_capture(MockSession())
    assert not capture._enabled
    
    capture._add_entry({"level": "log", "text": "ignored", "timestamp": 123, "source": ""})
    assert len(capture.entries) == 0
    
    result = stop_console_capture(capture)
    assert result["count"] == 0
    assert result["truncated"] is False

def test_console_capture_enabled():
    class MockSession:
        pass
        
    capture = start_console_capture(MockSession())
    assert capture._enabled
    
    capture._add_entry({"level": "info", "text": "hello", "timestamp": 1.0, "source": "app.js"})
    result = stop_console_capture(capture)
    assert result["count"] == 1
    assert result["entries"][0]["text"] == "hello"

def test_console_capture_500_limit():
    capture = ConsoleCapture()
    
    for i in range(600):
        capture._add_entry({
            "level": "log",
            "text": f"msg {i}",
            "timestamp": 1.0 + i,
            "source": "loop"
        })
        
    result = stop_console_capture(capture)
    assert result["count"] == 500
    assert result["truncated"] is True
    assert result["entries"][0]["text"] == "msg 100"
    assert result["entries"][-1]["text"] == "msg 599"

def test_on_event_runtime_console_api_called():
    capture = ConsoleCapture()
    event = {
        "type": "warning",
        "args": [{"value": "Deprecated API"}],
        "stackTrace": {
            "callFrames": [{"url": "http://example.com/script.js"}]
        },
        "timestamp": 1234.5
    }
    
    capture._on_event("Runtime.consoleAPICalled", event)
    
    assert len(capture.entries) == 1
    assert capture.entries[0] == {
        "level": "warning",
        "text": "Deprecated API",
        "timestamp": 1234.5,
        "source": "http://example.com/script.js"
    }

def test_on_event_log_entry_added():
    capture = ConsoleCapture()
    event = {
        "entry": {
            "level": "error",
            "text": "Network failed",
            "url": "http://example.com/api",
            "timestamp": 1234.6
        }
    }
    
    capture._on_event("Log.entryAdded", event)
    
    assert len(capture.entries) == 1
    assert capture.entries[0] == {
        "level": "error",
        "text": "Network failed",
        "timestamp": 1234.6,
        "source": "http://example.com/api"
    }

def test_on_event_runtime_exception_thrown():
    capture = ConsoleCapture()
    event = {
        "timestamp": 1234.7,
        "exceptionDetails": {
            "exception": {
                "message": "Uncaught SyntaxError",
                "description": "Uncaught SyntaxError: Unexpected token"
            },
            "scriptId": "123",
            "url": "http://example.com/bad.js"
        }
    }
    
    capture._on_event("Runtime.exceptionThrown", event)
    
    assert len(capture.entries) == 1
    assert capture.entries[0] == {
        "level": "error",
        "text": "Uncaught SyntaxError",
        "timestamp": 1234.7,
        "source": "123"
    }
