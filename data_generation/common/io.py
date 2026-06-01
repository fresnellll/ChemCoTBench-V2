"""I/O and sampling helpers for ChemCoTBench-V2 construction scripts."""

from __future__ import annotations

import json
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable, Sequence, TypeVar

T = TypeVar("T")


def project_root() -> Path:
    return Path(os.environ.get("CHEMCOTBENCH_ROOT", Path.cwd())).resolve()


def read_json(path: str | Path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def deduplicate(records: Iterable[dict], key_fn: Callable[[dict], object]) -> list[dict]:
    seen = set()
    out = []
    for rec in records:
        key = key_fn(rec)
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out


def balanced_sample(
    records: Sequence[T],
    *,
    target: int,
    key_fn: Callable[[T], object],
    seed: int = 42,
) -> list[T]:
    """Sample up to target records while spreading coverage across key groups."""
    rng = random.Random(seed)
    groups: dict[object, list[T]] = defaultdict(list)
    for rec in records:
        groups[key_fn(rec)].append(rec)
    for rows in groups.values():
        rng.shuffle(rows)

    keys = list(groups)
    rng.shuffle(keys)
    selected: list[T] = []
    while len(selected) < target and keys:
        next_keys = []
        for key in keys:
            if groups[key] and len(selected) < target:
                selected.append(groups[key].pop())
            if groups[key]:
                next_keys.append(key)
        keys = next_keys
    rng.shuffle(selected)
    return selected


def sequential_sample(records: Sequence[T], *, target: int, seed: int = 42) -> list[T]:
    rng = random.Random(seed)
    rows = list(records)
    rng.shuffle(rows)
    return rows[:target]

