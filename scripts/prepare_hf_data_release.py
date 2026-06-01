#!/usr/bin/env python3
"""Prepare the public Hugging Face data package.

The ARR/review export kept a few internal metadata fields that are not part of
the paper-facing benchmark, most notably difficulty labels and patch/debug
bookkeeping. This script creates a non-destructive cleaned copy for public data
release while preserving the fields required by the released evaluation code.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


SOFTWARE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SOFTWARE_ROOT.parent

DROP_KEYS = {
    "api_success",
    "completion_tokens",
    "difficulty",
    "difficulty_basis",
    "difficulty_bucket",
    "difficulty_label",
    "difficulty_primary_model",
    "difficulty_score",
    "elapsed_s",
    "empirical_difficulty",
    "error",
    "finish_reason",
    "parse_errors",
    "parse_note",
    "parse_ok",
    "patch_autofix_repairs",
    "patch_outcome_fixed",
    "patch_outcome_method",
    "patch_phase",
    "patch_request_attempt",
    "patch_resampled",
    "patch_resampled_from",
    "patch_tag",
    "patch_timestamp_utc",
    "prompt_tokens",
    "raw_output",
    "raw_output_steps",
    "reasoning_tokens",
    "text_tokens",
    "thinking_tokens",
    "total_completion_tokens",
    "total_tokens",
    "verify_msgs",
    "verify_note",
    "verify_skip_reason",
}

DATASET_CARD = """---
license: mit
task_categories:
- text-generation
- question-answering
language:
- en
tags:
- chemistry
- chemical-reasoning
- chain-of-thought
- process-supervision
- benchmark
pretty_name: ChemCoTBench-V2
size_categories:
- 1K<n<10K
---

# ChemCoTBench-V2 Data

This repository contains the public 5,620-sample active benchmark for
ChemCoTBench-V2, "From Answers to States: Verifiable Process-Level Evaluation
of Chemical Reasoning in Large Language Models".

ChemCoTBench-V2 evaluates both final-answer correctness and process-level
chemical reasoning. Each benchmark item pairs model-facing inputs with a
verified formal reasoning trace used by the released evaluation code.

## Dataset Structure

- `raw_benchmark_data/`: model-facing benchmark inputs and final-answer labels.
- `process_evaluation_data/`: verified process references, including
  `formal_cot_trace`, `parsed_reference_state`, and `verifier_checks`.
- `task_schema/`: task counts and field inventory after public-release cleanup.
- `formal_templates/`: structured step-field schemas for each subtask.
- `prompt_templates/`: evaluation-facing prompt format guidance.
- `verifier_rule_descriptions/`: verifier names and task-level rule notes.
- `sample_examples/`: small examples linking raw inputs with process references.
- `evaluation_split_metadata/`: manifest and split/count metadata.

## Benchmark Size

The active benchmark contains 5,620 samples across four task families:

| Family | Samples | Scope |
| --- | ---: | --- |
| MolEdit | 900 | Addition, deletion, and substitution edits |
| MolUnd | 1,500 | Functional groups, rings, scaffolds, and SMILES equivalence |
| RxnPred | 2,200 | Product prediction, retrosynthesis, mechanism/template reasoning, components, conditions, and yield |
| MolOpt | 1,020 | Single- and dual-objective molecular optimization |

These 31 implementation subtasks are aggregated into 18 reporting tasks in the
paper. The aggregation is presentation-level only and does not change the
benchmark files.

## Record Pairing

Every raw record has a corresponding process-level record with the same
`anonymous_sample_id`, in the same order. The field name is kept for
compatibility with the released evaluation code; it functions as a stable public
sample identifier.

The canonical file list and sample counts are stored in `manifest.json`.

## Use With the Evaluation Code

Clone the ChemCoTBench-V2 code release, install the `chemcot` environment, and
point the evaluator to this data directory:

```bash
export CHEMCOT_DATA_DIR=/path/to/ChemCoTBench-V2-data
python scripts/validate_release.py --fast
```

The evaluation loader requires `manifest.json`, the raw benchmark files, the
process evaluation files, and the `anonymous_sample_id` pairing. Difficulty
labels and internal patch/debug metadata are intentionally removed from this
public package because they are not part of the paper-facing benchmark.

## Citation

Please cite the ChemCoTBench-V2 paper if you use this dataset.
"""

PROMPT_README = """# Prompt Templates

This directory contains evaluation-facing prompt format summaries, not the
original reference-construction prompts. Ground-truth-injection lines, model
names, examples with sample-specific answers, and API metadata are not included
in this public data package.

For each subtask, use the fields in `../formal_templates/` to request the
required structured trace. The user prompt should contain only the input fields
from `../raw_benchmark_data/` and should not include the final answer or the
process reference states from `../process_evaluation_data/`.
"""


def clean_value(value: Any, dropped: Counter[str]) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in DROP_KEYS or key.startswith("patch_"):
                dropped[key] += 1
                continue
            out[key] = clean_value(item, dropped)
        return out
    if isinstance(value, list):
        return [clean_value(item, dropped) for item in value]
    return value


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def public_manifest(data: Any) -> Any:
    if isinstance(data, dict) and data.get("dataset_name"):
        data = dict(data)
        data["dataset_name"] = "ChemCoTBench-V2 active benchmark"
    return data


def process_json(src: Path, dst: Path, dropped: Counter[str]) -> None:
    data = clean_value(load_json(src), dropped)
    if src.name in {"manifest.json", "splits.json"}:
        data = public_manifest(data)
    save_json(dst, data)


def process_text(src: Path, dst: Path) -> None:
    if src.name == "README.md" and src.parent.name == "anonymous_data":
        text = DATASET_CARD
    elif src.name == "README.md" and src.parent.name == "prompt_templates":
        text = PROMPT_README
    else:
        text = src.read_text(encoding="utf-8")
        text = text.replace("anonymous active benchmark", "active benchmark")
        text = text.replace("Anonymous Data Package", "Data Package")
        text = text.replace("anonymous data package", "public data package")
        text = text.replace("anonymous 5,620-sample", "public 5,620-sample")
        text = text.replace("submission draft", "paper")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text.rstrip() + "\n", encoding="utf-8")


def copy_clean_tree(source: Path, output: Path) -> Counter[str]:
    dropped: Counter[str] = Counter()
    for src in sorted(source.rglob("*")):
        rel = src.relative_to(source)
        dst = output / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if src.suffix == ".json":
            process_json(src, dst, dropped)
        elif src.suffix in {".md", ".txt", ".csv"}:
            process_text(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return dropped


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a cleaned ChemCoTBench-V2 Hugging Face data package.")
    parser.add_argument("--source", type=Path, default=PROJECT_ROOT / "anonymous_data")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "hf_data_release")
    parser.add_argument("--force", action="store_true", help="Overwrite the output directory if it already exists.")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    if not (source / "manifest.json").exists():
        raise SystemExit(f"Source does not look like a ChemCoTBench-V2 data package: {source}")
    if output.exists():
        if not args.force:
            raise SystemExit(f"Output already exists: {output}. Use --force to overwrite it.")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    dropped = copy_clean_tree(source, output)
    print(f"Wrote cleaned data package to {output}")
    print("Dropped fields:")
    for key, count in sorted(dropped.items()):
        print(f"  {key}: {count}")


if __name__ == "__main__":
    main()
