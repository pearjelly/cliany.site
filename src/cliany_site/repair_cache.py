from pathlib import Path
from typing import TypedDict
import json
import hashlib
from datetime import datetime, UTC

from cliany_site.atomic_io import atomic_read_json, atomic_write_json


class RepairCacheEntry(TypedDict):
    selector_old: str
    selector_new: str
    axtree_subtree_hash: str
    success_count: int
    last_used_iso: str


def cache_path(domain: str) -> Path:
    return Path.home() / ".cliany-site" / "adapters" / domain / "repair-cache.json"


def load(domain: str) -> dict:
    path = cache_path(domain)
    return atomic_read_json(path, {})


def lookup(domain: str, selector_old: str, axtree_subtree_hash: str) -> str | None:
    data = load(domain)
    key = f"{selector_old}:{axtree_subtree_hash}"
    entry = data.get(key)
    if entry:
        return entry['selector_new']
    return None


def record(domain: str, selector_old: str, selector_new: str, axtree_subtree_hash: str) -> None:
    data = load(domain)
    key = f"{selector_old}:{axtree_subtree_hash}"
    now_iso = datetime.now(UTC).isoformat()
    if key in data:
        data[key]['success_count'] += 1
        data[key]['last_used_iso'] = now_iso
    else:
        data[key] = RepairCacheEntry(
            selector_old=selector_old,
            selector_new=selector_new,
            axtree_subtree_hash=axtree_subtree_hash,
            success_count=1,
            last_used_iso=now_iso
        )
    if len(data) > 100:
        sorted_keys = sorted(data.keys(), key=lambda k: data[k]['last_used_iso'])
        to_remove = sorted_keys[:len(data) - 100]
        for k in to_remove:
            del data[k]
    path = cache_path(domain)
    atomic_write_json(path, data)


def compute_subtree_hash(node_dict: dict) -> str:
    json_str = json.dumps(node_dict, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()