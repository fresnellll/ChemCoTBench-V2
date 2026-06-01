"""Generate, parse, and verify PRM-style formal-CoT records.

This script is intentionally small and provider-agnostic. It reuses the released
formal_cot prompt/parser/verifier modules and avoids historical sampler/client
code that contained experiment-specific details.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from importlib import import_module
from pathlib import Path
from typing import Any

from evaluation.api_client import create_client
from evaluation.config import ModelConfig
from evaluation.core.config import resolve_module_name


def load_json(path: Path) -> list[dict[str, Any]]:
    with open(path) as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise TypeError(f"Expected a JSON list in {path}, got {type(data).__name__}")
    return data


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


class SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def load_modules(task: str, subtask: str):
    module_name = resolve_module_name(task, subtask)
    base = f"formal_cot.{task}.{module_name}"
    return (
        import_module(f"{base}.prompt"),
        import_module(f"{base}.parser"),
        import_module(f"{base}.verifier"),
    )


def prompt_for_record(prompt_mod, task: str, subtask: str, record: dict[str, Any]) -> tuple[str, str]:
    """Return system and user prompts for one PRM reference-generation record."""
    keys = SafeFormatDict(record)

    if task == "mol_und" and subtask == "smiles_equivalent":
        source = record.get("source_subtask", "mutated")
        system_prompt = prompt_mod.system_prompt_for_source(source)
        template = prompt_mod.user_template_for_source(source)
        if source == "permutated":
            keys.setdefault("smiles_b", record.get("permutated", ""))
        else:
            keys.setdefault("smiles_b", record.get("mutated", ""))
        keys.setdefault("smiles_a", record.get("smiles", ""))
        return system_prompt, template.format_map(keys)

    system_prompt = prompt_mod.SYSTEM_PROMPT
    template = prompt_mod.USER_TEMPLATE
    return system_prompt, template.format_map(keys)


def trace_to_raw_output(record: dict[str, Any]) -> str:
    """Reconstruct raw unified-step output from an anonymous formal_cot_trace."""
    trace = record.get("formal_cot_trace")
    if not isinstance(trace, list):
        return ""
    lines = []
    for step in trace:
        step_text = step.get("step_text")
        if step_text:
            lines.append(str(step_text).strip())
        else:
            idx = step.get("step_index", "")
            name = step.get("step_name", "")
            natural = step.get("natural_language", "")
            formal = step.get("formal_ab", "")
            lines.append(f"Step {idx} [{name}]: {natural}\n  FORMAL: {formal}".strip())
    answer = (
        record.get("answer")
        or record.get("answer_smiles")
        or record.get("gt_answer")
        or record.get("gt_smiles")
        or record.get("outcome")
        or ""
    )
    if answer:
        lines.append(f"Answer: {answer}")
    return "\n\n".join(lines).strip()


def merge_raw_records(
    records: list[dict[str, Any]],
    raw_records: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge anonymous raw benchmark fields into process records."""
    if not raw_records:
        return records

    raw_by_id = {
        raw.get("anonymous_sample_id"): raw
        for raw in raw_records
        if raw.get("anonymous_sample_id")
    }
    merged = []
    for record in records:
        base = dict(raw_by_id.get(record.get("anonymous_sample_id"), {}))
        base.update(record)
        merged.append(base)
    return merged


def normalize_reference_record(record: dict[str, Any]) -> dict[str, Any]:
    """Fill compatibility aliases expected by historical parsers/verifiers."""
    out = dict(record)
    if out.get("raw_output"):
        out.setdefault("api_success", True)

    parsed_state = out.get("parsed_reference_state") or {}
    if isinstance(parsed_state, dict):
        for key, value in parsed_state.items():
            out.setdefault(key, value)

    if "src_smiles" not in out and out.get("source_smiles"):
        out["src_smiles"] = out["source_smiles"]
    if "src_smiles" not in out and out.get("indexed_smiles"):
        inferred = smiles_from_indexed_smiles(out["indexed_smiles"])
        if inferred:
            out["src_smiles"] = inferred
    if "smiles" not in out:
        inferred = first_formal_smiles(out.get("raw_output", ""))
        if inferred:
            out["smiles"] = inferred
    if "answer_smiles" not in out and out.get("gt_smiles"):
        out["answer_smiles"] = out["gt_smiles"]
    if "gt_product_smiles" not in out and out.get("answer_smiles"):
        out["gt_product_smiles"] = out["answer_smiles"]

    # MolOpt aliases used by the generic evaluation code.
    if "src" not in out and out.get("src_mol"):
        out["src"] = out["src_mol"]
    if "tgt" not in out and out.get("tgt_mol"):
        out["tgt"] = out["tgt_mol"]
    if "predicted_smiles" not in out and out.get("answer_smiles"):
        out["predicted_smiles"] = out["answer_smiles"]

    return out


def smiles_from_indexed_smiles(indexed_smiles: str) -> str:
    """Remove atom-map indices from an indexed SMILES string."""
    try:
        from rdkit import Chem

        mol = Chem.MolFromSmiles(indexed_smiles)
        if mol is None:
            return ""
        for atom in mol.GetAtoms():
            atom.SetAtomMapNum(0)
        return Chem.MolToSmiles(mol, isomericSmiles=True)
    except Exception:
        return ""


