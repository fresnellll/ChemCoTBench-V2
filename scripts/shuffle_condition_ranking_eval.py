#!/usr/bin/env python3
"""
Shuffle condition_ranking conditions for unbiased evaluation.

Problem: PRM generation provides conditions in GT rank order (1=best, 2=medium, 3=worst).
Direct evaluation would give 100% accuracy to any model outputting ["1","2","3"].

Solution: For each sample, randomly permute the three condition labels,
then recompute gt_ranking according to the new label positions.

Input:  results/formal_cot/rxn_pred/condition_ranking/clean_dataset.json
Output: results/formal_cot/rxn_pred/condition_ranking/eval_dataset_shuffled.json

Usage:
    python scripts/shuffle_condition_ranking_eval.py \
        --input results/formal_cot/rxn_pred/condition_ranking/clean_dataset.json \
        --output results/formal_cot/rxn_pred/condition_ranking/eval_dataset_shuffled.json \
        --seed 42
"""

import argparse
import json
import random
from pathlib import Path


def shuffle_one(record: dict, rng: random.Random) -> dict:
    """Shuffle condition labels for one record.

    GT rank order is always ["1","2","3"] in clean_dataset (1=best yield).
    We randomly permute labels and recompute gt_ranking.
    """
    # Original labels and their GT ranks
    # In clean_dataset: label "1" has rank 1 (best), "2" has rank 2, "3" has rank 3
    labels = ["1", "2", "3"]
    gt_ranks = {"1": 1, "2": 2, "3": 3}  # rank by yield (1=best)

    # Shuffle labels: create mapping old_label -> new_label
    shuffled = labels.copy()
    rng.shuffle(shuffled)
    old_to_new = {old: new for old, new in zip(labels, shuffled)}

    # Recompute gt_ranking: for each new label position, what was its original GT rank?
    new_to_old = {v: k for k, v in old_to_new.items()}
    new_gt_ranking = [new_to_old[pos] for pos in labels]
    # Wait, we need: given the new label positions, which new label has the best yield?
    # Actually simpler: the GT ranking by yield is the same, just labels moved.
    # If old "1" (best) is now at position "2", then gt_ranking[0] = "2".

    # Reconstruct: gt_ranking[new_pos] = old_label at that position
    # The ranking from best to worst yield:
    # old_label with rank 1 -> new_label = old_to_new["1"]
    # old_label with rank 2 -> new_label = old_to_new["2"]
    # old_label with rank 3 -> new_label = old_to_new["3"]
    gt_ranking_shuffled = [old_to_new[str(i)] for i in range(1, 4)]

    # Build shuffled record
    result = {
        "src_id": record.get("src_id"),
        "difficulty": record.get("difficulty"),
        "rxn_cls": record.get("rxn_cls"),
        "coarse_rxn_cls": record.get("coarse_rxn_cls"),
        "reactants": record.get("reactants"),
        "product": record.get("product"),
        # Shuffled conditions
        "cond_1": record.get(f"cond_{old_to_new['1']}"),
        "cond_2": record.get(f"cond_{old_to_new['2']}"),
        "cond_3": record.get(f"cond_{old_to_new['3']}"),
        # Original labels (for reference)
        "orig_label_1": old_to_new["1"],
        "orig_label_2": old_to_new["2"],
        "orig_label_3": old_to_new["3"],
        # Yields remain the same (associated with original labels)
        "yield_1": record.get("yield_1"),
        "yield_2": record.get("yield_2"),
        "yield_3": record.get("yield_3"),
        # GT ranking under new label positions
        "gt_ranking": gt_ranking_shuffled,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Shuffle condition_ranking conditions for unbiased eval.")
    parser.add_argument("--input", required=True, help="Path to condition_ranking clean_dataset.json")
    parser.add_argument("--output", required=True, help="Path to output eval_dataset_shuffled.json")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    with open(args.input) as f:
        records = json.load(f)

    rng = random.Random(args.seed)
    shuffled = [shuffle_one(r, rng) for r in records]

    with open(args.output, "w") as f:
        json.dump(shuffled, f, indent=2, ensure_ascii=False)

    # Stats
    from collections import Counter
    ranking_counts = Counter(tuple(r["gt_ranking"]) for r in shuffled)

    print(f"Shuffled {len(shuffled)} records -> {args.output}")
    print(f"Random seed: {args.seed}")
    print("GT ranking distribution:")
    for ranking, cnt in sorted(ranking_counts.items(), key=lambda x: -x[1]):
        print(f"  {list(ranking)}: {cnt} ({100*cnt/len(shuffled):.1f}%)")


if __name__ == "__main__":
    main()
