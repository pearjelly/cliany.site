import json


def success_response(data: dict) -> dict:
    return {"success": True, "data": data, "error": None}


def error_response(code: str, message: str, fix: str | None = None) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message, "fix": fix},
    }


def print_response(
    response: dict,
    json_mode: bool = True,
    exit_on_error: bool = True,
    compact: bool = False,
) -> None:
    # Support both old response format and new envelope format
    is_envelope = "ok" in response
    success = response.get("ok", response.get("success", False))
    
    if json_mode:
        if compact:
            print(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
        else:
            print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        # rich 输出模式（非 JSON）
        from rich.console import Console

        console = Console()
        if success:
            if is_envelope:
                data = response.get("data", "")
                console.print(f"[green]✓[/green] {data}")
            else:
                data = response.get("data", "")
                console.print(f"[green]✓[/green] {data}")
        else:
            if is_envelope:
                err = response.get("error", {})
                console.print(
                    f"[red]✗ {err.get('code', 'ERROR')}[/red]: {err.get('message', '')}"
                )
                if err.get("hint"):
                    console.print(f"[yellow]Hint:[/yellow] {err.get('hint')}")
            else:
                err = response.get("error", {})
                console.print(
                    f"[red]✗ {err.get('code', 'ERROR')}[/red]: {err.get('message', '')}"
                )
                if err.get("fix"):
                    console.print(f"[yellow]Fix:[/yellow] {err.get('fix')}")

    if exit_on_error and not success:
        raise SystemExit(1)


# 注意：以上函数已被 envelope.py 中的新统一 envelope 系统替代
# 为保持向后兼容性，这些函数继续保留，但新代码应使用 envelope.ok() 和 envelope.err()
