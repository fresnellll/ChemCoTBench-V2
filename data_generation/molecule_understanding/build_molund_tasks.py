"""Build molecular-understanding task records from a sanitized molecule pool."""

from __future__ import annotations

import argparse
import random

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold

from data_generation.common.chem import canonical_smiles, mol_from_smiles, tanimoto
from data_generation.common.io import balanced_sample, read_json, write_json


FG_SMARTS = {
    "hydroxyl": "[OX2H]",
    "amine": "[NX3;H2,H1,H0;!$(NC=O)]",
    "amide": "C(=O)N",
    "carboxylic_acid": "C(=O)[OX2H1]",
    "ester": "C(=O)O[#6]",
    "halogen": "[F,Cl,Br,I]",
    "nitrile": "C#N",
    "sulfonamide": "S(=O)(=O)N",
}


def detect_functional_groups(smiles: str) -> list[str]:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return []
    out = []
    for name, smarts in FG_SMARTS.items():
        patt = Chem.MolFromSmarts(smarts)
        if patt is not None and mol.HasSubstructMatch(patt):
            out.append(name)
    return out


def ring_count(smiles: str) -> int:
    mol = mol_from_smiles(smiles)
    return 0 if mol is None else int(rdMolDescriptors.CalcNumRings(mol))


def murcko(smiles: str) -> str:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return ""
    scaffold = MurckoScaffold.GetScaffoldForMol(mol)
    return Chem.MolToSmiles(scaffold) if scaffold is not None else ""


def permute_smiles(smiles: str, rng: random.Random) -> str:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return smiles
    return Chem.MolToSmiles(mol, canonical=False, doRandom=True)


def mutate_smiles(smiles: str) -> str | None:
    mol = mol_from_smiles(smiles)
    if mol is None or mol.GetNumAtoms() < 4:
        return None
    rw = Chem.RWMol(mol)
    atom = rw.GetAtomWithIdx(0)
    if atom.GetAtomicNum() == 6:
        atom.SetAtomicNum(7)
    elif atom.GetAtomicNum() == 7:
        atom.SetAtomicNum(6)
    else:
        return None
    try:
        Chem.SanitizeMol(rw)
    except Exception:
        return None
    mutated = Chem.MolToSmiles(rw)
    if canonical_smiles(mutated) == canonical_smiles(smiles):
        return None
    return mutated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--target-per-task", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    pool = read_json(args.pool_json)

    fg_records = []
    ring_records = []
    murcko_records = []
    ring_sys_records = []
    perm_records = []
    mutated_records = []

    for i, row in enumerate(pool):
        smiles = row["smiles"]
        fgs = detect_functional_groups(smiles)
        if fgs:
            fg_records.append({"id": f"fg_{i:06d}", "smiles": smiles, "target_groups": fgs})

        rings = ring_count(smiles)
        ring_records.append({"id": f"ring_{i:06d}", "smiles": smiles, "answer": rings})

        scaffold = murcko(smiles)
        if scaffold:
            murcko_records.append({"id": f"murcko_{i:06d}", "smiles": smiles, "answer": scaffold})
            ring_sys_records.append(
                {
                    "id": f"ring_sys_{i:06d}",
                    "smiles": smiles,
                    "answer": scaffold,
                    "scaffold_ring_count": ring_count(scaffold),
                }
            )

        permuted = permute_smiles(smiles, rng)
        if canonical_smiles(permuted) == canonical_smiles(smiles) and permuted != smiles:
            perm_records.append(
                {
                    "id": f"perm_{i:06d}",
                    "smiles": smiles,
                    "permutated": permuted,
                    "label": "Yes",
                    "source_subtask": "permutated",
                }
            )

        mutated = mutate_smiles(smiles)
        if mutated:
            sim = tanimoto(smiles, mutated)
            mutated_records.append(
                {
                    "id": f"mut_{i:06d}",
                    "smiles": smiles,
                    "mutated": mutated,
                    "label": "No",
                    "source_subtask": "mutated",
                    "tanimoto": round(float(sim), 4) if sim is not None else None,
                }
            )

    write_json(
        f"{args.output_dir}/1-fg_detect/fg_samples_v2.json",
        balanced_sample(fg_records, target=args.target_per_task, key_fn=lambda x: len(x["target_groups"]), seed=args.seed),
    )
    write_json(
        f"{args.output_dir}/2-frag_detect/ring_count_v2.json",
        balanced_sample(ring_records, target=args.target_per_task, key_fn=lambda x: x["answer"], seed=args.seed),
    )
    write_json(
        f"{args.output_dir}/2-frag_detect/Murcko_scaffold_v2.json",
        balanced_sample(murcko_records, target=args.target_per_task, key_fn=lambda x: ring_count(x["answer"]), seed=args.seed),
    )
    write_json(
        f"{args.output_dir}/2-frag_detect/ring_system_scaffold_v2.json",
        balanced_sample(ring_sys_records, target=args.target_per_task, key_fn=lambda x: x["scaffold_ring_count"], seed=args.seed),
    )
    write_json(
        f"{args.output_dir}/3-permute_smiles/permutated_v2.json",
        balanced_sample(perm_records, target=args.target_per_task, key_fn=lambda x: len(x["smiles"]) // 20, seed=args.seed),
    )
    write_json(
        f"{args.output_dir}/3-permute_smiles/mutated_v2.json",
        balanced_sample(mutated_records, target=args.target_per_task, key_fn=lambda x: len(x["smiles"]) // 20, seed=args.seed),
    )

    equiv = balanced_sample(perm_records, target=args.target_per_task // 2, key_fn=lambda x: len(x["smiles"]) // 20, seed=args.seed)
    neq = balanced_sample(mutated_records, target=args.target_per_task - len(equiv), key_fn=lambda x: len(x["smiles"]) // 20, seed=args.seed)
    write_json(f"{args.output_dir}/3-permute_smiles/smiles_equivalent_v2.json", equiv + neq)
    print(f"wrote MolUnd task files under {args.output_dir}")


if __name__ == "__main__":
    main()
