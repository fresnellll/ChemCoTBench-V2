"""Generate site-specific molecule-editing instructions for extracted edits."""

from __future__ import annotations

import argparse
import statistics
from itertools import combinations
from pathlib import Path

from data_generation.common.io import read_json, write_json
from data_generation.common.llm import call_chat_completion, parse_json_object

SYSTEM_PROMPT = """You are an expert organic chemist and molecular editor.
Given a source molecule, a target molecule, and reaction-derived structural-change
metadata, write one concise natural-language instruction that asks a model to
transform the source molecule into the target molecule.

Rules:
1. Describe the molecular edit, not reaction conditions.
2. Mention the local site when chemically identifiable.
3. Use one of three edit semantics: add, delete, or substitute.
4. Do not reveal the target SMILES.
5. Return JSON only."""

USER_TEMPLATE = """Source SMILES: {src}
Target SMILES: {tgt}
Reaction class: {reaction_class}
Edit type: {edit_type}
Leaving group: {leaving_group_smiles}
Incoming group: {incoming_group_smiles}
Source-target similarity: {source_tanimoto}
Heavy-atom difference: {heavy_atom_delta}

Return exactly:
{{
  "instruction": "<one sentence edit instruction>",
  "site": "<short site description>",
  "edit_type": "add|delete|substitute",
  "confidence": <0.0-1.0>
}}"""


def word_overlap(a: str, b: str) -> float:
    aw = set(a.lower().split())
    bw = set(b.lower().split())
    if not aw or not bw:
        return 0.0
    return len(aw & bw) / len(aw | bw)


def agreement(instructions: list[str]) -> float:
    if len(instructions) < 2:
        return 1.0
    return statistics.mean(word_overlap(a, b) for a, b in combinations(instructions, 2))


def generate_one(item: dict, args: argparse.Namespace) -> dict | None:
    prompt = USER_TEMPLATE.format(**item)
    generations = []
    for _ in range(args.n_rounds):
        raw = call_chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
            temperature=args.temperature,
        )
        parsed = parse_json_object(raw)
        if not parsed:
            continue
        if parsed.get("edit_type") != item["edit_type"]:
            continue
        if not parsed.get("instruction"):
            continue
        generations.append(parsed)

    if not generations:
        return None

    generations.sort(key=lambda row: float(row.get("confidence", 0.0)), reverse=True)
    instructions = [row["instruction"] for row in generations]
    best = generations[0]
    return {
        **item,
        "Instruction": best["instruction"],
        "site": best.get("site", ""),
        "instruction_agreement": round(agreement(instructions), 4),
        "mean_confidence": round(
            statistics.mean(float(row.get("confidence", 0.0)) for row in generations), 4
        ),
        "valid_rounds": len(generations),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--n-rounds", type=int, default=3)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    data = read_json(args.input_json)
    if args.limit:
        data = data[: args.limit]
    done = []
    if Path(args.output_json).exists():
        done = read_json(args.output_json)
    done_ids = {row["id"] for row in done}

    results = list(done)
    for item in data:
        if item["id"] in done_ids:
            continue
        generated = generate_one(item, args)
        if generated:
            results.append(generated)
            write_json(args.output_json, results)

    write_json(args.output_json, results)
    print(f"wrote {len(results)} instruction records to {args.output_json}")


if __name__ == "__main__":
    main()

