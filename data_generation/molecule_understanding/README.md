# Molecule Understanding Construction

This release keeps the paper-aligned construction path:

1. `build_molecule_pool.py`: sanitize and sample molecules from public molecule
   sources such as PubChem, ChEMBL, and ZINC-derived files.
2. `build_molund_tasks.py`: build functional-group, ring-count, scaffold, and
   SMILES-equivalence records with RDKit oracles.

Older probe scripts and hard/easy repair passes are intentionally excluded from
the release. The paper reports task-balanced active sets, not difficulty labels.

