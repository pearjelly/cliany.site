from __future__ import annotations

from typing import Any, TypedDict


class CompoundsMeta(TypedDict, total=False):
    role: str
    children: list[Any]
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
    commands: list[Any]
    canonical_actions: list[Any]
    selector_pool: list[Any]
    smoke: list[Any]
    heal_history: list[Any]
    axtree: dict
    capability: str | CapabilityMeta
    api_endpoints: list[Any]
