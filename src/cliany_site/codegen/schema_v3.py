from __future__ import annotations

from typing import Any, List, TypedDict


class CompoundsMeta(TypedDict, total=False):
    role: str
    children: List[Any]
    ref: str


class PruningMeta(TypedDict, total=False):
    pruned_count: int
    max_depth: int
    reason: str


class CapabilityMeta(TypedDict, total=False):
    read: bool
    write: bool
    navigate: bool


class MetadataV3(TypedDict, total=False):
    schema_version: int
    domain: str
    generated_at: str
    generator_version: str
    commands: List[Any]
    canonical_actions: List[Any]
    selector_pool: List[Any]
    smoke: List[Any]
    heal_history: List[Any]
    axtree: dict
    capability: CapabilityMeta
    api_endpoints: List[Any]
