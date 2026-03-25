from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cliany_site.atoms.models import AtomCommand, AtomParameter
from cliany_site.atoms.storage import load_atom, load_atoms
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult


class AdapterGenerator:
    def __init__(self, domain: str = ""):
        self.domain = domain

    def generate(self, explore_result: ExploreResult, domain: str) -> str:
        """将探索结果生成为可执行的 Python/Click 模块代码字符串"""
        generated_at = datetime.now(timezone.utc).isoformat()
        domain_doc = self._sanitize_docstring_text(domain)
        source_url = self._extract_source_url(explore_result)
        workflow_description = self._infer_workflow_description(explore_result)
        source_url_literal = source_url or f"https://{domain}"

        has_reuse_atom = self._has_reuse_atom_actions(explore_result)

        command_blocks: list[str] = []
        for index, command in enumerate(explore_result.commands):
            command_blocks.append(
                self._render_command_block(command, explore_result.actions, index)
            )

        if not command_blocks:
            command_blocks.append(self._render_empty_command_block())

        commands_text = "\n\n".join(command_blocks)

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
        normalized.append(item)
    return normalized
"""

        return f'''# 自动生成 — DO NOT EDIT
# 生成时间: {generated_at}
# 来源 URL: {source_url}
# 工作流: {workflow_description}

import asyncio
import json
import click
from cliany_site.action_runtime import execute_action_steps
from cliany_site.browser.cdp import CDPConnection
from cliany_site.session import load_session_data
from cliany_site.response import success_response, error_response, print_response
from cliany_site.errors import CDP_UNAVAILABLE, SESSION_EXPIRED, EXECUTION_FAILED{atom_imports}

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
        atom_id = self._sanitize_inline_text(atom.atom_id) or "unknown-atom"
        command_source_name = self._sanitize_inline_text(atom.name) or atom_id
        command_name = self._to_command_name(command_source_name, 0)
        function_name = self._to_function_name(command_name)
        description = self._sanitize_docstring_text(
            atom.description or f"执行原子命令 {command_name}"
        )
        missing_message = self._sanitize_inline_text(f"原子命令 '{atom_id}' 未找到")

        option_decorators: list[str] = []
        param_entries: list[str] = []
        used_names = {"ctx", "json_mode", "param_args"}

        for index, raw_parameter in enumerate(atom.parameters or []):
            if isinstance(raw_parameter, AtomParameter):
                parameter = raw_parameter
            elif isinstance(raw_parameter, dict):
                parameter = AtomParameter(
                    name=str(raw_parameter.get("name") or ""),
                    description=str(raw_parameter.get("description") or ""),
                    default=str(raw_parameter.get("default") or ""),
                    required=bool(raw_parameter.get("required", False)),
                )
            else:
                continue

            raw_name = (
                self._sanitize_inline_text(parameter.name) or f"param_{index + 1}"
            )
            option_name = re.sub(
                r"[^a-zA-Z0-9_-]+", "-", raw_name.replace("_", "-").lower()
            )
            option_name = re.sub(r"[_-]+", "-", option_name).strip("-")
            if not option_name:
                option_name = f"param-{index + 1}"

            parameter_name = self._unique_parameter_name(
                self._to_parameter_name(raw_name), used_names
            )
            used_names.add(parameter_name)

            option_parts = [
                repr(f"--{option_name}"),
                repr(parameter_name),
                f"required={bool(parameter.required)!r}",
            ]
            if parameter.default:
                option_parts.append(f"default={parameter.default!r}")

            help_text = self._sanitize_inline_text(parameter.description)
            if help_text:
                option_parts.append(f"help={help_text!r}")

            option_decorators.append(f"@click.option({', '.join(option_parts)})")

            param_key = raw_name
            param_entries.append(f"{param_key!r}: param_args.get({parameter_name!r})")

        params_payload = "{}"
        if param_entries:
            params_payload = "{" + ", ".join(param_entries) + "}"

        decorator_lines = [
            f'@atoms_group.command("{command_name}")',
            *option_decorators,
            '@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")',
            '@click.option("--retry", is_flag=True, default=False, help="执行失败时提示重新 explore")',
            "@click.pass_context",
        ]
        decorators_text = "\n".join(decorator_lines)

        return f'''{decorators_text}
def {function_name}(ctx: click.Context, json_mode: bool | None, retry: bool, **param_args):
    """{description}"""
    async def _run():
        atom = load_atom(DOMAIN, {atom_id!r})
        if atom is None:
            return error_response(EXECUTION_FAILED, {missing_message!r})
        params = {params_payload}
        actions = substitute_parameters(_normalize_atom_actions(atom.actions), params)
        cdp = CDPConnection()
        if not await cdp.check_available():
            return error_response(CDP_UNAVAILABLE, "Chrome CDP 不可用", "启动 Chrome 并开启 --remote-debugging-port=9222")
        browser_session = await cdp.connect()
        await browser_session.navigate_to(SOURCE_URL, new_tab=False)
        await asyncio.sleep(1.5)
        session_data = load_session_data(DOMAIN)
        if session_data:
            if session_data.get("expires_hint") == "expired":
                return error_response(SESSION_EXPIRED, "Session 已失效", "请重新登录后再执行命令")
            await browser_session._cdp_set_cookies(session_data.get("cookies", []))
        try:
            await execute_action_steps(browser_session, actions, continue_on_error=True)
            return success_response({{"status": "completed", "command": "atoms {command_name}", "atom_id": {atom_id!r}, "args": params}})
        except Exception as e:
            fix_hint = ""
            if hasattr(e, "to_dict"):
                fix_hint = e.to_dict().get("suggestion", "")
            if retry:
                retry_cmd = f"cliany-site explore \\"{{SOURCE_URL}}\\" \\"<workflow>\\" --force"
                fix_hint = f"{{fix_hint}} | 重试: {{retry_cmd}}" if fix_hint else f"重试: {{retry_cmd}}"
            return error_response(EXECUTION_FAILED, str(e), fix_hint or None)
        finally:
            await cdp.disconnect()
    result = asyncio.run(_run())
    print_response(result, _resolve_json_mode(json_mode))
'''

    def generate_with_atoms(self) -> str:
        domain = self._resolve_generation_domain()
        generated_at = datetime.now(timezone.utc).isoformat()
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
        resolved = self._sanitize_inline_text(
            domain if domain is not None else self.domain
        )
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
                self._sanitize_inline_text(step.action_type)
                for step in explore_result.actions
                if step.action_type
            ]
            if action_types:
                return " -> ".join(action_types[:5])

        return "自动探索工作流"

    def _render_command_block(
        self,
        command: CommandSuggestion,
        all_actions: list[ActionStep],
        index: int,
    ) -> str:
        command_name = self._to_command_name(command.name, index)
        function_name = self._to_function_name(command_name)
        description = self._sanitize_docstring_text(
            command.description or f"执行命令 {command_name}"
        )

        arg_decorators, arg_parameters = self._render_argument_decorators(command.args)
        decorator_lines = [
            f'@cli.command("{command_name}")',
            '@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")',
            '@click.option("--retry", is_flag=True, default=False, help="执行失败时提示重新 explore")',
            "@click.pass_context",
            *arg_decorators,
        ]
        decorators_text = "\n".join(decorator_lines)

        function_args = [
            "ctx: click.Context",
            "json_mode: bool | None",
            "retry: bool",
            *arg_parameters,
        ]
        function_signature = ", ".join(function_args)
        args_payload = self._render_args_payload(arg_parameters)

        execution_blocks = self._render_execution_blocks(
            command.action_steps, all_actions, arg_parameters
        )

        return f'''{decorators_text}
def {function_name}({function_signature}):
    """{description}"""
    async def _run():
        cdp = CDPConnection()
        if not await cdp.check_available():
            return error_response(CDP_UNAVAILABLE, "Chrome CDP 不可用", "启动 Chrome 并开启 --remote-debugging-port=9222")
        browser_session = await cdp.connect()
        await browser_session.navigate_to(SOURCE_URL, new_tab=False)
        await asyncio.sleep(1.5)
        session_data = load_session_data(DOMAIN)
        if session_data:
            if session_data.get("expires_hint") == "expired":
                return error_response(SESSION_EXPIRED, "Session 已失效", "请重新登录后再执行命令")
            await browser_session._cdp_set_cookies(session_data.get("cookies", []))
        try:
{execution_blocks}
            return success_response({{"status": "completed", "command": "{command_name}", "args": {args_payload}}})
        except Exception as e:
            fix_hint = ""
            if hasattr(e, "to_dict"):
                fix_hint = e.to_dict().get("suggestion", "")
            if retry:
                retry_cmd = f"cliany-site explore \\"{{SOURCE_URL}}\\" \\"<workflow>\\" --force"
                fix_hint = f"{{fix_hint}} | 重试: {{retry_cmd}}" if fix_hint else f"重试: {{retry_cmd}}"
            return error_response(EXECUTION_FAILED, str(e), fix_hint or None)
        finally:
            await cdp.disconnect()
    result = asyncio.run(_run())
    print_response(result, _resolve_json_mode(json_mode))
'''

    def _has_reuse_atom_actions(self, explore_result: ExploreResult) -> bool:
        for action in explore_result.actions:
            if action.action_type == "reuse_atom":
                return True
        return False

    def _collect_atom_refs(
        self, action_steps: list[int], all_actions: list[ActionStep]
    ) -> list[str]:
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

    def _render_execution_blocks(
        self,
        action_steps: list[int],
        all_actions: list[ActionStep],
        arg_parameters: list[str],
    ) -> str:
        if not action_steps:
            return "            action_steps = []\n            await execute_action_steps(browser_session, action_steps, continue_on_error=True)"

        groups: list[tuple[str, Any]] = []
        inline_group: list[int] = []

        for raw_step in action_steps:
            if not isinstance(raw_step, int):
                continue
            if raw_step < 0 or raw_step >= len(all_actions):
                continue
            action = all_actions[raw_step]
            if action.action_type == "reuse_atom":
                if inline_group:
                    groups.append(("inline", list(inline_group)))
                    inline_group = []
                groups.append(("atom", action))
            else:
                inline_group.append(raw_step)

        if inline_group:
            groups.append(("inline", inline_group))

        if not groups:
            return "            action_steps = []\n            await execute_action_steps(browser_session, action_steps, continue_on_error=True)"

        block_lines: list[str] = []
        var_counter = [0]

        for group_type, group_data in groups:
            if group_type == "inline":
                step_indices: list[int] = group_data
                var_counter[0] += 1
                var_name = (
                    f"action_steps_{var_counter[0]}"
                    if var_counter[0] > 1
                    else "action_steps"
                )
                comment_lines = self._render_action_comment_lines(
                    step_indices, all_actions
                )
                literal = self._render_action_data_literal(step_indices, all_actions)
                block_lines.append(f"            {var_name} = json.loads({literal!r})")
                block_lines.append(comment_lines)
                block_lines.append(
                    f"            await execute_action_steps(browser_session, {var_name}, continue_on_error=True)"
                )
            else:
                atom_action: ActionStep = group_data
                atom_id = atom_action.target_ref
                params_dict = atom_action.target_attributes or {}
                description_text = self._sanitize_inline_text(atom_action.description)
                safe_var = re.sub(r"[^a-zA-Z0-9]", "_", atom_id)
                atom_var = f"_atom_{safe_var}"
                params_code = self._render_atom_params_code(params_dict, arg_parameters)
                comment = f"            # atom: {atom_id}"
                if description_text:
                    comment += f" — {description_text}"
                block_lines.append(comment)
                block_lines.append(
                    f"            {atom_var} = load_atom(DOMAIN, {atom_id!r})"
                )
                block_lines.append(f"            if {atom_var}:")
                block_lines.append(
                    f"                _atom_actions = substitute_parameters(_normalize_atom_actions({atom_var}.actions), {params_code})"
                )
                block_lines.append(
                    f"                await execute_action_steps(browser_session, _atom_actions, continue_on_error=True)"
                )

        return "\n".join(block_lines)

    def _render_atom_params_code(
        self, params_dict: dict, arg_parameters: list[str]
    ) -> str:
        if not params_dict:
            return "{}"
        entries: list[str] = []
        for key, val in params_dict.items():
            key_as_param = self._to_parameter_name(str(key))
            if key_as_param in arg_parameters:
                entries.append(f"{key!r}: {key_as_param}")
            else:
                val_as_param = self._to_parameter_name(str(val))
                if val_as_param in arg_parameters:
                    entries.append(f"{key!r}: {val_as_param}")
                else:
                    entries.append(f"{key!r}: {str(val)!r}")
        return "{" + ", ".join(entries) + "}"

    def _render_empty_command_block(self) -> str:
        return '''@cli.command("run-workflow")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.option("--retry", is_flag=True, default=False, help="执行失败时提示重新 explore")
@click.pass_context
def run_workflow(ctx: click.Context, json_mode: bool | None, retry: bool):
    """执行默认工作流"""
    async def _run():
        cdp = CDPConnection()
        if not await cdp.check_available():
            return error_response(CDP_UNAVAILABLE, "Chrome CDP 不可用", "启动 Chrome 并开启 --remote-debugging-port=9222")
        browser_session = await cdp.connect()
        await browser_session.navigate_to(SOURCE_URL, new_tab=False)
        await asyncio.sleep(1.5)
        session_data = load_session_data(DOMAIN)
        if session_data:
            if session_data.get("expires_hint") == "expired":
                return error_response(SESSION_EXPIRED, "Session 已失效", "请重新登录后再执行命令")
            await browser_session._cdp_set_cookies(session_data.get("cookies", []))
        try:
            action_steps = []
            # - 无操作步骤
            await execute_action_steps(browser_session, action_steps, continue_on_error=True)
            return success_response({"status": "completed", "command": "run-workflow"})
        except Exception as e:
            fix_hint = ""
            if hasattr(e, "to_dict"):
                fix_hint = e.to_dict().get("suggestion", "")
            if retry:
                retry_cmd = f"cliany-site explore \\"{{SOURCE_URL}}\\" \\"<workflow>\\" --force"
                fix_hint = f"{{fix_hint}} | 重试: {{retry_cmd}}" if fix_hint else f"重试: {{retry_cmd}}"
            return error_response(EXECUTION_FAILED, str(e), fix_hint or None)
        finally:
            await cdp.disconnect()
    result = asyncio.run(_run())
    print_response(result, _resolve_json_mode(json_mode))
'''

    def _render_argument_decorators(
        self, args: list[dict[str, Any]]
    ) -> tuple[list[str], list[str]]:
        decorators: list[str] = []
        parameters: list[str] = []
        used_names = {"json_mode", "ctx"}

        for index, arg in enumerate(args or []):
            if not isinstance(arg, dict):
                continue

            raw_name = str(arg.get("name") or arg.get("key") or f"arg_{index + 1}")
            parameter_name = self._unique_parameter_name(
                self._to_parameter_name(raw_name), used_names
            )
            used_names.add(parameter_name)
            parameters.append(parameter_name)

            positional = bool(arg.get("positional", False)) or str(
                arg.get("kind", "")
            ).lower() in {"argument", "positional"}
            click_type = self._render_click_type(arg.get("type"), arg.get("choices"))
            required = bool(arg.get("required", False))
            default = arg.get("default")
            help_text = self._sanitize_inline_text(
                str(arg.get("description") or arg.get("help") or "")
            )

            if positional:
                argument_name = parameter_name
                params = [repr(argument_name)]
                if click_type:
                    params.append(f"type={click_type}")
                if not required:
                    params.append("required=False")
                if default is not None:
                    params.append(f"default={default!r}")
                decorators.append(f"@click.argument({', '.join(params)})")
                continue

            option_name = str(arg.get("option") or arg.get("flag") or "").strip()
            if not option_name:
                option_name = f"--{raw_name.replace('_', '-')}"
            elif not option_name.startswith("-"):
                option_name = f"--{option_name}"

            short_name = arg.get("short")
            option_parts = [repr(option_name)]
            if isinstance(short_name, str) and short_name:
                short_flag = (
                    short_name if short_name.startswith("-") else f"-{short_name}"
                )
                option_parts.append(repr(short_flag))
            option_parts.append(repr(parameter_name))

            option_kwargs: list[str] = []
            arg_type = str(arg.get("type") or "").lower()
            is_flag = bool(arg.get("is_flag", False)) or arg_type in {
                "bool",
                "boolean",
                "flag",
            }

            if is_flag:
                option_kwargs.append("is_flag=True")
                if default is not None:
                    option_kwargs.append(f"default={bool(default)!r}")
                else:
                    option_kwargs.append("default=False")
            else:
                if click_type:
                    option_kwargs.append(f"type={click_type}")
                if required:
                    option_kwargs.append("required=True")
                if default is not None:
                    option_kwargs.append(f"default={default!r}")

            if help_text:
                option_kwargs.append(f"help={help_text!r}")

            decorators.append(
                f"@click.option({', '.join(option_parts + option_kwargs)})"
            )

        return decorators, parameters

    def _render_click_type(self, type_value: Any, choices: Any) -> str | None:
        if isinstance(choices, list) and choices:
            normalized_choices = [str(item) for item in choices]
            return f"click.Choice({normalized_choices!r})"

        type_name = str(type_value or "").lower()
        if type_name in {"", "str", "string", "text"}:
            return None
        if type_name in {"int", "integer"}:
            return "int"
        if type_name in {"float", "number", "double"}:
            return "float"
        if type_name in {"path", "filepath", "file"}:
            return "click.Path()"

        return None

    def _render_action_comment_lines(
        self, action_steps: list[int], all_actions: list[ActionStep]
    ) -> str:
        lines: list[str] = []
        for raw_step in action_steps or []:
            if not isinstance(raw_step, int):
                lines.append("            # - 非法 action 索引，已跳过")
                continue
            if raw_step < 0 or raw_step >= len(all_actions):
                lines.append(f"            # - action[{raw_step}] 不存在，已跳过")
                continue

            action = all_actions[raw_step]
            action_type = self._sanitize_inline_text(action.action_type or "unknown")
            detail = self._action_detail(action)
            description = self._sanitize_inline_text(action.description)

            message = f"            # - [{raw_step}] {action_type}: {detail}"
            if description:
                message += f" | {description}"
            lines.append(message)

        if not lines:
            return "            # - 无操作步骤"
        return "\n".join(lines)

    def _render_action_data_literal(
        self, action_steps: list[int], all_actions: list[ActionStep]
    ) -> str:
        payload: list[dict[str, Any]] = []
        for raw_step in action_steps or []:
            if not isinstance(raw_step, int):
                continue
            if raw_step < 0 or raw_step >= len(all_actions):
                continue

            action = all_actions[raw_step]
            if action.action_type == "reuse_atom":
                continue
            payload.append(
                {
                    "type": action.action_type,
                    "ref": action.target_ref,
                    "url": action.target_url,
                    "value": action.value,
                    "description": action.description,
                    "target_name": action.target_name,
                    "target_role": action.target_role,
                    "target_attributes": action.target_attributes,
                }
            )
        return json.dumps(payload, ensure_ascii=False)

    def _action_detail(self, action: ActionStep) -> str:
        action_type = (action.action_type or "").lower()
        if action_type == "navigate":
            return self._sanitize_inline_text(
                action.target_url or action.page_url or "导航"
            )
        if action_type == "click":
            return self._sanitize_inline_text(action.target_ref or "点击元素")
        if action_type == "type":
            target = self._sanitize_inline_text(action.target_ref or "输入框")
            value = self._sanitize_inline_text(action.value)
            return f"{target} <- {value}"
        if action_type == "select":
            target = self._sanitize_inline_text(action.target_ref or "下拉框")
            value = self._sanitize_inline_text(action.value)
            return f"{target} => {value}"
        if action_type == "submit":
            return "提交当前表单"

        target = self._sanitize_inline_text(
            action.target_ref or action.target_url or action.page_url
        )
        return target or "执行操作"

    def _render_args_payload(self, arg_parameters: list[str]) -> str:
        if not arg_parameters:
            return "{}"
        parts = [f"{name!r}: {name}" for name in arg_parameters]
        return "{" + ", ".join(parts) + "}"

    def _to_command_name(self, name: str, index: int) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", (name or "").strip().lower())
        normalized = re.sub(r"[_-]+", "-", normalized).strip("-")
        if not normalized:
            return f"command-{index + 1}"
        if normalized[0].isdigit():
            normalized = f"cmd-{normalized}"
        return normalized

    def _to_function_name(self, command_name: str) -> str:
        function_name = command_name.replace("-", "_")
        function_name = re.sub(r"[^a-zA-Z0-9_]", "_", function_name)
        function_name = re.sub(r"_+", "_", function_name).strip("_")
        if not function_name:
            return "generated_command"
        if function_name[0].isdigit():
            return f"cmd_{function_name}"
        return function_name

    def _to_parameter_name(self, raw_name: str) -> str:
        parameter_name = raw_name.replace("-", "_")
        parameter_name = re.sub(r"[^a-zA-Z0-9_]", "_", parameter_name)
        parameter_name = re.sub(r"_+", "_", parameter_name).strip("_")
        if not parameter_name:
            parameter_name = "arg"
        if parameter_name[0].isdigit():
            parameter_name = f"arg_{parameter_name}"
        return parameter_name

    def _unique_parameter_name(self, base_name: str, used_names: set[str]) -> str:
        if base_name not in used_names:
            return base_name
        index = 2
        while f"{base_name}_{index}" in used_names:
            index += 1
        return f"{base_name}_{index}"

    def _sanitize_inline_text(self, value: str) -> str:
        return str(value or "").replace("\n", " ").replace("\r", " ").strip()

    def _sanitize_docstring_text(self, value: str) -> str:
        return self._sanitize_inline_text(value).replace('"""', '\\"\\"\\"')


def save_adapter(
    domain: str,
    code: str,
    metadata: dict | None = None,
    explore_result: ExploreResult | None = None,
) -> str:
    """保存 adapter 到 ~/.cliany-site/adapters/<domain>/"""
    adapter_dir = Path.home() / ".cliany-site" / "adapters" / _safe_domain(domain)
    adapter_dir.mkdir(parents=True, exist_ok=True)

    commands_path = adapter_dir / "commands.py"
    metadata_path = adapter_dir / "metadata.json"

    commands_path.write_text(code, encoding="utf-8")

    base_metadata = {
        "domain": domain,
        "source_url": _extract_header_value(code, "# 来源 URL:"),
        "workflow": _extract_header_value(code, "# 工作流:"),
        "commands": _extract_commands_from_code(code),
        "generated_at": datetime.now(timezone.utc).isoformat(),
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

    metadata_path.write_text(
        json.dumps(base_metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

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


__all__ = ["AdapterGenerator", "save_adapter"]
