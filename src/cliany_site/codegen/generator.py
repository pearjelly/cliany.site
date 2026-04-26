from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import time
from datetime import UTC, datetime
from importlib.metadata import version as _pkg_version
from typing import Any

from cliany_site.atoms.models import AtomCommand
from cliany_site.atoms.storage import load_atom, load_atoms
from cliany_site.codegen.naming import (
    sanitize_docstring_text,
    sanitize_inline_text,
    to_command_name,
    to_function_name,
    to_parameter_name,
    unique_parameter_name,
)
from cliany_site.codegen.templates import (
    render_atom_command,
    render_command_block_v2,
    render_empty_command_block_v2,
)
from cliany_site.config import get_config
from cliany_site.explorer.models import ActionStep, ExploreResult

METADATA_SCHEMA_VERSION = 2

try:
    _GENERATOR_VERSION: str = _pkg_version("cliany-site")
except Exception:
    _GENERATOR_VERSION = "unknown"

logger = logging.getLogger(__name__)


class AdapterGenerator:
    def __init__(self, domain: str = ""):
        self.domain = domain

    def generate(self, explore_result: ExploreResult, domain: str) -> str:
        gen_start = time.monotonic()
        logger.info(
            "开始生成 adapter: domain=%s actions=%d commands=%d",
            domain,
            len(explore_result.actions),
            len(explore_result.commands),
        )
        generated_at = datetime.now(UTC).isoformat()
        domain_doc = self._sanitize_docstring_text(domain)
        source_url = self._extract_source_url(explore_result)
        workflow_description = self._infer_workflow_description(explore_result)
        source_url_literal = source_url or f"https://{domain}"

        has_reuse_atom = self._has_reuse_atom_actions(explore_result)
        has_parameterized_args = any(cmd.args for cmd in explore_result.commands)
        has_param_placeholders = any(re.search(r"\{\{\w+\}\}", action.value or "") for action in explore_result.actions)

        command_blocks: list[str] = []
        for index, command in enumerate(explore_result.commands):
            command_blocks.append(render_command_block_v2(command, explore_result.actions, index))

        if not command_blocks:
            command_blocks.append(render_empty_command_block_v2())

        commands_text = "\n\n".join(command_blocks)

        substitute_import = ""
        if (has_parameterized_args or has_param_placeholders) and not has_reuse_atom:
            substitute_import = "\nfrom cliany_site.action_runtime import substitute_parameters"

        atom_imports = ""
        normalize_helper = ""
        if has_reuse_atom:
            atom_imports = (
                "\nfrom cliany_site.atoms.storage import load_atom"
                "\nfrom cliany_site.action_runtime import substitute_parameters"
            )
            normalize_helper = """

def _normalize_atom_actions(actions):
    normalized = []
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        item = dict(action)
        if "type" not in item and "action_type" in item:
            item["type"] = item.get("action_type")
        if "url" not in item and "target_url" in item:
            item["url"] = item.get("target_url")
        if "fields" not in item and "fields_map" in item:
            item["fields"] = item.get("fields_map")
        normalized.append(item)
    return normalized
"""

        gen_elapsed = (time.monotonic() - gen_start) * 1000
        logger.info(
            "adapter 生成完成: domain=%s commands=%d 耗时 %.0fms",
            domain,
            len(command_blocks),
            gen_elapsed,
        )

        return f'''# 自动生成 — DO NOT EDIT
# 生成时间: {generated_at}
# 来源 URL: {source_url}
# 工作流: {workflow_description}

import json
import click
from cliany_site.codegen.runtime_helpers import execute_steps_via_atoms
from cliany_site.response import success_response, error_response, print_response{atom_imports}{substitute_import}

DOMAIN = {domain!r}
SOURCE_URL = {source_url_literal!r}


@click.group()
def cli():
    """{domain_doc} 的自动生成 CLI 命令"""
    pass


def _resolve_json_mode(local_json_mode):
    if local_json_mode is not None:
        return bool(local_json_mode)
    ctx = click.get_current_context(silent=True)
    if ctx is None:
        return False
    root_ctx = ctx.find_root()
    obj = getattr(root_ctx, "obj", None)
    if not isinstance(obj, dict):
        return False
    return bool(obj.get("json_mode", False))
{normalize_helper}

{commands_text}


if __name__ == "__main__":
    cli()
'''

    def generate_atom_command(self, atom: AtomCommand) -> str:
        return render_atom_command(atom)

    def generate_with_atoms(self) -> str:
        domain = self._resolve_generation_domain()
        generated_at = datetime.now(UTC).isoformat()
        domain_doc = self._sanitize_docstring_text(domain)
        source_url = f"https://{domain}"
        atoms = load_atoms(domain)

        if not atoms:
            code = f'''# 自动生成 — DO NOT EDIT
# 生成时间: {generated_at}
# 来源 URL: {source_url}
# 工作流: 原子命令集合

import click


@click.group()
def cli():
    """{domain_doc} 的自动生成 CLI 命令"""
    pass


if __name__ == "__main__":
    cli()
'''
            return save_adapter(domain, code)

        atom_blocks: list[str] = [self.generate_atom_command(atom) for atom in atoms]
        atoms_text = "\n\n".join(atom_blocks)
        load_atom_name = load_atom.__name__

        code = f'''# 自动生成 — DO NOT EDIT
# 生成时间: {generated_at}
# 来源 URL: {source_url}
# 工作流: 原子命令集合

import asyncio
import click
from cliany_site.action_runtime import execute_action_steps, substitute_parameters
from cliany_site.atoms.storage import {load_atom_name}
from cliany_site.browser.cdp import CDPConnection
from cliany_site.session import load_session_data
from cliany_site.response import success_response, error_response, print_response
from cliany_site.errors import CDP_UNAVAILABLE, SESSION_EXPIRED, EXECUTION_FAILED

DOMAIN = {domain!r}
SOURCE_URL = {source_url!r}


@click.group()
def cli():
    """{domain_doc} 的自动生成 CLI 命令"""
    pass


def _resolve_json_mode(local_json_mode):
    if local_json_mode is not None:
        return bool(local_json_mode)
    ctx = click.get_current_context(silent=True)
    if ctx is None:
        return False
    root_ctx = ctx.find_root()
    obj = getattr(root_ctx, "obj", None)
    if not isinstance(obj, dict):
        return False
    return bool(obj.get("json_mode", False))


def _normalize_atom_actions(actions):
    normalized = []
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        item = dict(action)
        if "type" not in item and "action_type" in item:
            item["type"] = item.get("action_type")
        if "url" not in item and "target_url" in item:
            item["url"] = item.get("target_url")
        if "fields" not in item and "fields_map" in item:
            item["fields"] = item.get("fields_map")
        normalized.append(item)
    return normalized


atoms_group = click.Group("atoms", help="原子命令")
cli.add_command(atoms_group)


{atoms_text}


if __name__ == "__main__":
    cli()
'''
        return save_adapter(domain, code)

    def _resolve_generation_domain(self, domain: str | None = None) -> str:
        resolved = self._sanitize_inline_text(domain if domain is not None else self.domain)
        if not resolved:
            resolved = "unknown-domain"
        self.domain = resolved
        return resolved

    def _extract_source_url(self, explore_result: ExploreResult) -> str:
        if explore_result.pages:
            return self._sanitize_inline_text(explore_result.pages[0].url)
        return ""

    def _infer_workflow_description(self, explore_result: ExploreResult) -> str:
        labels: list[str] = []
        for command in explore_result.commands:
            label = self._sanitize_inline_text(command.description or command.name)
            if label:
                labels.append(label)

        if labels:
            return " | ".join(labels[:3])

        if explore_result.actions:
            action_types = [
                self._sanitize_inline_text(step.action_type) for step in explore_result.actions if step.action_type
            ]
            if action_types:
                return " -> ".join(action_types[:5])

        return "自动探索工作流"

    def _has_reuse_atom_actions(self, explore_result: ExploreResult) -> bool:
        return any(action.action_type == "reuse_atom" for action in explore_result.actions)

    def _collect_atom_refs(self, action_steps: list[int], all_actions: list[ActionStep]) -> list[str]:
        seen: list[str] = []
        for raw_step in action_steps or []:
            if not isinstance(raw_step, int):
                continue
            if raw_step < 0 or raw_step >= len(all_actions):
                continue
            action = all_actions[raw_step]
            if action.action_type == "reuse_atom" and action.target_ref:
                atom_id = action.target_ref
                if atom_id not in seen:
                    seen.append(atom_id)
        return seen

    # --- 向后兼容的委托方法（保留下划线前缀 API） ---

    def _to_command_name(self, name: str, index: int) -> str:
        return to_command_name(name, index)

    def _to_function_name(self, command_name: str) -> str:
        return to_function_name(command_name)

    def _to_parameter_name(self, raw_name: str) -> str:
        return to_parameter_name(raw_name)

    def _unique_parameter_name(self, base_name: str, used_names: set[str]) -> str:
        return unique_parameter_name(base_name, used_names)

    def _sanitize_inline_text(self, value: str) -> str:
        return sanitize_inline_text(value)

    def _sanitize_docstring_text(self, value: str) -> str:
        return sanitize_docstring_text(value)


