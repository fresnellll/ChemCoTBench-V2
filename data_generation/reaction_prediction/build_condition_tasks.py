"""Build condition-ranking and yield-prediction tasks from public HTE tables."""

from __future__ import annotations

import argparse
import itertools
import random
from collections import defaultdict

import pandas as pd

from data_generation.common.io import balanced_sample, write_json


def normalize_yield(value) -> float | None:
    try:
        y = float(value)
    except Exception:
        return None
    if y < 0 or y > 100:
        return None
    return y


def load_hte_csv(path: str, *, reaction_class: str, source_dataset: str) -> list[dict]:
    df = pd.read_csv(path)
    records = []
    for _, row in df.iterrows():
        reaction = str(row.get("rxn_smiles") or row.get("reaction_smiles") or row.get("reaction") or "")
        y = normalize_yield(row.get("yield") or row.get("yield_value") or row.get("YIELD"))
        if ">>" not in reaction or y is None:
            continue
        reactants, product = reaction.split(">>", 1)
        conditions = {
            "reagent": str(row.get("reagent", "")),
            "catalyst": str(row.get("catalyst", "")),
            "solvent": str(row.get("solvent", "")),
            "base": str(row.get("base", "")),
            "ligand": str(row.get("ligand", "")),
        }
        records.append(
            {
                "source_dataset": source_dataset,
                "reaction_class": reaction_class,
                "context_id": reaction,
                "reactants": reactants,
                "product": product,
                "conditions": {k: v for k, v in conditions.items() if v and v.lower() != "nan"},
                "yield_value": y,
            }
        )
    return records


def build_yield_records(pool: list[dict], target: int, seed: int) -> list[dict]:
    selected = balanced_sample(pool, target=target, key_fn=lambda x: x["reaction_class"], seed=seed)
    out = []
    for i, item in enumerate(selected, start=1):
        out.append(
            {
                "id": f"yield_pred_v2_{i:06d}",
                "task": "reaction",
                "subtask": "yield_pred",
                "query": (
                    f"Reaction type: {item['reaction_class']}\n"
                    f"Reactants: {item['reactants']}\n"
                    f"Product: {item['product']}\n"
                    f"Conditions: {item['conditions']}\n"
                    "Predict the reaction yield percentage."
                ),
                "gt": item["yield_value"],
                "source": "public_hte",
                "meta": item,
            }
        )
    return out


def build_condition_ranking(pool: list[dict], target: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_context: dict[str, list[dict]] = defaultdict(list)
    for item in pool:
        by_context[item["context_id"]].append(item)

    records = []
    for context_id, rows in by_context.items():
        if len(rows) < 3:
            continue
        rows = sorted(rows, key=lambda x: x["yield_value"], reverse=True)
        for combo in itertools.combinations(rows[: min(len(rows), 12)], 3):
            candidates = list(combo)
            rng.shuffle(candidates)
            labels = ["A", "B", "C"]
            labeled = []
            for label, cand in zip(labels, candidates):
                labeled.append({"label": label, "conditions": cand["conditions"], "observed_yield": cand["yield_value"]})
            gt = [
                row["label"]
                for row in sorted(labeled, key=lambda x: x["observed_yield"], reverse=True)
            ]
            first = candidates[0]
            query = (
                f"Reaction type: {first['reaction_class']}.\n"
                f"Reactants: {first['reactants']}\n"
                f"Product: {first['product']}\n"
                "Rank the candidate condition sets from highest to lowest expected yield.\n"
            )
            query += "\n".join(f"{row['label']}: {row['conditions']}" for row in labeled)
            records.append(
                {
                    "task": "reaction",
                    "subtask": "condition_ranking",
                    "query": query,
                    "gt": gt,
                    "source": "public_hte",
                    "meta": {**first, "candidates": labeled, "top1_label": gt[0]},
                }
            )
            break

    selected = balanced_sample(records, target=target, key_fn=lambda x: x["meta"]["reaction_class"], seed=seed)
    for i, row in enumerate(selected, start=1):
        row["id"] = f"cond_rank_v2_{i:06d}"
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hte-csv", action="append", required=True)
    parser.add_argument("--reaction-class", action="append", required=True)
    parser.add_argument("--source-name", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target-yield", type=int, default=200)
    parser.add_argument("--target-ranking", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not (len(args.hte_csv) == len(args.reaction_class) == len(args.source_name)):
        raise ValueError("--hte-csv, --reaction-class, and --source-name must have the same length.")

    pool = []
    for path, cls, name in zip(args.hte_csv, args.reaction_class, args.source_name):
        pool.extend(load_hte_csv(path, reaction_class=cls, source_dataset=name))

    write_json(f"{args.output_dir}/yield_pred_v2.json", build_yield_records(pool, args.target_yield, args.seed))
    write_json(
        f"{args.output_dir}/condition_ranking_v2.json",
        build_condition_ranking(pool, args.target_ranking, args.seed),
    )
    print(f"built condition/yield tasks from {len(pool)} HTE records")


if __name__ == "__main__":
    main()

