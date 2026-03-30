from __future__ import annotations

import json
import re
from typing import Any

from cliany_site.atoms.models import AtomCommand, AtomParameter
from cliany_site.codegen.dedup import (
    deduplicate_parameterized_actions,
    remove_consecutive_duplicate_clicks,
    remove_redundant_duplicate_actions,
)
from cliany_site.codegen.naming import (
    sanitize_docstring_text,
    sanitize_inline_text,
    to_command_name,
    to_function_name,
    to_parameter_name,
    unique_parameter_name,
)
from cliany_site.codegen.params import auto_detect_params_from_actions, build_param_overrides
from cliany_site.explorer.models import ActionStep, CommandSuggestion


def render_command_block(
    command: CommandSuggestion,
    all_actions: list[ActionStep],
    index: int,
) -> str:
    command_name = to_command_name(command.name, index)
    function_name = to_function_name(command_name)
    description = sanitize_docstring_text(command.description or f"执行命令 {command_name}")

    effective_args = command.args
    if not effective_args:
        effective_args = auto_detect_params_from_actions(command.action_steps, all_actions)

    # overrides 必须在 dedup 之前计算，使 dedup 知道哪些 index 是参数化的
    param_overrides = build_param_overrides(effective_args, command.action_steps, all_actions)
    cleaned_steps = deduplicate_parameterized_actions(command.action_steps, all_actions, param_overrides)
    cleaned_steps = remove_consecutive_duplicate_clicks(cleaned_steps, all_actions)
    cleaned_steps = remove_redundant_duplicate_actions(cleaned_steps, all_actions, param_overrides)
    param_overrides = {idx: v for idx, v in param_overrides.items() if idx in set(cleaned_steps)}

    arg_decorators, arg_parameters = render_argument_decorators(effective_args)

    has_extract = any(
        isinstance(raw_step, int)
        and 0 <= raw_step < len(all_actions)
        and all_actions[raw_step].action_type == "extract"
        for raw_step in cleaned_steps
    )

    decorator_lines = [
        f'@cli.command("{command_name}")',
        '@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")',
        '@click.option("--retry", is_flag=True, default=False, help="执行失败时提示重新 explore")',
        "@click.pass_context",
        *arg_decorators,
    ]
    if has_extract:
        decorator_lines.append(
            '@click.option("--output", type=click.Path(), default=None, help="提取结果保存路径（默认自动生成）")'
        )
    decorators_text = "\n".join(decorator_lines)

    function_args = [
        "ctx: click.Context",
        "json_mode: bool | None",
        "retry: bool",
        *arg_parameters,
    ]
    if has_extract:
        function_args.append("output: str | None")
    function_signature = ", ".join(function_args)
    args_payload = render_args_payload(arg_parameters)

    execution_blocks = render_execution_blocks(
        cleaned_steps,
        all_actions,
        arg_parameters,
        raw_args=effective_args,
        param_overrides=param_overrides,
    )

    if has_extract:
        success_line = f'            return success_response({{"status": "completed", "command": "{command_name}", "args": {args_payload}, "results": _extraction_results}})'
        writer_call = (
            "            from cliany_site.extract_writer import save_extract_markdown\n"
            "            from pathlib import Path as _Path\n"
            "            _saved = save_extract_markdown(\n"
            "                extraction_results=_extraction_results,\n"
            f"                domain=DOMAIN,\n"
            f"                workflow_description={description!r},\n"
            "                output_path=_Path(output) if output else None,\n"
            "            )\n"
            "            if _saved:\n"
            '                click.echo(f"\\U0001f4c4 提取结果已保存: {_saved}", err=True)'
        )
    else:
        success_line = f'            return success_response({{"status": "completed", "command": "{command_name}", "args": {args_payload}}})'
        writer_call = ""

    return f'''{decorators_text}
def {function_name}({function_signature}):
    """{description}"""
    async def _run():
        cdp = cdp_from_context(ctx)
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
{writer_call}
{success_line}
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


def render_empty_command_block() -> str:
    return '''@cli.command("run-workflow")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.option("--retry", is_flag=True, default=False, help="执行失败时提示重新 explore")
@click.pass_context
def run_workflow(ctx: click.Context, json_mode: bool | None, retry: bool):
    """执行默认工作流"""
    async def _run():
        cdp = cdp_from_context(ctx)
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


