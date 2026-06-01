"""Extract reaction-derived molecule edits from atom-mapped Schneider 50K rows.

This is the release version of the MolEdit construction step described in the
paper appendix. It keeps the main reproducible logic: identify the main
reactant/product fragments, remove atom mapping, classify add/delete/substitute
edits, and apply RDKit validity and relatedness filters.
"""

from __future__ import annotations

import argparse
import csv
import uuid
from collections import Counter
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.rdmolops import GetMolFrags

from data_generation.common.chem import (
    heavy_atom_count,
    mol_complexity,
    strip_atom_mapping,
    tanimoto,
)
from data_generation.common.io import write_json

SCHNEIDER_CLASS_NAMES = {
    "1": "C-C Bond Formation",
    "2": "C-N Bond Formation",
    "3": "C-O Bond Formation",
    "5": "Halogenation",
    "6": "Deprotection",
    "7": "Reduction",
    "8": "Oxidation",
    "9": "Heterocycle Synthesis",
    "10": "Functional Group Transformation",
}


def _fragment_smiles(mol: Chem.Mol, atom_indices: list[int]) -> str:
    if not atom_indices:
        return ""
    try:
        frag = Chem.MolFragmentToSmiles(mol, atom_indices)
        parsed = Chem.MolFromSmiles(frag)
        return strip_atom_mapping(parsed) if parsed is not None else frag
    except Exception:
        return ""


def classify_reaction_edit(original_rxn: str, schneider_top_class: str) -> dict | None:
    parts = original_rxn.split(">")
    if len(parts) != 3:
        return None
    reactant_smiles, _, product_smiles = parts
    reactants = Chem.MolFromSmiles(reactant_smiles)
    products = Chem.MolFromSmiles(product_smiles)
    if reactants is None or products is None:
        return None

    product_frags = GetMolFrags(products, asMols=True)
    reactant_frags = GetMolFrags(reactants, asMols=True)
    if not product_frags or not reactant_frags:
        return None

    main_product = max(product_frags, key=lambda mol: mol.GetNumHeavyAtoms())
    product_maps = {atom.GetAtomMapNum() for atom in main_product.GetAtoms() if atom.GetAtomMapNum() > 0}
    if not product_maps:
        return None

    def overlap(frag: Chem.Mol) -> int:
        maps = {atom.GetAtomMapNum() for atom in frag.GetAtoms() if atom.GetAtomMapNum() > 0}
        return len(maps & product_maps)

    main_reactant = max(reactant_frags, key=overlap)
    reactant_maps = {atom.GetAtomMapNum() for atom in main_reactant.GetAtoms() if atom.GetAtomMapNum() > 0}
    if not reactant_maps:
        return None

    appeared_maps = product_maps - reactant_maps
    unmapped_reactant_atoms = [
        atom for atom in main_reactant.GetAtoms() if atom.GetAtomicNum() > 1 and atom.GetAtomMapNum() == 0
    ]

    src = strip_atom_mapping(main_reactant)
    tgt = strip_atom_mapping(main_product)
    src_ha = main_reactant.GetNumHeavyAtoms()
    tgt_ha = main_product.GetNumHeavyAtoms()

    if schneider_top_class == "6":
        edit_type = "delete"
    elif unmapped_reactant_atoms and appeared_maps:
        edit_type = "substitute"
    elif appeared_maps:
        edit_type = "add"
    elif tgt_ha < src_ha - 2:
        edit_type = "delete"
    elif tgt_ha > src_ha:
        edit_type = "add"
    else:
        return None

    leaving_atoms = [
        atom.GetIdx()
        for atom in main_reactant.GetAtoms()
        if atom.GetAtomicNum() > 1 and atom.GetAtomMapNum() == 0
    ]
    incoming_atoms = [
        atom.GetIdx() for atom in main_product.GetAtoms() if atom.GetAtomMapNum() in appeared_maps
    ]

    return {
        "src": src,
        "tgt": tgt,
        "edit_type": edit_type,
        "src_heavy_atoms": src_ha,
        "tgt_heavy_atoms": tgt_ha,
        "heavy_atom_delta": tgt_ha - src_ha,
        "leaving_group_smiles": _fragment_smiles(main_reactant, leaving_atoms),
        "incoming_group_smiles": _fragment_smiles(main_product, incoming_atoms),
    }


def valid_candidate(
    rec: dict,
    *,
    min_complexity: float,
    min_tanimoto: float,
    max_tanimoto: float,
    max_heavy_atom_delta: int,
) -> bool:
    if heavy_atom_count(rec["src"]) is None or heavy_atom_count(rec["tgt"]) is None:
        return False
    if mol_complexity(rec["src"]) < min_complexity:
        return False
    delta = abs(int(rec["heavy_atom_delta"]))
    if delta < 1 or delta > max_heavy_atom_delta:
        return False
    sim = tanimoto(rec["src"], rec["tgt"])
    if sim is None:
        return False
    return min_tanimoto <= sim <= max_tanimoto


def run(args: argparse.Namespace) -> None:
    rows = list(csv.DictReader(Path(args.input_tsv).open(newline="", encoding="utf-8"), delimiter="\t"))
    if args.max_rows:
        rows = rows[: args.max_rows]

    records = []
    skipped = Counter()
    for row in rows:
        rxn_class = row.get("rxn_class", "")
        top_class = rxn_class.split(".")[0]
        if top_class == "7":
            skipped["reduction_class"] += 1
            continue
        extracted = classify_reaction_edit(row.get("original_rxn", ""), top_class)
        if extracted is None:
            skipped["not_extractable"] += 1
            continue
        if not valid_candidate(
            extracted,
            min_complexity=args.min_complexity,
            min_tanimoto=args.min_tanimoto,
            max_tanimoto=args.max_tanimoto,
            max_heavy_atom_delta=args.max_heavy_atom_delta,
        ):
            skipped["filtered"] += 1
            continue

        sim = tanimoto(extracted["src"], extracted["tgt"])
        records.append(
            {
                "id": str(uuid.uuid4()),
                **extracted,
                "reaction_class": SCHNEIDER_CLASS_NAMES.get(top_class, f"Class {top_class}"),
                "schneider_class": rxn_class,
                "source_tanimoto": round(float(sim), 4) if sim is not None else None,
                "source_mol_complexity": mol_complexity(extracted["src"]),
                "source": "Schneider50K",
            }
        )

    write_json(args.output_json, records)
    print(f"wrote {len(records)} candidates to {args.output_json}")
    if skipped:
        print(f"skipped: {dict(skipped)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-tsv", required=True, help="Schneider 50K TSV with original_rxn and rxn_class columns.")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--min-complexity", type=float, default=30.0)
    parser.add_argument("--min-tanimoto", type=float, default=0.35)
    parser.add_argument("--max-tanimoto", type=float, default=0.95)
    parser.add_argument("--max-heavy-atom-delta", type=int, default=15)
    parser.add_argument("--max-rows", type=int)
    run(parser.parse_args())


if __name__ == "__main__":
    main()