def _build_minimal_smoke(commands: list[dict]) -> list[dict]:
    result = []
    for cmd in commands[:3]:  # 最多取前 3 个
        result.append({
            "command": cmd.get("name", ""),
            "args": {},
            "expect": {"ok": True},
        })
    return result


def save_adapter(
    domain: str,
    code: str,
    metadata: dict | None = None,
    explore_result: ExploreResult | None = None,
) -> str:
    adapter_dir = get_config().adapters_dir / _safe_domain(domain)
    adapter_dir.mkdir(parents=True, exist_ok=True)
    logger.info("保存 adapter: domain=%s path=%s", domain, adapter_dir)

    commands_path = adapter_dir / "commands.py"
    metadata_path = adapter_dir / "metadata.json"

    fd, tmp_path = tempfile.mkstemp(dir=str(adapter_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(code)
        os.replace(tmp_path, str(commands_path))
    except OSError:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    base_metadata: dict[str, Any] = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "domain": domain,
        "source_url": _extract_header_value(code, "# 来源 URL:"),
        "workflow": _extract_header_value(code, "# 工作流:"),
        "commands": _extract_commands_from_code(code),
        "generated_at": datetime.now(UTC).isoformat(),
        "explore_model": explore_result.explore_model if explore_result else "",
        "generator_version": _GENERATOR_VERSION,
        "canonical_actions": [
            {
                "action_type": a.action_type,
                "target_ref": a.target_ref,
                "target_name": getattr(a, "target_name", None),
                "target_url": a.target_url,
                "description": getattr(a, "description", None),
            }
            for a in explore_result.actions
            if a.action_type
        ] if explore_result else [],
        "selector_pool": [],
        "smoke": _build_minimal_smoke(
            [{"name": cmd.name} for cmd in explore_result.commands]
            if explore_result
            else []
        ),
        "heal_history": [],
    }
    if metadata:
        base_metadata.update(metadata)

    if explore_result:
        command_defs: list[dict[str, Any]] = []
        for cmd in explore_result.commands:
            cmd_actions: list[dict[str, Any]] = []
            atom_refs: list[str] = []
            for step_idx in cmd.action_steps or []:
                if 0 <= step_idx < len(explore_result.actions):
                    action = explore_result.actions[step_idx]
                    cmd_actions.append(
                        {
                            "action_type": action.action_type,
                            "page_url": action.page_url,
                            "target_ref": action.target_ref,
                            "target_url": action.target_url,
                            "value": action.value,
                            "description": action.description,
                            "target_name": action.target_name,
                            "target_role": action.target_role,
                            "target_attributes": action.target_attributes,
                            "selector": action.selector,
                            "extract_mode": action.extract_mode,
                            "fields_map": action.fields_map,
                        }
                    )
                    if action.action_type == "reuse_atom" and action.target_ref:
                        atom_id = action.target_ref
                        if atom_id not in atom_refs:
                            atom_refs.append(atom_id)

            cmd_def: dict[str, Any] = {
                "name": cmd.name,
                "description": cmd.description,
                "args": cmd.args,
                "action_steps": cmd.action_steps,
                "actions": cmd_actions,
            }
            if atom_refs:
                cmd_def["atom_refs"] = atom_refs
            command_defs.append(cmd_def)

        base_metadata["commands"] = command_defs
    else:
        commands = base_metadata.get("commands")
        if not isinstance(commands, list):
            commands = []
        base_metadata["commands"] = [str(item) for item in commands]

    if "domain" not in base_metadata or not base_metadata["domain"]:
        base_metadata["domain"] = domain
    if "source_url" not in base_metadata:
        base_metadata["source_url"] = ""
    if "workflow" not in base_metadata:
        base_metadata["workflow"] = ""

    meta_content = json.dumps(base_metadata, ensure_ascii=False, indent=2)
    fd, tmp_path = tempfile.mkstemp(dir=str(adapter_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(meta_content)
        os.replace(tmp_path, str(metadata_path))
    except OSError:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    if explore_result:
        try:
            from cliany_site.snapshot import save_explore_snapshots

            save_explore_snapshots(domain, explore_result)
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("保存 AXTree 快照失败: %s", exc)

    return str(commands_path.resolve())


def _safe_domain(domain: str) -> str:
    safe = str(domain or "").strip()
    safe = safe.replace("/", "_").replace(":", "_")
    safe = safe.strip()
    if not safe:
        return "unknown-domain"
    return safe


def _extract_header_value(code: str, key_prefix: str) -> str:
    for line in code.splitlines():
        if line.startswith(key_prefix):
            return line[len(key_prefix) :].strip()
    return ""


def _extract_commands_from_code(code: str) -> list[str]:
    pattern = r"@cli\.command\((?:\"([^\"]+)\"|'([^']+)')"
    commands: list[str] = []
    for match in re.finditer(pattern, code):
        value = match.group(1) or match.group(2)
        if value:
            commands.append(value)
    return commands


__all__ = ["AdapterGenerator", "save_adapter", "METADATA_SCHEMA_VERSION", "_build_minimal_smoke"]