def render_execution_blocks(
    action_steps: list[int],
    all_actions: list[ActionStep],
    arg_parameters: list[str],
    raw_args: list[dict[str, Any]] | None = None,
    param_overrides: dict[int, str] | None = None,
) -> str:
    if not action_steps:
        return "            action_steps = []\n            await execute_action_steps(browser_session, action_steps, continue_on_error=True)"

    has_extract = any(
        isinstance(raw_step, int)
        and 0 <= raw_step < len(all_actions)
        and all_actions[raw_step].action_type == "extract"
        for raw_step in action_steps
    )

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

    if has_extract:
        block_lines.append("            _extraction_results = []")

    for group_type, group_data in groups:
        if group_type == "inline":
            step_indices: list[int] = group_data
            var_counter[0] += 1
            var_name = f"action_steps_{var_counter[0]}" if var_counter[0] > 1 else "action_steps"
            comment_lines = _render_action_comment_lines(step_indices, all_actions)
            literal = render_action_data_literal(step_indices, all_actions, param_overrides)
            block_lines.append(f"            {var_name} = json.loads({literal!r})")
            block_lines.append(comment_lines)
            if arg_parameters and raw_args:
                sub_code = render_substitute_params_code(raw_args, arg_parameters)
                block_lines.append(f"            {var_name} = substitute_parameters({var_name}, {sub_code})")
            if has_extract:
                block_lines.append(
                    f"            await execute_action_steps(browser_session, {var_name}, continue_on_error=True, extraction_results=_extraction_results)"
                )
            else:
                block_lines.append(
                    f"            await execute_action_steps(browser_session, {var_name}, continue_on_error=True)"
                )
        else:
            atom_action: ActionStep = group_data
            atom_id = atom_action.target_ref
            params_dict = atom_action.target_attributes or {}
            description_text = sanitize_inline_text(atom_action.description)
            safe_var = re.sub(r"[^a-zA-Z0-9]", "_", atom_id)
            atom_var = f"_atom_{safe_var}"
            params_code = render_atom_params_code(params_dict, arg_parameters)
            comment = f"            # atom: {atom_id}"
            if description_text:
                comment += f" — {description_text}"
            block_lines.append(comment)
            block_lines.append(f"            {atom_var} = load_atom(DOMAIN, {atom_id!r})")
            block_lines.append(f"            if {atom_var}:")
            block_lines.append(
                f"                _atom_actions = substitute_parameters(_normalize_atom_actions({atom_var}.actions), {params_code})"
            )
            if has_extract:
                block_lines.append(
                    "                await execute_action_steps(browser_session, _atom_actions, continue_on_error=True, extraction_results=_extraction_results)"
                )
            else:
                block_lines.append(
                    "                await execute_action_steps(browser_session, _atom_actions, continue_on_error=True)"
                )

    return "\n".join(block_lines)


def render_atom_params_code(params_dict: dict, arg_parameters: list[str]) -> str:
    if not params_dict:
        return "{}"
    entries: list[str] = []
    for key, val in params_dict.items():
        key_as_param = to_parameter_name(str(key))
        if key_as_param in arg_parameters:
            entries.append(f"{key!r}: {key_as_param}")
        else:
            val_as_param = to_parameter_name(str(val))
            if val_as_param in arg_parameters:
                entries.append(f"{key!r}: {val_as_param}")
            else:
                entries.append(f"{key!r}: {str(val)!r}")
    return "{" + ", ".join(entries) + "}"


def render_substitute_params_code(
    raw_args: list[dict[str, Any]],
    arg_parameters: list[str],
) -> str:
    entries: list[str] = []
    for i, arg in enumerate(raw_args or []):
        if not isinstance(arg, dict):
            continue
        raw_name = str(arg.get("name") or "").strip()
        if not raw_name or i >= len(arg_parameters):
            continue
        param_var = arg_parameters[i]
        entries.append(f"{raw_name!r}: {param_var}")
        if param_var != raw_name:
            entries.append(f"{param_var!r}: {param_var}")
    if not entries:
        return "{}"
    return "{" + ", ".join(entries) + "}"


