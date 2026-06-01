"""Remove construction-only fields from released benchmark records."""

from __future__ import annotations

import argparse

from data_generation.common.io import read_json, write_json

DEFAULT_DROP_FIELDS = {
    "difficulty",
    "difficulty_score",
    "difficulty_chemical",
    "empirical_difficulty",
    "selection_correct_count",
    "selection_wrong_count",
    "selection_model_exact_match",
}


def strip_fields(obj, drop_fields: set[str]):
    if isinstance(obj, list):
        return [strip_fields(x, drop_fields) for x in obj]
    if isinstance(obj, dict):
        return {k: strip_fields(v, drop_fields) for k, v in obj.items() if k not in drop_fields}
    return obj


def main() -> None:
    parser = argparse.ArgumentParser(description="Strip construction-only fields from JSON records.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--drop-field", action="append", default=[])
    args = parser.parse_args()

    drop = DEFAULT_DROP_FIELDS | set(args.drop_field)
    write_json(args.output, strip_fields(read_json(args.input), drop))


if __name__ == "__main__":
    main()

