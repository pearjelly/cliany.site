from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


@dataclass
class ElementDiff:
    ref: str
    name: str
    role: str
    status: str  # "missing" | "changed" | "matched"
    best_match_ref: str = ""
    best_match_name: str = ""
    best_match_score: int = 0


@dataclass
class HealthCheckResult:
    domain: str
    command_name: str
    snapshot_count: int
    current_count: int
    matched: int = 0
    missing: int = 0
    changed: int = 0
    diff_ratio: float = 0.0
    healthy: bool = True
    diffs: list[ElementDiff] = field(default_factory=list)
    fixes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "command_name": self.command_name,
            "snapshot_count": self.snapshot_count,
            "current_count": self.current_count,
            "matched": self.matched,
            "missing": self.missing,
            "changed": self.changed,
            "diff_ratio": round(self.diff_ratio, 4),
            "healthy": self.healthy,
            "diffs": [
                {
                    "ref": d.ref,
                    "name": d.name,
                    "role": d.role,
                    "status": d.status,
                    "best_match_ref": d.best_match_ref,
                    "best_match_name": d.best_match_name,
                    "best_match_score": d.best_match_score,
                }
                for d in self.diffs
            ],
            "fixes": self.fixes,
        }


DIFF_THRESHOLD = 0.30


def _score_element_match(
    snapshot_elem: dict[str, Any],
    candidate: dict[str, Any],
) -> int:
    score = 0

    snap_name = _normalize_text(snapshot_elem.get("target_name") or snapshot_elem.get("name", ""))
    cand_name = _normalize_text(candidate.get("name", ""))
    if snap_name and cand_name:
        if cand_name == snap_name:
            score += 40
        elif snap_name in cand_name or cand_name in snap_name:
            score += 20

    snap_role = _normalize_text(snapshot_elem.get("target_role") or snapshot_elem.get("role", ""))
    cand_role = _normalize_text(candidate.get("role", ""))
    if snap_role and cand_role and snap_role == cand_role:
        score += 15

    snap_attrs = snapshot_elem.get("target_attributes") or snapshot_elem.get("attributes") or {}
    cand_attrs = candidate.get("attributes") or {}
    if isinstance(snap_attrs, dict) and isinstance(cand_attrs, dict):
        for key, weight in {
            "id": 30,
            "name": 20,
            "aria-label": 20,
            "placeholder": 18,
            "href": 18,
            "title": 12,
            "type": 12,
        }.items():
            sv = _normalize_text(snap_attrs.get(key, ""))
            cv = _normalize_text(cand_attrs.get(key, ""))
            if sv and cv and sv == cv:
                score += weight

    return score


MATCH_THRESHOLD = 30


def compare_elements(
    snapshot_elements: list[dict[str, Any]],
    current_elements: list[dict[str, Any]],
    domain: str = "",
    command_name: str = "",
) -> HealthCheckResult:
    result = HealthCheckResult(
        domain=domain,
        command_name=command_name,
        snapshot_count=len(snapshot_elements),
        current_count=len(current_elements),
    )

    if not snapshot_elements:
        result.healthy = True
        return result

    used_candidates: set[int] = set()

    for snap_elem in snapshot_elements:
        snap_name = snap_elem.get("target_name") or snap_elem.get("name", "")
        snap_role = snap_elem.get("target_role") or snap_elem.get("role", "")
        snap_ref = snap_elem.get("target_ref") or snap_elem.get("ref", "")

        best_score = 0
        best_idx = -1
        best_cand: dict[str, Any] = {}

        for ci, cand in enumerate(current_elements):
            if ci in used_candidates:
                continue
            s = _score_element_match(snap_elem, cand)
            if s > best_score:
                best_score = s
                best_idx = ci
                best_cand = cand

        if best_score >= MATCH_THRESHOLD and best_idx >= 0:
            used_candidates.add(best_idx)
            if best_score >= 55:
                result.matched += 1
                result.diffs.append(
                    ElementDiff(
                        ref=str(snap_ref),
                        name=str(snap_name),
                        role=str(snap_role),
                        status="matched",
                        best_match_ref=str(best_cand.get("ref", "")),
                        best_match_name=str(best_cand.get("name", "")),
                        best_match_score=best_score,
                    )
                )
            else:
                result.changed += 1
                diff = ElementDiff(
                    ref=str(snap_ref),
                    name=str(snap_name),
                    role=str(snap_role),
                    status="changed",
                    best_match_ref=str(best_cand.get("ref", "")),
                    best_match_name=str(best_cand.get("name", "")),
                    best_match_score=best_score,
                )
                result.diffs.append(diff)
                result.fixes.append(
                    {
                        "old_ref": str(snap_ref),
                        "old_name": str(snap_name),
                        "new_ref": str(best_cand.get("ref", "")),
                        "new_name": str(best_cand.get("name", "")),
                        "score": best_score,
                    }
                )
        else:
            result.missing += 1
            result.diffs.append(
                ElementDiff(
                    ref=str(snap_ref),
                    name=str(snap_name),
                    role=str(snap_role),
                    status="missing",
                    best_match_ref=str(best_cand.get("ref", "")) if best_cand else "",
                    best_match_name=str(best_cand.get("name", "")) if best_cand else "",
                    best_match_score=best_score,
                )
            )

    broken = result.missing + result.changed
    result.diff_ratio = broken / len(snapshot_elements) if snapshot_elements else 0.0
    result.healthy = result.diff_ratio < DIFF_THRESHOLD

    return result


def apply_selector_fixes(
    actions_data: list[dict[str, Any]],
    fixes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not fixes:
        return actions_data

    fix_map: dict[str, dict[str, Any]] = {}
    for fix_entry in fixes:
        old_ref = fix_entry.get("old_ref", "")
        old_name = _normalize_text(fix_entry.get("old_name", ""))
        if old_ref:
            fix_map[old_ref] = fix_entry
        if old_name:
            fix_map[f"name:{old_name}"] = fix_entry

    patched = 0
    for action in actions_data:
        if not isinstance(action, dict):
            continue

        ref = str(action.get("ref", "") or action.get("target_ref", ""))
        name = _normalize_text(action.get("target_name", ""))

        matched_fix = fix_map.get(ref) or fix_map.get(f"name:{name}")
        if not matched_fix:
            continue

        new_ref = matched_fix.get("new_ref", "")
        new_name = matched_fix.get("new_name", "")
        if new_ref and ref:
            if "ref" in action:
                action["ref"] = new_ref
            if "target_ref" in action:
                action["target_ref"] = new_ref
            patched += 1
        if new_name and "target_name" in action:
            action["target_name"] = new_name

    if patched:
        logger.info("热修复: 更新了 %d 个 selector", patched)

    return actions_data
