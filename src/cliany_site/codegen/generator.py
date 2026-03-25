from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult


class AdapterGenerator:
    def generate(self, explore_result: ExploreResult, domain: str) -> str:
        """将探索结果生成为可执行的 Python/Click 模块代码字符串"""
        generated_at = datetime.now(timezone.utc).isoformat()
        domain_doc = self._sanitize_docstring_text(domain)
        source_url = self._extract_source_url(explore_result)
        workflow_description = self._infer_workflow_description(explore_result)
        source_url_literal = source_url or f"https://{domain}"

        command_blocks: list[str] = []
        for index, command in enumerate(explore_result.commands):
            command_blocks.append(
                self._render_command_block(command, explore_result.actions, index)
            )

        if not command_blocks:
            command_blocks.append(self._render_empty_command_block())

        commands_text = "\n\n".join(command_blocks)

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
from cliany_site.errors import CDP_UNAVAILABLE, SESSION_EXPIRED, EXECUTION_FAILED

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


{commands_text}


if __name__ == "__main__":
    cli()
'''

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
            "@click.pass_context",
            *arg_decorators,
        ]
        decorators_text = "\n".join(decorator_lines)

        function_args = [
            "ctx: click.Context",
            "json_mode: bool | None",
            *arg_parameters,
        ]
        function_signature = ", ".join(function_args)
        args_payload = self._render_args_payload(arg_parameters)
        action_comment_lines = self._render_action_comment_lines(
            command.action_steps, all_actions
        )
        action_data_literal = self._render_action_data_literal(
            command.action_steps, all_actions
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
            action_steps = json.loads({action_data_literal!r})
{action_comment_lines}
            await execute_action_steps(browser_session, action_steps, continue_on_error=True)
            return success_response({{"status": "completed", "command": "{command_name}", "args": {args_payload}}})
        except Exception as e:
            return error_response(EXECUTION_FAILED, str(e))
        finally:
            await cdp.disconnect()
    result = asyncio.run(_run())
    print_response(result, _resolve_json_mode(json_mode))
'''

    def _render_empty_command_block(self) -> str:
        return '''@cli.command("run-workflow")
@click.option("--json", "json_mode", is_flag=True, default=None, help="JSON 输出")
@click.pass_context
def run_workflow(ctx: click.Context, json_mode: bool | None):
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
            return error_response(EXECUTION_FAILED, str(e))
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


def save_adapter(domain: str, code: str, metadata: dict | None = None) -> str:
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
