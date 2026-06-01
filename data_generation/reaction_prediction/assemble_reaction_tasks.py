"""Assemble reaction-prediction tasks from derived reaction pools."""

from __future__ import annotations

import argparse
from collections import defaultdict

from data_generation.common.io import balanced_sample, deduplicate, read_json, write_json

TASK_FILES = {
    "forward": "fs_major_product_gemini_good_clean.json",
    "byproduct": "fs_by_product_gemini_good_clean.json",
    "retro": "retro_pred_gemini_good_full_clean.json",
    "nepp": "nepp_wo_H_gemini_good_full_clean.json",
    "rcr_catalyst": "rcr_catalyst_gemini_good_cls_full_clean.json",
    "rcr_reagent": "rcr_reagent_gemini_good_cls_full_clean.json",
    "rcr_solvent": "rcr_solvent_gemini_good_cls_full_clean.json",
}

DROP_FIELDS = {"difficulty", "difficulty_score"}


def task_key(item: dict) -> object:
    meta = item.get("meta") or {}
    if isinstance(meta, str):
        import json

        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = {}
    return item.get("rxn_cls") or meta.get("rxn_cls") or meta.get("reaction_class") or "unknown"


def clean_record(item: dict, subtask: str, idx: int) -> dict:
    out = {k: v for k, v in item.items() if k not in DROP_FIELDS}
    out.setdefault("task", "reaction")
    out["subtask"] = subtask
    out["id"] = out.get("id") or f"{subtask}_v2_{idx:06d}"
    out.setdefault("source", "derived_reaction_pool")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target-per-task", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    for subtask, filename in TASK_FILES.items():
        records = read_json(f"{args.pool_dir}/{filename}")
        records = deduplicate(records, lambda x: (x.get("query"), str(x.get("gt"))))
        selected = balanced_sample(records, target=args.target_per_task, key_fn=task_key, seed=args.seed)
        write_json(
            f"{args.output_dir}/{subtask}_v2.json",
            [clean_record(item, subtask, i + 1) for i, item in enumerate(selected)],
        )
        print(f"{subtask}: wrote {len(selected)} records")


if __name__ == "__main__":
    main()

