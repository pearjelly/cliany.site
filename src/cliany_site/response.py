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
    if json_mode:
        if compact:
            print(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
        else:
            print(json.dumps(response, ensure_ascii=False, indent=2))
    else:
        # rich 输出模式（非 JSON）
        from rich.console import Console

        console = Console()
        if response["success"]:
            console.print(f"[green]✓[/green] {response.get('data', '')}")
        else:
            err = response.get("error", {})
            console.print(
                f"[red]✗ {err.get('code', 'ERROR')}[/red]: {err.get('message', '')}"
            )
            if err.get("fix"):
                console.print(f"[yellow]Fix:[/yellow] {err.get('fix')}")

    if exit_on_error and not response.get("success", False):
        raise SystemExit(1)
