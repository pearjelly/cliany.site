from __future__ import annotations

import re
from typing import Any

from cliany_site.codegen.naming import argument_parameter_names, to_parameter_name
from cliany_site.explorer.models import ActionStep


def value_action_on_noneditable_link(action_type: str, role: str, attributes: Any) -> bool:
    kind = str(action_type or "").strip().casefold()
    if kind not in {"type", "select"} or str(role or "").strip().casefold() != "link":
        return False
    editable = (isinstance(attributes, dict) and "contenteditable" in attributes
                and str(attributes["contenteditable"]).strip().casefold() in {"", "true", "plaintext-only"})
    return kind == "select" or not editable


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
            "命令动作无效：不可输入的链接不能接收输入或选择值；请重新 explore"
            if reason == "value_target_incompatible" else
            "参数绑定无效：多个录制值匹配默认值；请显式声明 action_index 或 action_indices"
            if reason == "ambiguous_default" else
            "参数绑定无效：声明参数没有影响实际执行字段，或被其他参数覆盖；请绑定实测输入或选择动作"
            if reason == "parameter_unused" else
            f"参数绑定无效：动作 {action_index} ({action_type}) 不执行参数化 value；请绑定实测输入或选择动作"
        )


def declared_parameter_indices(arg: dict[str, Any], step_indices: list[int]) -> list[int] | None:
    fields = [name for name in ("action_index", "action_indices") if name in arg]
    if not fields:
        return None
    indices = [arg["action_index"]] if fields == ["action_index"] else arg.get("action_indices")
    if (len(fields) != 1 or not isinstance(indices, list) or not indices
            or any(type(index) is not int or index not in step_indices for index in indices)
            or len(set(indices)) != len(indices)):
        raise ValueError(f"参数 {arg.get('name', '')} 的索引无效、重复或不属于当前命令")
    return indices


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

    for index in step_indices:
        if 0 <= index < len(all_actions):
            action = all_actions[index]
            if value_action_on_noneditable_link(action.action_type, action.target_role, action.target_attributes):
                raise ParameterBindingError(index, action.action_type, reason="value_target_incompatible")

    for arg in args or []:
        if not isinstance(arg, dict):
            continue
        name = str(arg.get("name") or "").strip()
        if not name:
            continue
        placeholder = f"{{{{{name}}}}}"

        selected = declared_parameter_indices(arg, step_indices)
        if selected is None:
            default = str(arg.get("default") or "").strip()
            if default:
                selected = [idx for idx in step_indices if idx not in overrides
                            and 0 <= idx < len(all_actions) and (all_actions[idx].value or "").strip() == default]
                if len(selected) > 1:
                    raise ParameterBindingError(None, "", parameter_name=name, reason="ambiguous_default")

        if not selected:
            continue

        for index in selected:
            if 0 <= index < len(all_actions) and all_actions[index].action_type not in {"type", "select"}:
                raise ParameterBindingError(index, all_actions[index].action_type, parameter_name=name)
            overrides[index] = placeholder

    parameter_effect_action_indices(args or [], step_indices, all_actions, overrides)
    return overrides


def parameter_effect_action_indices(
    args: list[dict[str, Any]], indices: list[int], actions: list[ActionStep], overrides: dict[int, str],
) -> dict[str, list[int]]:
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

    effects: dict[int, set[int]] = {}
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
                for token in re.findall(r"\{\{(\w+)\}\}", value):
                    if token in substitutions:
                        effects.setdefault(substitutions[token], set()).add(index)
        if action.action_type == "reuse_atom":
            for key, value in (action.target_attributes or {}).items():
                key_var, value_var = to_parameter_name(str(key)), to_parameter_name(str(value))
                if key_var in owners:
                    effects.setdefault(owners[key_var], set()).add(index)
                elif value_var in owners:
                    effects.setdefault(owners[value_var], set()).add(index)

    for index, arg in enumerate(args):
        if isinstance(arg, dict) and index not in effects:
            action_index = arg.get("action_index")
            raise ParameterBindingError(
                action_index if type(action_index) is int else None, "",
                parameter_name=str(arg.get("name") or ""), reason="parameter_unused",
            )
    return {str(args[index].get("name") or ""): sorted(positions) for index, positions in effects.items()}


__all__ = [
    "ParameterBindingError",
    "auto_detect_params_from_actions",
    "build_param_overrides",
    "declared_parameter_indices",
    "parameter_effect_action_indices",
]
