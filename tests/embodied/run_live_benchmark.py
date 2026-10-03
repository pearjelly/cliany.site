"""Opt-in fresh explore/replay trials against controlled local pages."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import urlparse

from cliany_site.codegen.naming import to_command_name

ROOT = Path(__file__).resolve().parents[2]
PAGES = Path(__file__).resolve().parent / "pages"
CASES = Path(__file__).with_name("explore_benchmark_cases.json")
CLI_ENTRY = Path(__file__).with_name("benchmark_cli.py")


@contextmanager
def _serve_pages():
    sequence = count(1)

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?", 1)[0] != "/semantic_reorder.html":
                return super().do_GET()
            page = (PAGES / "semantic_reorder.html").read_bytes()
            body = page.replace(b"__SHIFT__", str(next(sequence)).encode("ascii"))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=PAGES))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _contains_subsequence(actions: list[str], required: list[str]) -> bool:
    remaining = iter(actions)
    return all(any(action == wanted for action in remaining) for wanted in required)


def _select_command(metadata: dict[str, Any], case: dict[str, Any]) -> str:
    expected_args = set(case["replays"][0]["args"])
    matches: list[str] = []
    for index, command in enumerate(metadata.get("commands", [])):
        if not isinstance(command, dict):
            continue
        actions = [
            action["action_type"]
            for action in command.get("actions", [])
            if isinstance(action, dict) and isinstance(action.get("action_type"), str)
        ]
        args = {arg.get("name") for arg in command.get("args", []) if isinstance(arg, dict)}
        if _contains_subsequence(actions, case["required_actions"]) and expected_args <= args:
            matches.append(to_command_name(command["name"], index))
    if len(matches) != 1:
        raise ValueError(f"expected one command with required actions and args, found {len(matches)}")
    return matches[0]


def _command_summaries(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = []
    for command in metadata.get("commands", []):
        if not isinstance(command, dict):
            continue
        summaries.append({
            "name": command.get("name"),
            "args": [arg.get("name") for arg in command.get("args", []) if isinstance(arg, dict)],
            "actions": [action.get("action_type") for action in command.get("actions", []) if isinstance(action, dict)],
        })
    return summaries


def _extract_action_summaries(command: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "mode": str(action.get("extract_mode") or "")[:40],
            "selector": str(action.get("selector") or "")[:200],
        }
        for action in command.get("actions", [])
        if isinstance(action, dict) and action.get("action_type") == "extract"
    ]


def _extract_contents(payload: dict[str, Any]) -> list[Any]:
    data = payload.get("data")
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return []
    return [
        result["data"]["content"]
        for result in results
        if isinstance(result, dict)
        and result.get("command") == "browser extract"
        and result.get("ok") is True
        and isinstance(result.get("data"), dict)
        and "content" in result["data"]
    ]


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for child in value.values() for text in _text_values(child)]
    if isinstance(value, list):
        return [text for child in value for text in _text_values(child)]
    return []


def _matches_expected_extracts(contents: list[Any], replay: dict[str, Any]) -> bool:
    values = [text for content in contents for text in _text_values(content)]
    expected_text = replay.get("expected_text")
    if isinstance(expected_text, str) and expected_text not in values:
        return False
    expected_summary = replay.get("expected_summary")
    if isinstance(expected_summary, str) and expected_summary not in values:
        return False
    expected_rows = replay.get("expected_rows")
    if isinstance(expected_rows, list):
        if any(row not in values for row in expected_rows):
            return False
        if not expected_rows and not any(content == [] for content in contents):
            return False
    return bool(contents)


def _summarize_trials(trials: list[dict[str, Any]], task_ids: list[str]) -> dict[str, dict[str, int]]:
    return {
        task_id: {
            "successful": sum(bool(trial["ok"]) for trial in trials if trial["case_id"] == task_id),
            "total": sum(trial["case_id"] == task_id for trial in trials),
        }
        for task_id in task_ids
    }


async def _run_cli(runtime_home: Path, cli_args: list[str], timeout: int) -> tuple[dict[str, Any], float]:
    env = os.environ.copy()
    env["CLIANY_NO_AGENT_MD"] = "1"
    start = time.monotonic()
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(CLI_ENTRY),
        "--runtime-home",
        str(runtime_home),
        "--",
        *cli_args,
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError:
        process.kill()
        await process.communicate()
        return {"ok": False, "error": {"code": "BENCHMARK_TIMEOUT"}}, time.monotonic() - start
    elapsed = time.monotonic() - start
    try:
        payload = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "error": {"code": "INVALID_CLI_JSON"}}, elapsed
    if not isinstance(payload, dict) or process.returncode != 0 or payload.get("ok") is not True:
        error = payload.get("error") if isinstance(payload, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        return {"ok": False, "error": {"code": code or "CLI_FAILED"}}, elapsed
    return payload, elapsed


async def _inspect_page(playwright: Any, cdp_port: int, case: dict[str, Any], replay: dict[str, Any]) -> bool:
    browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
    try:
        pages = [
            page
            for context in browser.contexts
            for page in context.pages
            if urlparse(page.url).path == case["path"]
        ]
        if not pages:
            return False
        page = pages[-1]
        if case["id"] == "filter-catalog":
            return bool(
                await page.locator("#summary").text_content() == replay["expected_summary"]
                and await page.locator("#results li").all_text_contents() == replay["expected_rows"]
                and await page.locator("#results li").evaluate_all(
                    "rows => rows.map(row => row.dataset.code)"
                ) == replay["expected_codes"]
            )
        result = await page.locator("#result").text_content()
        if case["id"] == "semantic-reorder":
            return bool(
                result == replay["expected_text"]
                and await page.locator("#result").get_attribute("data-hits") == "1"
            )
        return bool(result == replay["expected_text"])
    finally:
        await browser.close()


async def _trial(playwright: Any, server_url: str, case: dict[str, Any], runtime_home: Path, index: int) -> dict:
    outcome: dict[str, Any] = {"case_id": case["id"], "trial": index, "ok": False, "phase": "explore"}
    url = f"{server_url}{case['path']}"
    port = _free_port()
    browser = await playwright.chromium.launch(headless=True, args=[f"--remote-debugging-port={port}"])
    try:
        explore, elapsed = await _run_cli(
            runtime_home,
            ["--cdp-url", f"ws://127.0.0.1:{port}", "explore", url, case["workflow"], "--no-record", "--json"],
            timeout=300,
        )
        outcome["explore_seconds"] = round(elapsed, 2)
    finally:
        await browser.close()
    if not explore.get("ok"):
        outcome["error_code"] = explore.get("error", {}).get("code")
        return outcome

    data = explore.get("data", {})
    group = data.get("command_group")
    if not isinstance(group, str) or not group:
        outcome.update(phase="generation", error_code="MISSING_COMMAND_GROUP")
        return outcome
    metadata: Any = None
    try:
        metadata = json.loads((runtime_home / "adapters" / group / "metadata.json").read_text(encoding="utf-8"))
        outcome["model"] = metadata.get("explore_model") or None
        command = _select_command(metadata, case)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        error_code = "COMMAND_CONTRACT" if isinstance(exc, ValueError) else type(exc).__name__
        outcome.update(phase="generation", error_code=error_code)
        if isinstance(metadata, dict):
            outcome["generated_commands"] = _command_summaries(metadata)
        return outcome

    outcome["command"] = command
    outcome["replays"] = []
    for replay in case["replays"]:
        port = _free_port()
        browser = await playwright.chromium.launch(headless=True, args=[f"--remote-debugging-port={port}"])
        try:
            cli_args = ["--cdp-url", f"ws://127.0.0.1:{port}", group, command]
            for name, value in replay["args"].items():
                cli_args.extend([f"--{name.replace('_', '-')}", str(value)])
            cli_args.append("--json")
            result, elapsed = await _run_cli(runtime_home, cli_args, timeout=120)
            row: dict[str, Any] = {"args": replay["args"], "seconds": round(elapsed, 2)}
            contents = _extract_contents(result)
            if not result.get("ok") or not contents:
                row.update(ok=False, phase="replay", error_code=result.get("error", {}).get("code") or "NO_EXTRACT")
            else:
                try:
                    oracle_ok = await _inspect_page(playwright, port, case, replay)
                except Exception as exc:
                    oracle_ok = False
                    row["error_code"] = type(exc).__name__
                output_ok = _matches_expected_extracts(contents, replay)
                row.update(
                    ok=oracle_ok and output_ok,
                    oracle_ok=oracle_ok,
                    output_ok=output_ok,
                    phase="oracle" if not oracle_ok else "output" if not output_ok else "complete",
                )
                if not output_ok:
                    row["error_code"] = "EXTRACT_MISMATCH"
            outcome["replays"].append(row)
        finally:
            await browser.close()
    outcome["ok"] = all(row["ok"] for row in outcome["replays"])
    outcome["phase"] = (
        "complete" if outcome["ok"] else next(row["phase"] for row in outcome["replays"] if not row["ok"])
    )
    return outcome


async def _run(args: argparse.Namespace, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    from playwright.async_api import async_playwright

    report: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(UTC).isoformat(),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "package_version": importlib.metadata.version("cliany-site"),
        "provider": os.getenv("CLIANY_LLM_PROVIDER", "resolved by cliany-site"),
        "browser_mode": "fresh headless Chromium via CDP for explore and each replay",
        "task_ids": [task["id"] for task in tasks],
        "trials_requested": args.trials,
        "trials": [],
    }
    with tempfile.TemporaryDirectory(prefix="cliany-explore-benchmark-") as temporary, _serve_pages() as server_url:
        runtime_root = Path(temporary)
        async with async_playwright() as playwright:
            port = _free_port()
            browser = await playwright.chromium.launch(headless=True, args=[f"--remote-debugging-port={port}"])
            try:
                preflight, elapsed = await _run_cli(
                    runtime_root / "preflight",
                    [
                        "--cdp-url", f"ws://127.0.0.1:{port}", "doctor", "--llm-live",
                        "--require-capability", "generate_adapters", "--json",
                    ],
                    timeout=120,
                )
                report["preflight"] = {"ok": preflight.get("ok") is True, "seconds": round(elapsed, 2)}
                if not preflight.get("ok"):
                    report["preflight"]["error_code"] = preflight.get("error", {}).get("code")
                    return report
            finally:
                await browser.close()
            for task in tasks:
                for index in range(1, args.trials + 1):
                    runtime_home = runtime_root / task["id"] / str(index)
                    report["trials"].append(await _trial(playwright, server_url, task, runtime_home, index))
    report["success_count"] = sum(trial["ok"] for trial in report["trials"])
    report["total_count"] = len(report["trials"])
    report["by_task"] = _summarize_trials(report["trials"], report["task_ids"])
    report["eligible_for_issue_acceptance"] = args.trials >= 3 and len(tasks) == 3
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live-llm", action="store_true", help="Acknowledge real provider calls and cost.")
    parser.add_argument("--case", action="append", help="Run one named task; omit to run all three.")
    parser.add_argument("--trials", type=int, default=3, help="Fresh explorations per task (default: 3).")
    parser.add_argument("--report", type=Path, required=True, help="JSON report path outside the repository.")
    args = parser.parse_args(argv)
    if not args.allow_live_llm or os.getenv("CLIANY_QA_OFFLINE") == "1" or os.getenv("CLIANY_QA_FAKE_LLM_RESPONSES"):
        parser.error("live LLM calls require --allow-live-llm and no offline/fake-LLM environment")
    if args.trials < 1:
        parser.error("--trials must be positive")
    if args.report.resolve().is_relative_to(ROOT):
        parser.error("--report must be outside the repository")
    spec = json.loads(CASES.read_text(encoding="utf-8"))
    tasks = [task for task in spec["tasks"] if not args.case or task["id"] in args.case]
    if not tasks or (args.case and len(tasks) != len(set(args.case))):
        parser.error("--case must name existing distinct tasks")
    try:
        report = asyncio.run(_run(args, tasks))
    except (OSError, RuntimeError, TimeoutError) as exc:
        report = {"schema_version": 1, "error": type(exc).__name__, "trials": [], "success_count": 0, "total_count": 0}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(args.report),
        "success_count": report.get("success_count", 0),
        "total_count": report.get("total_count", 0),
    }))
    return 0 if report.get("total_count", 0) > 0 and report.get("success_count") == report.get("total_count") else 1


if __name__ == "__main__":
    sys.exit(main())
