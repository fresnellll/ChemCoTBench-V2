#!/usr/bin/env python3
"""Smoke-test the anonymous evaluation path with a fake API client.

The test avoids network calls.  It builds evaluation prompts from anonymous raw
records, returns the released PRM/reference trace as if it came from a model
API, then runs parser + released Layer 1/2/3 Type-I checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import import_module
from pathlib import Path
from typing import Any


SOFTWARE_ROOT = Path(__file__).resolve().parents[1]
ROOT = SOFTWARE_ROOT.parent
sys.path = [path for path in sys.path if path != str(SOFTWARE_ROOT)]
sys.path.insert(0, str(SOFTWARE_ROOT))

from evaluation.core.released_data import resolve_data_root
from evaluation.core.config import resolve_module_name
from evaluation.core.sampler import run_sampling
from prm_generation.generate_prm import trace_to_raw_output
from scripts.validate_anonymous_release import (
    active_files,
    evaluate_layer1,
    evaluate_layer2,
    infer_aliases_from_trace,
    layer1_pass_rate,
    layer2_full_rate,
    normalize_records,
    parse_batch,
)

DATA_ROOT = resolve_data_root()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


class FakeReferenceAPI:
    """API-compatible client that returns each record's released reference trace."""

    def call(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        record = getattr(self, "_active_record", {})
        content = record.get("raw_output") or trace_to_raw_output(record)
        return {
            "success": bool(content),
            "content": content,
            "reasoning_content": "",
            "input_tokens": max(1, (len(system_prompt) + len(user_prompt)) // 4),
            "output_tokens": max(1, len(content) // 4),
            "model": "fake-reference-api",
            "finish_reason": "stop",
            "error": "" if content else "empty fake response",
        }


def prompt_builder(task: str, subtask: str):
    if task == "mol_opt":
        prompt_mod = import_module("evaluation.mol_opt.prompt")
        utils_mod = import_module("evaluation.mol_opt.utils")
        is_multi = subtask in utils_mod.MULTI_SUBTASK_TO_PROPS

        class MolOptPromptBuilder:
            system_prompt = prompt_mod.build_system_prompt(subtask, is_multi)

            @staticmethod
            def build_user_prompt(record: dict[str, Any]) -> str:
                return prompt_mod.build_user_prompt(subtask, is_multi, record)

        return MolOptPromptBuilder()

    if task == "mol_edit":
        mod = import_module("evaluation.mol_edit.prompt_builder")
    elif task == "mol_und":
        mod = import_module("evaluation.mol_und.prompt_builder")
    elif task == "rxn_pred":
        mod = import_module("evaluation.rxn_pred.prompt_builder")
    else:
        raise ValueError(task)
    return mod.PromptBuilder(subtask)


def _fake_sampling(records: list[dict[str, Any]], pb, save_path: Path) -> list[dict[str, Any]]:
    client = FakeReferenceAPI()
    first_prompt = {"value": ""}
    save_path.parent.mkdir(parents=True, exist_ok=True)

    def build_user_prompt(record: dict[str, Any]) -> str:
        client._active_record = record
        prompt = pb.build_user_prompt(record)
        if not first_prompt["value"]:
            first_prompt["value"] = prompt
        return prompt

    sampled = run_sampling(
        records=records,
        client=client,
        system_prompt=pb.system_prompt,
        build_user_prompt=build_user_prompt,
        save_path=save_path,
        delay=0,
        rerun_failed=False,
        id_field="anonymous_sample_id",
        max_workers=1,
    )
    for record in sampled:
        record["_smoke_system_prompt_nonempty"] = bool(
            pb.system_prompt(record) if callable(pb.system_prompt) else pb.system_prompt
        )
        record["_smoke_user_prompt_nonempty"] = bool(first_prompt["value"].strip())
    return sampled


def _type1_from_export(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for record in records:
        merged = dict(record)
        checks = merged.get("verifier_checks") or {}
        if isinstance(checks, dict):
            merged.update(checks)
        out.append(merged)
    return out


def evaluate_one(entry: dict[str, Any], n_samples: int, out_dir: Path) -> dict[str, Any]:
    task = entry["family"]
    subtask = entry["subtask"]
    raw_records = load_json(DATA_ROOT / entry["raw_file"])[:n_samples]
    process_records = load_json(DATA_ROOT / entry["process_file"])[:n_samples]
    records = normalize_records(raw_records, process_records)

    pb = prompt_builder(task, subtask)
    sampled = _fake_sampling(records, pb, out_dir / task / subtask / "sampled.json")
    parsed = parse_batch(task, subtask, sampled)
    parsed = [infer_aliases_from_trace(record) for record in parsed]
    layer1 = evaluate_layer1(task, subtask, parsed, fast=True)
    layer2 = evaluate_layer2(task, subtask, layer1)
    verified = _type1_from_export(layer2)

    row = {
        "task": task,
        "subtask": subtask,
        "n": len(verified),
        "prompt_nonempty": all(
            record.get("_smoke_system_prompt_nonempty")
            and record.get("_smoke_user_prompt_nonempty")
            for record in sampled
        ),
        "api_success_rate": round(sum(1 for record in sampled if record.get("api_success")) / len(sampled), 4),
        "parse_ok_rate": round(sum(1 for record in parsed if record.get("parse_ok")) / len(parsed), 4),
        "layer1_pass_rate": layer1_pass_rate(task, verified),
        "layer2_full_state_rate": layer2_full_rate(verified),
        "type1_all_pass_rate": round(sum(1 for record in verified if record.get("all_pass") is True) / len(verified), 4),
    }
    row["status"] = "PASS" if all(
        row[key] == 1.0
        for key in ("api_success_rate", "parse_ok_rate", "layer2_full_state_rate", "type1_all_pass_rate")
    ) and (task == "mol_opt" or row["layer1_pass_rate"] == 1.0) else "CHECK"
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Fake-API smoke test for anonymous evaluation code")
    parser.add_argument("--n-samples", type=int, default=1)
    parser.add_argument("--tasks", default="", help="Comma-separated task families")
    parser.add_argument("--subtasks", default="", help="Comma-separated subtasks")
    parser.add_argument("--output", type=Path, default=SOFTWARE_ROOT / "fake_api_smoke_report.json")
    parser.add_argument("--artifacts-dir", type=Path, default=SOFTWARE_ROOT / "fake_api_smoke_outputs")
    args = parser.parse_args()

    entries = active_files()
    if args.tasks:
        wanted_tasks = {x.strip() for x in args.tasks.split(",") if x.strip()}
        entries = [entry for entry in entries if entry["family"] in wanted_tasks]
    if args.subtasks:
        wanted_subtasks = {x.strip() for x in args.subtasks.split(",") if x.strip()}
        entries = [entry for entry in entries if entry["subtask"] in wanted_subtasks]

    rows = []
    for entry in entries:
        row = evaluate_one(entry, args.n_samples, args.artifacts_dir)
        rows.append(row)
        print(
            f"{row['status']} {row['task']}/{row['subtask']} n={row['n']} "
            f"API={row['api_success_rate']:.4f} parse={row['parse_ok_rate']:.4f} "
            f"L1={row['layer1_pass_rate']:.4f} L2={row['layer2_full_state_rate']:.4f} "
            f"TypeI={row['type1_all_pass_rate']:.4f}",
            flush=True,
        )

    report = {
        "purpose": "Logical API smoke test: fake API returns released reference traces; no network calls are made.",
        "n_samples_per_subtask": args.n_samples,
        "status_counts": dict(__import__("collections").Counter(row["status"] for row in rows)),
        "rows": rows,
    }
    save_json(args.output, report)
    print(f"Saved report to {args.output}")
    if any(row["status"] != "PASS" for row in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
