#!/usr/bin/env python3
"""Export the 5,620-sample ChemCoTBench-V2 anonymous data package."""

from __future__ import annotations

import csv
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "anonymous_data"


ACTIVE_TASKS = [
    {
        "family": "mol_edit",
        "subtask": "add_v2",
        "reporting_task": "MolEdit/Add",
        "source_path": "results/formal_cot/mol_edit/add_v2/clean_dataset.json",
        "n": 300,
    },
    {
        "family": "mol_edit",
        "subtask": "delete_v2",
        "reporting_task": "MolEdit/Delete",
        "source_path": "results/formal_cot/mol_edit/delete_v2/clean_dataset.json",
        "n": 300,
    },
    {
        "family": "mol_edit",
        "subtask": "substitute_v2",
        "reporting_task": "MolEdit/Substitute",
        "source_path": "results/formal_cot/mol_edit/substitute_v2/clean_dataset.json",
        "n": 300,
    },
    {
        "family": "mol_und",
        "subtask": "fg_detect",
        "reporting_task": "MolUnd/Functional Group",
        "source_path": "results/formal_cot/mol_und/fg_detect/clean_dataset.json",
        "n": 300,
    },
    {
        "family": "mol_und",
        "subtask": "ring_count",
        "reporting_task": "MolUnd/Ring Count",
        "source_path": "results/formal_cot/mol_und/ring_count/clean_dataset.json",
        "n": 300,
    },
    {
        "family": "mol_und",
        "subtask": "murcko_scaffold",
        "reporting_task": "MolUnd/Murcko Scaffold",
        "source_path": "results/formal_cot/mol_und/murcko_scaffold/clean_dataset.json",
        "n": 300,
    },
    {
        "family": "mol_und",
        "subtask": "ring_sys_scaffold",
        "reporting_task": "MolUnd/Ring-System Scaffold",
        "source_path": "results/formal_cot/mol_und/ring_sys_scaffold/clean_dataset.json",
        "n": 300,
    },
    {
        "family": "mol_und",
        "subtask": "smiles_equivalent",
        "reporting_task": "MolUnd/SMILES Equivalence",
        "source_path": "results/formal_cot/mol_und/smiles_equivalent/clean_dataset.json",
        "n": 300,
    },
    {
        "family": "rxn_pred",
        "subtask": "forward",
        "reporting_task": "RxnPred/Product-Level Prediction",
        "source_path": "results/formal_cot/rxn_pred/forward/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "byproduct",
        "reporting_task": "RxnPred/Product-Level Prediction",
        "source_path": "results/formal_cot/rxn_pred/byproduct_fixed/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "nepp",
        "reporting_task": "RxnPred/Product-Level Prediction",
        "source_path": "results/formal_cot/rxn_pred/nepp/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "retro",
        "reporting_task": "RxnPred/Retrosynthesis",
        "source_path": "results/formal_cot/rxn_pred/retro/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "rxn_template",
        "reporting_task": "RxnPred/Template/Mechanism Reasoning",
        "source_path": "results/formal_cot/rxn_pred/rxn_template/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "mech_sel",
        "reporting_task": "RxnPred/Template/Mechanism Reasoning",
        "source_path": "results/formal_cot/rxn_pred/mech_sel/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "rcr_catalyst",
        "reporting_task": "RxnPred/Component Recommendation",
        "source_path": "results/formal_cot/rxn_pred/rcr_catalyst/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "rcr_reagent",
        "reporting_task": "RxnPred/Component Recommendation",
        "source_path": "results/formal_cot/rxn_pred/rcr_reagent/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "rcr_solvent",
        "reporting_task": "RxnPred/Component Recommendation",
        "source_path": "results/formal_cot/rxn_pred/rcr_solvent/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "condition_ranking",
        "reporting_task": "RxnPred/Condition Ranking",
        "source_path": "results/formal_cot/rxn_pred/condition_ranking/eval_dataset_shuffled.json",
        "n": 200,
    },
    {
        "family": "rxn_pred",
        "subtask": "yield_pred",
        "reporting_task": "RxnPred/Yield Prediction",
        "source_path": "results/formal_cot/rxn_pred/yield_pred/clean_dataset.json",
        "n": 200,
    },
    {
        "family": "mol_opt",
        "subtask": "logp",
        "reporting_task": "MolOpt/PhysChem-Single",
        "source_path": "results/formal_cot/mol_opt/logp/clean_dataset.json",
        "n": 120,
    },
    {
        "family": "mol_opt",
        "subtask": "qed",
        "reporting_task": "MolOpt/PhysChem-Single",
        "source_path": "results/formal_cot/mol_opt/qed/clean_dataset.json",
        "n": 120,
    },
    {
        "family": "mol_opt",
        "subtask": "solubility",
        "reporting_task": "MolOpt/PhysChem-Single",
        "source_path": "results/formal_cot/mol_opt/solubility/clean_dataset.json",
        "n": 120,
    },
    {
        "family": "mol_opt",
        "subtask": "drd",
        "reporting_task": "MolOpt/BioTarget-Single",
        "source_path": "results/formal_cot/mol_opt/drd/clean_dataset.json",
        "n": 120,
    },
    {
        "family": "mol_opt",
        "subtask": "jnk",
        "reporting_task": "MolOpt/BioTarget-Single",
        "source_path": "results/formal_cot/mol_opt/jnk/clean_dataset.json",
        "n": 120,
    },
    {
        "family": "mol_opt",
        "subtask": "gsk",
        "reporting_task": "MolOpt/BioTarget-Single",
        "source_path": "results/formal_cot/mol_opt/gsk/clean_dataset.json",
        "n": 120,
    },
    {
        "family": "mol_opt",
        "subtask": "logp_qed",
        "reporting_task": "MolOpt/PhysChem-Dual",
        "source_path": "results/formal_cot/mol_opt/logp_qed/clean_dataset.json",
        "n": 50,
    },
    {
        "family": "mol_opt",
        "subtask": "logp_solubility",
        "reporting_task": "MolOpt/PhysChem-Dual",
        "source_path": "results/formal_cot/mol_opt/logp_solubility/clean_dataset.json",
        "n": 50,
    },
    {
        "family": "mol_opt",
        "subtask": "qed_solubility",
        "reporting_task": "MolOpt/PhysChem-Dual",
        "source_path": "results/formal_cot/mol_opt/qed_solubility/clean_dataset.json",
        "n": 50,
    },
    {
        "family": "mol_opt",
        "subtask": "drd_logp",
        "reporting_task": "MolOpt/BioTarget-Dual",
        "source_path": "results/formal_cot/mol_opt/drd_logp/clean_dataset.json",
        "n": 50,
    },
    {
        "family": "mol_opt",
        "subtask": "drd_solubility",
        "reporting_task": "MolOpt/BioTarget-Dual",
        "source_path": "results/formal_cot/mol_opt/drd_solubility/clean_dataset.json",
        "n": 50,
    },
    {
        "family": "mol_opt",
        "subtask": "gsk_logp",
        "reporting_task": "MolOpt/BioTarget-Dual",
        "source_path": "results/formal_cot/mol_opt/gsk_logp/clean_dataset.json",
        "n": 50,
    },
]


