"""Assemble the active MolEdit benchmark records from generated instructions."""

from __future__ import annotations

import argparse
from collections import defaultdict

from data_generation.common.io import balanced_sample, deduplicate, read_json, write_json

DROP_FIELDS = {
    "difficulty",
    "difficulty_score",
    "rxn_cls_difficulty",
    "fg_complexity_val",
}


def quality_ok(item: dict, *, min_agreement: float, min_confidence: float, min_valid_rounds: int) -> bool:
    if item.get("valid_rounds", 0) < min_valid_rounds:
        return False
    if float(item.get("instruction_agreement", 0.0)) < min_agreement:
        return False
    if float(item.get("mean_confidence", 0.0)) < min_confidence:
        return False
    text = item.get("Instruction") or item.get("instruction") or ""
    if not text:
        return False
    bad_terms = ["temperature", "solvent", "catalyst", "reagent condition"]
    return not any(term in text.lower() for term in bad_terms)


def release_record(item: dict, idx: int) -> dict:
    out = {
        "id": f"moledit_{idx:05d}",
        "Instruction": item.get("Instruction") or item.get("instruction"),
        "molecule": item["src"],
        "reference": item["tgt"],
        "edit_type": item["edit_type"],
        "rxn_cls": item.get("reaction_class") or item.get("rxn_cls", "unknown"),
        "schneider_class": item.get("schneider_class", ""),
        "changed_group": " ".join(
            x for x in [item.get("leaving_group_smiles", ""), item.get("incoming_group_smiles", "")] if x
        ),
        "position_description": item.get("site", ""),
        "instruction_agreement": item.get("instruction_agreement"),
        "mean_confidence": item.get("mean_confidence"),
        "valid_rounds": item.get("valid_rounds"),
        "tanimoto": item.get("source_tanimoto") or item.get("tanimoto"),
        "heavy_atom_diff": item.get("heavy_atom_delta") or item.get("heavy_atom_diff"),
        "source": item.get("source", "Schneider50K"),
    }
    return {k: v for k, v in out.items() if k not in DROP_FIELDS and v is not None}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target-per-type", type=int, default=300)
    parser.add_argument("--min-agreement", type=float, default=0.7)
    parser.add_argument("--min-confidence", type=float, default=0.7)
    parser.add_argument("--min-valid-rounds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = [
        x
        for x in read_json(args.input_json)
        if quality_ok(
            x,
            min_agreement=args.min_agreement,
            min_confidence=args.min_confidence,
            min_valid_rounds=args.min_valid_rounds,
        )
    ]
    rows = deduplicate(rows, lambda x: (x["src"], x["tgt"]))

    by_type: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_type[row["edit_type"]].append(row)

    global_idx = 0
    for edit_type in ["add", "delete", "substitute"]:
        selected = balanced_sample(
            by_type.get(edit_type, []),
            target=args.target_per_type,
            key_fn=lambda x: x.get("reaction_class") or x.get("rxn_cls", "unknown"),
            seed=args.seed,
        )
        formatted = [release_record(item, global_idx + i) for i, item in enumerate(selected)]
        global_idx += len(formatted)
        write_json(f"{args.output_dir}/{edit_type}_v2.json", formatted)
        print(f"{edit_type}: wrote {len(formatted)} records")


if __name__ == "__main__":
    main()

