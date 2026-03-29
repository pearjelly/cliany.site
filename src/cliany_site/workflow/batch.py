from __future__ import annotations

import csv
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cliany_site.workflow.engine import StepExecutor, WorkflowContext, interpolate_params
from cliany_site.workflow.models import StepDef

logger = logging.getLogger(__name__)


# ── 数据源加载 ───────────────────────────────────────────


class BatchDataError(Exception):
    pass


def load_batch_data(path: str | Path) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        raise BatchDataError(f"批量数据文件不存在: {p}")

    suffix = p.suffix.lower()

    if suffix == ".csv":
        return _load_csv(p)
    if suffix == ".json":
        return _load_json(p)

    raise BatchDataError(f"不支持的数据格式: {suffix}（支持 .csv / .json）")


def _load_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [{str(k): str(v) for k, v in row.items()} for row in reader]
    except (OSError, csv.Error) as exc:
        raise BatchDataError(f"CSV 读取失败: {exc}") from exc

    if not rows:
        raise BatchDataError("CSV 文件无数据行")
    return rows


def _load_json(path: Path) -> list[dict[str, str]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BatchDataError(f"JSON 读取失败: {exc}") from exc

    if isinstance(raw, list):
        if not raw:
            raise BatchDataError("JSON 数组为空")
        rows: list[dict[str, str]] = []
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                raise BatchDataError(f"JSON 第 {i} 项不是对象")
            rows.append({str(k): str(v) for k, v in item.items()})
        return rows

    raise BatchDataError("JSON 顶层必须是数组")


# ── 批量执行结果 ─────────────────────────────────────────


@dataclass
class BatchItemResult:
    index: int
    params: dict[str, str]
    success: bool
    data: Any = None
    error: str | None = None
    elapsed_ms: float = 0.0


@dataclass
class BatchResult:
    total: int
    succeeded: int = 0
    failed: int = 0
    results: list[BatchItemResult] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "results": [
                {
                    "index": r.index,
                    "params": r.params,
                    "success": r.success,
                    "error": r.error,
                    "elapsed_ms": round(r.elapsed_ms, 1),
                }
                for r in self.results
            ],
        }


# ── 批量执行引擎 ─────────────────────────────────────────


def _execute_one_item(
    index: int,
    row_params: dict[str, str],
    step: StepDef,
    executor: StepExecutor,
) -> BatchItemResult:
    context = WorkflowContext(prev_result={"data": row_params})
    merged = {**step.params, **row_params}
    final_params = interpolate_params(merged, context)

    start = time.monotonic()
    try:
        result = executor.execute_step(step.adapter, step.command, final_params)
        success = bool(result.get("success", False))
        elapsed = (time.monotonic() - start) * 1000
        err: str | None = None
        if not success:
            raw_err = result.get("error")
            if isinstance(raw_err, dict):
                err = str(raw_err.get("message", str(raw_err)))
            elif isinstance(raw_err, str):
                err = raw_err
            else:
                err = "执行失败"
        return BatchItemResult(
            index=index,
            params=final_params,
            success=success,
            data=result.get("data"),
            error=err,
            elapsed_ms=elapsed,
        )
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        return BatchItemResult(
            index=index,
            params=final_params,
            success=False,
            error=str(exc),
            elapsed_ms=elapsed,
        )


def run_batch(
    step: StepDef,
    data: list[dict[str, str]],
    executor: StepExecutor,
    concurrency: int = 1,
) -> BatchResult:
    overall_start = time.monotonic()
    results: list[BatchItemResult] = []

    if concurrency <= 1:
        for i, row in enumerate(data):
            logger.info("批量执行 %d/%d", i + 1, len(data))
            item_result = _execute_one_item(i, row, step, executor)
            results.append(item_result)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(_execute_one_item, i, row, step, executor): i for i, row in enumerate(data)}
            for future in as_completed(futures):
                item_result = future.result()
                results.append(item_result)

    results.sort(key=lambda r: r.index)

    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    elapsed_ms = (time.monotonic() - overall_start) * 1000

    return BatchResult(
        total=len(data),
        succeeded=succeeded,
        failed=failed,
        results=results,
        elapsed_ms=elapsed_ms,
    )
