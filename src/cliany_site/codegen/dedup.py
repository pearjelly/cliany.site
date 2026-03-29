from __future__ import annotations

import re

from cliany_site.explorer.models import ActionStep


def action_fingerprint(action: ActionStep) -> tuple[str, str, str]:
    return (
        action.action_type or "",
        action.target_name or "",
        action.target_role or "",
    )


def deduplicate_parameterized_actions(
    step_indices: list[int],
    all_actions: list[ActionStep],
    param_overrides: dict[int, str] | None = None,
) -> list[int]:
    if not step_indices:
        return step_indices

    param_pattern = re.compile(r"\{\{\w+\}\}")
    overrides = param_overrides or {}

    param_positions: list[int] = []
    for pos, idx in enumerate(step_indices):
        if idx in overrides or (0 <= idx < len(all_actions) and param_pattern.search(all_actions[idx].value or "")):
            param_positions.append(pos)

    if not param_positions:
        return step_indices

    to_remove: set[int] = set()

    for param_pos in param_positions:
        param_idx = step_indices[param_pos]
        fp = action_fingerprint(all_actions[param_idx])
        for other_pos in range(len(step_indices)):
            if other_pos == param_pos or other_pos in to_remove:
                continue
            if other_pos in param_positions:
                continue
            other_idx = step_indices[other_pos]
            if not (0 <= other_idx < len(all_actions)):
                continue
            other_action = all_actions[other_idx]
            if (
                action_fingerprint(other_action) == fp
                and not param_pattern.search(other_action.value or "")
                and other_idx not in overrides
            ):
                to_remove.add(other_pos)

    if to_remove:
        first_removed = min(to_remove)
        first_param = min(param_positions)
        for pos in range(first_removed, first_param):
            if pos in to_remove:
                continue
            idx = step_indices[pos]
            if not (0 <= idx < len(all_actions)):
                continue
            action = all_actions[idx]
            if action.value:
                continue
            fp = action_fingerprint(action)
            for later_pos in range(first_param, len(step_indices)):
                if later_pos in to_remove:
                    continue
                later_idx = step_indices[later_pos]
                if 0 <= later_idx < len(all_actions):
                    later_action = all_actions[later_idx]
                    if action_fingerprint(later_action) == fp and not later_action.value:
                        to_remove.add(pos)
                        break

    if not to_remove:
        return step_indices

    return [idx for pos, idx in enumerate(step_indices) if pos not in to_remove]


def remove_consecutive_duplicate_clicks(
    step_indices: list[int],
    all_actions: list[ActionStep],
) -> list[int]:
    if len(step_indices) < 2:
        return step_indices

    result: list[int] = [step_indices[0]]
    for i in range(1, len(step_indices)):
        idx = step_indices[i]
        prev_idx = result[-1]
        if not (0 <= idx < len(all_actions) and 0 <= prev_idx < len(all_actions)):
            result.append(idx)
            continue
        cur = all_actions[idx]
        prev = all_actions[prev_idx]
        if (
            cur.action_type == prev.action_type
            and cur.action_type in ("click", "submit")
            and action_fingerprint(cur) == action_fingerprint(prev)
        ):
            continue
        result.append(idx)
    return result


def remove_redundant_duplicate_actions(
    step_indices: list[int],
    all_actions: list[ActionStep],
    param_overrides: dict[int, str],
) -> list[int]:
    seen: dict[tuple[str, str, str, str], int] = {}
    keep: list[int] = []
    for idx in step_indices:
        if not (0 <= idx < len(all_actions)):
            keep.append(idx)
            continue
        action = all_actions[idx]
        effective_value = param_overrides.get(idx, action.value or "")
        key = (*action_fingerprint(action), effective_value)
        if key in seen:
            continue
        seen[key] = idx
        keep.append(idx)
    return keep


__all__ = [
    "action_fingerprint",
    "deduplicate_parameterized_actions",
    "remove_consecutive_duplicate_clicks",
    "remove_redundant_duplicate_actions",
]
