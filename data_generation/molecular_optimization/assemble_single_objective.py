"""Assemble single-objective molecular-optimization records from MMP pools."""

from __future__ import annotations

import argparse
from pathlib import Path

from data_generation.common.chem import molecular_weight, ring_count, tanimoto
from data_generation.common.io import balanced_sample, deduplicate, read_json, write_json

PROPERTY_KEYS = {
    "logp": "logp",
    "qed": "qed",
    "solubility": "solubility",
    "drd": "drd2",
    "gsk": "gsk",
    "jnk": "jnk3",
}

DEFAULT_TARGETS = {
    "logp": 120,
    "qed": 120,
    "solubility": 120,
    "drd": 120,
    "gsk": 120,
    "jnk": 120,
}


def load_pool(prop_dir: Path) -> list[dict]:
    rows = []
    for filename in ["small_mmp.json", "middle_mmp.json", "large_mmp.json", "raw_mmp.json", "final_mmp.json"]:
        path = prop_dir / filename
        if not path.exists():
            continue
        bucket = filename.replace("_mmp.json", "")
        for item in read_json(path):
            item = dict(item)
            item.setdefault("type", bucket)
            rows.append(item)
    return rows


def valid_improvement(item: dict, prop_key: str, threshold: float) -> bool:
    src = item.get(f"src_{prop_key}")
    tgt = item.get(f"tgt_{prop_key}")
    if src is None or tgt is None:
        return False
    try:
        return float(tgt) - float(src) >= threshold
    except Exception:
        return False


def enrich(item: dict, prop: str, prop_key: str, idx: int) -> dict:
    out = {k: v for k, v in item.items() if k not in {"difficulty", "difficulty_score"}}
    out["idx"] = idx
    out["task"] = "mol_opt"
    out["subtask"] = prop
    out["objective"] = prop
    if "tanimoto" not in out:
        out["tanimoto"] = tanimoto(out["src"], out["tgt"])
    if "src_mw" not in out:
        out["src_mw"] = molecular_weight(out["src"])
    if "src_rings" not in out:
        out["src_rings"] = ring_count(out["src"])
    out["delta"] = float(out[f"tgt_{prop_key}"]) - float(out[f"src_{prop_key}"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool-root", required=True, help="Directory with one subdirectory per property.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--property", action="append", choices=sorted(PROPERTY_KEYS), default=[])
    parser.add_argument("--target", type=int)
    parser.add_argument("--threshold", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    props = args.property or list(PROPERTY_KEYS)
    for prop in props:
        prop_key = PROPERTY_KEYS[prop]
        pool = load_pool(Path(args.pool_root) / prop)
        pool = [x for x in pool if x.get("src") and x.get("tgt")]
        if args.threshold > 0:
            pool = [x for x in pool if valid_improvement(x, prop_key, args.threshold)]
        pool = deduplicate(pool, lambda x: (x["src"], x["tgt"]))
        target = args.target or DEFAULT_TARGETS[prop]
        selected = balanced_sample(pool, target=target, key_fn=lambda x: x.get("type", "unknown"), seed=args.seed)
        records = [enrich(item, prop, prop_key, i) for i, item in enumerate(selected)]
        write_json(f"{args.output_root}/{prop}/final_mmp_v2.json", records)
        print(f"{prop}: wrote {len(records)} records")


if __name__ == "__main__":
    main()

