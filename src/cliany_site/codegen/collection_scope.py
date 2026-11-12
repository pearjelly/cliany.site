from __future__ import annotations

from cliany_site.codegen.naming import argument_parameter_names
from cliany_site.codegen.params import (
    auto_detect_params_from_actions,
    build_param_overrides,
    parameter_effect_action_indices,
)
from cliany_site.explorer.models import ActionStep, CommandSuggestion

RESULT_LIMIT_PARAMETER = "_returned_row_limit"


class CollectionScopeError(ValueError):
    """A business collection cannot depend on a later command input."""


def validate_discovery_purposes(actions: list[ActionStep]) -> None:
    if any(action.purpose not in {"workflow", "probe", "baseline"}
           or (action.purpose != "workflow" and action.action_type != "extract") for action in actions):
        raise CollectionScopeError("只有只读 extract 可以声明探测或固定基线用途")


def validate_collection_scope(command: CommandSuggestion, actions: list[ActionStep]) -> None:
    validate_discovery_purposes(actions)
    indices = [index for index in command.action_steps if isinstance(index, int) and 0 <= index < len(actions)]
    if any(actions[index].purpose == "probe" for index in indices):
        raise CollectionScopeError("结构探测不能进入业务重放；探测用途须在执行前声明并保留原历史索引")
    args = command.args or auto_detect_params_from_actions(indices, actions)
    if command.result_limit:
        extracts = [index for index in indices if actions[index].action_type == "extract"]
        if (not indices or extracts != [indices[-1]] or actions[indices[-1]].extract_mode != "list"
                or actions[indices[-1]].purpose != "workflow" or not actions[indices[-1]].extract_target
                or any(actions[index].action_type == "reuse_atom" for index in indices)):
            raise CollectionScopeError("--limit 仅支持单一、已观测且位于末尾的业务列表")
        if RESULT_LIMIT_PARAMETER in argument_parameter_names(args) or any(
            str(arg.get(key) or "").strip().lstrip("-").split("/", 1)[0] == "limit"
            for arg in args if isinstance(arg, dict) for key in ("name", "key", "option", "flag", "short")
        ):
            raise CollectionScopeError("输出 --limit 与现有页面参数冲突")
    if not args:
        return
    overrides = build_param_overrides(args, indices, actions)
    effects = parameter_effect_action_indices(args, indices, actions, overrides)
    effect_indices = {position for positions in effects.values() for position in positions}
    input_seen = False
    for index in indices:
        input_seen = input_seen or index in effect_indices
        action = actions[index]
        if (action.action_type == "extract" and action.purpose != "baseline"
                and not input_seen):
            raise CollectionScopeError(
                "业务读取发生在任何命令参数生效前；不能将固定查询的探测结果混入参数化结果。"
                "请重新探索；结构探测或用户明确要求的固定基线必须在执行前声明，不能事后改写历史用途"
            )
