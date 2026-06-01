"""Chemistry utility functions used by the dataset-construction scripts."""

from __future__ import annotations

from typing import Iterable

from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors


def mol_from_smiles(smiles: str):
    if not smiles:
        return None
    try:
        return Chem.MolFromSmiles(smiles)
    except Exception:
        return None


def canonical_smiles(smiles: str, *, isomeric: bool = True) -> str | None:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, isomericSmiles=isomeric)


def strip_atom_mapping(mol: Chem.Mol) -> str:
    rw_mol = Chem.RWMol(mol)
    for atom in rw_mol.GetAtoms():
        atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(rw_mol)


def mol_complexity(smiles: str) -> float:
    """Simple structural complexity used for filtering and coverage summaries."""
    mol = mol_from_smiles(smiles)
    if mol is None:
        return 0.0
    heavy = mol.GetNumHeavyAtoms()
    rings = rdMolDescriptors.CalcNumRings(mol)
    aromatic = sum(1 for atom in mol.GetAtoms() if atom.GetIsAromatic())
    chiral = len(Chem.FindMolChiralCenters(mol, includeUnassigned=True))
    return float(heavy + 2 * rings + aromatic + 2 * chiral)


def heavy_atom_count(smiles: str) -> int | None:
    mol = mol_from_smiles(smiles)
    return None if mol is None else int(mol.GetNumHeavyAtoms())


def ring_count(smiles: str) -> int | None:
    mol = mol_from_smiles(smiles)
    return None if mol is None else int(rdMolDescriptors.CalcNumRings(mol))


def molecular_weight(smiles: str) -> float | None:
    mol = mol_from_smiles(smiles)
    return None if mol is None else float(Descriptors.MolWt(mol))


def tanimoto(smiles_a: str, smiles_b: str) -> float | None:
    mol_a = mol_from_smiles(smiles_a)
    mol_b = mol_from_smiles(smiles_b)
    if mol_a is None or mol_b is None:
        return None
    fp_a = AllChem.GetMorganFingerprintAsBitVect(mol_a, 2, 2048)
    fp_b = AllChem.GetMorganFingerprintAsBitVect(mol_b, 2, 2048)
    return float(DataStructs.TanimotoSimilarity(fp_a, fp_b))


def all_valid_smiles(smiles_list: Iterable[str]) -> bool:
    return all(mol_from_smiles(smiles) is not None for smiles in smiles_list)