DROP_KEYS = {
    "api_success",
    "completion_tokens",
    "difficulty_primary_model",
    "elapsed_s",
    "error",
    "finish_reason",
    "gemini_can_a",
    "gemini_can_b",
    "parse_errors",
    "parse_note",
    "parse_ok",
    "part1_text",
    "part2_text",
    "patch_tag",
    "prompt_tokens",
    "raw_output",
    "raw_output_steps",
    "reasoning_tokens",
    "selection_correct_count",
    "selection_model_exact_match",
    "selection_wrong_count",
    "text_tokens",
    "thinking_tokens",
    "total_completion_tokens",
    "verify_msgs",
    "verify_note",
    "verify_skip_reason",
}

PROCESS_METADATA_DROP_KEYS = DROP_KEYS - {"raw_output", "raw_output_steps"}

RAW_DROP_PREFIXES = ("S", "s", "step", "rdkit_", "answer_", "oracle_", "delta_")
PROCESS_KEEP_PREFIXES = ("S", "s", "step", "rdkit_")
IDENTITY_KEYS = {
    "id",
    "idx",
    "orig_id",
    "orig_idx",
    "pool_idx",
    "sample_id",
    "source_orig_idx",
    "source_task_orig_idx",
    "src_id",
}
META_KEYS = {
    "difficulty",
    "difficulty_basis",
    "difficulty_score",
    "list_pos",
    "source_dataset",
    "source_subtask",
    "smiles_equivalent_id",
    "shuffle_note",
    "shuffle_perm",
}
PROCESS_EXTRA_KEYS = {
    "abs_err",
    "all_pass",
    "answer",
    "answer_letter",
    "answer_smi",
    "answer_smiles",
    "answer_yield",
    "formula_used",
    "oracle_delta",
    "outcome",
    "outcome_any",
    "outcome_drd",
    "outcome_gsk",
    "outcome_jnk",
    "outcome_logp",
    "outcome_qed",
    "outcome_solubility",
    "outcome_strict",
    "parse_format_type",
}


