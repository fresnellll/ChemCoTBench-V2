# Data Generation Framework

This directory contains the paper-aligned construction framework for
ChemCoTBench-V2. It is intentionally narrower than the historical working
directory: release scripts keep the main reproducible data-construction path and
exclude exploratory probes, one-off repair passes, and difficulty-label tuning.

The paper describes the released active benchmark as a rule-verifiable,
task-balanced set constructed from public chemistry resources and derived task
pools. It does not introduce easy/medium/hard labels as benchmark metadata, so
the release utilities strip historical difficulty fields from public records.

## Directory Map

```text
common/                    Shared RDKit, JSON, sampling, API, and field-cleaning helpers.
molecule_editing/          Schneider 50K reaction edits and instruction generation.
molecule_understanding/    Molecule-pool cleaning and RDKit-oracle task construction.
reaction_prediction/       Reaction-pool, condition-ranking, yield, template, and mechanism tasks.
molecular_optimization/    Single- and dual-objective MMP optimization tasks.
```

## Expected Data Boundary

The GitHub repository should contain code and small templates only. Large or
license-sensitive upstream resources should not be mirrored here. Use the Hugging
Face data release for:

- active benchmark JSON files,
- derived intermediate pools where redistribution is allowed,
- split metadata and prompt/template metadata,
- optional construction pools needed to rerun these scripts.

Bulk upstream databases such as PubChem, ChEMBL, ZINC, USPTO/ORD, HTE
supplements, and TDC assets remain governed by their original terms.

## Main Flow

1. Build or download construction pools.
2. Run the task-family scripts to create candidate records.
3. Apply task-specific quality filters, deduplication, and task-balanced
   sampling.
4. Strip construction-only fields:

```bash
python -m data_generation.common.strip_fields \
  --input path/to/raw_constructed.json \
  --output path/to/released.json
```

5. Validate the resulting data package with:

```bash
python scripts/validate_release.py --fast
```

## Task Families

### Molecule Editing

```bash
python -m data_generation.molecule_editing.extract_reaction_edits \
  --input-tsv raw_data/mol_edit_rxn_pool/schneider50k.tsv \
  --output-json work/mol_edit/extracted_edits.json

python -m data_generation.molecule_editing.generate_edit_instructions \
  --input-json work/mol_edit/extracted_edits.json \
  --output-json work/mol_edit/instructions.json \
  --model gpt-5.4

python -m data_generation.molecule_editing.assemble_moledit \
  --input-json work/mol_edit/instructions.json \
  --output-dir dataset/mol_edit/1-instruct_to_edit
```

### Molecular Understanding

```bash
python -m data_generation.molecule_understanding.build_molecule_pool \
  --input raw_sources/zinc_smiles.txt \
  --input raw_sources/chembl_smiles.tsv \
  --smiles-column smiles \
  --output-json work/molund/molecule_pool.json

python -m data_generation.molecule_understanding.build_molund_tasks \
  --pool-json work/molund/molecule_pool.json \
  --output-dir dataset/mol_understanding
```

### Reaction Prediction

```bash
python -m data_generation.reaction_prediction.assemble_reaction_tasks \
  --pool-dir work/rxn_predict_pool \
  --output-dir dataset/rxn_predict

python -m data_generation.reaction_prediction.build_condition_tasks \
  --hte-csv raw_data/rxn_hte/Dreher_and_Doyle_reaction_t5_ready.csv \
  --reaction-class "Buchwald-Hartwig C-N coupling" \
  --source-name buchwald_hte_t5 \
  --output-dir dataset/rxn_predict

python -m data_generation.reaction_prediction.build_template_and_mechanism_tasks \
  --forward-json dataset/rxn_predict/forward_v2.json \
  --template-dict-json work/rxn_predict_pool/rxn_template_gemini_dict.json \
  --mechanism-pool-json work/rxn_predict_pool/mech_sel_pool.json \
  --output-dir dataset/rxn_predict
```

### Molecular Optimization

```bash
python -m data_generation.molecular_optimization.assemble_single_objective \
  --pool-root work/deep_mol_opt \
  --output-root dataset/deep_mol_opt

python -m data_generation.molecular_optimization.assemble_dual_objective \
  --input-json work/mol_opt_multistep/mmp_two_prop_full.json \
  --input-json work/mol_opt_multistep/mmp_three_prop_full.json \
  --output-root dataset/deep_mol_opt_multi
```

## Formal CoT / PRM References

Benchmark-record construction is separate from formal-CoT/reference-trace
construction. Formal templates, parsers, and verifiers are released under
`formal_cot/`; the API-facing reference-generation entry point is
`prm_generation/generate_prm.py`.

