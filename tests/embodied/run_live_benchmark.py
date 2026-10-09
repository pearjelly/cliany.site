"""Opt-in fresh explore/replay trials against controlled local pages."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import math
import os
import re
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
OUTPUT_ORACLE = "per-row-v2"


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


def _row_lists(value: Any) -> list[list[Any]]:
    if isinstance(value, list):
        return [value]
    if isinstance(value, dict):
        return [rows for child in value.values() for rows in _row_lists(child)]
    return []


def _matches_expected_extracts(contents: list[Any], replay: dict[str, Any]) -> bool:
    values = [text for content in contents for text in _text_values(content)]
    expected_text = replay.get("expected_text")
    if isinstance(expected_text, str) and (not values or any(value != expected_text for value in values)):
        return False
    expected_summary = replay.get("expected_summary")
    if isinstance(expected_summary, str):
        summaries = [value for value in values if re.fullmatch(r"\d+ matches", value)]
        if not summaries or any(summary != expected_summary for summary in summaries):
            return False
    expected_rows = replay.get("expected_rows")
    if isinstance(expected_rows, list):
        row_lists = [rows for content in contents for rows in _row_lists(content)]
        if not row_lists or any(
            len(rows) != len(expected_rows)
            or any(expected not in _text_values(row) for expected, row in zip(expected_rows, rows, strict=True))
            for rows in row_lists
        ):
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


_SAFE_FIELD_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_-]{0,79}\Z")
_QUALITY_REASONS = frozenset({
    "extract_quality_failed", "missing_extraction_evidence",
    "extraction_execution_failed", "missing_replay_prerequisites",
})
_CONTRACT_REASONS = frozenset({
    "llm_invalid_json", "llm_invalid_shape", "command_partition_invalid", "extract_selector_ungrounded",
    "command_list_invalid", "missing_commands", "explore_step_limit",
})


def _safe_explore_contract_diagnostics(error: dict[str, Any]) -> dict[str, str] | None:
    if error.get("code") != "E_UNKNOWN":
        return None
    details = error.get("details")
    if not isinstance(details, dict):
        return None
    reason, phase = details.get("reason"), details.get("phase")
    if (isinstance(reason, str) and reason in _CONTRACT_REASONS
            and isinstance(phase, str) and phase in {"llm_response", "completion"}):
        return {"reason": reason, "phase": phase}
    return None


def _safe_explore_quality_diagnostics(error: dict[str, Any]) -> dict[str, Any] | None:
    if error.get("code") != "E_EMPTY_RESULT":
        return None
    details = error.get("details")
    if not isinstance(details, dict):
        return None
    if "data_commands" not in details and "repair_attempts" not in details:
        return None
    failures = []
    commands = details.get("data_commands")
    for item in commands[:10] if isinstance(commands, list) else []:
        if not isinstance(item, dict):
            continue
        row: dict[str, Any] = {}
        reason = item.get("reason")
        if isinstance(reason, str) and reason in _QUALITY_REASONS:
            row["reason"] = reason
        index = item.get("action_index")
        if type(index) is int and index >= 0:
            row["action_index"] = index
        mode = item.get("extract_mode")
        if isinstance(mode, str) and mode in {"text", "attribute", "list", "table"}:
            row["extract_mode"] = mode
        if reason == "extraction_execution_failed":
            execution_error = item.get("error")
            if isinstance(execution_error, dict):
                code = execution_error.get("code")
                if isinstance(code, str) and code in {"E_PARSE_FAILED", "E_SELECTOR_NOT_FOUND"}:
                    row["error_code"] = code
                if "selector" in execution_error:
                    selector = execution_error["selector"]
                    row["selector_present"] = isinstance(selector, str) and bool(selector.strip())
        quality = item.get("quality")
        if isinstance(quality, dict):
            status = quality.get("status")
            if isinstance(status, str) and status in {"empty", "partial", "ok"}:
                row["quality_status"] = status
            count = quality.get("row_count")
            if type(count) is int and count >= 0:
                row["row_count"] = count
            blank_rows = quality.get("field_blank_rows")
            if isinstance(blank_rows, dict):
                row["blank_fields"] = [
                    name for name in list(blank_rows)[:5]
                    if isinstance(name, str) and _SAFE_FIELD_NAME.fullmatch(name)
                ]
        if row:
            failures.append(row)
    repairs = details.get("repair_attempts")
    return {
        "repair_attempts": repairs if type(repairs) is int and 0 <= repairs <= 10 else None,
        "failures": failures,
    }


def _safe_replay_quality_diagnostics(error: dict[str, Any]) -> dict[str, Any] | None:
    if error.get("code") != "E_EMPTY_RESULT":
        return None
    details = error.get("details")
    if not isinstance(details, dict):
        return None
    overall_status = details.get("status")
    if not isinstance(overall_status, str) or overall_status not in {"empty", "partial", "ok", "not_applicable"}:
        return None
    extracts = []
    for item in details.get("extracts", [])[:10] if isinstance(details.get("extracts"), list) else []:
        if not isinstance(item, dict):
            continue
        row: dict[str, Any] = {}
        mode = item.get("extract_mode")
        if isinstance(mode, str) and mode in {"text", "attribute", "list", "table"}:
            row["mode"] = mode
        status = item.get("status")
        if isinstance(status, str) and status in {"empty", "partial", "ok"}:
            row["status"] = status
        count = item.get("row_count")
        if type(count) is int and count >= 0:
            row["row_count"] = count
        index = item.get("step_index")
        if type(index) is int and index >= 0:
            row["step_index"] = index
        if row:
            extracts.append(row)
    return {"status": overall_status, "extracts": extracts}


def _safe_explore_timing(stderr: bytes, *, ended_at: float) -> dict[str, Any] | None:
    starts: dict[int, float] = {}
    waits: list[float] = []
    attempt_starts: dict[tuple[int, int], float] = {}
    attempt_seconds: list[float] = []
    attempt_outcomes: list[str] = []
    retry_count = 0
    scheduled_backoff_seconds = 0.0
    for line in stderr.splitlines():
        try:
            event = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(event, dict) or event.get("event") not in {
            "explore_llm_start", "explore_llm_done",
            "explore_llm_attempt_start", "explore_llm_attempt_done",
        }:
            continue
        step, ts = event.get("step"), event.get("ts")
        if type(step) is not int or step < 0 or not isinstance(ts, (int, float)) or isinstance(ts, bool):
            continue
        if not math.isfinite(ts):
            continue
        if event["event"] == "explore_llm_start":
            starts[step] = float(ts)
        elif event["event"] == "explore_llm_done" and step in starts and ts >= starts[step]:
            waits.append(round(float(ts) - starts.pop(step), 2))
        else:
            attempt = event.get("attempt")
            if type(attempt) is not int or not 1 <= attempt <= 20:
                continue
            key = (step, attempt)
            if event["event"] == "explore_llm_attempt_start":
                attempt_starts[key] = float(ts)
            elif event["event"] == "explore_llm_attempt_done" and key in attempt_starts:
                attempt_starts.pop(key)
                elapsed = event.get("elapsed_ms")
                backoff = event.get("backoff_ms")
                outcome = event.get("outcome")
                if (not isinstance(elapsed, (int, float)) or isinstance(elapsed, bool)
                        or not math.isfinite(elapsed) or elapsed < 0):
                    continue
                attempt_seconds.append(round(float(elapsed) / 1000, 2))
                attempt_outcomes.append(
                    outcome if isinstance(outcome, str) and outcome in {"success", "retry", "error"} else "unknown"
                )
                if (outcome == "retry" and isinstance(backoff, (int, float))
                        and not isinstance(backoff, bool) and math.isfinite(backoff) and backoff >= 0):
                    retry_count += 1
                    scheduled_backoff_seconds += float(backoff) / 1000
    if not waits and not starts and not attempt_seconds and not attempt_starts:
        return None
    summary: dict[str, Any] = {"llm_wait_seconds": waits[:20]}
    if starts:
        latest = max(starts.values())
        summary["inflight_llm_seconds"] = round(max(0.0, ended_at - latest), 2)
    if attempt_seconds or attempt_starts:
        summary["attempt_seconds"] = attempt_seconds[:20]
        summary["attempt_outcomes"] = attempt_outcomes[:20]
        summary["retry_count"] = retry_count
        summary["scheduled_backoff_seconds"] = round(scheduled_backoff_seconds, 2)
    if attempt_starts:
        summary["inflight_attempt_seconds"] = round(max(0.0, ended_at - max(attempt_starts.values())), 2)
    return summary


def _safe_provider_context(preflight: dict[str, Any]) -> dict[str, str]:
    context = {"provider": "unknown", "endpoint_type": "unknown"}
    data = preflight.get("data")
    checks = data.get("checks") if isinstance(data, dict) else None
    if not isinstance(checks, list):
        return context
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("details"), dict):
            continue
        details = check["details"]
        provider = details.get("provider")
        if check.get("name") == "llm_provider" and isinstance(provider, str) and provider in {"openai", "anthropic"}:
            context["provider"] = provider
        elif check.get("name") == "openai_base_url":
            base_url = details.get("base_url")
            if base_url is None or isinstance(base_url, str):
                context["endpoint_type"] = "custom" if base_url and base_url.strip() else "default"
    if context["provider"] != "openai":
        context["endpoint_type"] = "not_reported" if context["provider"] == "anthropic" else "unknown"
    return context


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
    communication = asyncio.create_task(process.communicate())
    try:
        stdout, stderr = await asyncio.wait_for(asyncio.shield(communication), timeout=timeout)
    except TimeoutError:
        process.kill()
        _, stderr = await communication
        timing = _safe_explore_timing(stderr, ended_at=time.time())
        result = {"ok": False, "error": {"code": "BENCHMARK_TIMEOUT"}}
        if timing is not None:
            result["benchmark_timing"] = timing
        return result, time.monotonic() - start
    elapsed = time.monotonic() - start
    timing = _safe_explore_timing(stderr, ended_at=time.time())
    try:
        payload = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "error": {"code": "INVALID_CLI_JSON"}}, elapsed
    if not isinstance(payload, dict) or process.returncode != 0 or payload.get("ok") is not True:
        error = payload.get("error") if isinstance(payload, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        summary = _safe_explore_quality_diagnostics(error) if isinstance(error, dict) else None
        if summary is None and isinstance(error, dict):
            summary = _safe_replay_quality_diagnostics(error)
        safe_error = {"code": code or "CLI_FAILED"}
        if summary is not None:
            safe_error["quality_diagnostics"] = summary
        contract = _safe_explore_contract_diagnostics(error) if isinstance(error, dict) else None
        if contract is not None:
            safe_error["contract_diagnostics"] = contract
        result = {"ok": False, "error": safe_error}
        if timing is not None:
            result["benchmark_timing"] = timing
        return result, elapsed
    if timing is not None:
        payload["benchmark_timing"] = timing
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
        if "benchmark_timing" in explore:
            outcome["timing"] = explore["benchmark_timing"]
    finally:
        await browser.close()
    if not explore.get("ok"):
        outcome["error_code"] = explore.get("error", {}).get("code")
        diagnostics = explore.get("error", {}).get("quality_diagnostics")
        if diagnostics is not None:
            outcome["quality_diagnostics"] = diagnostics
        contract = explore.get("error", {}).get("contract_diagnostics")
        if contract is not None:
            outcome["contract_diagnostics"] = contract
        return outcome

    data = explore.get("data", {})
    repairs = data.get("partition_repair_attempts") if isinstance(data, dict) else None
    if type(repairs) is int and repairs >= 0:
        outcome["partition_repair_attempts"] = repairs
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
    for command_index, definition in enumerate(metadata.get("commands", [])):
        name = definition.get("name") if isinstance(definition, dict) else None
        if isinstance(name, str) and to_command_name(name, command_index) == command:
            if isinstance(definition.get("expects_nonempty"), bool):
                outcome["expects_nonempty"] = definition["expects_nonempty"]
            break
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
                diagnostics = result.get("error", {}).get("quality_diagnostics")
                if diagnostics is not None:
                    row["quality_diagnostics"] = diagnostics
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
        "output_oracle": OUTPUT_ORACLE,
        "provider": "unknown",
        "endpoint_type": "unknown",
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
                report.update(_safe_provider_context(preflight))
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
        report = {
            "schema_version": 1, "output_oracle": OUTPUT_ORACLE,
            "error": type(exc).__name__, "trials": [], "success_count": 0, "total_count": 0,
        }
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
