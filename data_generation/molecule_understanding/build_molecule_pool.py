"""Build a sanitized molecule pool for molecular-understanding tasks."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from data_generation.common.chem import canonical_smiles, mol_complexity, molecular_weight
from data_generation.common.io import deduplicate, sequential_sample, write_json


def read_smiles_file(path: str | Path, column: str | None = None) -> list[str]:
    path = Path(path)
    if path.suffix.lower() in {".tsv", ".csv"}:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        rows = csv.DictReader(path.open("r", encoding="utf-8"), delimiter=delimiter)
        if column is None:
            column = rows.fieldnames[0] if rows.fieldnames else None
        return [row[column].strip() for row in rows if column and row.get(column)]
    return [line.strip().split()[0] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True, help="SMILES text/CSV/TSV file. Repeatable.")
    parser.add_argument("--smiles-column")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--target", type=int, default=5000)
    parser.add_argument("--min-mw", type=float, default=150.0)
    parser.add_argument("--max-mw", type=float, default=700.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    records = []
    for path in args.input:
        for smiles in read_smiles_file(path, args.smiles_column):
            can = canonical_smiles(smiles)
            if not can:
                continue
            mw = molecular_weight(can)
            if mw is None or mw < args.min_mw or mw > args.max_mw:
                continue
            records.append({"smiles": can, "mol_weight": mw, "mol_complexity": mol_complexity(can)})

    records = deduplicate(records, lambda x: x["smiles"])
    records = sequential_sample(records, target=args.target, seed=args.seed)
    write_json(args.output_json, records)
    print(f"wrote {len(records)} molecules to {args.output_json}")


if __name__ == "__main__":
    main()

