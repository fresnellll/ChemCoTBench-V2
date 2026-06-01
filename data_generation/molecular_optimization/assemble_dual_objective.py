"""Assemble dual-objective molecular-optimization records from multistep MMP paths."""

from __future__ import annotations

import argparse
import itertools

from data_generation.common.chem import molecular_weight, ring_count, tanimoto
from data_generation.common.io import balanced_sample, deduplicate, read_json, write_json

OBJECTIVE_PAIRS = [
    ("qed", "solubility"),
    ("logp", "solubility"),
    ("drd", "logp"),
    ("drd", "solubility"),
    ("logp", "qed"),
    ("gsk", "logp"),
]

THRESHOLDS = {
    "qed": 0.3,
    "drd": 0.3,
    "jnk": 0.3,
    "gsk": 0.3,
    "logp": 0.5,
    "solubility": 0.5,
}


def load_candidates(paths: list[str], objective_pairs: list[tuple[str, str]]) -> list[dict]:
    rows = []
    for path in paths:
        for item in read_json(path):
            smiles_path = item.get("two_step_path") or item.get("path_smiles")
            prop_path = item.get("mol_property") or item.get("path_props")
            if not smiles_path or not prop_path or len(smiles_path) != len(prop_path):
                continue
            src = smiles_path[0]
            tgt = smiles_path[-1]
            for p1, p2 in objective_pairs:
                d1 = float(prop_path[-1][p1]) - float(prop_path[0][p1])
                d2 = float(prop_path[-1][p2]) - float(prop_path[0][p2])
                if d1 < THRESHOLDS[p1] or d2 < THRESHOLDS[p2]:
                    continue
                rows.append(
                    {
                        "objective_props": [p1, p2],
                        "objective_thresholds": {p1: THRESHOLDS[p1], p2: THRESHOLDS[p2]},
                        "path_smiles": smiles_path,
                        "path_props": prop_path,
                        "src": src,
                        "tgt": tgt,
                        "path_steps": len(smiles_path) - 1,
                    }
                )
    return deduplicate(rows, lambda x: (tuple(x["objective_props"]), x["src"], x["tgt"]))


def enrich(item: dict, idx: int) -> dict:
    src_props = item["path_props"][0]
    tgt_props = item["path_props"][-1]
    out = {
        "id": f"multi_opt_{idx:04d}",
        "task": "mol_opt_multi",
        "subtask": "_".join(item["objective_props"]),
        "objective_props": item["objective_props"],
        "objective_thresholds": item["objective_thresholds"],
        "path_steps": item["path_steps"],
        "path_smiles": item["path_smiles"],
        "src": item["src"],
        "tgt": item["tgt"],
        "tanimoto": tanimoto(item["src"], item["tgt"]),
        "src_mw": molecular_weight(item["src"]),
        "src_rings": ring_count(item["src"]),
    }
    for prop in ["qed", "drd", "jnk", "gsk", "logp", "solubility"]:
        out[f"src_{prop}"] = float(src_props[prop])
        out[f"tgt_{prop}"] = float(tgt_props[prop])
        out[f"delta_{prop}"] = float(tgt_props[prop]) - float(src_props[prop])
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--target-per-pair", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    all_rows = load_candidates(args.input_json, OBJECTIVE_PAIRS)
    selected_all = []
    idx = itertools.count(1)
    for pair in OBJECTIVE_PAIRS:
        pair_rows = [x for x in all_rows if tuple(x["objective_props"]) == pair]
        selected = balanced_sample(pair_rows, target=args.target_per_pair, key_fn=lambda x: x["path_steps"], seed=args.seed)
        enriched = [enrich(item, next(idx)) for item in selected]
        selected_all.extend(enriched)
        pair_name = "__".join(pair)
        write_json(f"{args.output_root}/by_pair/{pair_name}_v2.json", enriched)
        print(f"{pair_name}: wrote {len(enriched)} records")
    write_json(f"{args.output_root}/final_multi_mmp_v2.json", selected_all)


if __name__ == "__main__":
    main()