_FORMAL_SMILES_RE = re.compile(r'SMILES\("([^"]+)"\)')


def first_formal_smiles(raw_output: str) -> str:
    """Extract the first SMILES("...") value from a formal-CoT trace."""
    match = _FORMAL_SMILES_RE.search(raw_output or "")
    return match.group(1).strip() if match else ""


def sample_missing_outputs(
    records: list[dict[str, Any]],
    prompt_mod,
    task: str,
    subtask: str,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    if all(record.get("raw_output") for record in records):
        return records

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    if not args.model or not args.base_url or not api_key:
        raise ValueError(
            "Some records lack raw_output. Provide --model, --base-url, and --api-key "
            "or OPENAI_API_KEY to sample new PRM references."
        )

    cfg = ModelConfig.from_args(
        args.model,
        args.base_url,
        api_key,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout=args.timeout,
    )
    client = create_client(cfg)
    sampled = []
    for idx, record in enumerate(records):
        out = dict(record)
        if not out.get("raw_output"):
            system_prompt, user_prompt = prompt_for_record(prompt_mod, task, subtask, out)
            response = client.call(system_prompt, user_prompt)
            out.update(
                {
                    "raw_output": response.get("content", ""),
                    "api_success": response.get("success", False),
                    "input_tokens": response.get("input_tokens", 0),
                    "output_tokens": response.get("output_tokens", 0),
                    "model": response.get("model", args.model),
                    "finish_reason": response.get("finish_reason"),
                    "error": response.get("error", ""),
                }
            )
            print(f"[sample] {idx + 1}/{len(records)} success={out['api_success']}")
            if args.delay:
                time.sleep(args.delay)
        sampled.append(normalize_reference_record(out))
    return sampled


def parse_records(parser_mod, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if hasattr(parser_mod, "parse_batch"):
        return parser_mod.parse_batch(records)
    if hasattr(parser_mod, "parse_all"):
        return parser_mod.parse_all(records)
    parsed = []
    for record in records:
        if hasattr(parser_mod, "parse_one"):
            parsed.append(parser_mod.parse_one(record))
        elif hasattr(parser_mod, "parse_output"):
            out = dict(record)
            out.update(parser_mod.parse_output(record.get("raw_output", "")))
            parsed.append(out)
        elif hasattr(parser_mod, "parse_formal_output"):
            out = dict(record)
            out.update(parser_mod.parse_formal_output(record.get("raw_output", "")))
            parsed.append(out)
        else:
            raise RuntimeError(f"No supported parser entry point in {parser_mod.__name__}")
    return parsed


def verify_records(verifier_mod, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if hasattr(verifier_mod, "verify_batch"):
        return verifier_mod.verify_batch(records)
    if hasattr(verifier_mod, "verify_all"):
        return verifier_mod.verify_all(records)

    verified = []
    for record in records:
        if hasattr(verifier_mod, "verify_one"):
            verified.append(verifier_mod.verify_one(record))
        elif hasattr(verifier_mod, "verify_record"):
            verified.append(verifier_mod.verify_record(record))
        else:
            raise RuntimeError(f"No supported verifier entry point in {verifier_mod.__name__}")
    summary = {
        "n_total": len(verified),
        "n_parse_ok": sum(1 for rec in verified if rec.get("parse_ok")),
        "n_all_pass": sum(1 for rec in verified if rec.get("all_pass")),
    }
    return verified, summary


def build_clean_dataset(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep parseable records. Verifier failures remain visible for debugging."""
    return [record for record in records if record.get("parse_ok", True)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate/parse/verify PRM formal-CoT data")
    parser.add_argument("--task", required=True, choices=["mol_edit", "mol_und", "rxn_pred", "mol_opt"])
    parser.add_argument("--subtask", required=True)
    parser.add_argument("--input-json", required=True, type=Path)
    parser.add_argument(
        "--raw-json",
        type=Path,
        default=None,
        help="Optional anonymous raw_benchmark_data file to merge by anonymous_sample_id.",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--timeout", type=float, default=800.0)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument(
        "--from-process-trace",
        action="store_true",
        help="Build raw_output from anonymous formal_cot_trace before parsing.",
    )
    args = parser.parse_args()

    prompt_mod, parser_mod, verifier_mod = load_modules(args.task, args.subtask)
    records = load_json(args.input_json)
    raw_records = load_json(args.raw_json) if args.raw_json else None
    records = merge_raw_records(records, raw_records)
    if args.from_process_trace:
        records = [
            {**record, "raw_output": record.get("raw_output") or trace_to_raw_output(record)}
            for record in records
        ]
    records = [normalize_reference_record(record) for record in records]

    sampled = sample_missing_outputs(records, prompt_mod, args.task, args.subtask, args)
    parsed = parse_records(parser_mod, sampled)
    verified, summary = verify_records(verifier_mod, parsed)
    clean = build_clean_dataset(verified)

    save_json(args.output_dir / "sampled.json", sampled)
    save_json(args.output_dir / "parsed.json", parsed)
    save_json(args.output_dir / "verified.json", verified)
    save_json(args.output_dir / "clean_dataset.json", clean)
    save_json(args.output_dir / "summary.json", summary | {"n_clean": len(clean)})

    print(json.dumps(summary | {"n_clean": len(clean)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
