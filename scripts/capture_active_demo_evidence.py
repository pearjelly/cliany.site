#!/usr/bin/env python3
"""Capture a bounded, dated evidence snapshot for one active demo case."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "cases" / "manifest.json"


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    skipped: bool = False
    skip_reason: str = ""

    @property
    def payload(self) -> Any:
        text = self.stdout.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    @property
    def json_error(self) -> str:
        text = self.stdout.strip()
        if not text:
            return "stdout is empty"
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            return str(exc)
        return ""

    @property
    def envelope_success(self) -> bool:
        payload = self.payload
        return isinstance(payload, dict) and (payload.get("ok") is True or payload.get("success") is True)

    @property
    def ok(self) -> bool:
        return not self.skipped and self.returncode == 0 and self.envelope_success


def load_manifest(path: Path = DEFAULT_MANIFEST) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"案例 manifest 必须是 JSON 数组: {path}")
    return [case for case in raw if isinstance(case, dict)]


def select_case(cases: Sequence[dict[str, Any]], case_id: str) -> dict[str, Any]:
    matches = [case for case in cases if case.get("id") == case_id]
    if not matches:
        raise ValueError(f"未找到案例: {case_id}")
    case = matches[0]
    if case.get("status") != "active":
        raise ValueError(f"案例 {case_id} 不是 active；不会捕获 candidate 或其他状态的在线证据")
    return case


def declared_commands(case: dict[str, Any]) -> tuple[str, str]:
    domain = str(case.get("adapter_domain") or "").strip()
    if not domain:
        raise ValueError("active 案例缺少 adapter_domain")
    validation = case.get("validation")
    online_description = validation.get("online") if isinstance(validation, dict) else ""
    if "read-only" not in str(online_description).lower():
        raise ValueError("active 案例没有声明 read-only online validation")

    raw_commands = case.get("commands")
    commands = [str(command) for command in raw_commands] if isinstance(raw_commands, list) else []
    read_only = next(
        (
            command
            for command in commands
            if command.startswith(f"cliany-site {domain} ") and "--json" in command
        ),
        "",
    )
    if not read_only:
        raise ValueError("active 案例没有声明带 --json 的只读 adapter 命令")
    return f"cliany-site verify {domain} --strict --json", read_only


def command_argv(command: str) -> list[str]:
    parts = shlex.split(command)
    if not parts or parts[0] != "cliany-site":
        raise ValueError(f"只允许执行 cliany-site 命令: {command}")
    return [sys.executable, "-m", "cliany_site", *parts[1:]]


Runner = Callable[..., subprocess.CompletedProcess[str]]


def run_command(command: str, *, runner: Runner = subprocess.run) -> CommandResult:
    completed = runner(
        command_argv(command),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        command=command,
        returncode=int(completed.returncode),
        stdout=str(completed.stdout or ""),
        stderr=str(completed.stderr or ""),
    )


def capture_case(
    case: dict[str, Any],
    *,
    captured: str | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    verify_command, read_only_command = declared_commands(case)
    verify = run_command(verify_command, runner=runner)
    if verify.ok:
        read_only = run_command(read_only_command, runner=runner)
    else:
        read_only = CommandResult(
            command=read_only_command,
            returncode=0,
            stdout="",
            stderr="",
            skipped=True,
            skip_reason="strict verify did not return ok=true; read-only command was not run",
        )
    return {
        "captured": captured or date.today().isoformat(),
        "case_id": str(case.get("id") or ""),
        "title": str(case.get("title") or ""),
        "target_url": str(case.get("target_url") or ""),
        "adapter_domain": str(case.get("adapter_domain") or ""),
        "source_release": case.get("source_release"),
        "verify": verify,
        "read_only": read_only,
        "ok": verify.ok and read_only.ok,
    }


def _result_to_dict(result: CommandResult) -> dict[str, Any]:
    return {
        "command": result.command,
        "returncode": result.returncode,
        "ok": result.ok,
        "envelope_success": result.envelope_success,
        "skipped": result.skipped,
        "skip_reason": result.skip_reason,
        "payload": result.payload,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "json_error": result.json_error,
    }


def report_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (_result_to_dict(value) if isinstance(value, CommandResult) else value)
        for key, value in report.items()
    }


def _json_block(result: CommandResult) -> str:
    payload = result.payload
    if payload is not None:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return result.stdout.strip() or "(no stdout)"


def _result_markdown(label: str, result: CommandResult) -> list[str]:
    lines = [
        f"### {label}",
        f"- Command: `{result.command}`",
        f"- Exit status: `{result.returncode}`",
        f"- JSON envelope success (`ok` or `success`): `{str(result.envelope_success).lower()}`",
    ]
    if result.skipped:
        lines.append(f"- Status: skipped (`{result.skip_reason}`)")
    if result.stderr.strip():
        lines.extend(["", "#### stderr", "", "```text", result.stderr.strip(), "```"])
    lines.extend(["", "#### stdout", "", "```json", _json_block(result), "```"])
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    verify = report["verify"]
    read_only = report["read_only"]
    assert isinstance(verify, CommandResult)
    assert isinstance(read_only, CommandResult)
    package_version = __import__("cliany_site").__version__
    lines = [
        f"# Active Demo Evidence: {report['adapter_domain']}",
        "",
        f"**Captured:** {report['captured']}",
        f"**Package baseline:** `cliany-site` {package_version}",
        f"**Case:** `{report['case_id']}` ({report['title']})",
        f"**Target:** {report['target_url']}",
        f"**Overall:** `{str(bool(report['ok'])).lower()}`",
        "",
        "This is a dated maintainer evidence snapshot, not a service-availability guarantee. "
        "It records only the commands declared by the active case. The read-only command is "
        "run only after strict static verification returns a successful JSON envelope. "
        "It does not prove that the adapter is a downloadable release asset, candidate package "
        "promotion, live LLM availability, or continuing third-party workflow availability.",
        "",
        "## Results",
        "",
    ]
    lines.extend(_result_markdown("Strict Static Verification", verify))
    lines.extend(["", *(_result_markdown("Declared Read-Only Command", read_only))])
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="要捕获的 active case id")
    parser.add_argument("--output", required=True, type=Path, help="写入 Markdown snapshot 的路径")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help=argparse.SUPPRESS)
    parser.add_argument("--captured", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help="同时将结构化 report 输出到 stdout")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        case = select_case(load_manifest(args.manifest), args.case_id)
        report = capture_case(case, captured=args.captured)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report_payload(report), ensure_ascii=False, indent=2))
    else:
        print(f"wrote {args.output} (ok={str(bool(report['ok'])).lower()})")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
