"""Build reaction-template and mechanism-selection tasks from derived pools."""

from __future__ import annotations

import argparse
import random

from data_generation.common.io import balanced_sample, read_json, write_json


def build_template_tasks(source_records: list[dict], template_dict: dict, target: int, seed: int) -> list[dict]:
    rows = []
    for item in source_records:
        meta = item.get("meta") or {}
        rxn_cls = item.get("rxn_cls") or meta.get("rxn_cls") or meta.get("reaction_class")
        tpl = template_dict.get(rxn_cls)
        if not tpl:
            continue
        rxn_smiles = meta.get("rxn_smiles") or item.get("rxn_smiles") or item.get("query", "")
        options = [tpl["smarts"]] + list(tpl.get("distractors", []))[:4]
        if len(options) < 5:
            continue
        rng = random.Random(f"{seed}:{rxn_smiles}")
        rng.shuffle(options)
        letters = "ABCDE"
        correct = letters[options.index(tpl["smarts"])]
        rows.append(
            {
                "task": "reaction",
                "subtask": "rxn_template",
                "query": "Reaction SMILES: " + rxn_smiles + "\n" + "\n".join(
                    f"{letter}. {option}" for letter, option in zip(letters, options)
                ),
                "gt": correct,
                "source": "derived_reaction_pool",
                "meta": {"rxn_cls": rxn_cls, "correct_smarts": tpl["smarts"]},
            }
        )
    selected = balanced_sample(rows, target=target, key_fn=lambda x: x["meta"]["rxn_cls"], seed=seed)
    for i, row in enumerate(selected, start=1):
        row["id"] = f"rxn_template_v2_{i:06d}"
    return selected


def build_mechanism_tasks(pool: list[dict], target: int, seed: int) -> list[dict]:
    rows = []
    for item in pool:
        out = {k: v for k, v in item.items() if k not in {"difficulty", "difficulty_score"}}
        out.setdefault("task", "reaction")
        out["subtask"] = "mech_sel"
        out.setdefault("source", "derived_mechanism_pool")
        rows.append(out)
    selected = balanced_sample(
        rows,
        target=target,
        key_fn=lambda x: x.get("rxn_cls") or (x.get("meta") or {}).get("rxn_cls", "unknown"),
        seed=seed,
    )
    for i, row in enumerate(selected, start=1):
        row["id"] = row.get("id") or f"mech_sel_v2_{i:06d}"
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward-json", required=True)
    parser.add_argument("--byproduct-json")
    parser.add_argument("--template-dict-json", required=True)
    parser.add_argument("--mechanism-pool-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    source = read_json(args.forward_json)
    if args.byproduct_json:
        source += read_json(args.byproduct_json)
    write_json(
        f"{args.output_dir}/rxn_template_v2.json",
        build_template_tasks(source, read_json(args.template_dict_json), args.target, args.seed),
    )
    write_json(
        f"{args.output_dir}/mech_sel_v2.json",
        build_mechanism_tasks(read_json(args.mechanism_pool_json), args.target, args.seed),
    )
    print("wrote rxn_template_v2.json and mech_sel_v2.json")


if __name__ == "__main__":
    main()

