from __future__ import annotations

from cliany_site.codegen.params import (
    auto_detect_params_from_actions,
    build_param_overrides,
    parameter_effect_action_indices,
)
from cliany_site.explorer.models import ActionStep, CommandSuggestion


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
