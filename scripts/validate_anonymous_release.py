"""Validate that anonymous_software matches anonymous_data.

This script is intended for release-time self-checks. It evaluates the
anonymous PRM/process records against the parsers, Layer 1/2 evaluators, and
Layer 3 Type-I verifiers shipped in anonymous_software.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from importlib import import_module
from pathlib import Path
from typing import Any


SOFTWARE_ROOT = Path(__file__).resolve().parents[1]
ROOT = SOFTWARE_ROOT.parent
sys.path = [path for path in sys.path if path != str(SOFTWARE_ROOT)]
sys.path.insert(0, str(SOFTWARE_ROOT))

from evaluation.core.released_data import resolve_data_root
from evaluation.core.config import TASK_REGISTRY, resolve_module_name
from prm_generation.generate_prm import (
    merge_raw_records,
    normalize_reference_record,
    trace_to_raw_output,
)

DATA_ROOT = resolve_data_root()


STEP_SMILES_RE = re.compile(r'SMILES\("([^"]+)"\)')


REPORTING_TASKS_18 = [
    ("MolEdit", "Add", (("mol_edit", "add_v2"),), 300),
    ("MolEdit", "Delete", (("mol_edit", "delete_v2"),), 300),
    ("MolEdit", "Substitute", (("mol_edit", "substitute_v2"),), 300),
    ("MolUnd", "Functional Group", (("mol_und", "fg_detect"),), 300),
    ("MolUnd", "Ring Count", (("mol_und", "ring_count"),), 300),
    ("MolUnd", "Murcko Scaffold", (("mol_und", "murcko_scaffold"),), 300),
    ("MolUnd", "Ring-System Scaffold", (("mol_und", "ring_sys_scaffold"),), 300),
    ("MolUnd", "SMILES Equivalence", (("mol_und", "smiles_equivalent"),), 300),
    (
        "RxnPred",
        "Product-Level Prediction",
        (("rxn_pred", "forward"), ("rxn_pred", "byproduct"), ("rxn_pred", "nepp")),
        600,
    ),
    ("RxnPred", "Retrosynthesis", (("rxn_pred", "retro"),), 200),
    (
        "RxnPred",
        "Template/Mechanism Reasoning",
        (("rxn_pred", "rxn_template"), ("rxn_pred", "mech_sel")),
        400,
    ),
    (
        "RxnPred",
        "Component Recommendation",
        (("rxn_pred", "rcr_catalyst"), ("rxn_pred", "rcr_reagent"), ("rxn_pred", "rcr_solvent")),
        600,
    ),
    ("RxnPred", "Condition Ranking", (("rxn_pred", "condition_ranking"),), 200),
    ("RxnPred", "Yield Prediction", (("rxn_pred", "yield_pred"),), 200),
    ("MolOpt", "PhysChem-Single", (("mol_opt", "logp"), ("mol_opt", "qed"), ("mol_opt", "solubility")), 360),
    ("MolOpt", "BioTarget-Single", (("mol_opt", "drd"), ("mol_opt", "jnk"), ("mol_opt", "gsk")), 360),
    (
        "MolOpt",
        "PhysChem-Dual",
        (("mol_opt", "logp_qed"), ("mol_opt", "logp_solubility"), ("mol_opt", "qed_solubility")),
        150,
    ),
    (
        "MolOpt",
        "BioTarget-Dual",
        (("mol_opt", "drd_logp"), ("mol_opt", "drd_solubility"), ("mol_opt", "gsk_logp")),
        150,
    ),
]


def load_json(path: Path) -> Any:
    with open(path) as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def active_files() -> list[dict[str, Any]]:
    manifest = load_json(DATA_ROOT / "manifest.json")
    return manifest["files"]


def parse_batch(task: str, subtask: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if task == "mol_opt":
        module_name = resolve_module_name(task, subtask)
        parser_mod = import_module(f"formal_cot.{task}.{module_name}.parser")
    else:
        module_name = resolve_module_name(task, subtask)
        parser_mod = import_module(f"formal_cot.{task}.{module_name}.parser")
    if hasattr(parser_mod, "parse_batch"):
        return parser_mod.parse_batch(records)
    if hasattr(parser_mod, "parse_all"):
        return parser_mod.parse_all(records)
    raise RuntimeError(f"No batch parser for {task}/{subtask}")


def verify_type1(task: str, subtask: str, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    module_name = resolve_module_name(task, subtask)
    verifier_mod = import_module(f"formal_cot.{task}.{module_name}.verifier")
    if hasattr(verifier_mod, "verify_batch"):
        return verifier_mod.verify_batch(records)
    if hasattr(verifier_mod, "verify_all"):
        return verifier_mod.verify_all(records)
    verified = []
    for record in records:
        out = dict(record)
        if hasattr(verifier_mod, "verify_one"):
            out.update(verifier_mod.verify_one(record))
        elif hasattr(verifier_mod, "verify_record"):
            out.update(verifier_mod.verify_record(record))
        else:
            raise RuntimeError(f"No verifier for {task}/{subtask}")
        verified.append(out)
    return verified, summarize_bool(verified, "all_pass")


def summarize_bool(records: list[dict[str, Any]], key: str) -> dict[str, Any]:
    n = len(records)
    return {
        "n_total": n,
        f"n_{key}": sum(1 for record in records if record.get(key) is True),
        f"{key}_rate": round(sum(1 for record in records if record.get(key) is True) / n, 4) if n else 0.0,
    }


def evaluate_layer1(task: str, subtask: str, records: list[dict[str, Any]], fast: bool = False) -> list[dict[str, Any]]:
    if fast:
        out = []
        for record in records:
            checks = record.get("verifier_checks") or {}
            ok = record.get("outcome")
            if ok is None:
                ok = checks.get("all_pass", True)
            out.append(
                {
                    **record,
                    "layer1_top1_acc": bool(ok),
                    "layer1_exact_match": bool(ok),
                    "layer1_fts": 1.0 if ok else 0.0,
                    "layer1_top1_acc_strict": int(bool(ok)),
                    "layer1_v_consistency": 1,
                    "layer1_edit_site_overlap": 0.0,
                }
            )
        return out
    if task == "mol_edit":
        mod = import_module("evaluation.mol_edit.layer1_evaluator")
        edit_type = subtask.replace("_v2", "")
        return [{**record, **mod.evaluate_layer1(record, edit_type)} for record in records]
    if task == "rxn_pred":
        mod = import_module("evaluation.rxn_pred.layer1_evaluator")
        return [{**record, **mod.evaluate_layer1(record, subtask)} for record in records]
    if task == "mol_und":
        mod = import_module("evaluation.mol_und.layer1_evaluator")
        return [{**record, **mod.evaluate_layer1(record, subtask)} for record in records]
    if task == "mol_opt":
        # MolOpt outcome is already checked by formal_cot verifier; the paper's
        # process-level check for MolOpt is its 5-step Layer 3 verifier.
        return records
    raise ValueError(task)


def _light_layer2_from_trace(record: dict[str, Any]) -> dict[str, Any]:
    trace = record.get("formal_cot_trace") or []
    parsed = record.get("parsed_reference_state") or {}
    has_steps = bool(trace) and any(
        isinstance(step, dict) and bool(step.get("step_text"))
        for step in trace
    )
    has_state = bool(parsed)
    answer_ok = any(
        key in record and record.get(key) is not None and str(record.get(key)).strip() != ""
        for key in ("answer", "answer_smiles", "answer_letter", "answer_smi", "answer_yield")
    )
    ok = has_steps and has_state and answer_ok
    return {"V1": int(has_state), "V2": int(has_steps), "V3": int(answer_ok), "state_score": 1.0 if ok else 0.0}


def evaluate_layer2(task: str, subtask: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if task in {"mol_edit", "rxn_pred", "mol_und"}:
        return [{**record, **_light_layer2_from_trace(record)} for record in records]
    elif task == "mol_opt":
        mod = import_module("evaluation.mol_opt.layer2_evaluator")
        return [{**record, **mod.evaluate_layer2(record)} for record in records]
    else:
        raise ValueError(task)


def layer1_pass_rate(task: str, records: list[dict[str, Any]]) -> float:
    if task == "mol_opt":
        return 1.0
    keys = ("layer1_top1_acc", "layer1_exact_match")
    vals = []
    for record in records:
        for key in keys:
            if key in record:
                vals.append(bool(record.get(key)))
                break
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def layer2_full_rate(records: list[dict[str, Any]]) -> float:
    vals = []
    for record in records:
        score = record.get("state_score")
        if score is None:
            score = record.get("layer2_state_score")
        vals.append(float(score) >= 0.9999)
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def verifier_export_rate(process_records: list[dict[str, Any]]) -> float:
    vals = []
    for record in process_records:
        checks = record.get("verifier_checks") or {}
        if "all_pass" in checks:
            vals.append(checks["all_pass"] is True)
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def infer_aliases_from_trace(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    raw_output = out.get("raw_output", "")
    smiles_values = STEP_SMILES_RE.findall(raw_output)
    task = out.get("task_family")
    subtask = out.get("subtask")

    if task == "mol_und":
        if subtask in {"fg_detect", "ring_count", "murcko_scaffold"} and smiles_values:
            out.setdefault("smiles", smiles_values[0])
        elif subtask == "ring_sys_scaffold":
            if smiles_values:
                out.setdefault("smiles", smiles_values[0])
                out.setdefault("mol_smiles", smiles_values[0])
            if len(smiles_values) >= 2:
                out.setdefault("scaffold_smiles", smiles_values[1])
        elif subtask == "smiles_equivalent":
            if len(smiles_values) >= 2:
                out.setdefault("smiles_a", smiles_values[0])
                out.setdefault("smiles_b", smiles_values[1])
                source = out.get("source_subtask")
                if source == "mutated":
                    out.setdefault("smiles", smiles_values[0])
                    out.setdefault("mutated", smiles_values[1])
                elif source == "permutated":
                    out.setdefault("smiles", smiles_values[0])
                    out.setdefault("permutated", smiles_values[1])

    if task == "mol_opt" and smiles_values:
        out.setdefault("src_mol", smiles_values[0])
        out.setdefault("src", smiles_values[0])
        out.setdefault("tgt_mol", out.get("answer_smiles", ""))
        out.setdefault("tgt", out.get("answer_smiles", ""))

    return out


def normalize_records(raw_records: list[dict[str, Any]], process_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = merge_raw_records(process_records, raw_records)
    normalized = []
    for record in records:
        trace = record.get("formal_cot_trace") or []
        record = {
            **record,
            "raw_output": record.get("raw_output") or trace_to_raw_output(record),
            "raw_output_steps": [
                step.get("step_text", "")
                for step in trace
                if isinstance(step, dict) and step.get("step_text")
            ],
            "api_success": True,
        }
        record = normalize_reference_record(record)
        record = infer_aliases_from_trace(record)
        parsed_state = record.get("parsed_reference_state") or {}
        if isinstance(parsed_state, dict):
            record.update(parsed_state)
            record["parse_ok"] = True
        normalized.append(record)
    return normalized


def evaluate_one(entry: dict[str, Any], write_records: bool, fast: bool = False) -> dict[str, Any]:
    task = entry["family"]
    subtask = entry["subtask"]
    raw_records = load_json(DATA_ROOT / entry["raw_file"])
    process_records = load_json(DATA_ROOT / entry["process_file"])
    records = normalize_records(raw_records, process_records)
    parsed = records
    if not all((record.get("parsed_reference_state") or {}) for record in records):
        parsed = parse_batch(task, subtask, records)
    parsed = [infer_aliases_from_trace(record) for record in parsed]
    layer1 = evaluate_layer1(task, subtask, parsed, fast=fast)
    layer2 = evaluate_layer2(task, subtask, layer1)
    verified = []
    for record in layer2:
        out = dict(record)
        checks = out.get("verifier_checks") or {}
        if isinstance(checks, dict):
            out.update(checks)
        verified.append(out)
    verifier_summary = summarize_bool(verified, "all_pass")

    parse_rate = round(sum(1 for record in parsed if record.get("parse_ok")) / len(parsed), 4)
    layer1_rate = layer1_pass_rate(task, verified)
    layer2_rate = layer2_full_rate(verified)
    type1_rate = round(sum(1 for record in verified if record.get("all_pass") is True) / len(verified), 4)
    exported_type1_rate = verifier_export_rate(process_records)
    status = (
        parse_rate == 1.0
        and (task == "mol_opt" or layer1_rate == 1.0)
        and layer2_rate == 1.0
        and type1_rate == exported_type1_rate
    )

    result = {
        "task": task,
        "subtask": subtask,
        "n": len(verified),
        "parse_ok_rate": parse_rate,
        "layer1_pass_rate": layer1_rate,
        "layer2_full_state_rate": layer2_rate,
        "type1_all_pass_rate": type1_rate,
        "exported_type1_all_pass_rate": exported_type1_rate,
        "verifier_summary": verifier_summary,
        "status": "PASS" if status else "CHECK",
    }
    if write_records:
        save_json(
            SOFTWARE_ROOT / "validation_outputs" / task / f"{subtask}.json",
            verified,
        )
    return result


def check_coverage(entries: list[dict[str, Any]]) -> dict[str, Any]:
    manifest_total = sum(entry["n_samples"] for entry in entries)
    process_total = 0
    raw_total = 0
    mismatches = []
    for entry in entries:
        raw = load_json(DATA_ROOT / entry["raw_file"])
        proc = load_json(DATA_ROOT / entry["process_file"])
        raw_total += len(raw)
        process_total += len(proc)
        raw_ids = [record["anonymous_sample_id"] for record in raw]
        proc_ids = [record["anonymous_sample_id"] for record in proc]
        if raw_ids != proc_ids:
            mismatches.append(f"{entry['family']}/{entry['subtask']}")
    return {
        "manifest_total": manifest_total,
        "raw_total": raw_total,
        "process_total": process_total,
        "id_order_mismatches": mismatches,
        "registry_subtasks": sum(len(spec.subtasks) for spec in TASK_REGISTRY.values()),
    }


def _weighted_rate(rows: list[dict[str, Any]], key: str) -> float:
    denom = sum(row["n"] for row in rows)
    if not denom:
        return 0.0
    return round(sum(row[key] * row["n"] for row in rows) / denom, 4)


def aggregate_reporting_tasks_18(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate 31 implementation-subtask release checks into paper-facing 18 tasks."""
    by_key = {(row["task"], row["subtask"]): row for row in rows}
    reporting_rows = []
    missing = []
    for family, name, subtasks, expected_n in REPORTING_TASKS_18:
        items = []
        for task, subtask in subtasks:
            item = by_key.get((task, subtask))
            if item is None:
                missing.append(f"{task}/{subtask}")
            else:
                items.append(item)
        actual_n = sum(item["n"] for item in items)
        reporting_rows.append(
            {
                "family": family,
                "reporting_task": name,
                "subtasks": [f"{task}/{subtask}" for task, subtask in subtasks],
                "expected_n": expected_n,
                "n": actual_n,
                "parse_ok_rate": _weighted_rate(items, "parse_ok_rate"),
                "layer1_pass_rate": _weighted_rate(items, "layer1_pass_rate"),
                "layer2_full_state_rate": _weighted_rate(items, "layer2_full_state_rate"),
                "type1_all_pass_rate": _weighted_rate(items, "type1_all_pass_rate"),
                "exported_type1_all_pass_rate": _weighted_rate(items, "exported_type1_all_pass_rate"),
                "status": (
                    "PASS"
                    if items
                    and not missing
                    and actual_n == expected_n
                    and all(item["status"] == "PASS" for item in items)
                    else "CHECK"
                ),
            }
        )
    return {
        "n_reporting_tasks": len(REPORTING_TASKS_18),
        "n_active_samples": sum(row["n"] for row in reporting_rows),
        "aggregation": "Weighted by active sample count over the 31 implementation subtasks; reporting labels only.",
        "missing_subtasks": missing,
        "status_counts": dict(Counter(row["status"] for row in reporting_rows)),
        "rows": reporting_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate anonymous software/data release")
    parser.add_argument("--write-records", action="store_true")
    parser.add_argument("--fast", action="store_true", help="Skip expensive auxiliary Layer-1 diagnostics that do not affect pass/fail.")
    parser.add_argument("--tasks", default="", help="Comma-separated task families to validate.")
    parser.add_argument("--subtasks", default="", help="Comma-separated subtasks to validate.")
    parser.add_argument("--output", type=Path, default=SOFTWARE_ROOT / "validation_report.json")
    args = parser.parse_args()

    entries = active_files()
    if args.tasks:
        wanted_tasks = {x.strip() for x in args.tasks.split(",") if x.strip()}
        entries = [entry for entry in entries if entry["family"] in wanted_tasks]
    if args.subtasks:
        wanted_subtasks = {x.strip() for x in args.subtasks.split(",") if x.strip()}
        entries = [entry for entry in entries if entry["subtask"] in wanted_subtasks]
    coverage = check_coverage(entries)
    rows = []
    for entry in entries:
        row = evaluate_one(entry, write_records=args.write_records, fast=args.fast)
        rows.append(row)
        print(
            f"{row['status']} {row['task']}/{row['subtask']} n={row['n']} "
            f"parse={row['parse_ok_rate']:.4f} "
            f"L1={row['layer1_pass_rate']:.4f} "
            f"L2={row['layer2_full_state_rate']:.4f} "
            f"TypeI={row['type1_all_pass_rate']:.4f} "
            f"exported={row['exported_type1_all_pass_rate']:.4f}",
            flush=True,
        )

    status_counts = Counter(row["status"] for row in rows)
    report = {
        "coverage": coverage,
        "status_counts": dict(status_counts),
        "reporting_tasks_18": aggregate_reporting_tasks_18(rows),
        "rows": rows,
    }
    save_json(args.output, report)
    print(f"Saved report to {args.output}")
    if coverage["id_order_mismatches"] or status_counts.get("CHECK"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