PROMPT_README = """# Prompt Templates

This directory intentionally contains evaluation-facing prompt format summaries,
not the original reference-construction prompts. Ground-truth-injection lines,
model names, examples with sample-specific answers, and API metadata are not
included in this anonymous data package.

For each subtask, use the fields in `../formal_templates/` to request the
required structured trace. The user prompt should contain only the input fields
from `../raw_benchmark_data/` and should not include the final answer or the
process reference states from `../process_evaluation_data/`.
"""


README = """# ChemCoTBench-V2 Anonymous Data Package

This directory contains the anonymous 5,620-sample active benchmark used by the
ChemCoTBench-V2 submission draft.

## Layout

- `raw_benchmark_data/`: model-facing benchmark inputs plus final-answer labels.
- `process_evaluation_data/`: PRM-like process-level reference traces. Each
  sample contains step names, natural-language descriptions, FORMAL A-to-B
  lines, parsed reference states, and verifier pass flags.
- `task_schema/`: task counts, field inventory, and per-subtask schemas.
- `formal_templates/`: step-field schemas inferred from the verified references.
- `prompt_templates/`: evaluation-facing prompt format guidance.
- `verifier_rule_descriptions/`: verifier check names and task-level rule notes.
- `sample_examples/`: small examples linking raw inputs with process references.
- `evaluation_split_metadata/`: manifest and split/count metadata.

## Active Benchmark Size

The active benchmark contains 5,620 samples:

- MolEdit: 3 x 300 = 900
- MolUnd: 5 x 300 = 1,500
- RxnPred: 11 x 200 = 2,200
- MolOpt: 6 x 120 + 6 x 50 = 1,020

`condition_temperature` is excluded from the active benchmark. The older
`mutated` and `permutated` MolUnd subtasks are represented by the merged
`smiles_equivalent` subtask.

## Anonymization

The export removes runtime artifacts such as token counts, API success/debug
fields, finish reasons, model names, patch tags, and model-selection metadata.
The retained process-level files keep the cleaned formal reference trace because
it is the PRM-like supervision/evaluation target for process-level scoring.
"""


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def save_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def is_verifier_key(key: str) -> bool:
    return bool(re.match(r"^[Ss]\d", key))


def should_drop(key: str) -> bool:
    return key in DROP_KEYS or key.endswith("_text")


def should_drop_process_metadata(key: str) -> bool:
    return key in PROCESS_METADATA_DROP_KEYS or key.endswith("_text")


def stable_sample_id(family: str, subtask: str, idx: int) -> str:
    return f"{family}.{subtask}.{idx:04d}"


def clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: clean_value(v) for k, v in value.items() if not should_drop(k)}
    if isinstance(value, list):
        return [clean_value(v) for v in value]
    return value


def raw_record(record: dict[str, Any], task: dict[str, Any], idx: int) -> dict[str, Any]:
    out = {
        "anonymous_sample_id": stable_sample_id(task["family"], task["subtask"], idx),
        "task_family": task["family"],
        "subtask": task["subtask"],
        "reporting_task": task["reporting_task"],
    }
    for key, value in record.items():
        if should_drop(key):
            continue
        if key in PROCESS_EXTRA_KEYS or key.startswith(PROCESS_KEEP_PREFIXES) or is_verifier_key(key):
            continue
        out[key] = clean_value(value)
    return out


STEP_RE = re.compile(r"(?=^Step\s+\d+\s+\[[^\]]+\]:)", re.MULTILINE)
STEP_HEADER_RE = re.compile(r"^Step\s+(\d+)\s+\[([^\]]+)\]:\s*(.*)", re.DOTALL)
FORMAL_RE = re.compile(r"^\s*FORMAL:\s*(.+)$", re.MULTILINE)


def split_raw_steps(record: dict[str, Any]) -> list[str]:
    steps = record.get("raw_output_steps")
    if isinstance(steps, list) and steps:
        return [str(step).strip() for step in steps if str(step).strip()]
    raw = record.get("raw_output")
    if not isinstance(raw, str) or not raw.strip():
        return []
    chunks = [chunk.strip() for chunk in STEP_RE.split(raw.strip()) if chunk.strip()]
    return [chunk for chunk in chunks if chunk.startswith("Step ")]