def render_argument_decorators(args: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    decorators: list[str] = []
    parameters: list[str] = []
    used_names = {"json_mode", "ctx"}

    for index, arg in enumerate(args or []):
        if not isinstance(arg, dict):
            continue

        raw_name = str(arg.get("name") or arg.get("key") or f"arg_{index + 1}")
        parameter_name = unique_parameter_name(to_parameter_name(raw_name), used_names)
        used_names.add(parameter_name)
        parameters.append(parameter_name)

        positional = bool(arg.get("positional", False)) or str(arg.get("kind", "")).lower() in {
            "argument",
            "positional",
        }
        click_type = render_click_type(arg.get("type"), arg.get("choices"))
        required = bool(arg.get("required", False))
        default = arg.get("default")
        help_text = sanitize_inline_text(str(arg.get("description") or arg.get("help") or ""))

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
            short_flag = short_name if short_name.startswith("-") else f"-{short_name}"
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

        decorators.append(f"@click.option({', '.join(option_parts + option_kwargs)})")

    return decorators, parameters


def render_click_type(type_value: Any, choices: Any) -> str | None:
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


def _render_action_comment_lines(action_steps: list[int], all_actions: list[ActionStep]) -> str:
    lines: list[str] = []
    for raw_step in action_steps or []:
        if not isinstance(raw_step, int):
            lines.append("            # - 非法 action 索引，已跳过")
            continue
        if raw_step < 0 or raw_step >= len(all_actions):
            lines.append(f"            # - action[{raw_step}] 不存在，已跳过")
            continue

        action = all_actions[raw_step]
        action_type = sanitize_inline_text(action.action_type or "unknown")
        detail = action_detail(action)
        description = sanitize_inline_text(action.description)

        message = f"            # - [{raw_step}] {action_type}: {detail}"
        if description:
            message += f" | {description}"
        lines.append(message)

    if not lines:
        return "            # - 无操作步骤"
    return "\n".join(lines)


def render_action_data_literal(
    action_steps: list[int],
    all_actions: list[ActionStep],
    param_overrides: dict[int, str] | None = None,
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

        value = action.value
        if param_overrides and raw_step in param_overrides:
            value = param_overrides[raw_step]

        entry: dict[str, Any] = {
            "type": action.action_type,
            "ref": action.target_ref,
            "url": action.target_url,
            "value": value,
            "description": action.description,
            "target_name": action.target_name,
            "target_role": action.target_role,
            "target_attributes": action.target_attributes,
        }
        if action.action_type == "extract":
            entry["selector"] = action.selector
            entry["extract_mode"] = action.extract_mode
            entry["fields"] = action.fields_map
        payload.append(entry)
    return json.dumps(payload, ensure_ascii=False)


def action_detail(action: ActionStep) -> str:
    action_type = (action.action_type or "").lower()
    if action_type == "navigate":
        return sanitize_inline_text(action.target_url or action.page_url or "导航")
    if action_type == "click":
        return sanitize_inline_text(action.target_ref or "点击元素")
    if action_type == "type":
        target = sanitize_inline_text(action.target_ref or "输入框")
        value = sanitize_inline_text(action.value)
        return f"{target} <- {value}"
    if action_type == "select":
        target = sanitize_inline_text(action.target_ref or "下拉框")
        value = sanitize_inline_text(action.value)
        return f"{target} => {value}"
    if action_type == "submit":
        return "提交当前表单"

    target = sanitize_inline_text(action.target_ref or action.target_url or action.page_url)
    return target or "执行操作"


def render_args_payload(arg_parameters: list[str]) -> str:
    if not arg_parameters:
        return "{}"
    parts = [f"{name!r}: {name}" for name in arg_parameters]
    return "{" + ", ".join(parts) + "}"


def render_atom_command(atom: AtomCommand) -> str:
    atom_id = sanitize_inline_text(atom.atom_id) or "unknown-atom"
    command_source_name = sanitize_inline_text(atom.name) or atom_id
    command_name = to_command_name(command_source_name, 0)
    function_name = to_function_name(command_name)
    description = sanitize_docstring_text(atom.description or f"执行原子命令 {command_name}")
    missing_message = sanitize_inline_text(f"原子命令 '{atom_id}' 未找到")

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

        raw_name = sanitize_inline_text(parameter.name) or f"param_{index + 1}"
        option_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw_name.replace("_", "-").lower())
        option_name = re.sub(r"[_-]+", "-", option_name).strip("-")
        if not option_name:
            option_name = f"param-{index + 1}"

        parameter_name = unique_parameter_name(to_parameter_name(raw_name), used_names)
        used_names.add(parameter_name)

        option_parts = [
            repr(f"--{option_name}"),
            repr(parameter_name),
            f"required={bool(parameter.required)!r}",
        ]
        if parameter.default:
            option_parts.append(f"default={parameter.default!r}")

        help_text = sanitize_inline_text(parameter.description)
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
        cdp = cdp_from_context(ctx)
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


__all__ = [
    "render_command_block",
    "render_empty_command_block",
    "render_execution_blocks",
    "render_atom_command",
    "render_atom_params_code",
    "render_substitute_params_code",
    "render_argument_decorators",
    "render_click_type",
    "render_action_data_literal",
    "action_detail",
    "render_args_payload",
]
