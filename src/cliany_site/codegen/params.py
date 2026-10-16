from __future__ import annotations

import re
from typing import Any

from cliany_site.codegen.dedup import action_fingerprint
from cliany_site.codegen.naming import argument_parameter_names, to_parameter_name
from cliany_site.explorer.models import ActionStep


class ParameterBindingError(ValueError):
    def __init__(
        self, action_index: int | None, action_type: str, *,
        parameter_name: str = "", reason: str = "unsupported_value",
    ):
        self.action_index = action_index
        self.action_type = action_type
        self.parameter_name = parameter_name
        self.reason = reason
        super().__init__(
            "参数绑定无效：声明参数没有影响实际执行字段，或被其他参数覆盖；请绑定实测输入或选择动作"
            if reason == "parameter_unused" else
            f"参数绑定无效：动作 {action_index} ({action_type}) 不执行参数化 value；请绑定实测输入或选择动作"
        )


def auto_detect_params_from_actions(
    step_indices: list[int],
    all_actions: list[ActionStep],
) -> list[dict[str, Any]]:
    param_pattern = re.compile(r"\{\{(\w+)\}\}")
    seen: set[str] = set()
    auto_args: list[dict[str, Any]] = []

    for idx in step_indices:
        if not (0 <= idx < len(all_actions)):
            continue
        action = all_actions[idx]
        for match in param_pattern.finditer(action.value or ""):
            param_name = match.group(1)
            if param_name not in seen:
                seen.add(param_name)
                auto_args.append(
                    {
                        "name": param_name,
                        "description": f"参数 {param_name}",
                        "required": True,
                    }
                )
    return auto_args


def build_param_overrides(
    args: list[dict[str, Any]] | None,
    step_indices: list[int],
    all_actions: list[ActionStep],
) -> dict[int, str]:
    overrides: dict[int, str] = {}
    step_set = set(step_indices)

    for arg in args or []:
        if not isinstance(arg, dict):
            continue
        name = str(arg.get("name") or "").strip()
        if not name:
            continue
        placeholder = f"{{{{{name}}}}}"

        primary_idx: int | None = None
        action_idx = arg.get("action_index")
        if "action_index" in arg:
            if type(action_idx) is not int or action_idx not in step_set:
                raise ValueError(f"参数 {name} 的 action_index 不属于当前命令")
            primary_idx = action_idx
        else:
            default = str(arg.get("default") or "").strip()
            if default:
                for idx in step_indices:
                    if idx in overrides:
                        continue
                    if 0 <= idx < len(all_actions) and (all_actions[idx].value or "").strip() == default:
                        primary_idx = idx
                        break

        if primary_idx is None:
            continue

        if 0 <= primary_idx < len(all_actions) and all_actions[primary_idx].action_type not in {"type", "select"}:
            raise ParameterBindingError(primary_idx, all_actions[primary_idx].action_type, parameter_name=name)

        overrides[primary_idx] = placeholder

        if 0 <= primary_idx < len(all_actions):
            fp = action_fingerprint(all_actions[primary_idx])
            for idx in step_indices:
                if idx == primary_idx or idx in overrides:
                    continue
                if 0 <= idx < len(all_actions) and action_fingerprint(all_actions[idx]) == fp:
                    overrides[idx] = placeholder

    _validate_parameter_effects(args or [], step_indices, all_actions, overrides)
    return overrides


def _validate_parameter_effects(
    args: list[dict[str, Any]], indices: list[int], actions: list[ActionStep], overrides: dict[int, str],
) -> None:
    variables = argument_parameter_names(args)
    owners = dict(zip(variables, (index for index, arg in enumerate(args) if isinstance(arg, dict)), strict=True))
    substitutions: dict[str, int] = {}
    # Match the emitted substitution dictionary, including alias precedence.
    for index, arg in enumerate(args):
        if not isinstance(arg, dict):
            continue
        name = str(arg.get("name") or "").strip()
        if name and index < len(variables):
            substitutions[name] = owners[variables[index]]
            substitutions[variables[index]] = owners[variables[index]]

    bound: set[int] = set()
    for index in indices:
        if not 0 <= index < len(actions):
            continue
        action = actions[index]
        fields = []
        if action.action_type in {"type", "select"}:
            fields.append(overrides.get(index, action.value))
        if action.action_type in {"type", "select", "click", "submit"}:
            fields.append(action.target_name)
        if action.action_type == "navigate":
            fields.append(action.target_url)
        if action.action_type == "extract" and not action.extract_target:
            fields.append(action.selector)
        for value in fields:
            if isinstance(value, str):
                bound.update(substitutions[token] for token in re.findall(r"\{\{(\w+)\}\}", value)
                             if token in substitutions)
        if action.action_type == "reuse_atom":
            for key, value in (action.target_attributes or {}).items():
                key_var, value_var = to_parameter_name(str(key)), to_parameter_name(str(value))
                if key_var in owners:
                    bound.add(owners[key_var])
                elif value_var in owners:
                    bound.add(owners[value_var])

    for index, arg in enumerate(args):
        if isinstance(arg, dict) and index not in bound:
            action_index = arg.get("action_index")
            raise ParameterBindingError(
                action_index if type(action_index) is int else None, "",
                parameter_name=str(arg.get("name") or ""), reason="parameter_unused",
            )


__all__ = [
    "ParameterBindingError",
    "auto_detect_params_from_actions",
    "build_param_overrides",
]