def parse_trace_step(step_text: str) -> dict[str, Any]:
    stripped = step_text.strip()
    header = STEP_HEADER_RE.match(stripped)
    step_index = None
    step_name = ""
    body = stripped
    if header:
        step_index = int(header.group(1))
        step_name = header.group(2).strip()
        body = header.group(3).strip()
    formal_match = FORMAL_RE.search(stripped)
    formal_ab = formal_match.group(1).strip() if formal_match else ""
    body_lines = []
    for line in body.splitlines():
        if line.strip().startswith("FORMAL:"):
            break
        body_lines.append(line)
    natural_language = "\n".join(body_lines).strip()
    return {
        "step_index": step_index,
        "step_name": step_name,
        "natural_language": natural_language,
        "formal_ab": formal_ab,
        "step_text": stripped,
    }


def build_formal_cot_trace(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [parse_trace_step(step) for step in split_raw_steps(record)]


def process_record(record: dict[str, Any], task: dict[str, Any], idx: int) -> dict[str, Any]:
    out: dict[str, Any] = {
        "anonymous_sample_id": stable_sample_id(task["family"], task["subtask"], idx),
        "task_family": task["family"],
        "subtask": task["subtask"],
        "reporting_task": task["reporting_task"],
    }

    for key in IDENTITY_KEYS:
        if key in record and not should_drop_process_metadata(key):
            out[key] = clean_value(record[key])
    for key in META_KEYS:
        if key in record and not should_drop_process_metadata(key):
            out[key] = clean_value(record[key])

    trace = build_formal_cot_trace(record)
    if trace:
        out["formal_cot_trace"] = trace

    parsed_reference_state = {}
    verifier_checks = {}
    for key, value in record.items():
        if should_drop_process_metadata(key):
            continue
        if key in IDENTITY_KEYS or key in META_KEYS or key in {"raw_output", "raw_output_steps"}:
            continue
        if key.startswith("step") or key.startswith("rdkit_"):
            parsed_reference_state[key] = clean_value(value)
        elif is_verifier_key(key) or key == "all_pass" or key.startswith(("outcome_", "delta_")):
            verifier_checks[key] = clean_value(value)
        elif key.startswith("answer") or key in {"outcome", "abs_err", "oracle_delta", "formula_used", "parse_format_type"}:
            out[key] = clean_value(value)
        elif key.startswith("gt_") or key.startswith("expected_"):
            out[key] = clean_value(value)
    if parsed_reference_state:
        out["parsed_reference_state"] = parsed_reference_state
    if verifier_checks:
        out["verifier_checks"] = verifier_checks
    return out


def infer_template(records: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set().union(*(r.keys() for r in records)))
    step_fields = [k for k in keys if k.startswith("step") and not k.endswith("_text")]
    verifier_fields = [k for k in keys if is_verifier_key(k)]
    rdkit_fields = [k for k in keys if k.startswith("rdkit_")]
    return {
        "task_family": task["family"],
        "subtask": task["subtask"],
        "reporting_task": task["reporting_task"],
        "n_samples": len(records),
        "step_fields": step_fields,
        "rdkit_reference_fields": rdkit_fields,
        "verifier_fields": verifier_fields,
        "notes": [
            "Step fields are structured reference states extracted from verified traces.",
            "Process files also include formal_cot_trace with step_name, natural_language, and formal_ab fields.",
        ],
    }


def infer_rule_description(records: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set().union(*(r.keys() for r in records)))
    verifier_fields = [k for k in keys if is_verifier_key(k)]
    outcomes = [k for k in keys if k == "outcome" or k.startswith("outcome_")]
    return {
        "task_family": task["family"],
        "subtask": task["subtask"],
        "reporting_task": task["reporting_task"],
        "all_pass_definition": (
            "The all_pass field is the task-specific conjunction of required "
            "process verifier checks used when constructing the verified reference."
        ),
        "verifier_checks": [
            {
                "name": field,
                "description": "Task-specific deterministic verifier flag.",
            }
            for field in verifier_fields
        ],
        "outcome_fields": outcomes,
        "type_notes": [
            "Type-I checks are intrinsic symbolic checks such as validity, arithmetic, canonicalization, scaffold preservation, or consistency.",
            "Type-II checks compare closed-answer process states or final answers with the verified benchmark reference.",
            "Molecular optimization uses oracle-computable constraints rather than strict path matching for the final outcome.",
        ],
    }


def field_schema(records: list[dict[str, Any]]) -> dict[str, str]:
    types: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        for key, value in record.items():
            types[key][type(value).__name__] += 1
    return {key: counts.most_common(1)[0][0] for key, counts in sorted(types.items())}


def write_manifest_csv(rows: list[dict[str, Any]]) -> None:
    path = OUT / "evaluation_split_metadata" / "active_benchmark_manifest.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "family",
                "subtask",
                "reporting_task",
                "n_samples",
                "raw_file",
                "process_file",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_prompt_guidance(templates: dict[str, dict[str, Any]]) -> None:
    save_text(PROMPT_README, OUT / "prompt_templates" / "README.md")
    lines = [
        "# Evaluation Prompt Format Summary",
        "",
        "Evaluation prompts should expose the required structured fields without final-answer labels.",
        "The following subtask sections list the step fields expected by the process-level schema.",
        "",
    ]
    for name, template in sorted(templates.items()):
        lines.append(f"## {name}")
        step_fields = template["step_fields"]
        if step_fields:
            for field in step_fields:
                lines.append(f"- `{field}`")
        else:
            lines.append("- No explicit `step*` fields are present in the exported reference; use the task-specific verifier fields.")
        lines.append("")
    save_text("\n".join(lines), OUT / "prompt_templates" / "evaluation_prompt_format.md")


def export() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    save_text(README, OUT / "README.md")

    manifest_rows = []
    family_counts = Counter()
    reporting_counts = Counter()
    task_schemas = {}
    templates = {}
    examples = {}

    for task in ACTIVE_TASKS:
        source_path = ROOT / task["source_path"]
        records = load_json(source_path)
        if len(records) != task["n"]:
            raise ValueError(f"{source_path} has {len(records)} records, expected {task['n']}")

        raw_records = [raw_record(record, task, idx) for idx, record in enumerate(records)]
        process_records = [process_record(record, task, idx) for idx, record in enumerate(records)]

        raw_rel = Path("raw_benchmark_data") / task["family"] / f"{task['subtask']}.json"
        process_rel = Path("process_evaluation_data") / task["family"] / f"{task['subtask']}.json"
        save_json(raw_records, OUT / raw_rel)
        save_json(process_records, OUT / process_rel)

        name = f"{task['family']}/{task['subtask']}"
        task_schemas[name] = {
            "task_family": task["family"],
            "subtask": task["subtask"],
            "reporting_task": task["reporting_task"],
            "n_samples": len(records),
            "raw_fields": field_schema(raw_records),
            "process_fields": field_schema(process_records),
        }
        templates[name] = infer_template(records, task)
        save_json(templates[name], OUT / "formal_templates" / task["family"] / f"{task['subtask']}.json")
        save_json(
            infer_rule_description(records, task),
            OUT / "verifier_rule_descriptions" / task["family"] / f"{task['subtask']}.json",
        )
        examples[name] = {
            "raw_benchmark_data": raw_records[:2],
            "process_evaluation_data": process_records[:2],
        }

        manifest_rows.append(
            {
                "family": task["family"],
                "subtask": task["subtask"],
                "reporting_task": task["reporting_task"],
                "n_samples": len(records),
                "raw_file": str(raw_rel),
                "process_file": str(process_rel),
            }
        )
        family_counts[task["family"]] += len(records)
        reporting_counts[task["reporting_task"]] += len(records)

    manifest = {
        "dataset_name": "ChemCoTBench-V2 anonymous active benchmark",
        "total_samples": sum(family_counts.values()),
        "implementation_subtasks": len(ACTIVE_TASKS),
        "reporting_tasks": len(reporting_counts),
        "family_counts": dict(family_counts),
        "reporting_task_counts": dict(reporting_counts),
        "excluded_from_active_benchmark": [
            "rxn_pred/condition_temperature",
            "mol_und/mutated as a standalone reporting task",
            "mol_und/permutated as a standalone reporting task",
        ],
        "files": manifest_rows,
    }
    save_json(manifest, OUT / "manifest.json")
    save_json(manifest, OUT / "evaluation_split_metadata" / "splits.json")
    save_json(task_schemas, OUT / "task_schema" / "task_schema.json")
    save_json(examples, OUT / "sample_examples" / "examples.json")
    write_manifest_csv(manifest_rows)
    write_prompt_guidance(templates)


if __name__ == "__main__":
    export()
